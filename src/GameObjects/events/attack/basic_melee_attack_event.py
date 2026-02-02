from __future__ import annotations

import logging

from board import consts
from combat import effective_ac, flat_footed_penalty, refresh_flanking_statuses
from GameObjects.interactions_mixin import prompt_for_roll

from ..base import EventContext, EventResult, GameEvent

logger = logging.getLogger(__name__)


class BasicMeleeAttackEvent(GameEvent):
    """Wspólna logika dla prostych ataków bronią białą."""

    # konfiguracja per broń
    weapon_label: str = "bronią"
    damage_prompt: str = "1k6 + STR"
    action_id_base: str = "attack_melee"
    damage_type: str = "slashing"
    default_tags = ["attack_melee"]
    consumes_action = True

    # --- główna logika ---
    def execute(self, ctx: EventContext) -> EventResult:  # noqa: C901 - złożone ale liniowe
        hero = ctx.actor
        if hero is None:
            logger.info("Brak aktywnego bohatera do ataku %s.", self.weapon_label)
            return EventResult(success=False, consumed_action=False, message="Brak aktywnego bohatera.")
        hero_pos = getattr(hero, "position", None)
        if hero_pos is None:
            logger.info("Bohater nie jest na planszy.")
            return EventResult(success=False, consumed_action=False, message="Bohater nie jest na planszy.")
        try:
            hero.remove_status("range_attacker")  # powrót OA po ataku wręcz
        except Exception:
            pass

        candidates = self._adjacent_enemies(ctx.game, hero_pos)
        if not candidates:
            logger.info("Brak wrogów na sąsiednich polach.")
            return EventResult(success=False, consumed_action=False, message="Brak wrogów w zasięgu.")

        enemy, enemy_pos = self._pick_enemy(ctx, candidates)
        if enemy is None:
            return EventResult.cancelled(message="Nie wybrano celu.")

        target_ac = effective_ac(enemy)
        base_ac = getattr(enemy, "ac", target_ac)
        penalty = flat_footed_penalty(enemy)
        prompt_ac = (
            f"{target_ac} (bazowe {base_ac}, -{penalty} flankowanie)"
            if penalty
            else str(base_ac)
        )

        ctx.game.events.safe_emit_action(
            actor=hero,
            action_id=f"{self.action_id_base}_pre",
            action_tags=self._effective_tags(ctx),
            target=enemy,
            target_pos=enemy_pos,
        )

        roll = prompt_for_roll(f"Atak {self.weapon_label} przeciwko AC {prompt_ac}. Podaj wynik k20: ")
        hit = roll >= target_ac
        if not hit:
            ctx.game.events.safe_emit_action(
                actor=hero,
                action_id=f"{self.action_id_base}_miss",
                action_tags=self._effective_tags(ctx),
                target=enemy,
                target_pos=enemy_pos,
                roll=roll,
                target_ac=target_ac,
            )
            return EventResult(success=True, consumed_action=self.consumes_action, message=f"Atak {self.weapon_label}: pudło.")

        damage = prompt_for_roll(f"Trafienie! Podaj obrażenia {self.damage_prompt}: ")
        defeated = False
        try:
            _, defeated = enemy.apply_damage(damage, self.damage_type)
        except Exception as exc:
            logger.error("Nie udało się zadać obrażeń: %s", exc)
            return EventResult(success=False, consumed_action=False, message=str(exc))

        ctx.game.events.safe_emit_action(
            actor=hero,
            action_id=self.action_id_base,
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

        msg = "Przeciwnik pokonany." if defeated else f"Atak {self.weapon_label} trafia."
        return EventResult(success=True, consumed_action=self.consumes_action, message=msg)

    # --- helpers ---
    @staticmethod
    def _adjacent_enemies(game, pos):
        board = game.board
        neighbors = board.get_neighbors(pos, include_position=False, diagonal=True)
        enemies = []
        for npos in neighbors:
            occ = board.occupant_at(npos)
            if occ in game.enemies:
                enemies.append((occ, npos))
        return enemies

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
