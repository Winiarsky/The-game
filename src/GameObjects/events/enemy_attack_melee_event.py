from __future__ import annotations

import logging
import random

from board import consts
from combat import flat_footed_penalty

from .base import EventContext, EventResult, GameEvent
from .registry import register_event

logger = logging.getLogger(__name__)


@register_event
class EnemyMeleeAttackEvent(GameEvent):
    name = "enemy_attack_melee"
    default_tags = ["attack_melee", "enemy"]
    consumes_action = True
    available_in_exploration = False

    def execute(self, ctx: EventContext) -> EventResult:
        enemy = ctx.actor
        if enemy is None or getattr(enemy, "position", None) is None:
            return EventResult(success=False, consumed_action=False, message="Wróg nie jest na planszy.")

        game = ctx.game
        board = game.board
        conn = game.conn
        enemy_pos = enemy.position

        neighbors = board.get_neighbors(enemy_pos, include_position=False, diagonal=True)
        targets = [pos for pos in neighbors if board.occupant_at(pos) in game.heroes]
        if not targets:
            return EventResult(success=False, consumed_action=False, message="Brak bohaterów w zasięgu.")

        conn.set_leds(targets, consts.MOVE_FIELD_RGB)
        try:
            target_pos = conn.scan_board(targets)
        finally:
            try:
                conn.leds_off()
            except Exception:
                pass

        hero = board.occupant_at(target_pos)
        if hero not in game.heroes:
            return EventResult(success=False, consumed_action=True, message="Wybrano cel niebędący bohaterem.")

        attack_bonus = getattr(enemy, "attack_bonus", 0)
        roll = random.randint(1, 20) + attack_bonus
        penalty = flat_footed_penalty(hero)
        penalty_note = f" (cel flankowany: -{penalty} do AC)" if penalty else ""

        prompt = (
            f"{getattr(enemy, 'name', 'wróg')} atakuje bohatera na {target_pos}: "
            f"r={roll} (1d20 + {attack_bonus}){penalty_note}. "
            "Potwierdź trafienie: ACCEPT/DECLINE"
        )
        response = conn.read_card(prompt, ["ACCEPT", "DECLINE"])
        if response.upper() != "ACCEPT":
            logger.info("Atak wroga odrzucony.")
            game.ui_log("Atak wroga odrzucony.")
            return EventResult(success=True, consumed_action=True, message="Atak odrzucony.")

        damage = random.randint(1, 6) + getattr(enemy, "strength", 0)
        try:
            hero.wounds += damage  # type: ignore[attr-defined]
        except Exception:
            pass
        dmg_msg = (
            f"{getattr(enemy, 'name', 'wróg')} zadaje {damage} obrażeń (1d6 + {getattr(enemy, 'strength', 0)}). "
            f"Rany bohatera: {getattr(hero, 'wounds', '?')}."
        )
        logger.info(dmg_msg)
        game.ui_log(dmg_msg)

        game.events.safe_emit_action(
            actor=enemy,
            action_id="enemy_attack_melee",
            action_tags=self._effective_tags(ctx),
            target=hero,
            target_pos=target_pos,
            damage=damage,
        )

        return EventResult(success=True, consumed_action=True, message="Atak wroga wykonany.")

