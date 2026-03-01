from __future__ import annotations

import logging
from typing import Iterable, Optional
import re

from bonuses import BonusEffect, BonusType, compute_total_modifier, format_effects_log, select_best_effects
from damage_types import DamageType
from combat import effective_ac
from GameObjects.interactions_mixin import prompt_for_roll
from statuses import CONCEALED_STATUS, DARKVISION_STATUS, DIM_LIGHT_VISION_STATUS, IN_DIM_LIGHT_STATUS, LOW_LIGHT_VISION_STATUS

from ..base import GameEvent

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
            if combat_state is not None and hasattr(combat_state, "attack_state"):
                return combat_state.attack_state.setdefault(actor, {})
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

    def _record_attack(
        self,
        ctx,
        actor,
        *,
        weapon_key: str,
        weapon_type: str | None,
        target,
    ) -> None:
        state = self._get_attack_state(ctx, actor)
        state["attacks_this_turn"] = int(state.get("attacks_this_turn", 0) or 0) + 1
        weapon_counts = state.setdefault("weapon_counts", {})
        weapon_counts[weapon_key] = int(weapon_counts.get(weapon_key, 0) or 0) + 1
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
