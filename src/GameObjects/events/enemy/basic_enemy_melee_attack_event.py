from __future__ import annotations

import logging
import random

from board import consts
from combat import effective_ac
from combat.hero_side_targets import hero_side_targets, is_hero_side_target
from combat.hp_engine import apply_damage as hp_apply_damage
from combat.degree_of_success import is_critical_success, natural_shift_from_roll, resolve_outcome
from damage_types import DamageType
from statuses.race.dwarf.feats.vengeful_hatred import grant_vengeful_hatred_revenge
from enemy_prompting import clear_enemy_highlight, enemy_highlight, enemy_prompt_step, format_roll_components

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
        if not is_hero_side_target(game, hero):
            return EventResult(success=False, consumed_action=True, message="Wybrano cel spoza strony bohaterów.")

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
        hit = outcome in {"success", "critical_success"}
        clumsy_note = None
        try:
            from statuses.clumsy import clumsy_ac_prompt_note

            clumsy_note = clumsy_ac_prompt_note(hero)
        except Exception:
            clumsy_note = None

        roll_components = [
            {
                "label": "k20",
                "value": natural_roll,
                "description": "Naturalny wynik rzutu.",
            },
            {
                "label": "Bonus ataku",
                "value": int(attack_bonus or 0),
                "description": "Podstawowy bonus przeciwnika.",
            },
            {
                "label": "Modyfikator sytuacyjny",
                "value": int(extra_mod or 0),
                "description": "Dodatkowe premie lub kary.",
            },
        ]
        prompt = (
            f"{getattr(enemy, 'name', 'wróg')} wykonuje {self.weapon_label} przeciw {getattr(hero, 'name', 'celowi')}.\n"
            f"Cel stoi na polu {target_pos}.\n"
            "Jeśli przeciwnik ma więcej niż jeden możliwy cel, wskaż odpowiednią figurkę na planszy.\n\n"
            f"Rozpiska rzutu:\n{format_roll_components(roll_components)}\n\n"
            f"Wynik końcowy: {roll}\n"
            f"Próg obrony: AC {target_ac}\n"
            f"Wynik testu: {outcome}"
        )
        if clumsy_note:
            prompt = f"{prompt} {clumsy_note}"
        enemy_highlight(
            game,
            [enemy_pos, target_pos],
            [consts.ENEMY_START_RGB, consts.HERO_HIGHLIGHT_RGB],
        )
        try:
            enemy_prompt_step(
                game,
                f"Atak przeciwnika: {getattr(enemy, 'name', 'wróg')}",
                prompt_long=prompt,
                source=self.action_id_base,
                log_message=(
                    f"{getattr(enemy, 'name', 'wróg')} atakuje {getattr(hero, 'name', 'cel')} "
                    f"({roll} vs AC {target_ac}, {outcome})."
                ),
            )
            if not hit:
                return EventResult(success=True, consumed_action=True, message="Atak wroga pudłuje.")

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
            enemy_prompt_step(
                game,
                f"Wynik ataku: {getattr(enemy, 'name', 'wróg')}",
                prompt_long=(
                    f"Atak trafia {'krytycznie' if critical_hit else 'normalnie'}.\n"
                    f"Obrażenia: {damage} {self.damage_type}.\n"
                    f"Rany celu po trafieniu: {getattr(hero, 'wounds', '?')}.\n"
                    "Zastosuj wynik na planszy i potwierdź Enterem."
                ),
                source=f"{self.action_id_base}_result",
                log_message=dmg_msg,
            )
            try:
                game.ui_hero(hero)
            except Exception:
                pass
        finally:
            clear_enemy_highlight(game)

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
        targets = list(hero_side_targets(game, only_living=True))
        return [p for p in neighbors if board.occupant_at(p) in targets]

    @staticmethod
    def _pick_target(conn, targets):
        conn.set_leds(targets, consts.HERO_HIGHLIGHT_RGB)
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
