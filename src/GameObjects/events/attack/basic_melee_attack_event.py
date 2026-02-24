from __future__ import annotations

import logging
from typing import Iterable, Sequence

from board import consts
from bonuses import BonusEffect, BonusType, build_modifiers_grid
from combat import refresh_flanking_statuses
from combat.damage_utils import burn_it_bonus, burn_it_prompt_note
from GameObjects.interactions_mixin import prompt_for_roll
from damage_types import DamageType
from statuses import Status

from .attack_base import AttackEventBase, check_concealed
from ..targeting import is_target_blocked_by_tags
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
            hero.remove_status(Status(id="range_attacker"))  # powrót OA po ataku wręcz
        except Exception:
            pass

        tags = self._effective_tags(ctx)
        candidates = self._reachable_enemies(ctx.game, hero_pos, tags)
        candidates = [(enemy, pos) for enemy, pos in candidates if not is_target_blocked_by_tags(enemy, tags)]
        if not candidates:
            logger.info("Brak wrogów na sąsiednich polach.")
            return EventResult(success=False, consumed_action=False, message="Brak wrogów w zasięgu.")

        enemy, enemy_pos = self._pick_enemy(ctx, candidates)
        if enemy is None:
            return EventResult.cancelled(message="Nie wybrano celu.")

        # --- weapon trait state (przed atakiem) ---
        state = self._get_attack_state(ctx, hero)
        weapon_key = self._weapon_key()
        weapon_type = self._weapon_type_tag(tags)
        attacks_this_turn = int(state.get("attacks_this_turn", 0) or 0)
        weapon_counts = state.setdefault("weapon_counts", {})
        weapon_attack_count = int(weapon_counts.get(weapon_key, 0) or 0)
        backswing_ready = state.setdefault("backswing_ready", set())
        weapon_targets = state.setdefault("weapon_targets", {})
        target_set = weapon_targets.setdefault(weapon_key, set())
        target_id = self._target_id(enemy)

        if not check_concealed(ctx, enemy):
            ctx.game.events.safe_emit_action(
                actor=hero,
                action_id=f"{self.action_id_base}_concealed_miss",
                action_tags=self._effective_tags(ctx),
                target=enemy,
                target_pos=enemy_pos,
            )
            if self._has_trait(tags, "backswing"):
                try:
                    backswing_ready.add(weapon_key)
                except Exception:
                    pass
            self._record_attack(ctx, hero, weapon_key=weapon_key, weapon_type=weapon_type, target=enemy)
            return EventResult(success=True, consumed_action=self.consumes_action, message=f"Atak {self.weapon_label}: pudło (concealed).")

        extra_bonuses = []
        try:
            from statuses.clumsy import clumsy_ac_penalty_effect

            clumsy_bonus = clumsy_ac_penalty_effect(enemy)
            if clumsy_bonus:
                extra_bonuses.append(clumsy_bonus)
        except Exception:
            pass
        target_ac, base_ac, modifier = self._ac_with_bonuses(
            enemy,
            attacker=hero,
            extra_bonuses=extra_bonuses or None,
        )
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

        action_tag = (tags or ["attack_melee"])[0]
        extra_effects = []
        trait_notes: list[str] = []
        try:
            from statuses.clumsy import clumsy_attack_penalty_effects

            extra_effects.extend(
                clumsy_attack_penalty_effects(
                    hero,
                    action_tag=action_tag,
                    is_ranged=False,
                    is_finesse=("finesse" in tags),
                )
            )
        except Exception:
            pass
        map_penalty = 0
        if attacks_this_turn >= 1:
            if self._has_trait(tags, "agile"):
                map_penalty = 4 if attacks_this_turn == 1 else 8
            else:
                map_penalty = 5 if attacks_this_turn == 1 else 10
        if map_penalty:
            extra_effects.append(
                BonusEffect(
                    type=BonusType.CIRCUMSTANCE,
                    value=map_penalty,
                    tag=action_tag,
                    source="map",
                    label=f"MAP{' (agile)' if self._has_trait(tags, 'agile') else ''}",
                    is_penalty=True,
                )
            )
        if self._has_trait(tags, "backswing") and weapon_key in backswing_ready:
            extra_effects.append(
                BonusEffect(
                    type=BonusType.CIRCUMSTANCE,
                    value=1,
                    tag=action_tag,
                    source="backswing",
                    label="backswing",
                )
            )
            try:
                backswing_ready.discard(weapon_key)
            except Exception:
                pass
        if self._has_trait(tags, "sweep") and target_id:
            try:
                if any(tid != target_id for tid in target_set):
                    extra_effects.append(
                        BonusEffect(
                            type=BonusType.CIRCUMSTANCE,
                            value=1,
                            tag=action_tag,
                            source="sweep",
                            label="sweep",
                        )
                    )
            except Exception:
                pass
        if self._has_trait(tags, "nonlethal"):
            trait_notes.append("Nonlethal: atak nieśmiertelny; jeśli lethal, -2 do ataku (ręcznie).")
        if self._has_trait(tags, "finesse"):
            trait_notes.append("Finesse: możesz użyć ZR zamiast SI do premii ataku.")
        modifier, best_effects, log_lines = self._attack_modifier_details(
            hero, action_tag, target=enemy, extra_effects=extra_effects or None
        )
        if log_lines:
            try:
                ctx.game.ui_log(f"Modyfikatory ({action_tag}): {', '.join(log_lines)}.")
            except Exception:
                pass
        prompt_long = f"Modyfikator łączny: {modifier:+d} (doliczany automatycznie)."
        if trait_notes:
            prompt_long = f"{prompt_long}\n" + "\n".join(trait_notes)

        roll = prompt_for_roll(
            f"Atak {self.weapon_label} przeciwko AC {prompt_ac}.",
            layout="test",
            prompt_long=prompt_long,
            modifiers=build_modifiers_grid(best_effects),
            answer_placeholder="Wynik k20",
        )
        total_roll = roll + modifier
        self._consume_aid_attack_bonus(hero)
        critical = total_roll >= target_ac + 10
        hit = total_roll >= target_ac
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
            if self._has_trait(tags, "backswing"):
                try:
                    backswing_ready.add(weapon_key)
                except Exception:
                    pass
            self._record_attack(ctx, hero, weapon_key=weapon_key, weapon_type=weapon_type, target=enemy)
            return EventResult(success=True, consumed_action=self.consumes_action, message=f"Atak {self.weapon_label}: pudło.")

        self._maybe_prompt_vengeful_hatred(hero, enemy)
        dmg_prompt = f"{'Trafienie krytyczne! ' if critical else 'Trafienie! '}Obrażenia {self.damage_prompt}: "
        resolved_damage_type = self._choose_damage_type(tags, self.damage_type)
        first_type = resolved_damage_type if isinstance(resolved_damage_type, str) else list(resolved_damage_type)[0]
        note = burn_it_prompt_note(hero, first_type)
        damage_bonus = 0
        damage_notes: list[str] = []
        dice_count = self._damage_dice_count(self.damage_prompt)
        if self._has_trait(tags, "versatile") and not self._tag_value(tags, "versatile"):
            damage_notes.append("Versatile: brak typu w tagu (np. versatile:p) – wybierz ręcznie.")
        deadly_tag = self._tag_value(tags, "deadly")
        deadly_die = self._die_size_from_tag(deadly_tag)
        if self._has_trait(tags, "deadly") and not deadly_die:
            damage_notes.append("Deadly: brak kości w tagu (np. deadly:d8) – dodaj ręcznie.")
        if self._has_trait(tags, "forceful"):
            if dice_count:
                if weapon_attack_count >= 1:
                    add = dice_count if weapon_attack_count == 1 else dice_count * 2
                    damage_bonus += add
                    damage_notes.append(f"Forceful: +{add} obrażeń (doliczone).")
            else:
                damage_notes.append("Forceful: dodaj bonus za kości obrażeń (ręcznie).")
        if self._has_trait(tags, "twin") and weapon_type:
            last_by_type = state.get("last_weapon_by_type", {}) or {}
            last_weapon = last_by_type.get(weapon_type)
            if last_weapon and last_weapon != weapon_key:
                if dice_count:
                    damage_bonus += dice_count
                    damage_notes.append(f"Twin: +{dice_count} obrażeń (doliczone).")
                else:
                    damage_notes.append("Twin: dodaj bonus za kości obrażeń (ręcznie).")
        if self._has_trait(tags, "backstabber") and self._is_flat_footed(enemy):
            damage_bonus += 1
            damage_notes.append("Backstabber: +1 precision (doliczone; +2 jeśli broń +3).")
        if self._has_trait(tags, "propulsive"):
            damage_notes.append("Propulsive: dodaj 1/2 STR do obrażeń (ręcznie).")
        if self._has_trait(tags, "fatal"):
            damage_notes.append("Fatal: zmień kości bazowe i dodaj 1 kość fatal (ręcznie).")
        if self._has_trait(tags, "two_hand"):
            damage_notes.append("Two-Hand: użycie dwuręczne zmienia kości obrażeń (ręcznie).")
        if damage_notes:
            note = f"{note}\n" + "\n".join(damage_notes) if note else "\n".join(damage_notes)
        damage = prompt_for_roll(
            dmg_prompt,
            layout="damage",
            answer_placeholder="Suma obrażeń",
            prompt_long=note,
        )
        damage_components = self._collect_damage_components(
            damage,
            actor=hero,
            damage_type_override=resolved_damage_type,
            flat_bonus=damage_bonus,
        )
        if critical and deadly_die:
            extra = prompt_for_roll(
                f"Deadly {deadly_die}: dodatkowe obrażenia (rzut): ",
                layout="damage",
                answer_placeholder="Dodatkowe obrażenia",
            )
            try:
                damage_components.append((first_type, int(extra)))
            except Exception:
                pass
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
        self._record_attack(ctx, hero, weapon_key=weapon_key, weapon_type=weapon_type, target=enemy)

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

        msg = "Przeciwnik pokonany." if defeated else ("Trafienie krytyczne!" if critical else f"Atak {self.weapon_label} trafia.")
        return EventResult(success=True, consumed_action=self.consumes_action, message=msg, data={"critical": critical})

    # --- helpers ---
    def _collect_damage_components(
        self,
        first_roll: int,
        *,
        actor=None,
        damage_type_override: str | Sequence[str] | None = None,
        flat_bonus: int = 0,
    ) -> list[tuple[str, int]]:
        """Zwraca listę (typ, obrażenia) – obsługa wielu typów."""
        damage_type = damage_type_override if damage_type_override is not None else self.damage_type
        if isinstance(damage_type, str):
            bonus = burn_it_bonus(actor, damage_type)
            return [(damage_type, int(first_roll) + int(bonus) + int(flat_bonus))]
        components: list[tuple[str, int]] = []
        damage_types = list(damage_type)
        bonus = burn_it_bonus(actor, damage_types[0])
        components.append((damage_types[0], int(first_roll) + int(bonus) + int(flat_bonus)))
        for idx, dtype in enumerate(damage_types[1:], start=1):
            prompt = f"Trafienie! Obrażenia dodatkowe ({dtype}): "
            note = burn_it_prompt_note(actor, dtype)
            roll = prompt_for_roll(
                prompt,
                layout="damage",
                answer_placeholder=f"Obrażenia {dtype}",
                prompt_long=note,
            )
            bonus = burn_it_bonus(actor, dtype)
            components.append((dtype, int(roll) + int(bonus)))
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

    def _reachable_enemies(self, game, pos, tags):
        board = game.board
        reach_tag = self._tag_value(tags, "reach")
        if not self._has_trait(tags, "reach"):
            return self._adjacent_enemies(game, pos)
        try:
            reach_ft = int(reach_tag) if reach_tag else 10
        except Exception:
            reach_ft = 10
        steps = max(1, int(reach_ft / 5))
        enemies = []
        for dx in range(-steps, steps + 1):
            for dy in range(-steps, steps + 1):
                if dx == 0 and dy == 0:
                    continue
                if max(abs(dx), abs(dy)) > steps:
                    continue
                npos = (pos[0] + dx, pos[1] + dy)
                try:
                    if not board.in_bounds(npos):
                        continue
                except Exception:
                    continue
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
