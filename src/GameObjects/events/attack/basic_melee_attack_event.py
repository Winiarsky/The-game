from __future__ import annotations

import logging
from typing import Iterable, Sequence

from board import consts
from bonuses import BonusEffect, BonusType, build_modifiers_grid
from combat import refresh_flanking_statuses
from combat.degree_of_success import is_critical_success, is_hit, natural_shift_from_roll, resolve_outcome
from combat.damage_utils import burn_it_bonus, burn_it_prompt_note
from GameObjects.interactions_mixin import prompt_for_roll
from damage_types import DamageType
from statuses import Status, inspire_courage_damage_bonus, make_persistent_damage

from .attack_base import AttackEventBase, check_concealed
from ..targeting import is_target_blocked_by_tags
from ..base import EventContext, EventResult

logger = logging.getLogger(__name__)

_PHYSICAL_DAMAGE_TYPES = {"slashing", "piercing", "bludgeoning"}


def is_target_incorporeal(target) -> bool:
    if target is None:
        return False
    has_tag = getattr(target, "has_tag", None)
    if callable(has_tag):
        try:
            return bool(has_tag("incorporeal"))
        except Exception:
            return False
    tags = getattr(target, "tags", None) or []
    return "incorporeal" in tags


def _ignores_incorporeal(attacker) -> bool:
    if attacker is None:
        return False
    has_status = getattr(attacker, "has_status", None)
    if callable(has_status):
        try:
            return bool(has_status("spirit_instinct_active"))
        except Exception:
            return False
    for status in getattr(attacker, "statuses", []) or []:
        if getattr(status, "id", None) == "spirit_instinct_active":
            return True
    return False


def _apply_incorporeal_reductions(target, components, *, ignore: bool, tags: list[str]):
    if target is None or ignore or not is_target_incorporeal(target):
        return components
    if "precision" in (tags or []):
        return [(dtype, 0) for dtype, _amt in components]
    reduced = []
    for dtype, amt in components:
        if str(dtype) in _PHYSICAL_DAMAGE_TYPES:
            reduced.append((dtype, int(amt) // 2))
        else:
            reduced.append((dtype, int(amt)))
    return reduced


class BasicMeleeAttackEvent(AttackEventBase):
    """Wspólna logika dla prostych ataków bronią białą."""

    # konfiguracja per broń
    weapon_label: str = "bronią"
    damage_prompt: str | Sequence[str] = "1k6 + STR"
    action_id_base: str = "attack_melee"
    damage_type: str | Sequence[str] = DamageType.SLASHING.value
    default_tags = ["attack_melee"]
    consumes_action = True
    critical_doubles_damage: bool = False
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

        selected_weapon = self._selected_weapon(ctx)
        tags = self._effective_tags(ctx)
        if selected_weapon is not None:
            tags = self._merged_weapon_tags(tags, selected_weapon)
        if self._has_status_id(hero, "monk_stance_active") and "unarmed" not in tags:
            stance_label = str(getattr(hero, "get_status_data", lambda *_a, **_k: "")("monk_stance_active", "stance_label", "") or "")
            if not stance_label:
                stance_label = "Monk Stance"
            return EventResult.cancelled(
                message=f"{stance_label}: twarda blokada Strike'ów spoza stance (użyj unarmed/flurry_of_blows)."
            )
        metadata = dict(getattr(ctx, "metadata", None) or {})
        candidates = self._reachable_enemies(ctx.game, hero_pos, tags)
        candidates = [(enemy, pos) for enemy, pos in candidates if not is_target_blocked_by_tags(enemy, tags)]
        if not candidates:
            logger.info("Brak wrogów na sąsiednich polach.")
            return EventResult(success=False, consumed_action=False, message="Brak wrogów w zasięgu.")

        forced_target = metadata.get("forced_target")
        forced_target_pos = metadata.get("forced_target_pos")
        enemy = None
        enemy_pos = None
        if forced_target is not None:
            for candidate_enemy, candidate_pos in candidates:
                if candidate_enemy is forced_target:
                    enemy, enemy_pos = candidate_enemy, candidate_pos
                    break
            if enemy is None:
                return EventResult.cancelled(message="Wymuszony cel nie jest w zasięgu ataku.")
        elif isinstance(forced_target_pos, tuple) and len(forced_target_pos) == 2:
            for candidate_enemy, candidate_pos in candidates:
                if tuple(candidate_pos) == tuple(forced_target_pos):
                    enemy, enemy_pos = candidate_enemy, candidate_pos
                    break
            if enemy is None:
                return EventResult.cancelled(message="Wymuszony cel nie jest w zasięgu ataku.")
        else:
            enemy, enemy_pos = self._pick_enemy(ctx, candidates)
        if enemy is None:
            return EventResult.cancelled(message="Nie wybrano celu.")

        if self._consume_feint_next_attack(ctx, hero, enemy, is_melee=True):
            metadata["force_flat_footed"] = True
            metadata.setdefault("force_flat_footed_source", "feint")

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
        suppress_record = bool(metadata.get("suppress_attack_record", False))
        exacting_strike_press = bool(metadata.get("exacting_strike_press", False))
        try:
            map_attack_count = max(1, int(metadata.get("map_attack_count", 1) or 1))
        except Exception:
            map_attack_count = 1
        try:
            fixed_attacks_this_turn = metadata.get("fixed_attacks_this_turn", None)
            if fixed_attacks_this_turn is not None:
                attacks_this_turn = max(0, int(fixed_attacks_this_turn))
        except Exception:
            pass
        try:
            attack_roll_penalty = max(0, int(metadata.get("attack_roll_penalty", 0) or 0))
        except Exception:
            attack_roll_penalty = 0
        try:
            attack_roll_bonus = max(0, int(metadata.get("ki_strike_attack_bonus", 0) or 0))
        except Exception:
            attack_roll_bonus = 0
        try:
            power_attack_extra_dice = max(0, int(metadata.get("power_attack_extra_dice", 0) or 0))
        except Exception:
            power_attack_extra_dice = 0
        roll_only = bool(metadata.get("roll_only", False))
        allow_auto_precision_bonus = metadata.get("allow_auto_precision_bonus", True)
        if isinstance(allow_auto_precision_bonus, str):
            allow_auto_precision_bonus = allow_auto_precision_bonus.strip().lower() not in {
                "0",
                "false",
                "no",
                "nie",
            }
        allow_auto_precision_bonus = bool(allow_auto_precision_bonus)
        force_lethal = self._bool_from_metadata(metadata.get("force_lethal"), default=False)
        nonlethal_attack = self._has_trait(tags, "nonlethal") and not force_lethal

        if not check_concealed(ctx, enemy):
            ctx.game.events.safe_emit_action(
                actor=hero,
                action_id=f"{self.action_id_base}_concealed_miss",
                action_tags=tags,
                target=enemy,
                target_pos=enemy_pos,
            )
            if self._has_trait(tags, "backswing"):
                try:
                    backswing_ready.add(weapon_key)
                except Exception:
                    pass
            if not suppress_record:
                self._record_attack(
                    ctx,
                    hero,
                    weapon_key=weapon_key,
                    weapon_type=weapon_type,
                    target=enemy,
                    attack_count=map_attack_count,
                )
            self._apply_concealing_trait(hero, tags)
            return EventResult(
                success=True,
                consumed_action=self.consumes_action,
                message=f"Atak {self.weapon_label}: pudło (concealed).",
                data={"hit": False, "critical": False, "target": enemy, "target_pos": enemy_pos},
            )

        ctx.game.events.safe_emit_action(
            actor=hero,
            action_id=f"{self.action_id_base}_pre",
            action_tags=tags,
            target=enemy,
            target_pos=enemy_pos,
        )

        is_off_guard_for_attack, target_natural_flat_footed, surprise_attack_active = self._is_off_guard_for_attack(
            ctx,
            hero,
            enemy,
            metadata=metadata,
            is_melee=True,
        )
        extra_bonuses = []
        if is_off_guard_for_attack and not target_natural_flat_footed:
            source = str(metadata.get("force_flat_footed_source", "") or "").strip().lower()
            if surprise_attack_active:
                source = "rogue:surprise_attack"
            if not source:
                source = "flat_footed:forced"
            extra_bonuses.append(
                BonusEffect(
                    type=BonusType.CIRCUMSTANCE,
                    value=2,
                    tag="ac",
                    source=source,
                    target_id=getattr(hero, "object_id", None),
                    label="flat-footed",
                    is_penalty=True,
                )
            )
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
        self._consume_nimble_dodge_bonus(enemy, hero)
        modifier_note = ""
        if modifier:
            sign = "+" if modifier > 0 else ""
            modifier_note = f" (bazowe {base_ac}, modyfikatory {sign}{modifier})"
        prompt_ac = f"{target_ac}{modifier_note}"

        action_tag = (tags or ["attack_melee"])[0]
        extra_effects = []
        trait_notes: list[str] = []
        if "unarmed" in (tags or []):
            wild_shape_bonus = 0
            getter = getattr(hero, "get_status_data", None)
            if callable(getter):
                try:
                    wild_shape_bonus = int(getter("wild_shape_active", "attack_status_bonus", 0) or 0)
                except Exception:
                    wild_shape_bonus = 0
            else:
                for item in getattr(hero, "statuses", []) or []:
                    if getattr(item, "id", None) != "wild_shape_active":
                        continue
                    data = getattr(item, "data", None) or {}
                    try:
                        wild_shape_bonus = int(data.get("attack_status_bonus", 0) or 0)
                    except Exception:
                        wild_shape_bonus = 0
                    break
            if wild_shape_bonus > 0:
                extra_effects.append(
                    BonusEffect(
                        type=BonusType.STATUS,
                        value=wild_shape_bonus,
                        tag=action_tag,
                        source="wild_shape",
                        label="wild shape",
                    )
                )
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
        try:
            from statuses import enfeebled_attack_penalty_effects

            extra_effects.extend(enfeebled_attack_penalty_effects(hero, action_tag))
        except Exception:
            pass
        map_penalty = 0
        if attacks_this_turn >= 1:
            if self._has_trait(tags, "agile"):
                map_penalty = 4 if attacks_this_turn == 1 else 8
            else:
                map_penalty = 5 if attacks_this_turn == 1 else 10
        ranger_map_penalty = self._ranger_map_penalty(
            hero,
            tags=tags,
            attacks_this_turn=attacks_this_turn,
            target=enemy,
        )
        if ranger_map_penalty is not None:
            map_penalty = int(ranger_map_penalty)
        if map_penalty:
            extra_effects.append(
                BonusEffect(
                    type=BonusType.CIRCUMSTANCE,
                    value=map_penalty,
                    tag=action_tag,
                    source="map",
                    label=(
                        "MAP ranger flurry"
                        if ranger_map_penalty is not None
                        else f"MAP{' (agile)' if self._has_trait(tags, 'agile') else ''}"
                    ),
                    is_penalty=True,
                )
            )
        if attack_roll_penalty > 0:
            extra_effects.append(
                BonusEffect(
                    type=BonusType.CIRCUMSTANCE,
                    value=attack_roll_penalty,
                    tag=action_tag,
                    source="fighter:attack_roll_penalty",
                    label="fighter penalty",
                    is_penalty=True,
                )
            )
        if attack_roll_bonus > 0:
            extra_effects.append(
                BonusEffect(
                    type=BonusType.STATUS,
                    value=attack_roll_bonus,
                    tag=action_tag,
                    source="ki_strike",
                    label="ki strike",
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
            if force_lethal:
                extra_effects.append(
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=2,
                        tag=action_tag,
                        source="nonlethal:lethal",
                        label="nonlethal (lethal)",
                        is_penalty=True,
                    )
                )
                trait_notes.append("Nonlethal: wymuszono lethal, -2 do ataku (doliczone).")
            else:
                trait_notes.append("Nonlethal: obrażenia nieśmiertelne (doliczone).")
        if self._has_trait(tags, "finesse"):
            trait_notes.append("Finesse: możesz użyć ZR zamiast SI do premii ataku.")
        if surprise_attack_active:
            trait_notes.append("Surprise Attack: cel traktowany jako flat-footed (-2 AC vs ten atak).")
        modifier, best_effects, log_lines = self._attack_modifier_details(
            hero, action_tag, target=enemy, extra_effects=extra_effects or None
        )
        weapon_attack_bonus = self._weapon_attack_roll_bonus(hero, tags, is_ranged=False)
        weapon_roll_mod = int(weapon_attack_bonus.get("total", 0) or 0)
        if log_lines:
            try:
                ctx.game.ui_log(f"Modyfikatory ({action_tag}): {', '.join(log_lines)}.")
            except Exception:
                pass
        prompt_long = f"Modyfikator łączny: {modifier:+d} (doliczany automatycznie)."
        if weapon_roll_mod:
            prompt_long = (
                f"{prompt_long}\nBonus broni: {weapon_roll_mod:+d} "
                f"(prof {int(weapon_attack_bonus.get('proficiency_bonus', 0) or 0):+d}, "
                f"ability {int(weapon_attack_bonus.get('ability_bonus', 0) or 0):+d}, "
                f"item {int(weapon_attack_bonus.get('item_bonus', 0) or 0):+d})."
            )
        if trait_notes:
            prompt_long = f"{prompt_long}\n" + "\n".join(trait_notes)

        roll_data = prompt_for_roll(
            f"Atak {self.weapon_label} przeciwko AC {prompt_ac}.",
            layout="test",
            prompt_long=prompt_long,
            modifiers=build_modifiers_grid(best_effects),
            answer_placeholder="Wynik k20",
            return_details=True,
            infer_natural_from_roll=True,
        )
        if isinstance(roll_data, dict):
            roll = int(roll_data.get("roll", 0) or 0)
            natural_shift = int(roll_data.get("natural_shift", 0) or 0)
        else:
            roll = int(roll_data or 0)
            natural_shift = natural_shift_from_roll(roll)

        total_roll = roll + modifier + weapon_roll_mod
        self._consume_aid_attack_bonus(hero, action_tag=action_tag)
        self._consume_monster_hunter_bonus(hero)
        outcome = resolve_outcome(total_roll, target_ac, natural_shift=natural_shift)
        critical = is_critical_success(outcome)
        hit = is_hit(outcome)
        if not hit:
            ctx.game.events.safe_emit_action(
                actor=hero,
                action_id=f"{self.action_id_base}_miss",
                action_tags=tags,
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
            if not exacting_strike_press and not suppress_record:
                self._record_attack(
                    ctx,
                    hero,
                    weapon_key=weapon_key,
                    weapon_type=weapon_type,
                    target=enemy,
                    attack_count=map_attack_count,
                )
            miss_message = f"Atak {self.weapon_label}: pudło."
            if exacting_strike_press:
                miss_message = "Exacting Strike: pudło (MAP bez zmian)."
            self._apply_concealing_trait(hero, tags)
            return EventResult(
                success=True,
                consumed_action=self.consumes_action,
                message=miss_message,
                data={"hit": False, "critical": False, "target": enemy, "target_pos": enemy_pos},
            )

        self._maybe_prompt_vengeful_hatred(hero, enemy)
        effective_damage_prompt, class_upgrade_notes = self._damage_prompt_with_class_upgrades(
            hero,
            weapon_type=weapon_type or getattr(self, "name", None),
            damage_prompt=self.damage_prompt,
            tags=tags,
            is_melee=True,
        )
        two_hand_raw = self._tag_value(tags, "two_hand")
        two_hand_die = self._die_size_from_tag(two_hand_raw)
        if two_hand_die and self._wants_two_hand_usage(
            ctx,
            tags=tags,
            selected_weapon=selected_weapon,
        ):
            effective_damage_prompt = self._replace_first_die_size(effective_damage_prompt, two_hand_die)
            class_upgrade_notes.append(f"Two-Hand: użycie oburącz ({two_hand_die}).")
        effective_damage_prompt, fatal_die = self._fatal_critical_profile(
            tags=tags,
            critical=critical,
            damage_prompt=effective_damage_prompt,
        )
        self._maybe_log_ruffian_crit_spec_placeholder(
            ctx=ctx,
            actor=hero,
            critical=critical,
            is_off_guard=is_off_guard_for_attack,
            weapon_type=weapon_type or getattr(self, "name", None),
            tags=tags,
            damage_prompt=effective_damage_prompt,
        )
        dmg_prompt = (
            f"{'Trafienie krytyczne! ' if critical else 'Trafienie! '}Obrażenia {effective_damage_prompt}: "
        )
        resolved_damage_type = self._choose_damage_type(tags, self.damage_type)
        try:
            if not (getattr(ctx, "metadata", None) or {}).get("skip_dragon_instinct"):
                has_status = getattr(hero, "has_status", None)
                has_rage = False
                if callable(has_status):
                    has_rage = bool(has_status("rage"))
                else:
                    for item in getattr(hero, "statuses", []) or []:
                        if getattr(item, "id", None) == "rage" or item == "rage":
                            has_rage = True
                            break
                if has_rage:
                    getter = getattr(hero, "get_status_data", None)
                    if callable(getter):
                        dragon_type = getter("dragon_instinct_active", "dragon_damage_type", None)
                    else:
                        dragon_type = None
                        for item in getattr(hero, "statuses", []) or []:
                            if getattr(item, "id", None) != "dragon_instinct_active":
                                continue
                            data = getattr(item, "data", None) or {}
                            dragon_type = data.get("dragon_damage_type")
                            break
                    if dragon_type:
                        base_type = (
                            resolved_damage_type
                            if isinstance(resolved_damage_type, str)
                            else list(resolved_damage_type)[0]
                        )
                        if base_type != dragon_type:
                            choice = self._prompt_choice(
                                "Dragon Instinct: wybierz typ obrażeń",
                                choices=[base_type, str(dragon_type)],
                                source="dragon_instinct",
                            )
                            if choice is not None and str(choice).strip().lower() == str(dragon_type).strip().lower():
                                resolved_damage_type = str(dragon_type)
        except Exception:
            pass
        try:
            if not (getattr(ctx, "metadata", None) or {}).get("skip_spirit_instinct"):
                has_status = getattr(hero, "has_status", None)
                has_rage = False
                if callable(has_status):
                    has_rage = bool(has_status("rage"))
                else:
                    for item in getattr(hero, "statuses", []) or []:
                        if getattr(item, "id", None) == "rage" or item == "rage":
                            has_rage = True
                            break
                if has_rage:
                    getter = getattr(hero, "get_status_data", None)
                    if callable(getter):
                        spirit_type = getter("spirit_instinct_active", "spirit_damage_type", None)
                    else:
                        spirit_type = None
                        for item in getattr(hero, "statuses", []) or []:
                            if getattr(item, "id", None) != "spirit_instinct_active":
                                continue
                            data = getattr(item, "data", None) or {}
                            spirit_type = data.get("spirit_damage_type")
                            break
                    if spirit_type and str(spirit_type) != "weapon":
                        base_type = (
                            resolved_damage_type
                            if isinstance(resolved_damage_type, str)
                            else list(resolved_damage_type)[0]
                        )
                        if base_type != spirit_type:
                            choice = self._prompt_choice(
                                "Spirit Instinct: wybierz typ obrażeń",
                                choices=[base_type, str(spirit_type)],
                                source="spirit_instinct",
                            )
                            if choice is not None and str(choice).strip().lower() == str(spirit_type).strip().lower():
                                resolved_damage_type = str(spirit_type)
        except Exception:
            pass
        first_type = resolved_damage_type if isinstance(resolved_damage_type, str) else list(resolved_damage_type)[0]
        note = burn_it_prompt_note(hero, first_type)
        damage_bonus = 0
        damage_notes: list[str] = []
        inspire_bonus = int(inspire_courage_damage_bonus(hero) or 0)
        if inspire_bonus:
            damage_bonus += inspire_bonus
            damage_notes.append(f"Inspire Courage: +{inspire_bonus} do obrazen (doliczone).")
        try:
            from statuses import enfeebled_damage_penalty

            enfeebled_penalty = int(enfeebled_damage_penalty(hero) or 0)
            if enfeebled_penalty > 0:
                damage_bonus -= enfeebled_penalty
                damage_notes.append(f"Enfeebled: -{enfeebled_penalty} do obrazen (doliczone).")
        except Exception:
            pass
        dice_count = self._damage_dice_count(effective_damage_prompt)
        weapon_dice = max(1, int(dice_count or 1))
        vengeful_bonus = self._vengeful_hatred_damage_bonus(hero, enemy, weapon_dice=weapon_dice)
        if vengeful_bonus:
            damage_bonus += vengeful_bonus
            damage_notes.append(f"Vengeful Hatred: +{vengeful_bonus} obrażeń (doliczone).")
        if self._has_trait(tags, "versatile") and not self._tag_value(tags, "versatile"):
            damage_notes.append("Versatile: brak typu w tagu (np. versatile:p) – wybierz ręcznie.")
        deadly_tag = self._tag_value(tags, "deadly")
        deadly_die = self._die_size_from_tag(deadly_tag)
        if self._has_trait(tags, "deadly") and not deadly_die:
            damage_notes.append("Deadly: brak kości w tagu (np. deadly:d8) – dodaj ręcznie.")
        if self._has_trait(tags, "fatal") and not fatal_die:
            damage_notes.append("Fatal: brak kości w tagu (np. fatal:d12) – dodaj ręcznie.")
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
        if allow_auto_precision_bonus and self._has_trait(tags, "backstabber") and is_off_guard_for_attack:
            damage_bonus += 1
            damage_notes.append("Backstabber: +1 precision (doliczone; +2 jeśli broń +3).")
        if is_off_guard_for_attack and self._rogue_sneak_attack_eligible(
            actor=hero,
            target=enemy,
            tags=tags,
            is_ranged=False,
        ):
            sneak_dice = self._rogue_sneak_attack_dice(hero)
            if sneak_dice > 0:
                sneak_roll = prompt_for_roll(
                    f"Sneak Attack: dodatkowe obrażenia {sneak_dice}k6:",
                    layout="damage",
                    answer_placeholder="Sneak attack damage",
                )
                try:
                    sneak_bonus = max(0, int(sneak_roll or 0))
                except Exception:
                    sneak_bonus = 0
                if sneak_bonus > 0:
                    damage_bonus += sneak_bonus
                    damage_notes.append(f"Sneak Attack: +{sneak_bonus} precision (doliczone).")
        if self._ranger_precision_ready(ctx, hero, enemy):
            precision_roll = prompt_for_roll(
                "Hunter's Edge (Precision): dodatkowe obrażenia 1k8:",
                layout="damage",
                answer_placeholder="Precision damage",
            )
            try:
                precision_bonus = max(0, int(precision_roll or 0))
            except Exception:
                precision_bonus = 0
            self._mark_ranger_precision(ctx, hero, enemy)
            if precision_bonus > 0:
                damage_bonus += precision_bonus
                damage_notes.append(f"Hunter's Edge (Precision): +{precision_bonus} precision (doliczone).")
        try:
            from statuses.rage import rage_damage_bonus

            rage_bonus = rage_damage_bonus(hero, is_agile=self._has_trait(tags, "agile"))
            if rage_bonus:
                damage_bonus += rage_bonus
                if self._has_trait(tags, "agile"):
                    damage_notes.append(f"Rage: +{rage_bonus} dmg (agile).")
                else:
                    damage_notes.append(f"Rage: +{rage_bonus} dmg.")
        except Exception:
            pass
        propulsive_bonus = self._propulsive_damage_bonus(hero, tags)
        if propulsive_bonus:
            damage_bonus += propulsive_bonus
            damage_notes.append(f"Propulsive: {propulsive_bonus:+d} do obrażeń (doliczone).")
        damage_notes.extend(class_upgrade_notes)
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
            damage_prompt_override=effective_damage_prompt,
        )
        try:
            ignore_incorporeal = _ignores_incorporeal(hero)
            if (
                critical
                and self.critical_doubles_damage
                and not (is_target_incorporeal(enemy) and not ignore_incorporeal)
            ):
                damage_components = [(dtype, int(amt) * 2) for dtype, amt in damage_components]
            damage_components = _apply_incorporeal_reductions(
                enemy, damage_components, ignore=ignore_incorporeal, tags=tags
            )
        except Exception:
            pass
        if critical:
            crit_resistance = self._critical_hit_resistance(enemy)
            if crit_resistance > 0:
                damage_components = self._reduce_damage_components(damage_components, crit_resistance)
                try:
                    ctx.game.ui_log(
                        f"{getattr(enemy, 'name', 'Cel')}: odporność na critical hit redukuje obrażenia o {crit_resistance}."
                    )
                except Exception:
                    pass
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
        if critical and fatal_die:
            extra = prompt_for_roll(
                f"Fatal {fatal_die}: dodatkowa kość obrażeń (rzut): ",
                layout="damage",
                answer_placeholder="Dodatkowe obrażenia",
            )
            try:
                damage_components.append((first_type, int(extra)))
            except Exception:
                pass
        if power_attack_extra_dice > 0:
            extra = prompt_for_roll(
                f"Power Attack: dodatkowe obrażenia ({power_attack_extra_dice}k): ",
                layout="damage",
                answer_placeholder="Dodatkowe obrażenia",
            )
            try:
                damage_components.append((first_type, int(extra)))
            except Exception:
                pass
        ki_formula = str(metadata.get("ki_strike_extra_formula", "") or "").strip()
        ki_damage_type = str(metadata.get("ki_strike_extra_damage_type", "") or "").strip().lower()
        if ki_formula and ki_damage_type:
            extra = prompt_for_roll(
                f"Ki Strike: dodatkowe obrażenia ({ki_formula} {ki_damage_type}) - podaj wynik:",
                layout="damage",
                answer_placeholder="Dodatkowe obrażenia",
            )
            try:
                damage_components.append((ki_damage_type, int(extra)))
            except Exception:
                pass
        if critical:
            try:
                from GameObjects.items.armor import apply_critical_damage_reduction

                damage_components, armor_notes = apply_critical_damage_reduction(
                    enemy,
                    damage_components,
                    critical=True,
                )
                for note_line in armor_notes:
                    try:
                        ctx.game.ui_log(note_line)
                    except Exception:
                        pass
            except Exception:
                pass

        pending_persistent_payload = None
        persistent_payload = metadata.get("on_hit_persistent_damage")
        if isinstance(persistent_payload, dict):
            critical_only = bool(persistent_payload.get("on_critical_only", False))
            if (not critical_only) or critical:
                pending_persistent_payload = dict(persistent_payload)

        if roll_only:
            total_damage = sum(max(0, int(amount or 0)) for _, amount in damage_components)
            ctx.game.events.safe_emit_action(
                actor=hero,
                action_id=self.action_id_base,
                action_tags=tags,
                target=enemy,
                target_pos=enemy_pos,
                damage=total_damage,
                damage_components=damage_components,
                defeated=False,
                roll_only=True,
                nonlethal=nonlethal_attack,
            )
            if not suppress_record:
                self._record_attack(
                    ctx,
                    hero,
                    weapon_key=weapon_key,
                    weapon_type=weapon_type,
                    target=enemy,
                    attack_count=map_attack_count,
                )
            try:
                refresh_flanking_statuses(ctx.game)
            except Exception as exc:
                logger.error("Nie udało się odświeżyć flankowania: %s", exc)
            msg = "Trafienie krytyczne!" if critical else f"Atak {self.weapon_label} trafia."
            self._apply_concealing_trait(hero, tags)
            return EventResult(
                success=True,
                consumed_action=self.consumes_action,
                message=f"{msg} Obrażenia do rozliczenia przez efekt zewnętrzny.",
                data={
                    "hit": True,
                    "critical": critical,
                    "defeated": False,
                    "target": enemy,
                    "target_pos": enemy_pos,
                    "damage_components": list(damage_components),
                    "damage_total": int(total_damage),
                    "roll_only": True,
                    "pending_persistent_payload": pending_persistent_payload,
                    "nonlethal": nonlethal_attack,
                },
            )

        crit_spec_notes = self._apply_weapon_critical_specialization(
            ctx,
            actor=hero,
            target=enemy,
            critical=critical,
            is_off_guard=is_off_guard_for_attack,
            weapon_type=weapon_type,
            tags=tags,
            selected_weapon=selected_weapon,
            damage_prompt=effective_damage_prompt,
            damage_components=damage_components,
            default_damage_type=first_type,
            roll_for_bleed=prompt_for_roll,
        )
        for note_line in crit_spec_notes:
            try:
                ctx.game.ui_log(note_line)
            except Exception:
                pass

        defeated = False
        try:
            defeated = self._apply_damage_components(enemy, damage_components, nonlethal=nonlethal_attack)
        except Exception as exc:
            logger.error("Nie udało się zadać obrażeń: %s", exc)
            return EventResult(success=False, consumed_action=False, message=str(exc))

        if pending_persistent_payload:
            self._apply_on_hit_persistent(enemy, pending_persistent_payload, ctx=ctx, source=self.action_id_base)

        ctx.game.events.safe_emit_action(
            actor=hero,
            action_id=self.action_id_base,
            action_tags=tags,
            target=enemy,
            target_pos=enemy_pos,
            damage=sum(d for _, d in damage_components),
            damage_components=damage_components,
            defeated=defeated,
            nonlethal=nonlethal_attack,
        )
        if not suppress_record:
            self._record_attack(
                ctx,
                hero,
                weapon_key=weapon_key,
                weapon_type=weapon_type,
                target=enemy,
                attack_count=map_attack_count,
            )

        if defeated:
            try:
                from GameObjects.events.rogue_feat_events import try_trigger_youre_next

                try_trigger_youre_next(ctx, hero, defeated_target=enemy)
            except Exception:
                pass
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
        self._apply_concealing_trait(hero, tags)
        return EventResult(
            success=True,
            consumed_action=self.consumes_action,
            message=msg,
            data={"hit": True, "critical": critical, "defeated": defeated, "target": enemy, "target_pos": enemy_pos},
        )

    # --- helpers ---
    def _apply_concealing_trait(self, actor, tags: Iterable[str]) -> None:
        if actor is None or not self._has_trait(tags, "concealing"):
            return
        has_status = getattr(actor, "has_status", None)
        try:
            if callable(has_status) and has_status("concealed"):
                return
        except Exception:
            pass
        try:
            actor.add_status(Status(id="concealed", label="Concealed", duration=1, source="trait:concealing"))
        except Exception:
            return

    def _collect_damage_components(
        self,
        first_roll: int,
        *,
        actor=None,
        damage_type_override: str | Sequence[str] | None = None,
        flat_bonus: int = 0,
        damage_prompt_override: str | Sequence[str] | None = None,
    ) -> list[tuple[str, int]]:
        """Zwraca listę (typ, obrażenia) – obsługa wielu typów."""
        damage_prompt = damage_prompt_override if damage_prompt_override is not None else self.damage_prompt
        damage_type = damage_type_override if damage_type_override is not None else self.damage_type
        if isinstance(damage_type, str):
            bonus = burn_it_bonus(actor, damage_type)
            return [(damage_type, int(first_roll) + int(bonus) + int(flat_bonus))]
        components: list[tuple[str, int]] = []
        damage_types = list(damage_type)
        bonus = burn_it_bonus(actor, damage_types[0])
        components.append((damage_types[0], int(first_roll) + int(bonus) + int(flat_bonus)))
        for idx, dtype in enumerate(damage_types[1:], start=1):
            prompt_text = damage_prompt
            if isinstance(damage_prompt, (list, tuple)):
                prompt_text = damage_prompt[idx] if idx < len(damage_prompt) else damage_prompt[-1]
            prompt = f"Trafienie! Obrażenia dodatkowe {prompt_text} ({dtype}): "
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
    def _apply_damage_components(target, comps: Iterable[tuple[str, int]], *, nonlethal: bool = False) -> bool:
        defeated = False
        for dmg_type, amount in comps:
            try:
                _, defeated = target.apply_damage(amount, dmg_type, nonlethal=bool(nonlethal))
            except TypeError:
                _, defeated = target.apply_damage(amount, dmg_type)
        return defeated

    @staticmethod
    def _critical_hit_resistance(target) -> int:
        statuses = getattr(target, "statuses", None)
        if not isinstance(statuses, list):
            return 0
        best = 0
        for status in statuses:
            data = getattr(status, "data", None) or {}
            try:
                value = int(data.get("critical_hit_resistance", 0) or 0)
            except Exception:
                value = 0
            if value > best:
                best = value
        return max(0, int(best))

    @staticmethod
    def _reduce_damage_components(
        components: list[tuple[str, int]],
        reduction: int,
    ) -> list[tuple[str, int]]:
        left = max(0, int(reduction or 0))
        if left <= 0:
            return list(components)
        reduced: list[tuple[str, int]] = []
        for dtype, amount in components:
            dmg = max(0, int(amount))
            if left <= 0:
                reduced.append((dtype, dmg))
                continue
            take = min(dmg, left)
            left -= take
            reduced.append((dtype, max(0, dmg - take)))
        return reduced

    def _apply_on_hit_persistent(self, target, payload, *, ctx: EventContext, source: str) -> None:
        if target is None:
            return
        if not isinstance(payload, dict):
            return
        formula = str(payload.get("formula", "") or "").strip().lower()
        damage_type = str(payload.get("damage_type", DamageType.BLEED.value) or DamageType.BLEED.value)
        if not formula:
            return
        amount = 0
        if formula.isdigit():
            amount = int(formula)
        else:
            rolled = prompt_for_roll(
                f"Persistent on hit ({formula} {damage_type}) - podaj wynik:",
                layout="damage",
                answer_placeholder="Persistent",
            )
            try:
                amount = int(rolled or 0)
            except Exception:
                amount = 0
        if amount <= 0:
            return
        try:
            adder = getattr(target, "add_status", None)
            if callable(adder):
                adder(make_persistent_damage(amount, damage_type, source=source))
            else:
                statuses = getattr(target, "statuses", None)
                if isinstance(statuses, list):
                    statuses.append(make_persistent_damage(amount, damage_type, source=source))
            ctx.game.ui_log(
                f"{getattr(target, 'name', 'Cel')} otrzymuje persistent {damage_type} {amount}."
            )
        except Exception:
            pass

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
