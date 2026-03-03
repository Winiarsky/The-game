from __future__ import annotations

import logging
import math
from typing import Sequence

from bonuses import BonusEffect, BonusType, build_modifiers_grid
from GameObjects.interactions_mixin import RangeAttackAffectMixin, prompt_for_roll
from statuses import Status, inspire_courage_damage_bonus
from damage_types import DamageType
from combat.damage_utils import burn_it_bonus, burn_it_prompt_note
from combat.degree_of_success import is_critical_success, is_hit, natural_shift_from_roll, resolve_outcome

from .attack_base import AttackEventBase, check_concealed
from . import basic_melee_attack_event
from ..targeting import is_target_blocked_by_tags
from ..base import EventContext, EventResult

logger = logging.getLogger(__name__)


CoverType = str


class BaseRangeAttackEvent(AttackEventBase):
    """Wspólna logika dla ataków dystansowych (łuki, kusze itd.)."""

    weapon_label: str = "bronią dystansową"
    damage_prompt: str | Sequence[str] = "1k6 + DEX"
    action_id_base: str = "attack_ranged"
    damage_type: str | Sequence[str] = DamageType.PIERCING.value
    range_increment_ft: int = 60
    max_range_increments: int = 6
    feet_per_cell: int = 5
    default_tags = ["attack_ranged", "ranged_attack"]
    consumes_action = True
    critical_doubles_damage: bool = False

    COVER_RANK = {"none": 0, "minor": 1, "standard": 2, "greater": 3, "block": 4}
    COVER_AC = {"minor": 1, "standard": 2, "greater": 4}
    COVER_LED = {
        "minor": [30, 120, 0],
        "standard": [90, 90, 0],
        "greater": [150, 60, 0],
        "block": [180, 0, 0],
    }
    TARGET_LED = [0, 40, 140]

    # --- main flow ---
    def execute(self, ctx: EventContext) -> EventResult:  # noqa: C901
        game = ctx.game
        hero = ctx.actor
        if hero is None:
            return EventResult.cancelled(message="Brak bohatera do ataku dystansowego.")
        if self._has_status_id(hero, "monk_stance_active"):
            stance_label = str(getattr(hero, "get_status_data", lambda *_a, **_k: "")("monk_stance_active", "stance_label", "") or "")
            if not stance_label:
                stance_label = "Monk Stance"
            return EventResult.cancelled(
                message=f"{stance_label}: twarda blokada Strike'ów spoza stance (użyj unarmed/flurry_of_blows)."
            )
        if getattr(hero, "has_status", lambda _s: False)("restrained"):
            return EventResult.cancelled(message="Nie możesz wykonywać ataków dystansowych będąc restrained.")
        hero_pos = getattr(hero, "position", None)
        if hero_pos is None:
            return EventResult.cancelled(message="Bohater nie stoi na planszy.")

        candidates = [(e, getattr(e, "position", None)) for e in getattr(game, "enemies", [])]
        candidates = [(e, pos) for e, pos in candidates if pos is not None]
        tags = self._effective_tags(ctx)
        metadata = dict(getattr(ctx, "metadata", None) or {})
        candidates = [(e, pos) for e, pos in candidates if not is_target_blocked_by_tags(e, tags)]
        if not candidates:
            return EventResult.cancelled(message="Brak wrogów na planszy.")

        analyses = []
        for enemy, pos in candidates:
            analysis = self._analyze_shot(game, hero_pos, pos, target=enemy)
            analysis["enemy"] = enemy
            analyses.append(analysis)

        # LED: przeszkody + potencjalne cele
        led_positions: list[tuple[int, int]] = []
        led_colors: list[list[int]] = []
        obstacle_led: dict[tuple[int, int], CoverType] = {}
        for analysis in analyses:
            for obs in analysis.get("obstacles", []):
                for p in obs["positions"]:
                    current = obstacle_led.get(p, "none")
                    if self.COVER_RANK[obs["cover_type"]] > self.COVER_RANK[current]:
                        obstacle_led[p] = obs["cover_type"]
        for pos, ctype in obstacle_led.items():
            led_positions.append(pos)
            led_colors.append(self.COVER_LED.get(ctype, self.COVER_LED["standard"]))

        hittable = [a for a in analyses if not a["blocked"]]
        for analysis in hittable:
            led_positions.append(analysis["target_pos"])
            led_colors.append(self.TARGET_LED)

        if led_positions:
            try:
                game.conn.set_leds(led_positions, led_colors)
            except Exception as exc:
                logger.warning("Nie udało się ustawić LEDów: %s", exc)

        try:
            if not hittable:
                return EventResult.cancelled(message="Brak wrogów w zasięgu lub linia strzału zablokowana.")

            target_pos_list = [a["target_pos"] for a in hittable]
            try:
                choice = game.conn.scan_board(target_pos_list)
            except Exception:
                choice = None
            target_analysis = None
            for a in hittable:
                if a["target_pos"] == choice:
                    target_analysis = a
                    break
            if target_analysis is None:
                return EventResult.cancelled(message="Nie wybrano poprawnego celu.")

            enemy = target_analysis["enemy"]
            target_pos = target_analysis["target_pos"]
            cover_type = target_analysis["cover_type"]
            cover_bonus = self.COVER_AC.get(cover_type, 0)
            distance_ft = target_analysis["distance_ft"]
            range_penalty = target_analysis["range_penalty"]
            increments = target_analysis["increments"]
            target_id = self._target_id(enemy)

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

            if not check_concealed(ctx, enemy):
                game.events.safe_emit_action(
                    actor=hero,
                    action_id=f"{self.action_id_base}_concealed_miss",
                    action_tags=self._effective_tags(ctx),
                    target=enemy,
                    target_pos=target_pos,
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
                self._apply_range_attacker_status(hero)
                return EventResult(
                    success=True,
                    consumed_action=self.consumes_action,
                    message="Strzał chybia (concealed).",
                    data={"hit": False, "critical": False, "target": enemy, "target_pos": target_pos},
                )

            cover_bonus_effect = None
            if cover_bonus:
                cover_bonus_effect = BonusEffect(
                    type=BonusType.CIRCUMSTANCE,
                    value=cover_bonus,
                    tag="ac",
                    source=f"cover:{cover_type}",
                    target_id=getattr(hero, "object_id", None),
                    label=f"osłona ({cover_type})",
                )

            game.events.safe_emit_action(
                actor=hero,
                action_id=f"{self.action_id_base}_pre",
                action_tags=self._effective_tags(ctx),
                target=enemy,
                target_pos=target_pos,
            )

            extra_bonuses = []
            if cover_bonus_effect:
                extra_bonuses.append(cover_bonus_effect)
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

            mods: list[str] = []
            if cover_bonus:
                mods.append(f"+{cover_bonus} osłona ({cover_type})")
            if range_penalty:
                mods.append(f"-{range_penalty} zasięg ({increments}x{self.range_increment_ft} stóp)")
            mods_note = "; ".join(mods) if mods else "brak"

            action_tag = (self._effective_tags(ctx) or ["attack_ranged"])[0]
            extra_effects = []
            trait_notes: list[str] = []
            has_point_blank_shot = bool(getattr(hero, "has_status", lambda *_a, **_k: False)("point_blank_shot_stance"))
            has_volley_trait = self._has_trait(tags, "volley")
            if range_penalty:
                extra_effects.append(
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=range_penalty,
                        tag=action_tag,
                        source="range_penalty",
                        label=f"zasięg {increments}x{self.range_increment_ft}",
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
            volley_range = self._tag_value(tags, "volley")
            if has_point_blank_shot and has_volley_trait:
                trait_notes.append("Point-Blank Shot: kara volley zignorowana.")
            elif volley_range:
                try:
                    volley_ft = int(volley_range)
                except Exception:
                    volley_ft = 0
                if volley_ft > 0 and distance_ft <= volley_ft:
                    extra_effects.append(
                        BonusEffect(
                            type=BonusType.CIRCUMSTANCE,
                            value=2,
                            tag=action_tag,
                            source="volley",
                            label=f"volley {volley_ft}ft",
                            is_penalty=True,
                        )
                    )
            elif has_volley_trait:
                trait_notes.append("Volley: brak zasięgu w tagu (np. volley:30) – dodaj ręcznie.")
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
            try:
                from statuses.clumsy import clumsy_attack_penalty_effects

                extra_effects.extend(
                    clumsy_attack_penalty_effects(
                        hero,
                        action_tag=action_tag,
                        is_ranged=True,
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
            modifier, best_effects, log_lines = self._attack_modifier_details(
                hero, action_tag, target=enemy, extra_effects=extra_effects
            )
            if log_lines:
                try:
                    game.ui_log(f"Modyfikatory ({action_tag}): {', '.join(log_lines)}.")
                except Exception:
                    pass
            prompt_long = f"Modyfikator łączny: {modifier:+d} (doliczany automatycznie)."
            if trait_notes:
                prompt_long = f"{prompt_long}\n" + "\n".join(trait_notes)

            roll_data = prompt_for_roll(
                f"Atak {self.weapon_label} na AC {target_ac}",
                layout="test",
                subtitle=f"bazowe {base_ac}, modyfikatory: {mods_note}",
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

            total_roll = roll + modifier
            self._consume_aid_attack_bonus(hero, action_tag=action_tag)
            outcome = resolve_outcome(total_roll, target_ac, natural_shift=natural_shift)
            critical = is_critical_success(outcome)
            hit = is_hit(outcome)
            if not hit:
                game.events.safe_emit_action(
                    actor=hero,
                    action_id=f"{self.action_id_base}_miss",
                    action_tags=self._effective_tags(ctx),
                    target=enemy,
                    target_pos=target_pos,
                    roll=roll,
                    target_ac=target_ac,
                    cover=cover_type,
                    range_penalty=range_penalty,
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
                self._apply_range_attacker_status(hero)
                miss_message = "Strzał chybia."
                if exacting_strike_press:
                    miss_message = "Exacting Strike: pudło (MAP bez zmian)."
                return EventResult(
                    success=True,
                    consumed_action=self.consumes_action,
                    message=miss_message,
                    data={"hit": False, "critical": False, "target": enemy, "target_pos": target_pos},
                )

            prompt_prefix = "Trafienie krytyczne! " if critical else "Trafienie! "
            self._maybe_prompt_vengeful_hatred(hero, enemy)
            effective_damage_prompt, class_upgrade_notes = self._damage_prompt_with_class_upgrades(
                hero,
                weapon_type=getattr(self, "name", None),
                damage_prompt=self.damage_prompt,
            )
            resolved_damage_type = self._choose_damage_type(tags, self.damage_type)
            try:
                if self._has_trait(tags, "thrown"):
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
                if self._has_trait(tags, "thrown"):
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
            damage_bonus = 0
            damage_notes: list[str] = []
            inspire_bonus = int(inspire_courage_damage_bonus(hero) or 0)
            if inspire_bonus:
                damage_bonus += inspire_bonus
                damage_notes.append(f"Inspire Courage: +{inspire_bonus} do obrazen (doliczone).")
            if has_point_blank_shot and not has_volley_trait and distance_ft <= int(self.range_increment_ft):
                damage_bonus += 2
                damage_notes.append("Point-Blank Shot: +2 circumstance do obrażeń (1. przyrost zasięgu).")
            try:
                from statuses import enfeebled_damage_penalty

                enfeebled_penalty = int(enfeebled_damage_penalty(hero) or 0)
                if enfeebled_penalty > 0:
                    damage_bonus -= enfeebled_penalty
                    damage_notes.append(f"Enfeebled: -{enfeebled_penalty} do obrazen (doliczone).")
            except Exception:
                pass
            dice_count = self._damage_dice_count(effective_damage_prompt)
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
            try:
                if self._has_trait(tags, "thrown"):
                    has_status = getattr(hero, "has_status", None)
                    has_rage = False
                    has_thrower = False
                    if callable(has_status):
                        has_rage = has_status("rage")
                        has_thrower = has_status("raging_thrower")
                    else:
                        for item in getattr(hero, "statuses", []) or []:
                            sid = getattr(item, "id", None)
                            if sid == "rage" or item == "rage":
                                has_rage = True
                            if sid == "raging_thrower" or item == "raging_thrower":
                                has_thrower = True
                    if has_rage and has_thrower:
                        from statuses.rage import rage_damage_bonus

                        rage_bonus = rage_damage_bonus(hero, is_agile=self._has_trait(tags, "agile"))
                        if rage_bonus:
                            damage_bonus += rage_bonus
                            if self._has_trait(tags, "agile"):
                                damage_notes.append(f"Raging Thrower: +{rage_bonus} dmg (agile).")
                            else:
                                damage_notes.append(f"Raging Thrower: +{rage_bonus} dmg.")
            except Exception:
                pass
            if self._has_trait(tags, "propulsive"):
                damage_notes.append("Propulsive: dodaj 1/2 STR do obrażeń (ręcznie).")
            if self._has_trait(tags, "fatal"):
                damage_notes.append("Fatal: zmień kości bazowe i dodaj 1 kość fatal (ręcznie).")
            if self._has_trait(tags, "two_hand"):
                damage_notes.append("Two-Hand: użycie dwuręczne zmienia kości obrażeń (ręcznie).")
            damage_notes.extend(class_upgrade_notes)
            damage_components = self._collect_damage_components(
                actor=hero,
                prompt_prefix=prompt_prefix,
                damage_type_override=resolved_damage_type,
                flat_bonus=damage_bonus,
                extra_notes=damage_notes,
                damage_prompt_override=effective_damage_prompt,
            )
            try:
                ignore_incorporeal = basic_melee_attack_event._ignores_incorporeal(hero)
                if (
                    critical
                    and self.critical_doubles_damage
                    and not (basic_melee_attack_event.is_target_incorporeal(enemy) and not ignore_incorporeal)
                ):
                    damage_components = [(dtype, int(amt) * 2) for dtype, amt in damage_components]
                damage_components = basic_melee_attack_event._apply_incorporeal_reductions(
                    enemy, damage_components, ignore=ignore_incorporeal, tags=tags
                )
            except Exception:
                pass
            first_type = resolved_damage_type if isinstance(resolved_damage_type, str) else list(resolved_damage_type)[0]
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
                logger.error("Błąd przy zadawaniu obrażeń: %s", exc)
                return EventResult(success=False, consumed_action=False, message=str(exc))

            game.events.safe_emit_action(
                actor=hero,
                action_id=self.action_id_base,
                action_tags=self._effective_tags(ctx),
                target=enemy,
                target_pos=target_pos,
                damage=sum(d for _, d in damage_components),
                damage_components=damage_components,
                defeated=defeated,
                cover=cover_type,
                range_penalty=range_penalty,
                critical=critical,
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
                    game.board.remove(target_pos)
                    try:
                        game.enemies.remove(enemy)
                    except ValueError:
                        pass
                except Exception as exc:
                    logger.error("Nie udało się usunąć wroga: %s", exc)
                enemy.position = None

            self._apply_range_attacker_status(hero)
            msg = "Przeciwnik pokonany." if defeated else ("Trafienie krytyczne!" if critical else f"Atak {self.weapon_label} trafia.")
            return EventResult(
                success=True,
                consumed_action=self.consumes_action,
                message=msg,
                data={"hit": True, "critical": critical, "defeated": defeated, "target": enemy, "target_pos": target_pos},
            )
        finally:
            try:
                game.conn.leds_off()
            except Exception:
                pass

    # --- helpers ---
    def _apply_range_attacker_status(self, hero) -> None:
        try:
            if hasattr(hero, "add_status"):
                hero.add_status(Status(id="range_attacker", label="Range attacker"))
        except Exception:
            logger.debug("Nie udało się nadać statusu range_attacker.", exc_info=True)

    def _cover_rank(self, cover_type: CoverType) -> int:
        return self.COVER_RANK.get(cover_type, 0)

    # --- damage helpers ---
    def _collect_damage_components(
        self,
        *,
        actor=None,
        prompt_prefix: str = "",
        damage_type_override: str | Sequence[str] | None = None,
        flat_bonus: int = 0,
        extra_notes: list[str] | None = None,
        damage_prompt_override: str | Sequence[str] | None = None,
    ) -> list[tuple[str, int]]:
        """Pozyskaj wartości obrażeń dla 1+ typów."""
        damage_prompt = damage_prompt_override if damage_prompt_override is not None else self.damage_prompt
        damage_type = damage_type_override if damage_type_override is not None else self.damage_type
        if isinstance(damage_type, str):
            note = burn_it_prompt_note(actor, damage_type)
            if extra_notes:
                note = f"{note}\n" + "\n".join(extra_notes) if note else "\n".join(extra_notes)
            dmg = prompt_for_roll(
                f"{prompt_prefix}Obrażenia {damage_prompt}: ",
                layout="damage",
                answer_placeholder="Suma obrażeń",
                prompt_long=note,
            )
            bonus = burn_it_bonus(actor, damage_type)
            return [(damage_type, int(dmg) + int(bonus) + int(flat_bonus))]

        damage_types = list(damage_type)
        components: list[tuple[str, int]] = []
        for idx, dtype in enumerate(damage_types):
            prompt = damage_prompt
            if isinstance(prompt, (list, tuple)):
                prompt_text = prompt[idx] if idx < len(prompt) else prompt[-1]
            else:
                prompt_text = prompt
            note = burn_it_prompt_note(actor, dtype)
            if idx == 0 and extra_notes:
                note = f"{note}\n" + "\n".join(extra_notes) if note else "\n".join(extra_notes)
            roll = prompt_for_roll(
                f"{prompt_prefix}Obrażenia {prompt_text} ({dtype}): ",
                layout="damage",
                answer_placeholder=f"Obrażenia {dtype}",
                prompt_long=note,
            )
            bonus = burn_it_bonus(actor, dtype)
            total = int(roll) + int(bonus)
            if idx == 0:
                total += int(flat_bonus)
            components.append((dtype, total))
        return components

    @staticmethod
    def _apply_damage_components(target, comps):
        defeated = False
        for dmg_type, amount in comps:
            _, defeated = target.apply_damage(amount, dmg_type)
        return defeated

    def _line_cells(self, start: tuple[int, int], end: tuple[int, int]) -> list[tuple[int, int]]:
        """Prosty Bresenham na siatce."""
        x0, y0 = start
        x1, y1 = end
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        cells: list[tuple[int, int]] = []
        while True:
            cells.append((x, y))
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy
        return cells

    def _analyze_shot(self, game, start: tuple[int, int], end: tuple[int, int], *, target) -> dict:
        board = game.board
        line = self._line_cells(start, end)
        obstacles: list[dict] = []
        cover_type: CoverType = "none"
        blocked = False
        seen_ids: set[int] = set()

        # dystans / zakres
        dx, dy = abs(start[0] - end[0]), abs(start[1] - end[1])
        distance_ft = math.sqrt(dx * dx + dy * dy) * self.feet_per_cell
        increments = max(1, math.ceil(distance_ft / self.range_increment_ft))
        range_penalty = max(0, increments - 1) * 2
        if increments > self.max_range_increments:
            blocked = True
            cover_type = "block"

        # pola pomiędzy
        for idx, pos in enumerate(line[1:]):  # pomijamy start
            if pos == end:
                break
            occupant = board.occupant_at(pos)
            if occupant is target:
                continue
            ctype = None
            if occupant:
                if occupant in getattr(game, "heroes", []):
                    ctype = None  # sojusznik nie daje osłony
                elif occupant in getattr(game, "enemies", []):
                    ctype = "minor"
                elif isinstance(occupant, RangeAttackAffectMixin):
                    ctype = occupant.range_cover_type()
            if ctype:
                obstacles.append({"positions": [pos], "cover_type": ctype, "source": occupant})
                if self._cover_rank(ctype) > self._cover_rank(cover_type):
                    cover_type = ctype
                if ctype == "block":
                    blocked = True

            for obj in board.interactables_at(pos):
                if id(obj) in seen_ids:
                    continue
                if isinstance(obj, RangeAttackAffectMixin):
                    seen_ids.add(id(obj))
                    ctype = obj.range_cover_type()
                    obstacles.append({"positions": [pos], "cover_type": ctype, "source": obj})
                    if self._cover_rank(ctype) > self._cover_rank(cover_type):
                        cover_type = ctype
                    if ctype == "block":
                        blocked = True

        # krawędzie między kolejnymi polami
        for a, b in zip(line, line[1:]):
            if board.is_blocked(a, b):
                ctype = "block"
                obstacles.append({"positions": [a, b], "cover_type": ctype, "source": board.get_wall(a, b)})
                cover_type = "block"
                blocked = True
            for obj in board.edge_interactables_between(a, b):
                if id(obj) in seen_ids:
                    continue
                if isinstance(obj, RangeAttackAffectMixin):
                    seen_ids.add(id(obj))
                    ctype = obj.range_cover_type()
                    obstacles.append({"positions": [a, b], "cover_type": ctype, "source": obj})
                    if self._cover_rank(ctype) > self._cover_rank(cover_type):
                        cover_type = ctype
                    if ctype == "block":
                        blocked = True

        if getattr(target, "has_status", lambda _s: False)("prone"):
            if self._cover_rank("greater") > self._cover_rank(cover_type):
                cover_type = "greater"

        return {
            "target_pos": end,
            "cover_type": cover_type,
            "blocked": blocked,
            "obstacles": obstacles,
            "distance_ft": distance_ft,
            "increments": increments,
            "range_penalty": range_penalty,
        }
