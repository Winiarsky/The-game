from __future__ import annotations

import logging
from typing import Iterable, Optional
import re

from bonuses import BonusEffect, BonusType, compute_total_modifier, format_effects_log, select_best_effects
from damage_types import DamageType
from combat import effective_ac
from GameObjects.interactions_mixin import prompt_for_roll
from statuses import CONCEALED_STATUS, DARKVISION_STATUS, DIM_LIGHT_VISION_STATUS, IN_DIM_LIGHT_STATUS, LOW_LIGHT_VISION_STATUS

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
    has_status = getattr(target, "has_status", None)
    if callable(has_status):
        concealed = has_status(CONCEALED_STATUS)
    else:
        concealed = False
        for status in getattr(target, "statuses", []) or []:
            if getattr(status, "id", None) == CONCEALED_STATUS.id or status == CONCEALED_STATUS.id:
                concealed = True
                break
    if not concealed:
        return True
    dc = 5
    if _has_status(attacker, "keen_eyes"):
        dc = 3
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
    has_status = getattr(obj, "has_status", None)
    if callable(has_status):
        return bool(has_status(status))
    for item in getattr(obj, "statuses", []) or []:
        item_id = getattr(item, "id", None)
        if item_id == status.id or item == status.id:
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

    def _ac_with_bonuses(
        self,
        target,
        *,
        attacker=None,
        extra_bonuses: Optional[Iterable[BonusEffect]] = None,
    ) -> tuple[int, int, int]:
        """Zwraca (target_ac, base_ac, modifier) z uwzględnieniem tymczasowych bonusów (np. osłony).

        base_ac – pochodzi z atrybutu celu lub effective_ac (które uwzględnia np. flat-footed).
        modifier – suma najlepszych bonusów/kar z listy bonusów celu + extra_bonuses pod tagiem "ac".
        """

        base_ac = getattr(target, "ac", effective_ac(target))
        bonuses = list(getattr(target, "bonuses", [])) if hasattr(target, "bonuses") else []
        if extra_bonuses:
            bonuses.extend(list(extra_bonuses))

        modifier = compute_total_modifier(bonuses, "ac", getattr(attacker, "object_id", None)) if bonuses else 0
        target_ac = base_ac + modifier
        return target_ac, base_ac, modifier

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
        if not critical or not is_off_guard:
            return
        if not self._is_rogue_actor(actor):
            return
        if self._rogue_racket(actor) != "ruffian":
            return

        simple_weapon_ids = {
            "club",
            "crossbow",
            "dagger",
            "javelin",
            "mace",
            "shortspear",
            "sickle",
            "staff",
            "spear",
            "unarmed",
        }
        normalized_weapon = self._normalize_weapon_type(weapon_type) or self._weapon_type_tag(tags) or self._normalize_weapon_type(
            getattr(self, "name", None)
        )
        if normalized_weapon not in simple_weapon_ids:
            return

        die_size = self._first_damage_die_size(damage_prompt)
        if die_size is not None and die_size > 8:
            return
        try:
            ctx.game.ui_log(
                "Ruffian TODO: critical specialization efekt dla simple weapon do podpiecia z globalna mechanika broni."
            )
        except Exception:
            pass

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
        }
        return aliases.get(normalized, normalized)

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
                return bool(has_status("flat_footed"))
            except Exception:
                return False
        for status in getattr(target, "statuses", []) or []:
            if getattr(status, "id", None) == "flat_footed" or status == "flat_footed":
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
        alt_raw = self._tag_value(tags, "versatile")
        if not alt_raw:
            return base_damage_type
        alt_key = str(alt_raw).strip().lower()
        alt_type = self._VERSATILE_MAP.get(alt_key)
        if not alt_type:
            return base_damage_type
        choice = self._prompt_choice(
            "Versatile: wybierz typ obrażeń",
            choices=[base_damage_type, alt_type],
            source="versatile",
        )
        if choice is None:
            return base_damage_type
        choice_norm = str(choice).strip().lower()
        if choice_norm == alt_type:
            return alt_type
        if choice_norm == base_damage_type:
            return base_damage_type
        if choice_norm.startswith(alt_type[:1]):
            return alt_type
        return base_damage_type

    def _maybe_prompt_vengeful_hatred(self, attacker, target) -> None:
        """Pokaż informację o +1 do obrażeń vs wybrany typ przeciwnika (bez naliczania)."""
        getter = getattr(attacker, "get_status_data", None)
        if callable(getter):
            enemy_type = getter("vengeful_hatred", "enemy_type", None)
            bonus = getter("vengeful_hatred", "damage_bonus", 1)
        else:
            enemy_type = None
            bonus = 1
            for status in getattr(attacker, "statuses", []) or []:
                if getattr(status, "id", None) != "vengeful_hatred":
                    continue
                data = getattr(status, "data", {}) or {}
                enemy_type = data.get("enemy_type")
                bonus = data.get("damage_bonus", 1)
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
                    f"Bonus do obrazen +{int(bonus)} vs {enemy_type_norm}. "
                    "Dodaj recznie do wyniku."
                ),
                source="vengeful_hatred",
            )
        except Exception:
            return
