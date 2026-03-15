from __future__ import annotations

import logging
from typing import Iterable, Optional
import re

from bonuses import BonusEffect, BonusType, compute_total_modifier, format_effects_log, select_best_effects
from damage_types import DamageType
from combat import ac_with_bonuses
from GameObjects.interactions_mixin import prompt_for_roll
from statuses import (
    CONCEALED_STATUS,
    DARKVISION_STATUS,
    DIM_LIGHT_VISION_STATUS,
    IN_DIM_LIGHT_STATUS,
    LOW_LIGHT_VISION_STATUS,
    visibility_block_reason,
    visibility_flat_check_dc,
    attack_penalty_effects,
)

from ..base import GameEvent, mapping_setdefault_actor

logger = logging.getLogger(__name__)


def check_concealed(ctx, target) -> bool:
    if target is None:
        return True
    try:
        from GameObjects.events.magic.lighting_effects import is_position_illuminated

        if is_position_illuminated(ctx.game, getattr(target, "position", None)):
            return True
    except Exception:
        pass
    attacker = getattr(ctx, "actor", None)
    if _has_status(attacker, DARKVISION_STATUS):
        return True
    if (_has_status(attacker, DIM_LIGHT_VISION_STATUS) or _has_status(attacker, LOW_LIGHT_VISION_STATUS)) and _has_status(
        target, IN_DIM_LIGHT_STATUS
    ):
        return True
    blocked = visibility_block_reason(attacker, target)
    if blocked:
        try:
            ctx.game.ui_log(blocked)
        except Exception:
            pass
        return False
    ignore_target_concealed = False
    has_status = getattr(target, "has_status", None)
    if callable(has_status):
        ignore_target_concealed = not bool(has_status(CONCEALED_STATUS))
    else:
        ignore_target_concealed = True
        for status in getattr(target, "statuses", []) or []:
            if getattr(status, "id", None) == CONCEALED_STATUS.id or status == CONCEALED_STATUS.id:
                ignore_target_concealed = False
                break
    dc = visibility_flat_check_dc(attacker, target, ignore_target_concealed=ignore_target_concealed)
    if _has_status(attacker, "keen_eyes"):
        concealed_dc = 3
        hidden_dc = 9
        getter = getattr(attacker, "get_status_data", None)
        if callable(getter):
            try:
                concealed_dc = int(getter("keen_eyes", "concealed_flat_check_dc_override", concealed_dc) or concealed_dc)
            except Exception:
                concealed_dc = 3
            try:
                hidden_dc = int(getter("keen_eyes", "hidden_flat_check_dc_override", hidden_dc) or hidden_dc)
            except Exception:
                hidden_dc = 9
        if dc == 5:
            dc = concealed_dc
        elif dc >= 11 and _has_status(target, "hidden"):
            dc = hidden_dc
    if dc <= 0:
        return True
    roll = prompt_for_roll(
        f"Concealed: rzut k20 (DC {dc}) przed atakiem.",
        layout="test",
        subtitle="Flat check bez premii.",
        answer_placeholder="Wynik k20",
    )
    if roll >= dc:
        return True
    try:
        ui = getattr(ctx.game, "ui", None)
        if ui is not None and hasattr(ui, "prompt_info"):
            ui.prompt_info(
                "Atak chybia",
                prompt_long="Nie trafiłeś z powodu zaciemnienia (concealed).",
                source="concealed",
            )
        else:
            ctx.game.ui_log("Nie trafiłeś z powodu zaciemnienia (concealed).")
    except Exception:
        pass
    return False


def _has_status(obj, status) -> bool:
    if obj is None:
        return False
    wanted = getattr(status, "id", status)
    has_status = getattr(obj, "has_status", None)
    if callable(has_status):
        return bool(has_status(wanted))
    for item in getattr(obj, "statuses", []) or []:
        item_id = getattr(item, "id", None)
        if item_id == wanted or item == wanted:
            return True
    return False


class AttackEventBase(GameEvent):
    """Wspólne helpery dla wszystkich eventów ataku (wręcz i dystans)."""
    _DEIFIC_DIE_UPGRADE = {
        "4": "6",
        "6": "8",
        "8": "10",
        "10": "12",
    }
    _ALT_UNARMED_PROFILE_STATUS_IDS = {
        "wild_shape_active",
        "wild_morph_active",
        "animal_instinct_active",
        "monk_stance_active",
    }
    _WEAPON_GROUP_BY_WEAPON = {
        "dagger": "knife",
        "club": "club",
        "mace": "club",
        "spear": "spear",
        "javelin": "spear",
        "sword": "sword",
        "longsword": "sword",
        "shortsword": "sword",
        "rapier": "sword",
        "greataxe": "axe",
        "warhammer": "hammer",
        "halberd": "polearm",
        "glaive": "polearm",
        "shortbow": "bow",
        "longbow": "bow",
        "bow": "bow",
        "crossbow": "crossbow",
        "light_crossbow": "crossbow",
        "simple_crossbow": "crossbow",
    }
    _SIMPLE_WEAPON_IDS = {
        "club",
        "crossbow",
        "dagger",
        "javelin",
        "light_crossbow",
        "mace",
        "spear",
        "unarmed",
    }
    _ABILITY_TOKEN_TO_KEY = {
        "STR": "strength",
        "DEX": "dexterity",
        "CON": "constitution",
        "INT": "intelligence",
        "WIS": "wisdom",
        "CHA": "charisma",
    }

    def _ac_with_bonuses(
        self,
        target,
        *,
        attacker=None,
        extra_bonuses: Optional[Iterable[BonusEffect]] = None,
    ) -> tuple[int, int, int]:
        """Zwraca (target_ac, base_ac, modifier) z uwzględnieniem tymczasowych bonusów (np. osłony).

        base_ac – bazowa wartość z atrybutu celu.
        modifier – najlepsze bonusy/kary z runtime pod tagiem "ac" oraz wsparcie dla legacy aktorów.
        """

        return ac_with_bonuses(target, attacker=attacker, extra_bonuses=extra_bonuses)

    def _attacker_modifier(self, attacker, action_tag: str, target=None) -> int:
        """Oblicz modyfikator atakującego dla podanego tagu (np. prone = -2)."""

        compute = getattr(attacker, "compute_modifier", None)
        if callable(compute):
            try:
                return int(compute(action_tag, target=target))
            except Exception:
                logger.debug("Nie udało się policzyć compute_modifier dla %s", action_tag, exc_info=True)
        return 0

    def _attack_modifier_details(self, attacker, action_tag: str, target=None, extra_effects=None):
        effects = list(getattr(attacker, "bonuses", [])) if hasattr(attacker, "bonuses") else []
        if action_tag in ("attack_melee", "attack_ranged", "magic"):
            try:
                has_status = getattr(attacker, "has_status", None)
                has_ic = bool(has_status("inspire_courage")) if callable(has_status) else False
                if not has_ic:
                    for item in getattr(attacker, "statuses", []) or []:
                        if getattr(item, "id", None) == "inspire_courage":
                            has_ic = True
                            break
                if has_ic:
                    effects.append(
                        BonusEffect(
                            type=BonusType.STATUS,
                            value=1,
                            tag=action_tag,
                            source="status:inspire_courage",
                            label="inspire courage",
                        )
                    )
            except Exception:
                pass
        if extra_effects:
            effects.extend(list(extra_effects))
        try:
            effects.extend(attack_penalty_effects(attacker, action_tag=action_tag))
        except Exception:
            pass
        target_id = getattr(target, "object_id", None)
        modifier = compute_total_modifier(effects, action_tag, target_id) if effects else 0
        best_effects = select_best_effects(effects, action_tag, target_id)
        log_lines = format_effects_log(effects, action_tag, target_id)
        return modifier, best_effects, log_lines

    def _format_bonus_info(self, attacker, action_tag: str, target=None) -> str:
        """Opis modyfikatorów do wyświetlenia w promptcie (z BonusMixin.format_prompt)."""

        modifier, best_effects, _ = self._attack_modifier_details(attacker, action_tag, target=target)
        if not best_effects and not modifier:
            return ""
        return f"\nModyfikator łączny: {modifier:+d} (doliczany automatycznie).\n"

    def _consume_aid_attack_bonus(self, attacker, *, action_tag: str | None = None) -> None:
        target_source = f"aid:attack:{action_tag}" if action_tag else None
        bonuses = getattr(attacker, "bonuses", None)
        if isinstance(bonuses, list):
            kept = []
            removed = False
            for eff in bonuses:
                source = str(getattr(eff, "source", "") or "")
                if removed:
                    kept.append(eff)
                    continue
                if target_source and source == target_source:
                    removed = True
                    continue
                if target_source and source == "aid:attack":
                    removed = True
                    continue
                if target_source is None and source == "aid:attack":
                    removed = True
                    continue
                kept.append(eff)
            if removed:
                try:
                    attacker.bonuses = kept
                except Exception:
                    pass
                return
        remover = getattr(attacker, "remove_bonuses_by_source", None)
        if callable(remover):
            try:
                if target_source:
                    remover(target_source)
                    remover("aid:attack")
                else:
                    remover("aid:attack")
            except Exception:
                pass

    # --- weapon trait helpers ---
    _TRAIT_TAGS = {
        "agile",
        "attached",
        "backstabber",
        "backswing",
        "brutal",
        "concealing",
        "deadly",
        "disarm",
        "dwarf",
        "elf",
        "fatal",
        "finesse",
        "forceful",
        "free_hand",
        "gnome",
        "goblin",
        "grapple",
        "halfling",
        "jousting",
        "monk",
        "modular",
        "nonlethal",
        "orc",
        "parry",
        "propulsive",
        "reach",
        "shove",
        "sweep",
        "thrown",
        "trip",
        "twin",
        "two_hand",
        "unarmed",
        "versatile",
        "volley",
        "knockdown",
    }
    _GENERIC_TAGS = {
        "attack",
        "attack_melee",
        "attack_ranged",
        "ranged_attack",
        "melee_attack",
        "weapon",
    }
    _VERSATILE_MAP = {
        "s": DamageType.SLASHING.value,
        "p": DamageType.PIERCING.value,
        "b": DamageType.BLUDGEONING.value,
        "slashing": DamageType.SLASHING.value,
        "piercing": DamageType.PIERCING.value,
        "bludgeoning": DamageType.BLUDGEONING.value,
    }

    def _weapon_key(self) -> str:
        return getattr(self, "action_id_base", None) or getattr(self, "name", "weapon")

    def _weapon_type_tag(self, tags: Iterable[str]) -> str | None:
        for tag in tags or []:
            if tag in self._GENERIC_TAGS:
                continue
            if tag in self._TRAIT_TAGS:
                continue
            if ":" in tag:
                continue
            if "_" in tag and tag.split("_", 1)[0] in self._TRAIT_TAGS:
                continue
            return tag
        return None

    @staticmethod
    def _parse_trait_value(tag: str, trait: str) -> str | None:
        if tag == trait:
            return None
        if tag.startswith(f"{trait}:"):
            return tag.split(":", 1)[1].strip() or None
        if tag.startswith(f"{trait}_"):
            return tag.split("_", 1)[1].strip() or None
        return None

    @staticmethod
    def _die_size_from_tag(value: str | None) -> str | None:
        if not value:
            return None
        val = str(value).strip().lower()
        if val.startswith("d"):
            return val
        if val.isdigit():
            return f"d{val}"
        return None

    @staticmethod
    def _normalized_trait_tags(raw_tags: Iterable[object] | None) -> list[str]:
        out: list[str] = []
        for item in raw_tags or ():
            tag = str(item or "").strip().lower().replace("-", "_").replace(" ", "_")
            if not tag:
                continue
            out.append(tag)
        return list(dict.fromkeys(out))

    def _selected_weapon(self, ctx):
        metadata = dict(getattr(ctx, "metadata", None) or {})
        selected = metadata.get("selected_weapon")
        if selected is not None:
            return selected
        selected_iid = str(metadata.get("selected_weapon_instance_id", "") or "").strip()
        if not selected_iid:
            return None
        try:
            from GameObjects.items.inventory import get_equipped_weapons

            for item in list(get_equipped_weapons(getattr(ctx, "actor", None)) or []):
                if str(getattr(item, "instance_id", "") or "").strip() == selected_iid:
                    return item
        except Exception:
            pass
        return None

    @classmethod
    def _merged_weapon_tags(cls, base_tags: Iterable[str], weapon) -> list[str]:
        tags = list(base_tags or [])
        item_id = str(getattr(weapon, "item_id", "") or "").strip().lower().replace("-", "_").replace(" ", "_")
        if item_id and item_id not in tags:
            tags.append(item_id)
        prof_category = (
            str(getattr(weapon, "proficiency_category", "") or "")
            .strip()
            .lower()
            .replace("-", "_")
            .replace(" ", "_")
        )
        if prof_category in {"simple", "martial", "advanced", "unarmed"} and prof_category not in tags:
            tags.append(prof_category)
        for tag in cls._normalized_trait_tags(getattr(weapon, "traits", ())):
            if tag not in tags:
                tags.append(tag)
        return tags

    @staticmethod
    def _replace_first_die_size(
        damage_prompt: str | Iterable[str],
        die_size: str | None,
    ) -> str | Iterable[str]:
        target_die = AttackEventBase._die_size_from_tag(die_size)
        if not target_die:
            return damage_prompt
        digits = re.sub(r"[^0-9]", "", str(target_die))
        if not digits:
            return damage_prompt

        def _replace_one(text: str) -> str:
            return re.sub(r"([kKdD])\s*\d+", rf"\g<1>{digits}", str(text or ""), count=1)

        if isinstance(damage_prompt, str):
            return _replace_one(damage_prompt)
        prompt_list = list(damage_prompt or [])
        if not prompt_list:
            return damage_prompt
        prompt_list[0] = _replace_one(str(prompt_list[0]))
        return prompt_list

    def _fatal_critical_profile(
        self,
        *,
        tags: Iterable[str],
        critical: bool,
        damage_prompt: str | Iterable[str],
    ) -> tuple[str | Iterable[str], str | None]:
        if not critical:
            return damage_prompt, None
        fatal_raw = self._tag_value(tags, "fatal")
        fatal_die = self._die_size_from_tag(fatal_raw)
        if not fatal_die:
            return damage_prompt, None
        upgraded = self._replace_first_die_size(damage_prompt, fatal_die)
        return upgraded, fatal_die

    @staticmethod
    def _ability_modifier(actor, ability_key: str | None) -> int:
        if actor is None or not ability_key:
            return 0
        key = str(ability_key or "").strip().lower()
        if not key:
            return 0

        direct_names = {
            "strength": ("str_mod", "strength_mod"),
            "dexterity": ("dex_mod", "dexterity_mod"),
            "constitution": ("con_mod", "constitution_mod"),
            "intelligence": ("int_mod", "intelligence_mod"),
            "wisdom": ("wis_mod", "wisdom_mod"),
            "charisma": ("cha_mod", "charisma_mod"),
        }
        for attr in direct_names.get(key, ()):
            value = getattr(actor, attr, None)
            if value is None:
                continue
            try:
                return int(value)
            except Exception:
                continue

        ability_modifiers = getattr(actor, "ability_modifiers", None)
        if isinstance(ability_modifiers, dict):
            try:
                return int(ability_modifiers.get(key, 0) or 0)
            except Exception:
                return 0
        return 0

    @staticmethod
    def _strength_modifier(actor) -> int:
        return AttackEventBase._ability_modifier(actor, "strength")

    def _propulsive_damage_bonus(self, actor, tags: Iterable[str]) -> int:
        if not self._has_trait(tags, "propulsive"):
            return 0
        str_mod = int(self._strength_modifier(actor) or 0)
        if str_mod > 0:
            return int(str_mod // 2)
        return int(str_mod)

    def _can_use_two_hand(self, actor, selected_weapon=None) -> bool:
        if actor is None:
            return False
        if getattr(actor, "equipped_shield", None) is not None:
            return False
        try:
            from GameObjects.items.inventory import get_equipped_weapons

            equipped = list(get_equipped_weapons(actor) or [])
        except Exception:
            equipped = []
        if not equipped:
            return selected_weapon is None
        if selected_weapon is not None:
            others = [item for item in equipped if item is not selected_weapon]
            return len(others) == 0
        return len(equipped) <= 1

    @staticmethod
    def _bool_from_metadata(value: object, default: bool = False) -> bool:
        if value is None:
            return bool(default)
        if isinstance(value, bool):
            return value
        raw = str(value).strip().lower()
        if raw in {"1", "true", "yes", "y", "tak", "t"}:
            return True
        if raw in {"0", "false", "no", "n", "nie"}:
            return False
        return bool(default)

    def _wants_two_hand_usage(self, ctx, *, tags: Iterable[str], selected_weapon=None) -> bool:
        if not self._has_trait(tags, "two_hand"):
            return False
        if not self._die_size_from_tag(self._tag_value(tags, "two_hand")):
            return False
        actor = getattr(ctx, "actor", None)
        if not self._can_use_two_hand(actor, selected_weapon=selected_weapon):
            return False
        metadata = dict(getattr(ctx, "metadata", None) or {})
        if "use_two_hand" in metadata:
            return self._bool_from_metadata(metadata.get("use_two_hand"), default=False)
        choice = self._prompt_choice(
            "Two-Hand: użyć broni oburącz?",
            choices=["tak", "nie"],
            source="two_hand",
        )
        return self._bool_from_metadata(choice, default=False)

    @classmethod
    def _modular_options(cls, tags: Iterable[str]) -> list[str]:
        raw = cls._tag_value(tags, "modular")
        chunks: list[str] = []
        if raw:
            chunks.append(str(raw))
        for tag in tags or []:
            if tag.startswith("modular:"):
                chunks.append(tag.split(":", 1)[1])
            elif tag.startswith("modular_"):
                chunks.append(tag.split("_", 1)[1])
        out: list[str] = []
        for chunk in chunks:
            for part in re.split(r"[,/|_ ]+", str(chunk or "").strip().lower()):
                if not part:
                    continue
                mapped = cls._VERSATILE_MAP.get(part)
                if mapped and mapped not in out:
                    out.append(mapped)
        return out

    @classmethod
    def _tag_value(cls, tags: Iterable[str], trait: str) -> str | None:
        for tag in tags or []:
            if tag == trait or tag.startswith(f"{trait}:") or tag.startswith(f"{trait}_"):
                return cls._parse_trait_value(tag, trait)
        return None

    @classmethod
    def _has_trait(cls, tags: Iterable[str], trait: str) -> bool:
        for tag in tags or []:
            if tag == trait or tag.startswith(f"{trait}:") or tag.startswith(f"{trait}_"):
                return True
        return False

    @staticmethod
    def _damage_dice_count(damage_prompt: str | Iterable[str]) -> int | None:
        if isinstance(damage_prompt, (list, tuple)):
            text = str(damage_prompt[0]) if damage_prompt else ""
        else:
            text = str(damage_prompt)
        match = re.search(r"(\d+)\s*[kd]\s*\d+", text, re.IGNORECASE)
        if not match:
            return None
        try:
            return int(match.group(1))
        except Exception:
            return None

    def _get_attack_state(self, ctx, actor) -> dict:
        if actor is None:
            return {}
        if getattr(ctx, "in_combat", False):
            combat_state = getattr(ctx.game, "state", None)
            attack_state = getattr(combat_state, "attack_state", None)
            if isinstance(attack_state, dict):
                return mapping_setdefault_actor(attack_state, actor, dict)
        state = getattr(actor, "_attack_trait_state", None)
        if not isinstance(state, dict):
            state = {}
            try:
                setattr(actor, "_attack_trait_state", state)
            except Exception:
                pass
        return state

    @staticmethod
    def _target_id(target) -> str | None:
        if target is None:
            return None
        return getattr(target, "object_id", None) or getattr(target, "name", None) or str(id(target))

    @staticmethod
    def _combat_round_index(ctx) -> int | None:
        try:
            if not getattr(ctx, "in_combat", False):
                return None
            state = getattr(ctx, "game", None)
            state = getattr(state, "state", None)
            return int(getattr(state, "round_index", 0) or 0)
        except Exception:
            return None

    @staticmethod
    def _is_rogue_actor(actor) -> bool:
        if actor is None:
            return False
        class_name = str(getattr(actor, "class_name", "") or "").strip().lower()
        if class_name == "rogue":
            return True
        has_status = getattr(actor, "has_status", None)
        if callable(has_status):
            try:
                return bool(has_status("rogue"))
            except Exception:
                return False
        for status in getattr(actor, "statuses", []) or []:
            if getattr(status, "id", status) == "rogue":
                return True
        return False

    @staticmethod
    def _rogue_initiative_allows_surprise(actor) -> bool:
        if actor is None:
            return False
        skill = str(getattr(actor, "initiative_skill", "") or "").strip().lower().replace("-", "_")
        if not skill:
            return True
        return skill in {"stealth", "deception"}

    def _rogue_surprise_attack_applies(self, ctx, actor, target) -> bool:
        if actor is None or target is None:
            return False
        if not getattr(ctx, "in_combat", False):
            return False
        if not self._has_status_id(actor, "surprise_attack"):
            return False
        if not self._is_rogue_actor(actor):
            return False
        if not self._rogue_initiative_allows_surprise(actor):
            return False
        round_index = self._combat_round_index(ctx)
        if round_index != 1:
            return False
        state = getattr(getattr(ctx, "game", None), "state", None)
        round_queue = getattr(state, "round_queue", None)
        if not isinstance(round_queue, list):
            return False
        if target not in round_queue:
            return False
        if round_queue and round_queue[0] is target:
            return False
        return True

    def _is_off_guard_for_attack(
        self,
        ctx,
        attacker,
        target,
        *,
        metadata: dict | None = None,
        is_melee: bool | None = None,
    ) -> tuple[bool, bool, bool]:
        data = dict(metadata or {})
        forced = bool(data.get("force_flat_footed", False) or data.get("force_off_guard", False))
        natural = self._is_flat_footed(target)
        feint_flat_footed = self._feint_flat_footed_status_applies(target, attacker, is_melee=bool(is_melee))
        surprise = self._rogue_surprise_attack_applies(ctx, attacker, target)
        return bool(forced or natural or surprise or feint_flat_footed), bool(natural), bool(surprise)

    @staticmethod
    def _target_allows_precision_damage(target) -> bool:
        try:
            from statuses.classes.ranger.ranger_utils import target_allows_precision_damage

            return bool(target_allows_precision_damage(target))
        except Exception:
            return True

    def _rogue_sneak_attack_dice(self, actor) -> int:
        if actor is None:
            return 0
        if not self._has_status_id(actor, "sneak_attack"):
            return 0
        if not self._is_rogue_actor(actor):
            return 0
        try:
            level = max(1, int(getattr(actor, "level", 1) or 1))
        except Exception:
            level = 1
        if level >= 17:
            return 4
        if level >= 11:
            return 3
        if level >= 5:
            return 2
        return 1

    def _rogue_sneak_attack_eligible(
        self,
        *,
        actor,
        target,
        tags: Iterable[str],
        is_ranged: bool,
    ) -> bool:
        if self._rogue_sneak_attack_dice(actor) <= 0:
            return False
        if not self._target_allows_precision_damage(target):
            return False
        is_agile_or_finesse = self._has_trait(tags, "agile") or self._has_trait(tags, "finesse")
        if is_ranged:
            if self._has_trait(tags, "thrown") and not is_agile_or_finesse:
                return False
            return True
        if self._has_trait(tags, "unarmed"):
            return bool(is_agile_or_finesse)
        return bool(is_agile_or_finesse)

    def _rogue_racket(self, actor) -> str | None:
        if actor is None:
            return None
        getter = getattr(actor, "get_status_data", None)
        if callable(getter):
            try:
                value = getter("rogue", "rogue_racket", None)
                raw = str(value or "").strip().lower()
                if raw:
                    return raw
                setup = getter("rogue", "rogue_setup", {})
                if isinstance(setup, dict):
                    raw = str(setup.get("racket", "") or "").strip().lower()
                    if raw:
                        return raw
            except Exception:
                pass
        for status in getattr(actor, "statuses", []) or []:
            if getattr(status, "id", None) != "rogue":
                continue
            data = getattr(status, "data", None) or {}
            raw = str(data.get("rogue_racket", "") or "").strip().lower()
            if raw:
                return raw
            setup = data.get("rogue_setup")
            if isinstance(setup, dict):
                raw = str(setup.get("racket", "") or "").strip().lower()
                if raw:
                    return raw
        raw = str(getattr(actor, "rogue_racket", "") or "").strip().lower()
        return raw or None

    @staticmethod
    def _first_damage_die_size(damage_prompt: str | Iterable[str]) -> int | None:
        text = str(damage_prompt[0]) if isinstance(damage_prompt, (list, tuple)) and damage_prompt else str(damage_prompt)
        match = re.search(r"[kKdD]\s*(\d+)", text)
        if not match:
            return None
        try:
            return int(match.group(1))
        except Exception:
            return None

    def _maybe_log_ruffian_crit_spec_placeholder(
        self,
        *,
        ctx,
        actor,
        critical: bool,
        is_off_guard: bool,
        weapon_type: str | None,
        tags: Iterable[str],
        damage_prompt: str | Iterable[str],
    ) -> None:
        # Zachowane dla kompatybilności wywołań – globalna obsługa critical specialization działa w `_apply_weapon_critical_specialization`.
        return

    @staticmethod
    def _consume_nimble_dodge_bonus(target, attacker) -> None:
        if target is None:
            return
        bonuses = getattr(target, "bonuses", None)
        if not isinstance(bonuses, list):
            return
        attacker_id = str(getattr(attacker, "object_id", None) or "")
        kept = []
        removed = False
        for effect in bonuses:
            source = str(getattr(effect, "source", "") or "")
            if not source.startswith("nimble_dodge:"):
                kept.append(effect)
                continue
            effect_target_id = str(getattr(effect, "target_id", None) or "")
            if effect_target_id and attacker_id and effect_target_id != attacker_id:
                kept.append(effect)
                continue
            removed = True
        if not removed:
            return
        try:
            target.bonuses = kept
        except Exception:
            pass

    def _ranger_hunter_edge(self, actor) -> str | None:
        try:
            from statuses.classes.ranger.ranger_utils import hunter_edge

            return hunter_edge(actor)
        except Exception:
            return None

    def _is_hunted_prey(self, actor, target) -> bool:
        try:
            from statuses.classes.ranger.ranger_utils import is_hunted_prey

            return bool(is_hunted_prey(actor, target))
        except Exception:
            return False

    def _ranger_map_penalty(self, actor, *, tags: Iterable[str], attacks_this_turn: int, target) -> int | None:
        if self._ranger_hunter_edge(actor) != "flurry":
            return None
        if not self._is_hunted_prey(actor, target):
            return None
        if attacks_this_turn < 1:
            return 0
        agile = self._has_trait(tags, "agile")
        if attacks_this_turn == 1:
            return 2 if agile else 3
        return 4 if agile else 6

    def _ranger_precision_ready(self, ctx, actor, target) -> bool:
        round_index = self._combat_round_index(ctx)
        try:
            from statuses.classes.ranger.ranger_utils import precision_allowed, target_allows_precision_damage

            if not target_allows_precision_damage(target):
                return False
            return bool(precision_allowed(actor, target, round_index=round_index))
        except Exception:
            return False

    def _mark_ranger_precision(self, ctx, actor, target) -> None:
        round_index = self._combat_round_index(ctx)
        try:
            from statuses.classes.ranger.ranger_utils import mark_precision_applied

            mark_precision_applied(actor, target, round_index=round_index)
        except Exception:
            return

    def _consume_monster_hunter_bonus(self, actor) -> None:
        if actor is None:
            return
        bonuses = getattr(actor, "bonuses", None)
        if isinstance(bonuses, list):
            kept = [eff for eff in bonuses if str(getattr(eff, "source", "") or "") != "ranger:monster_hunter:attack"]
            try:
                actor.bonuses = kept
            except Exception:
                pass
            return
        remover = getattr(actor, "remove_bonuses_by_source", None)
        if callable(remover):
            try:
                remover("ranger:monster_hunter:attack")
            except Exception:
                pass

    def _record_attack(
        self,
        ctx,
        actor,
        *,
        weapon_key: str,
        weapon_type: str | None,
        target,
        attack_count: int = 1,
        weapon_attack_count: int | None = None,
    ) -> None:
        state = self._get_attack_state(ctx, actor)
        try:
            count = max(0, int(attack_count))
        except Exception:
            count = 1
        if count <= 0:
            return
        state["attacks_this_turn"] = int(state.get("attacks_this_turn", 0) or 0) + count
        weapon_counts = state.setdefault("weapon_counts", {})
        if weapon_attack_count is None:
            weapon_count = count
        else:
            try:
                weapon_count = max(0, int(weapon_attack_count))
            except Exception:
                weapon_count = count
        weapon_counts[weapon_key] = int(weapon_counts.get(weapon_key, 0) or 0) + weapon_count
        weapon_targets = state.setdefault("weapon_targets", {})
        target_set = weapon_targets.setdefault(weapon_key, set())
        tid = self._target_id(target)
        if tid:
            try:
                target_set.add(tid)
            except Exception:
                pass
        if weapon_type:
            last_by_type = state.setdefault("last_weapon_by_type", {})
            last_by_type[weapon_type] = weapon_key

    @staticmethod
    def _normalize_weapon_type(value: object) -> str | None:
        raw = str(value or "").strip().lower()
        if not raw:
            return None
        normalized = raw.replace("-", "_").replace(" ", "_")
        aliases = {
            "fist": "unarmed",
            "longsword": "sword",
            "bow": "longbow",
            "simple_crossbow": "crossbow",
        }
        return aliases.get(normalized, normalized)

    def _weapon_id_from_attack(
        self,
        *,
        weapon_type: str | None,
        tags: Iterable[str] | None,
        selected_weapon=None,
    ) -> str | None:
        from_weapon = self._normalize_weapon_type(getattr(selected_weapon, "item_id", None))
        if from_weapon:
            return from_weapon
        from_type = self._normalize_weapon_type(weapon_type)
        if from_type:
            return from_type
        from_tags = self._normalize_weapon_type(self._weapon_type_tag(tags or []))
        if from_tags:
            return from_tags
        return self._normalize_weapon_type(getattr(self, "name", None))

    def _weapon_group_from_attack(
        self,
        *,
        weapon_type: str | None,
        tags: Iterable[str] | None,
        selected_weapon=None,
    ) -> str | None:
        explicit = self._normalize_weapon_type(getattr(selected_weapon, "weapon_group", None))
        if explicit:
            return explicit
        weapon_id = self._weapon_id_from_attack(
            weapon_type=weapon_type,
            tags=tags,
            selected_weapon=selected_weapon,
        )
        if not weapon_id:
            return None
        return self._WEAPON_GROUP_BY_WEAPON.get(weapon_id)

    def _iter_statuses(self, actor):
        for status in getattr(actor, "statuses", []) or []:
            yield status

    def _critical_specialization_state(self, actor) -> tuple[bool, set[str]]:
        if actor is None:
            return False, set()
        allow_all = False
        groups: set[str] = set()
        for status in self._iter_statuses(actor):
            sid = self._normalize_weapon_type(getattr(status, "id", None))
            data = getattr(status, "data", None) or {}
            if not isinstance(data, dict):
                data = {}
            if sid in {"critical_specialization_all", "weapon_critical_specialization_all"}:
                allow_all = True
            if bool(data.get("all_weapon_groups", False) or data.get("critical_specialization_all", False) or data.get("all", False)):
                allow_all = True

            for key in ("weapon_group", "group", "critical_specialization_group"):
                value = self._normalize_weapon_type(data.get(key))
                if value:
                    groups.add(value)
            for key in ("weapon_groups", "groups", "critical_specialization_groups"):
                values = data.get(key)
                if not isinstance(values, (list, tuple, set)):
                    continue
                for value in values:
                    normalized = self._normalize_weapon_type(value)
                    if normalized:
                        groups.add(normalized)
        actor_groups = getattr(actor, "critical_specialization_groups", None)
        if isinstance(actor_groups, (list, tuple, set)):
            for value in actor_groups:
                normalized = self._normalize_weapon_type(value)
                if normalized:
                    groups.add(normalized)
        if bool(getattr(actor, "critical_specialization_all", False)):
            allow_all = True
        return allow_all, groups

    def _ruffian_critical_specialization_enabled(self, actor) -> bool:
        if self._rogue_racket(actor) != "ruffian":
            return False
        getter = getattr(actor, "get_status_data", None)
        if callable(getter):
            try:
                setup = getter("rogue", "rogue_setup", {})
                if isinstance(setup, dict) and bool(setup.get("ruffian_crit_spec_todo", False)):
                    return True
            except Exception:
                pass
        for status in self._iter_statuses(actor):
            if getattr(status, "id", None) != "rogue":
                continue
            data = getattr(status, "data", None) or {}
            if not isinstance(data, dict):
                continue
            setup = data.get("rogue_setup")
            if isinstance(setup, dict) and bool(setup.get("ruffian_crit_spec_todo", False)):
                return True
        return False

    def _has_critical_specialization_for_group(
        self,
        actor,
        *,
        weapon_group: str | None,
        weapon_id: str | None,
        is_off_guard: bool = False,
        damage_prompt: str | Iterable[str] | None = None,
    ) -> bool:
        normalized_group = self._normalize_weapon_type(weapon_group)
        normalized_weapon = self._normalize_weapon_type(weapon_id)
        if not normalized_group:
            return False

        allow_all, groups = self._critical_specialization_state(actor)
        if allow_all:
            return True
        if normalized_group in groups:
            return True
        if normalized_weapon and normalized_weapon in groups:
            return True

        # Kompatybilność z Ruffian placeholderem: simple weapon d8 lub mniej vs Off-Guard.
        if self._ruffian_critical_specialization_enabled(actor):
            if not is_off_guard:
                return False
            if normalized_weapon not in self._SIMPLE_WEAPON_IDS:
                return False
            if damage_prompt is None:
                return True
            die_size = self._first_damage_die_size(damage_prompt)
            return die_size is None or die_size <= 8

        return False

    @staticmethod
    def _target_alive(target) -> bool:
        hp = getattr(target, "hp", None)
        if hp is None:
            return True
        try:
            return int(hp) > 0
        except Exception:
            return True

    @staticmethod
    def _add_or_refresh_status(target, status_obj) -> bool:
        if target is None or status_obj is None:
            return False
        status_id = getattr(status_obj, "id", None)
        remover = getattr(target, "remove_status", None)
        if status_id and callable(remover):
            try:
                remover(status_id)
            except Exception:
                pass
        adder = getattr(target, "add_status", None)
        if callable(adder):
            try:
                adder(status_obj)
                return True
            except Exception:
                pass
        statuses = getattr(target, "statuses", None)
        if isinstance(statuses, list):
            if status_id:
                statuses[:] = [item for item in statuses if getattr(item, "id", item) != status_id]
            statuses.append(status_obj)
            return True
        return False

    @staticmethod
    def _target_adjacent_to_surface(game, target_pos: tuple[int, int] | None) -> bool:
        if game is None or target_pos is None:
            return False
        board = getattr(game, "board", None)
        if board is None:
            return False
        try:
            neighbors = board.get_neighbors(target_pos, include_position=False, diagonal=False)
        except TypeError:
            neighbors = board.get_neighbors(target_pos, include_position=False)
        except Exception:
            neighbors = []
        for nxt in list(neighbors or []):
            try:
                if not board.in_bounds(nxt):
                    return True
            except Exception:
                pass
            try:
                if board.is_blocked(target_pos, nxt):
                    return True
            except Exception:
                pass
            try:
                if board.occupant_at(nxt) is not None:
                    return True
            except Exception:
                pass
            try:
                if list(board.interactables_at(nxt) or []):
                    return True
            except Exception:
                pass
        return False

    @staticmethod
    def _push_target_away(ctx, attacker, target, *, steps: int) -> bool:
        if ctx is None or attacker is None or target is None:
            return False
        source_pos = getattr(attacker, "position", None)
        target_pos = getattr(target, "position", None)
        board = getattr(getattr(ctx, "game", None), "board", None)
        if source_pos is None or target_pos is None or board is None:
            return False
        try:
            from actions.move_utils import adjusted_forced_movement_squares

            steps = adjusted_forced_movement_squares(target, steps)
        except Exception:
            pass
        try:
            move_steps = max(0, int(steps or 0))
        except Exception:
            move_steps = 0
        if move_steps <= 0:
            return False
        dx = target_pos[0] - source_pos[0]
        dy = target_pos[1] - source_pos[1]
        step_x = 0 if dx == 0 else (1 if dx > 0 else -1)
        step_y = 0 if dy == 0 else (1 if dy > 0 else -1)
        cur = target_pos
        moved = False
        for _ in range(move_steps):
            nxt = (cur[0] + step_x, cur[1] + step_y)
            try:
                if board.is_blocked(cur, nxt):
                    break
            except Exception:
                pass
            try:
                if not board.can_enter(nxt, allow_occupied=False):
                    break
            except Exception:
                break
            try:
                board.move(cur, nxt)
            except Exception:
                break
            try:
                target.position = nxt
            except Exception:
                pass
            cur = nxt
            moved = True
        return moved

    def _apply_weapon_critical_specialization(
        self,
        ctx,
        *,
        actor,
        target,
        critical: bool,
        is_off_guard: bool,
        weapon_type: str | None,
        tags: Iterable[str],
        selected_weapon=None,
        damage_prompt: str | Iterable[str] | None = None,
        damage_components: list[tuple[str, int]] | None = None,
        default_damage_type: str | None = None,
        roll_for_bleed=None,
    ) -> list[str]:
        if not critical or actor is None or target is None or not self._target_alive(target):
            return []

        weapon_id = self._weapon_id_from_attack(
            weapon_type=weapon_type,
            tags=tags,
            selected_weapon=selected_weapon,
        )
        weapon_group = self._weapon_group_from_attack(
            weapon_type=weapon_type,
            tags=tags,
            selected_weapon=selected_weapon,
        )
        if not self._has_critical_specialization_for_group(
            actor,
            weapon_group=weapon_group,
            weapon_id=weapon_id,
            is_off_guard=is_off_guard,
            damage_prompt=damage_prompt,
        ):
            return []

        notes: list[str] = []
        source = f"weapon_crit_spec:{weapon_group or weapon_id or 'unknown'}"

        if weapon_group == "knife":
            bleed_amount = 1
            if callable(roll_for_bleed):
                try:
                    bleed_amount = int(
                        roll_for_bleed(
                            "Critical Specialization (Knife): persistent bleed 1k6 - podaj wynik: ",
                            layout="damage",
                            answer_placeholder="Bleed",
                        )
                        or 0
                    )
                except Exception:
                    bleed_amount = 1
            bleed_amount = max(1, int(bleed_amount or 1))
            try:
                from statuses import make_persistent_damage
                from damage_types import DamageType as _DamageType

                self._add_or_refresh_status(target, make_persistent_damage(bleed_amount, _DamageType.BLEED.value, source=source))
                notes.append(f"Critical Specialization (Knife): persistent bleed {bleed_amount}.")
            except Exception:
                pass
            return notes

        if weapon_group == "club":
            moved = self._push_target_away(ctx, actor, target, steps=2)
            if moved:
                notes.append("Critical Specialization (Club): cel odepchnięty o 10 ft.")
            else:
                notes.append("Critical Specialization (Club): brak miejsca na odepchnięcie.")
            return notes

        if weapon_group == "spear":
            try:
                from statuses import ClumsyStatus

                if self._add_or_refresh_status(target, ClumsyStatus(value=1, duration=1, source=source)):
                    notes.append("Critical Specialization (Spear): cel otrzymuje Clumsy 1.")
            except Exception:
                pass
            return notes

        if weapon_group == "sword":
            try:
                from statuses import OffGuardStatus

                if self._add_or_refresh_status(target, OffGuardStatus(duration=1, source=source, source_id=getattr(actor, "object_id", None))):
                    notes.append("Critical Specialization (Sword): cel staje się Off-Guard.")
            except Exception:
                pass
            return notes

        if weapon_group == "axe":
            bonus = self._strength_modifier(actor)
            if bonus > 0 and isinstance(damage_components, list):
                dtype = default_damage_type or DamageType.NORMAL.value
                damage_components.append((dtype, int(bonus)))
                notes.append(f"Critical Specialization (Axe): +{int(bonus)} obrażeń.")
            return notes

        if weapon_group in {"hammer", "polearm"}:
            try:
                from statuses import PRONE_STATUS, apply_prone_effects

                if self._add_or_refresh_status(target, PRONE_STATUS):
                    apply_prone_effects(target)
                    notes.append(f"Critical Specialization ({weapon_group.title()}): cel zostaje przewrócony.")
            except Exception:
                pass
            return notes

        if weapon_group == "bow":
            target_pos = getattr(target, "position", None)
            if self._target_adjacent_to_surface(getattr(ctx, "game", None), target_pos):
                try:
                    from statuses import ImmobilizedStatus

                    if self._add_or_refresh_status(
                        target,
                        ImmobilizedStatus(duration=1, source=source, source_id=getattr(actor, "object_id", None), source_turns_left=1),
                    ):
                        notes.append("Critical Specialization (Bow): cel przypięty (immobilized).")
                except Exception:
                    pass
            else:
                notes.append("Critical Specialization (Bow): brak powierzchni do przypięcia celu.")
            return notes

        if weapon_group == "crossbow":
            target_pos = getattr(target, "position", None)
            if self._target_adjacent_to_surface(getattr(ctx, "game", None), target_pos):
                try:
                    from statuses import ImmobilizedStatus

                    if self._add_or_refresh_status(
                        target,
                        ImmobilizedStatus(duration=1, source=source, source_id=getattr(actor, "object_id", None), source_turns_left=1),
                    ):
                        notes.append("Critical Specialization (Crossbow): cel przypięty (immobilized).")
                except Exception:
                    pass
            else:
                try:
                    from statuses import SpeedPenaltyStatus

                    if self._add_or_refresh_status(
                        target,
                        SpeedPenaltyStatus(
                            penalty_feet=10,
                            duration=1,
                            source=source,
                            source_id=getattr(actor, "object_id", None),
                            source_turns_left=1,
                            label="slowed by crossbow crit",
                        ),
                    ):
                        notes.append("Critical Specialization (Crossbow): cel spowolniony (Speed -10 ft).")
                except Exception:
                    pass
            return notes

        return notes

    @staticmethod
    def _has_status_id(actor, status_id: str) -> bool:
        if actor is None:
            return False
        has_status = getattr(actor, "has_status", None)
        if callable(has_status):
            try:
                return bool(has_status(status_id))
            except Exception:
                return False
        for status in getattr(actor, "statuses", []) or []:
            if getattr(status, "id", status) == status_id:
                return True
        return False

    def _deific_weapon_type(self, actor) -> str | None:
        if actor is None:
            return None
        has_status = getattr(actor, "has_status", None)
        try:
            if callable(has_status) and not has_status("deific_weapon"):
                return None
        except Exception:
            return None
        getter = getattr(actor, "get_status_data", None)
        if callable(getter):
            try:
                value = getter("deific_weapon", "deific_weapon_type", None)
                normalized = self._normalize_weapon_type(value)
                if normalized:
                    return normalized
            except Exception:
                pass
        for status in getattr(actor, "statuses", []) or []:
            if getattr(status, "id", None) != "deific_weapon":
                continue
            data = getattr(status, "data", None) or {}
            normalized = self._normalize_weapon_type(data.get("deific_weapon_type"))
            if normalized:
                return normalized
        return self._normalize_weapon_type(getattr(actor, "deific_weapon_type", None))

    def _cleric_favored_weapon_type(self, actor) -> str | None:
        if actor is None:
            return None
        getter = getattr(actor, "get_status_data", None)
        if callable(getter):
            try:
                setup = getter("cleric", "cleric_setup", {})
                if isinstance(setup, dict):
                    normalized = self._normalize_weapon_type(setup.get("favored_weapon"))
                    if normalized:
                        return normalized
                value = getter("cleric", "cleric_favored_weapon", None)
                normalized = self._normalize_weapon_type(value)
                if normalized:
                    return normalized
            except Exception:
                pass
        for status in getattr(actor, "statuses", []) or []:
            if getattr(status, "id", None) != "cleric":
                continue
            data = getattr(status, "data", None) or {}
            setup = data.get("cleric_setup")
            if isinstance(setup, dict):
                normalized = self._normalize_weapon_type(setup.get("favored_weapon"))
                if normalized:
                    return normalized
            normalized = self._normalize_weapon_type(data.get("cleric_favored_weapon"))
            if normalized:
                return normalized
        return self._normalize_weapon_type(getattr(actor, "cleric_favored_weapon", None))

    def _cleric_favored_weapon_group(self, actor) -> str | None:
        if actor is None:
            return None
        getter = getattr(actor, "get_status_data", None)
        if callable(getter):
            try:
                setup = getter("cleric", "cleric_setup", {})
                if isinstance(setup, dict):
                    group = str(setup.get("favored_weapon_group", "") or "").strip().lower().replace("-", "_")
                    if group in {"simple", "martial", "unarmed"}:
                        return group
                value = getter("cleric", "cleric_favored_weapon_group", None)
                group = str(value or "").strip().lower().replace("-", "_")
                if group in {"simple", "martial", "unarmed"}:
                    return group
            except Exception:
                pass
        for status in getattr(actor, "statuses", []) or []:
            if getattr(status, "id", None) != "cleric":
                continue
            data = getattr(status, "data", None) or {}
            setup = data.get("cleric_setup")
            if isinstance(setup, dict):
                group = str(setup.get("favored_weapon_group", "") or "").strip().lower().replace("-", "_")
                if group in {"simple", "martial", "unarmed"}:
                    return group
            group = str(data.get("cleric_favored_weapon_group", "") or "").strip().lower().replace("-", "_")
            if group in {"simple", "martial", "unarmed"}:
                return group
        group = str(getattr(actor, "cleric_favored_weapon_group", "") or "").strip().lower().replace("-", "_")
        if group in {"simple", "martial", "unarmed"}:
            return group
        return None

    def _deadly_simplicity_active_for_weapon(self, actor, weapon_type: str | None) -> bool:
        if actor is None:
            return False
        has_status = getattr(actor, "has_status", None)
        try:
            if callable(has_status) and not has_status("deadly_simplicity"):
                return False
        except Exception:
            return False
        favored = self._cleric_favored_weapon_type(actor)
        selected = self._normalize_weapon_type(weapon_type)
        if not favored or not selected:
            return False
        if favored != selected:
            return False
        group = self._cleric_favored_weapon_group(actor)
        return group in {"simple", "unarmed"}

    def _upgrade_damage_prompt_one_step(self, prompt_text: str) -> str:
        text = str(prompt_text or "")
        pattern = re.compile(r"([kKdD])(\d+)")
        match = pattern.search(text)
        if not match:
            return text
        current = str(match.group(2))
        upgraded = self._DEIFIC_DIE_UPGRADE.get(current)
        if not upgraded:
            return text
        start, end = match.span(2)
        return f"{text[:start]}{upgraded}{text[end:]}"

    def _deific_damage_prompt(
        self,
        actor,
        *,
        weapon_type: str | None,
        damage_prompt: str | Iterable[str],
    ):
        selected = self._deific_weapon_type(actor)
        weapon_key = self._normalize_weapon_type(weapon_type)
        if not selected or not weapon_key or selected != weapon_key:
            return damage_prompt, False
        if isinstance(damage_prompt, str):
            upgraded = self._upgrade_damage_prompt_one_step(damage_prompt)
            return upgraded, upgraded != damage_prompt
        prompt_list = list(damage_prompt)
        if not prompt_list:
            return damage_prompt, False
        first = str(prompt_list[0])
        upgraded_first = self._upgrade_damage_prompt_one_step(first)
        if upgraded_first == first:
            return damage_prompt, False
        prompt_list[0] = upgraded_first
        return prompt_list, True

    def _deadly_simplicity_damage_prompt(
        self,
        actor,
        *,
        weapon_type: str | None,
        damage_prompt: str | Iterable[str],
    ):
        if not self._deadly_simplicity_active_for_weapon(actor, weapon_type):
            return damage_prompt, False

        prompt = damage_prompt
        if isinstance(prompt, str):
            upgraded = self._upgrade_damage_prompt_one_step(prompt)
            weapon_group = self._cleric_favored_weapon_group(actor)
            if weapon_group == "unarmed":
                upgraded = re.sub(r"([kKdD])4\\b", r"\\g<1>6", upgraded)
            return upgraded, upgraded != prompt

        prompt_list = list(prompt)
        if not prompt_list:
            return damage_prompt, False
        first = str(prompt_list[0])
        upgraded_first = self._upgrade_damage_prompt_one_step(first)
        if self._cleric_favored_weapon_group(actor) == "unarmed":
            upgraded_first = re.sub(r"([kKdD])4\\b", r"\\g<1>6", upgraded_first)
        if upgraded_first == first:
            return damage_prompt, False
        prompt_list[0] = upgraded_first
        return prompt_list, True

    def _powerful_fist_damage_prompt(
        self,
        actor,
        *,
        weapon_type: str | None,
        damage_prompt: str | Iterable[str],
    ):
        if actor is None:
            return damage_prompt, False
        if not self._has_status_id(actor, "powerful_fist"):
            return damage_prompt, False
        if self._normalize_weapon_type(weapon_type) != "unarmed":
            return damage_prompt, False
        if any(self._has_status_id(actor, status_id) for status_id in self._ALT_UNARMED_PROFILE_STATUS_IDS):
            return damage_prompt, False

        def _upgrade(text: str) -> str:
            return re.sub(r"([kKdD])4\b", r"\g<1>6", str(text or ""), count=1)

        if isinstance(damage_prompt, str):
            upgraded = _upgrade(damage_prompt)
            return upgraded, upgraded != damage_prompt

        prompt_list = list(damage_prompt)
        if not prompt_list:
            return damage_prompt, False
        first = str(prompt_list[0])
        upgraded_first = _upgrade(first)
        if upgraded_first == first:
            return damage_prompt, False
        prompt_list[0] = upgraded_first
        return prompt_list, True

    def _damage_prompt_with_class_upgrades(
        self,
        actor,
        *,
        weapon_type: str | None,
        damage_prompt: str | Iterable[str],
        tags: Iterable[str] | None = None,
        is_melee: bool | None = None,
    ):
        current_prompt = damage_prompt
        notes: list[str] = []

        current_prompt, powerful_applied = self._powerful_fist_damage_prompt(
            actor,
            weapon_type=weapon_type,
            damage_prompt=current_prompt,
        )
        if powerful_applied:
            notes.append("Powerful Fist: bazowe unarmed 1k4 -> 1k6.")

        current_prompt, deific_applied = self._deific_damage_prompt(
            actor,
            weapon_type=weapon_type,
            damage_prompt=current_prompt,
        )
        if deific_applied:
            notes.append("Deific Weapon: kosc obrazen zwiekszona o 1 stopien.")

        current_prompt, deadly_applied = self._deadly_simplicity_damage_prompt(
            actor,
            weapon_type=weapon_type,
            damage_prompt=current_prompt,
        )
        if deadly_applied:
            notes.append("Deadly Simplicity: kosc obrazen zwiekszona dla favored weapon.")

        current_prompt, thief_applied = self._thief_dex_damage_prompt(
            actor,
            damage_prompt=current_prompt,
            tags=tags,
            is_melee=is_melee,
        )
        if thief_applied:
            notes.append("Thief racket: finesse melee używa DEX zamiast STR w promptcie obrażeń.")

        return current_prompt, notes

    def _thief_dex_damage_prompt(
        self,
        actor,
        *,
        damage_prompt: str | Iterable[str],
        tags: Iterable[str] | None,
        is_melee: bool | None,
    ) -> tuple[str | Iterable[str], bool]:
        if not bool(is_melee):
            return damage_prompt, False
        if self._rogue_racket(actor) != "thief":
            return damage_prompt, False
        if not self._has_trait(tags or [], "finesse"):
            return damage_prompt, False

        def _replace(text: str) -> tuple[str, bool]:
            replaced = re.sub(r"\bSTR\b", "DEX", str(text), flags=re.IGNORECASE)
            return replaced, replaced != str(text)

        if isinstance(damage_prompt, str):
            replaced, changed = _replace(damage_prompt)
            return replaced, changed
        if isinstance(damage_prompt, (list, tuple)):
            changed = False
            out = []
            for item in damage_prompt:
                replaced, item_changed = _replace(str(item))
                changed = changed or item_changed
                out.append(replaced)
            return out, changed
        return damage_prompt, False

    def _feint_flat_footed_status_applies(self, target, attacker, *, is_melee: bool) -> bool:
        statuses = getattr(target, "statuses", None)
        if not isinstance(statuses, list):
            return False
        attacker_id = self._target_id(attacker)
        for status in statuses:
            if getattr(status, "id", status) != "feint_flat_footed":
                continue
            data = getattr(status, "data", None) or {}
            if bool(data.get("melee_only", False)) and not bool(is_melee):
                continue
            required_attacker_id = str(data.get("attacker_id", "") or "").strip()
            if required_attacker_id and str(attacker_id or "").strip() != required_attacker_id:
                continue
            return True
        return False

    def _consume_feint_next_attack(self, ctx, attacker, target, *, is_melee: bool) -> bool:
        state = self._get_attack_state(ctx, attacker)
        if not isinstance(state, dict):
            return False
        target_id = str(state.get("feint_next_attack_target_id", "") or "").strip()
        if not target_id:
            return False
        if bool(state.get("feint_next_attack_melee_only", True)) and not bool(is_melee):
            return False
        current_target_id = str(self._target_id(target) or "").strip()
        if not current_target_id or current_target_id != target_id:
            return False
        for key in (
            "feint_next_attack_target_id",
            "feint_next_attack_melee_only",
            "feint_next_attack_source",
            "feint_next_attack_source_id",
        ):
            state.pop(key, None)
        return True

    @staticmethod
    def _is_flat_footed(target) -> bool:
        if target is None:
            return False
        try:
            from combat import flat_footed_penalty

            if flat_footed_penalty(target) > 0:
                return True
        except Exception:
            pass
        has_status = getattr(target, "has_status", None)
        if callable(has_status):
            try:
                return bool(has_status("flat_footed") or has_status("off_guard"))
            except Exception:
                return False
        for status in getattr(target, "statuses", []) or []:
            if getattr(status, "id", None) in ("flat_footed", "off_guard") or status in ("flat_footed", "off_guard"):
                return True
        return False

    @staticmethod
    def _prompt_choice(prompt: str, choices: list[str], *, source: str) -> str | None:
        ui = None
        try:
            from ui_client import get_ui_client

            ui = get_ui_client()
            if ui is not None and getattr(ui, "enabled", True) and hasattr(ui, "prompt_choice"):
                return ui.prompt_choice(prompt, choices=choices, source=source)
        except Exception:
            pass
        if ui is not None and not getattr(ui, "allow_cli_fallback", False):
            return None
        try:
            raw = input(f"{prompt} {choices}: ").strip()
            return raw or None
        except Exception:
            return None

    def _choose_damage_type(self, tags: Iterable[str], base_damage_type: str | Iterable[str]) -> str | Iterable[str]:
        if not isinstance(base_damage_type, str):
            return base_damage_type
        choices: list[str] = [base_damage_type]
        for option in self._modular_options(tags):
            if option not in choices:
                choices.append(option)
        alt_raw = self._tag_value(tags, "versatile")
        if alt_raw:
            alt_key = str(alt_raw).strip().lower()
            alt_type = self._VERSATILE_MAP.get(alt_key)
            if alt_type and alt_type not in choices:
                choices.append(alt_type)
        if len(choices) <= 1:
            return base_damage_type
        choice = self._prompt_choice(
            "Wybierz typ obrażeń broni",
            choices=choices,
            source="weapon_damage_type",
        )
        if choice is None:
            return base_damage_type
        choice_norm = str(choice).strip().lower()
        for option in choices:
            if choice_norm == option:
                return option
            if option and choice_norm.startswith(option[:1]):
                return option
        return base_damage_type

    def _maybe_prompt_vengeful_hatred(self, attacker, target) -> None:
        """Pokaż informację o aktywnym Vengeful Hatred."""
        getter = getattr(attacker, "get_status_data", None)
        if callable(getter):
            enemy_type = getter("vengeful_hatred", "enemy_type", None)
            bonus = getter("vengeful_hatred", "damage_bonus_per_die", getter("vengeful_hatred", "damage_bonus", 1))
        else:
            enemy_type = None
            bonus = 1
            for status in getattr(attacker, "statuses", []) or []:
                if getattr(status, "id", None) != "vengeful_hatred":
                    continue
                data = getattr(status, "data", {}) or {}
                enemy_type = data.get("enemy_type")
                bonus = data.get("damage_bonus_per_die", data.get("damage_bonus", 1))
                break
        if not enemy_type:
            return
        target_type = getattr(target, "enemy_type", None)
        if target_type is None:
            return
        enemy_type_norm = getattr(enemy_type, "value", enemy_type)
        target_type_norm = getattr(target_type, "value", target_type)
        if enemy_type_norm != target_type_norm:
            return
        try:
            from ui_client import get_ui_client

            get_ui_client().prompt_info(
                "Vengeful Hatred",
                prompt_long=(
                    f"Vengeful Hatred aktywne vs {enemy_type_norm}: +{int(bonus)} za każdą kość obrażeń broni/unarmed. "
                    "Bonus jest doliczany automatycznie."
                ),
                source="vengeful_hatred",
            )
        except Exception:
            return

    def _vengeful_hatred_damage_bonus(self, attacker, target, *, weapon_dice: int = 1) -> int:
        try:
            from statuses.race.dwarf.feats.vengeful_hatred import vengeful_hatred_damage_bonus

            return int(vengeful_hatred_damage_bonus(attacker, target, weapon_dice=max(1, int(weapon_dice or 1))) or 0)
        except Exception:
            return 0

    def _weapon_attack_roll_bonus(self, attacker, tags: Iterable[str], *, is_ranged: bool) -> dict[str, object]:
        try:
            from combat.weapon_proficiency import compute_weapon_attack_roll_bonus

            return dict(
                compute_weapon_attack_roll_bonus(
                    attacker,
                    weapon_tags=list(tags or []),
                    is_ranged=bool(is_ranged),
                    finesse=self._has_trait(tags, "finesse"),
                    brutal=self._has_trait(tags, "brutal"),
                )
                or {}
            )
        except Exception:
            return {
                "total": 0,
                "proficiency_bonus": 0,
                "ability_bonus": 0,
                "ability_key": "strength",
                "item_bonus": 0,
                "rank": "untrained",
                "rank_step": 0,
                "level": 0,
            }

    @staticmethod
    def _ability_label_pl(ability_key: object) -> str:
        raw = str(ability_key or "").strip().lower()
        mapping = {
            "strength": "Sila",
            "str": "Sila",
            "dexterity": "Zrecznosc",
            "dex": "Zrecznosc",
            "constitution": "Kondycja",
            "con": "Kondycja",
            "intelligence": "Inteligencja",
            "int": "Inteligencja",
            "wisdom": "Madrosc",
            "wis": "Madrosc",
            "charisma": "Charyzma",
            "cha": "Charyzma",
        }
        return mapping.get(raw, str(raw or "-").title())

    @staticmethod
    def _rank_label_pl(rank: object) -> str:
        raw = str(rank or "").strip().lower()
        mapping = {
            "untrained": "Niewyszkolony",
            "trained": "Wyszkolony",
            "expert": "Ekspert",
            "master": "Mistrz",
            "legendary": "Legendarny",
        }
        return mapping.get(raw, str(raw or "-").title())

    def _attack_prompt_breakdown_lines(
        self,
        *,
        weapon_attack_bonus: dict[str, object],
        modifier: int,
        log_lines: Iterable[str] | None = None,
    ) -> list[str]:
        lines: list[str] = []
        lines.append(f"Modyfikator sytuacyjny: {int(modifier or 0):+d} (doliczany automatycznie).")

        total = int(weapon_attack_bonus.get("total", 0) or 0)
        prof = int(weapon_attack_bonus.get("proficiency_bonus", 0) or 0)
        ability = int(weapon_attack_bonus.get("ability_bonus", 0) or 0)
        item = int(weapon_attack_bonus.get("item_bonus", 0) or 0)
        level = int(weapon_attack_bonus.get("level", 0) or 0)
        rank_step = int(weapon_attack_bonus.get("rank_step", 0) or 0)
        rank_label = self._rank_label_pl(weapon_attack_bonus.get("rank"))
        ability_label = self._ability_label_pl(weapon_attack_bonus.get("ability_key"))

        lines.append(
            f"Bonus ataku bronia: {total:+d} "
            f"(Bieglosc {rank_label}: poziom {level} + {rank_step} = {prof:+d}; "
            f"{ability_label}: {ability:+d}; Item: {item:+d})."
        )
        lines.append("Wynik ataku = k20 + bonus broni + modyfikator sytuacyjny.")

        details = [str(line).strip() for line in list(log_lines or []) if str(line).strip()]
        if details:
            lines.append("Aktywne premie/kary:")
            lines.extend(f"- {entry}" for entry in details)
        return lines

    def _attack_roll_stack_payload(
        self,
        *,
        weapon_attack_bonus: dict[str, object],
        modifier: int,
    ) -> dict[str, object]:
        prof = int(weapon_attack_bonus.get("proficiency_bonus", 0) or 0)
        ability = int(weapon_attack_bonus.get("ability_bonus", 0) or 0)
        item = int(weapon_attack_bonus.get("item_bonus", 0) or 0)
        situational = int(modifier or 0)
        rank_label = self._rank_label_pl(weapon_attack_bonus.get("rank"))
        level = int(weapon_attack_bonus.get("level", 0) or 0)
        rank_step = int(weapon_attack_bonus.get("rank_step", 0) or 0)
        ability_label = self._ability_label_pl(weapon_attack_bonus.get("ability_key"))

        components: list[dict[str, object]] = [
            {
                "id": "proficiency",
                "label": "Biegłość",
                "value": prof,
                "description": f"{rank_label}: poziom {level} + {rank_step}.",
                "editable": True,
            },
            {
                "id": "ability",
                "label": f"{ability_label}",
                "value": ability,
                "description": f"Modyfikator cechy ({ability_label}).",
                "editable": True,
            },
            {
                "id": "item",
                "label": "Przedmiot",
                "value": item,
                "description": "Premie/kary z wyposażenia.",
                "editable": True,
            },
        ]
        if situational:
            components.append(
                {
                    "id": "situational",
                    "label": "Sytuacyjne",
                    "value": situational,
                    "description": "Status/circumstance/MAP i inne modyfikatory akcji.",
                    "editable": True,
                }
            )

        return {
            "components": components,
            "auto_total_modifier": int(prof + ability + item + situational),
        }

    @staticmethod
    def _primary_damage_prompt_text(damage_prompt: str | Iterable[str]) -> str:
        if isinstance(damage_prompt, str):
            return str(damage_prompt)
        prompt_list = list(damage_prompt or [])
        if not prompt_list:
            return ""
        return str(prompt_list[0] or "")

    def _damage_prompt_ability_key(self, damage_prompt: str | Iterable[str]) -> str | None:
        text = self._primary_damage_prompt_text(damage_prompt).upper()
        for token, ability_key in self._ABILITY_TOKEN_TO_KEY.items():
            if re.search(rf"\b{token}\b", text):
                return ability_key
        return None

    @staticmethod
    def _static_damage_prompt_modifier(damage_prompt: str | Iterable[str]) -> int:
        text = AttackEventBase._primary_damage_prompt_text(damage_prompt)
        if not text:
            return 0
        # Wytnij "XdY"/"XkY", aby zebrać tylko stałe składniki z formuły.
        cleaned = re.sub(r"\d+\s*[kKdD]\s*\d+", "", text)
        total = 0
        for sign, value in re.findall(r"([+-])\s*(\d+)", cleaned):
            try:
                amount = int(value)
            except Exception:
                continue
            total += amount if sign == "+" else -amount
        return int(total)

    def _damage_roll_stack_payload(
        self,
        *,
        actor,
        damage_prompt: str | Iterable[str],
        extra_flat_bonus: int = 0,
    ) -> dict[str, object]:
        ability_key = self._damage_prompt_ability_key(damage_prompt)
        ability_bonus = self._ability_modifier(actor, ability_key)
        static_bonus = self._static_damage_prompt_modifier(damage_prompt)
        other_bonus = int(extra_flat_bonus or 0) + int(static_bonus or 0)
        ability_label = self._ability_label_pl(ability_key) if ability_key else "Cecha"
        ability_desc = (
            f"Modyfikator cechy ({ability_label}) z formuły obrażeń."
            if ability_key
            else "Brak cechy w formule obrażeń (możesz skorygować ręcznie)."
        )

        components: list[dict[str, object]] = [
            {
                "id": "ability",
                "label": ability_label,
                "value": int(ability_bonus),
                "description": ability_desc,
                "editable": True,
            },
            {
                "id": "item",
                "label": "Przedmiot",
                "value": 0,
                "description": "Premie/kary z broni i wyposażenia.",
                "editable": True,
            },
            {
                "id": "status",
                "label": "Status",
                "value": 0,
                "description": "Premie/kary status do obrażeń.",
                "editable": True,
            },
            {
                "id": "circumstance",
                "label": "Okoliczności",
                "value": 0,
                "description": "Premie/kary circumstance do obrażeń.",
                "editable": True,
            },
            {
                "id": "other",
                "label": "Inne",
                "value": int(other_bonus),
                "description": "Dodatkowe automatyczne modyfikatory (featy, cechy, efekt ataku).",
                "editable": True,
            },
        ]
        auto_total = sum(int(item.get("value", 0) or 0) for item in components)
        return {
            "components": components,
            "auto_total_modifier": int(auto_total),
        }

    def _prompt_damage_roll_total(
        self,
        *,
        prompt: str,
        actor,
        damage_prompt: str | Iterable[str],
        extra_flat_bonus: int = 0,
        prompt_long: str | None = None,
        answer_placeholder: str = "Suma obrażeń",
        roll_for_damage=None,
    ) -> int:
        stack = self._damage_roll_stack_payload(
            actor=actor,
            damage_prompt=damage_prompt,
            extra_flat_bonus=int(extra_flat_bonus or 0),
        )
        roller = roll_for_damage if callable(roll_for_damage) else prompt_for_roll
        roll_data = roller(
            prompt,
            layout="damage",
            answer_placeholder=answer_placeholder,
            prompt_long=prompt_long,
            roll_stack=stack,
            auto_total_modifier=int(stack.get("auto_total_modifier", 0) or 0),
            return_details=True,
        )
        if isinstance(roll_data, dict):
            try:
                computed_total = roll_data.get("computed_total", None)
                if computed_total is not None:
                    total = int(computed_total or 0)
                    raw_roll = int(roll_data.get("raw_roll", roll_data.get("roll", 0)) or 0)
                    rolled = int(roll_data.get("roll", raw_roll) or raw_roll)
                    return int(total + (rolled - raw_roll))
            except Exception:
                pass
            try:
                rolled = int(roll_data.get("roll", 0) or 0)
            except Exception:
                rolled = 0
            try:
                modifier_delta = int(roll_data.get("modifier_delta", 0) or 0)
            except Exception:
                modifier_delta = 0
            return int(rolled + int(stack.get("auto_total_modifier", 0) or 0) + modifier_delta)
        try:
            rolled = int(roll_data or 0)
        except Exception:
            return 0
        return int(rolled + int(stack.get("auto_total_modifier", 0) or 0))
