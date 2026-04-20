from __future__ import annotations

import logging
import random

from board import consts
from combat import effective_ac
from combat.hp_engine import apply_damage as hp_apply_damage
from combat.degree_of_success import is_critical_success, natural_shift_from_roll, resolve_outcome
from damage_types import DamageType
from statuses.race.dwarf.feats.vengeful_hatred import grant_vengeful_hatred_revenge

from ..base import EventContext, EventResult, GameEvent
from ..attack.attack_base import check_concealed
from ..targeting import is_target_blocked_by_tags

logger = logging.getLogger(__name__)


class BasicEnemyMeleeAttackEvent(GameEvent):
    """Wspólna logika dla prostych wrogich ataków w zwarciu."""

    name = "enemy_attack_melee_base"
    default_tags = ["attack_melee", "enemy"]
    consumes_action = True
    available_in_exploration = False

    # konfiguracja per broń / przeciwnik
    weapon_label: str = "atak wręcz"
    action_id_base: str = "enemy_attack_melee"
    damage_die_sides: int = 6
    damage_type: str = DamageType.SLASHING.value
    attack_bonus_attr: str = "attack_bonus"
    strength_attr: str = "strength"

    def execute(self, ctx: EventContext) -> EventResult:
        enemy = ctx.actor
        if enemy is None or getattr(enemy, "position", None) is None:
            return EventResult(success=False, consumed_action=False, message="Wróg nie jest na planszy.")

        game = ctx.game
        board = game.board
        conn = game.conn
        enemy_pos = enemy.position

        targets = self._adjacent_heroes(game, enemy_pos)
        tags = self._effective_tags(ctx)
        targets = [p for p in targets if not is_target_blocked_by_tags(board.occupant_at(p), tags)]
        if not targets:
            return EventResult(success=False, consumed_action=False, message="Brak bohaterów w zasięgu.")

        target_pos = self._pick_target(conn, targets)
        if target_pos is None:
            return EventResult(success=False, consumed_action=False, message="Atak wroga anulowany.")

        hero = board.occupant_at(target_pos)
        if hero not in game.heroes:
            return EventResult(success=False, consumed_action=True, message="Wybrano cel niebędący bohaterem.")

        if not check_concealed(ctx, hero):
            game.events.safe_emit_action(
                actor=enemy,
                action_id=f"{self.action_id_base}_concealed_miss",
                action_tags=self._effective_tags(ctx),
                target=hero,
                target_pos=target_pos,
            )
            return EventResult(success=True, consumed_action=True, message="Atak wroga chybia (concealed).")

        attack_bonus = getattr(enemy, self.attack_bonus_attr, 0)
        bonus_mixin = getattr(enemy, "compute_modifier", None)
        extra_mod = 0
        if callable(bonus_mixin):
            try:
                extra_mod = bonus_mixin("attack_melee", target=hero)
            except Exception:
                extra_mod = 0
        if self._consume_familiar_distract(enemy):
            extra_mod -= 1
        natural_roll = random.randint(1, 20)
        roll = natural_roll + attack_bonus + extra_mod

        target_ac = effective_ac(hero)
        outcome = resolve_outcome(roll, target_ac, natural_shift=natural_shift_from_roll(natural_roll))
        critical_hit = is_critical_success(outcome)
        clumsy_note = None
        try:
            from statuses.clumsy import clumsy_ac_prompt_note

            clumsy_note = clumsy_ac_prompt_note(hero)
        except Exception:
            clumsy_note = None

        prompt = (
            f"{getattr(enemy, 'name', 'wróg')} {self.weapon_label} na {target_pos}: "
            f"r={roll} (1d20={natural_roll} + {attack_bonus} {'+' if extra_mod >=0 else ''}{extra_mod}). "
            f"AC celu: {target_ac}. "
            "Potwierdź trafienie: ACCEPT/DECLINE"
        )
        if clumsy_note:
            prompt = f"{prompt} {clumsy_note}"
        ui = getattr(game, "ui", None)
        response = "ACCEPT"
        if ui is not None and hasattr(ui, "prompt_choice"):
            try:
                response = ui.prompt_choice(prompt, choices=["ACCEPT", "DECLINE"], source=self.action_id_base)
            except Exception:
                response = "ACCEPT"
        if str(response or "").strip().upper() != "ACCEPT":
            logger.info("Atak wroga odrzucony.")
            game.ui_log("Atak wroga odrzucony.")
            return EventResult(success=True, consumed_action=True, message="Atak odrzucony.")

        damage = self.roll_damage(enemy)
        hp_dealt = self.apply_damage(hero, damage)
        if critical_hit and hp_dealt > 0:
            try:
                grant_vengeful_hatred_revenge(hero, enemy, rounds=10)
            except Exception:
                pass

        dmg_msg = (
            f"{getattr(enemy, 'name', 'wróg')} zadaje {damage} obrażeń "
            f"(1d{self.damage_die_sides} + {getattr(enemy, self.strength_attr, 0)}). "
            f"Rany bohatera: {getattr(hero, 'wounds', '?')}."
        )
        logger.info(dmg_msg)
        game.ui_log(dmg_msg)
        try:
            game.ui_hero(hero)
        except Exception:
            pass

        game.events.safe_emit_action(
            actor=enemy,
            action_id=self.action_id_base,
            action_tags=self._effective_tags(ctx),
            target=hero,
            target_pos=target_pos,
            damage=damage,
        )

        return EventResult(success=True, consumed_action=True, message="Atak wroga wykonany.")

    # --- helpers ---
    @staticmethod
    def _consume_familiar_distract(enemy) -> bool:
        has_status = getattr(enemy, "has_status", None)
        if callable(has_status):
            active = has_status("familiar_distract")
        else:
            active = False
            for status in getattr(enemy, "statuses", []) or []:
                if getattr(status, "id", None) == "familiar_distract" or status == "familiar_distract":
                    active = True
                    break
        if not active:
            return False
        try:
            enemy.remove_status("familiar_distract")
        except Exception:
            pass
        return True

    @staticmethod
    def _adjacent_heroes(game, pos):
        board = game.board
        neighbors = board.get_neighbors(pos, include_position=False, diagonal=True)
        return [p for p in neighbors if board.occupant_at(p) in game.heroes]

    @staticmethod
    def _pick_target(conn, targets):
        conn.set_leds(targets, consts.MOVE_FIELD_RGB)
        try:
            return conn.scan_board(targets)
        finally:
            try:
                conn.leds_off()
            except Exception:
                pass

    def roll_damage(self, enemy) -> int:
        strength = getattr(enemy, self.strength_attr, 0)
        return random.randint(1, self.damage_die_sides) + strength

    def apply_damage(self, hero, damage: int) -> int:
        # Minimalny zapis: zwiększ rany; jeśli istnieje metoda apply_damage, użyj jej.
        before_hp = None
        current_hp = getattr(hero, "current_hp", None)
        if callable(current_hp):
            try:
                before_hp = int(current_hp())
            except Exception:
                before_hp = None
        apply = getattr(hero, "apply_damage", None)
        if callable(apply):
            try:
                apply(damage, self.damage_type)
                if before_hp is not None and callable(current_hp):
                    try:
                        after_hp = int(current_hp())
                        return max(0, before_hp - after_hp)
                    except Exception:
                        return max(0, int(damage))
                return max(0, int(damage))
            except Exception:
                pass
        try:
            info = hp_apply_damage(hero, damage, self.damage_type, source=f"enemy_attack:{self.action_id_base}")
            return max(0, int((info or {}).get("hp_damage", 0) or 0))
        except Exception:
            return 0
