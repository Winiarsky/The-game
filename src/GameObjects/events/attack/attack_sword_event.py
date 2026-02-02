from __future__ import annotations

import logging

from board import consts
from combat import effective_ac, flat_footed_penalty, refresh_flanking_statuses
from GameObjects.interactions_mixin import prompt_for_roll

from ..base import EventContext, EventResult, GameEvent
from ..registry import register_event

logger = logging.getLogger(__name__)


def _adjacent_enemies(game, pos):
    board = game.board
    neighbors = board.get_neighbors(pos, include_position=False, diagonal=True)
    enemies = []
    for npos in neighbors:
        occ = board.occupant_at(npos)
        if occ in game.enemies:
            enemies.append((occ, npos))
    return enemies


@register_event
class SwordAttackEvent(GameEvent):
    name = "attack_sword"
    default_tags = ["attack_melee", "sword"]
    consumes_action = True

    def execute(self, ctx: EventContext) -> EventResult:
        hero = ctx.actor
        if hero is None:
            logger.info("Brak aktywnego bohatera do ataku mieczem.")
            return EventResult(success=False, consumed_action=False, message="Brak aktywnego bohatera.")
        hero_pos = getattr(hero, "position", None)
        if hero_pos is None:
            logger.info("Bohater nie jest na planszy.")
            return EventResult(success=False, consumed_action=False, message="Bohater nie jest na planszy.")

        candidates = _adjacent_enemies(ctx.game, hero_pos)
        if not candidates:
            logger.info("Brak wrogów na sąsiednich polach.")
            return EventResult(success=False, consumed_action=False, message="Brak wrogów w zasięgu.")

        enemy, enemy_pos = self._pick_enemy(ctx, candidates)
        if enemy is None:
            return EventResult.cancelled(message="Nie wybrano celu.")

        target_ac = effective_ac(enemy)
        base_ac = getattr(enemy, "ac", target_ac)
        penalty = flat_footed_penalty(enemy)
        if penalty:
            prompt_ac = f"{target_ac} (bazowe {base_ac}, -{penalty} flankowanie)"
        else:
            prompt_ac = str(base_ac)

        # pre-hook emit
        ctx.game.events.safe_emit_action(
            actor=hero,
            action_id="attack_sword_pre",
            action_tags=self._effective_tags(ctx),
            target=enemy,
            target_pos=enemy_pos,
        )

        roll = prompt_for_roll(f"Atak mieczem przeciwko AC {prompt_ac}. Podaj wynik k20: ")
        hit = roll >= target_ac
        if not hit:
            ctx.game.events.safe_emit_action(
                actor=hero,
                action_id="attack_sword_miss",
                action_tags=self._effective_tags(ctx),
                target=enemy,
                target_pos=enemy_pos,
                roll=roll,
                target_ac=target_ac,
            )
            return EventResult(success=True, consumed_action=self.consumes_action, message="Atak mieczem: pudło.")

        damage = prompt_for_roll("Trafienie! Podaj obrażenia 1k6 + STR: ")
        defeated = False
        try:
            _, defeated = enemy.apply_damage(damage, "slashing")
        except Exception as exc:
            logger.error("Nie udało się zadać obrażeń: %s", exc)
            return EventResult(success=False, consumed_action=False, message=str(exc))

        ctx.game.events.safe_emit_action(
            actor=hero,
            action_id="attack_sword",
            action_tags=self._effective_tags(ctx),
            target=enemy,
            target_pos=enemy_pos,
            damage=damage,
            defeated=defeated,
        )

        if defeated:
            try:
                ctx.game.board.remove(enemy_pos)
                try:
                    ctx.game.enemies.remove(enemy)
                except ValueError:
                    pass
            except Exception as exc:
                logger.error("Nie udało się usunąć przeciwnika: %s", exc)
            enemy.position = None
            logger.info("Przeciwnik pokonany.")
        else:
            logger.info("Przeciwnik przyjmuje obrażenia, pozostaje przy życiu (HP %s).", getattr(enemy, "hp", "?"))

        try:
            refresh_flanking_statuses(ctx.game)
        except Exception as exc:
            logger.error("Nie udało się odświeżyć flankowania: %s", exc)

        msg = "Przeciwnik pokonany." if defeated else "Atak mieczem trafia."
        return EventResult(success=True, consumed_action=self.consumes_action, message=msg)

    def _pick_enemy(self, ctx: EventContext, candidates):
        if not candidates:
            return None, None
        if len(candidates) == 1:
            return candidates[0]
        positions = [pos for _, pos in candidates]
        while True:
            try:
                ctx.game.conn.set_leds(positions, consts.INTERACT_FIELD_RGB)
                choice = ctx.game.conn.scan_board(positions)
            finally:
                try:
                    ctx.game.conn.leds_off()
                except Exception:
                    pass
            for enemy, pos in candidates:
                if pos == choice:
                    return enemy, pos
            logger.info("Nie wybrano poprawnego celu – spróbuj ponownie.")
            ctx.game.ui_log("Nie wybrano poprawnego celu – spróbuj ponownie.")
