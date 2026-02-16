from __future__ import annotations

import logging
import random

from board import consts
from combat import effective_ac
from damage_types import DamageType

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
        roll = random.randint(1, 20) + attack_bonus + extra_mod

        target_ac = effective_ac(hero)

        prompt = (
            f"{getattr(enemy, 'name', 'wróg')} {self.weapon_label} na {target_pos}: "
            f"r={roll} (1d20 + {attack_bonus} {'+' if extra_mod >=0 else ''}{extra_mod}). "
            f"AC celu: {target_ac}. "
            "Potwierdź trafienie: ACCEPT/DECLINE"
        )
        response = conn.read_card(prompt, ["ACCEPT", "DECLINE"])
        if response.upper() != "ACCEPT":
            logger.info("Atak wroga odrzucony.")
            game.ui_log("Atak wroga odrzucony.")
            return EventResult(success=True, consumed_action=True, message="Atak odrzucony.")

        damage = self.roll_damage(enemy)
        self.apply_damage(hero, damage)

        dmg_msg = (
            f"{getattr(enemy, 'name', 'wróg')} zadaje {damage} obrażeń "
            f"(1d{self.damage_die_sides} + {getattr(enemy, self.strength_attr, 0)}). "
            f"Rany bohatera: {getattr(hero, 'wounds', '?')}."
        )
        logger.info(dmg_msg)
        game.ui_log(dmg_msg)

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

    def apply_damage(self, hero, damage: int) -> None:
        # Minimalny zapis: zwiększ rany; jeśli istnieje metoda apply_damage, użyj jej.
        apply = getattr(hero, "apply_damage", None)
        if callable(apply):
            try:
                apply(damage, self.damage_type)
                return
            except Exception:
                pass
        try:
            hero.wounds += damage  # type: ignore[attr-defined]
        except Exception:
            pass
