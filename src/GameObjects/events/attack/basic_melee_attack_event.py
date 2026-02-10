from __future__ import annotations

import logging
from typing import Iterable, Sequence

from board import consts
from combat import refresh_flanking_statuses
from GameObjects.interactions_mixin import prompt_for_roll
from damage_types import DamageType

from .attack_base import AttackEventBase
from ..base import EventContext, EventResult

logger = logging.getLogger(__name__)


class BasicMeleeAttackEvent(AttackEventBase):
    """Wspólna logika dla prostych ataków bronią białą."""

    # konfiguracja per broń
    weapon_label: str = "bronią"
    damage_prompt: str | Sequence[str] = "1k6 + STR"
    action_id_base: str = "attack_melee"
    damage_type: str | Sequence[str] = DamageType.SLASHING.value
    default_tags = ["attack_melee"]
    consumes_action = True
    # może być str lub lista str przy wielu typach obrażeń

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

        target_ac, base_ac, modifier = self._ac_with_bonuses(enemy, attacker=hero)
        modifier_note = ""
        if modifier:
            sign = "+" if modifier > 0 else ""
            modifier_note = f" (bazowe {base_ac}, modyfikatory {sign}{modifier})"
        prompt_ac = f"{target_ac}{modifier_note}"

        ctx.game.events.safe_emit_action(
            actor=hero,
            action_id=f"{self.action_id_base}_pre",
            action_tags=self._effective_tags(ctx),
            target=enemy,
            target_pos=enemy_pos,
        )

        action_tag = (self._effective_tags(ctx) or ["attack_melee"])[0]
        bonus_info = self._format_bonus_info(hero, action_tag, target=enemy)

        roll = prompt_for_roll(f"Atak {self.weapon_label} przeciwko AC {prompt_ac}.{bonus_info}Podaj wynik k20: ")
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
        damage_components = self._collect_damage_components(damage)
        defeated = False
        try:
            defeated = self._apply_damage_components(enemy, damage_components)
        except Exception as exc:
            logger.error("Nie udało się zadać obrażeń: %s", exc)
            return EventResult(success=False, consumed_action=False, message=str(exc))

        ctx.game.events.safe_emit_action(
            actor=hero,
            action_id=self.action_id_base,
            action_tags=self._effective_tags(ctx),
            target=enemy,
            target_pos=enemy_pos,
            damage=sum(d for _, d in damage_components),
            damage_components=damage_components,
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
    def _collect_damage_components(self, first_roll: int) -> list[tuple[str, int]]:
        """Zwraca listę (typ, obrażenia) – obsługa wielu typów."""
        if isinstance(self.damage_type, str):
            return [(self.damage_type, first_roll)]
        components: list[tuple[str, int]] = []
        damage_types = list(self.damage_type)
        components.append((damage_types[0], first_roll))
        for idx, dtype in enumerate(damage_types[1:], start=1):
            prompt = f"Trafienie! Podaj dodatkowe obrażenia ({dtype}): "
            roll = prompt_for_roll(prompt)
            components.append((dtype, roll))
        return components

    @staticmethod
    def _apply_damage_components(target, comps: Iterable[tuple[str, int]]) -> bool:
        defeated = False
        for dmg_type, amount in comps:
            _, defeated = target.apply_damage(amount, dmg_type)
        return defeated

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
