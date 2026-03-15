from __future__ import annotations

from typing import Iterable

from .base_armor import BaseArmor
from .basic_armors import (
    BreastplateArmor,
    ChainShirtArmor,
    ChainMailArmor,
    FullPlateArmor,
    HalfPlateArmor,
    HideArmor,
    LeatherArmor,
    PaddedArmor,
    ScaleMailArmor,
    SplintMailArmor,
    StuddedLeatherArmor,
    armor_profile,
    create_armor,
    list_armor_ids,
    normalize_armor_id,
)
from .specialization import (
    armor_potency_rune_value,
    armor_specialization_rule,
    normalize_armor_category,
    normalize_armor_group,
)

_PHYSICAL_DAMAGE_TYPES = {"normal", "slashing", "piercing", "bludgeoning"}
_BULWARK_CONTEXT_TAGS = {
    "area",
    "aoe",
    "burst",
    "cone",
    "emanation",
    "explosion",
    "line",
    "splash",
    "whole_body",
}


def _normalize_tags(raw_tags: Iterable[object] | None) -> set[str]:
    out: set[str] = set()
    for item in raw_tags or ():
        tag = str(item or "").strip().lower().replace("-", "_").replace(" ", "_")
        if tag:
            out.add(tag)
    return out


def _iter_status_data(actor):
    for status in getattr(actor, "statuses", []) or []:
        data = getattr(status, "data", None)
        if isinstance(data, dict):
            yield str(getattr(status, "id", "") or ""), data


def _has_status(actor, status_id: str) -> bool:
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


def _dex_modifier(actor) -> int:
    if actor is None:
        return 0
    for key in ("dex_mod", "dexterity_mod"):
        raw = getattr(actor, key, None)
        if raw is None:
            continue
        try:
            return int(raw)
        except Exception:
            continue
    ability_modifiers = getattr(actor, "ability_modifiers", None)
    if isinstance(ability_modifiers, dict):
        try:
            return int(ability_modifiers.get("dexterity", 0) or 0)
        except Exception:
            return 0
    return 0


def get_equipped_armor(actor) -> object | None:
    if actor is None:
        return None
    equipped = getattr(actor, "equipped_armor", None)
    if equipped is not None and str(getattr(equipped, "category", "") or "").strip().lower() == "armor":
        return equipped

    equipped_id = str(getattr(actor, "equipped_armor_item_id", "") or "").strip()
    if not equipped_id:
        return None
    inventory = getattr(actor, "inventory", None)
    if not isinstance(inventory, list):
        return None
    for item in inventory:
        if str(getattr(item, "category", "") or "").strip().lower() != "armor":
            continue
        if str(getattr(item, "instance_id", "") or "").strip() == equipped_id:
            return item
    return None


def equipped_armor_traits(actor) -> set[str]:
    armor = get_equipped_armor(actor)
    if armor is None:
        return set()
    return _normalize_tags(getattr(armor, "traits", ()))


def armor_has_trait(actor, trait: str) -> bool:
    needle = str(trait or "").strip().lower().replace("-", "_").replace(" ", "_")
    if not needle:
        return False
    return needle in equipped_armor_traits(actor)


def armor_ac_bonus(actor) -> int:
    armor = get_equipped_armor(actor)
    if armor is None:
        return 0
    try:
        return max(0, int(getattr(armor, "ac_bonus", 0) or 0))
    except Exception:
        return 0


def armor_skill_check_penalty(actor, *, skill_id: str) -> int:
    armor = get_equipped_armor(actor)
    if armor is None:
        return 0
    skill = str(skill_id or "").strip().lower()
    if skill not in {"stealth", "acrobatics", "athletics"}:
        return 0

    penalty = 0
    try:
        penalty = max(0, int(getattr(armor, "check_penalty", 0) or 0))
    except Exception:
        penalty = 0
    if penalty <= 0:
        return 0

    if skill in {"acrobatics", "athletics"} and armor_has_trait(actor, "flexible"):
        return 0

    # Noisy does not change magnitude; it only prevents ignoring stealth penalty
    # from strength handling. Strength-based mitigation is not modeled yet.
    return max(0, int(penalty))


def armor_stealth_penalty(actor) -> int:
    return armor_skill_check_penalty(actor, skill_id="stealth")


def bulwark_reflex_bonus(actor, *, tags: Iterable[object] | None = None) -> int:
    armor = get_equipped_armor(actor)
    if armor is None or not armor_has_trait(actor, "bulwark"):
        return 0
    normalized_tags = _normalize_tags(tags)
    if normalized_tags and not (_BULWARK_CONTEXT_TAGS & normalized_tags):
        return 0
    if not normalized_tags:
        return 0
    try:
        floor = int(getattr(armor, "bulwark_reflex_floor", 3) or 3)
    except Exception:
        floor = 3
    return max(0, int(floor) - int(_dex_modifier(actor)))


def _armor_specialization_enabled(actor) -> bool:
    return bool(_has_status(actor, "armor_specialization") or _has_status(actor, "armor_specialization_all"))


def _armor_specialization_amount_override(actor, *, category: str) -> int:
    amount = 0
    for status_id, data in _iter_status_data(actor):
        if status_id not in {"armor_specialization", "armor_specialization_all"}:
            continue
        value = data.get("armor_specialization_reduction")
        try:
            if value is not None:
                amount = max(amount, int(value))
        except Exception:
            pass
        mapping = data.get("armor_specialization_reduction_by_category")
        if isinstance(mapping, dict):
            try:
                mapped = int(mapping.get(category, 0) or 0)
                amount = max(amount, mapped)
            except Exception:
                pass
    return max(0, int(amount))


def _armor_specialization_effect(actor, *, armor) -> dict[str, object]:
    category = normalize_armor_category(getattr(armor, "armor_category", "light"))
    group = normalize_armor_group(getattr(armor, "armor_group", "cloth"))
    if not _armor_specialization_enabled(actor):
        return {
            "enabled": False,
            "group": group,
            "category": category,
            "kind": "",
            "amount": 0,
        }

    potency = max(0, int(armor_potency_rune_value(armor)))
    effect = armor_specialization_rule(
        armor_group=group,
        armor_category=category,
        potency=potency,
    )
    if not bool(effect.get("enabled")):
        return effect

    override = _armor_specialization_amount_override(actor, category=category)
    if override > 0:
        effect["amount"] = max(int(effect.get("amount", 0) or 0), override)
    return effect


def armor_specialization_reduction(actor, *, armor=None) -> int:
    selected = armor if armor is not None else get_equipped_armor(actor)
    if selected is None:
        return 0
    effect = _armor_specialization_effect(actor, armor=selected)
    if str(effect.get("kind", "") or "") != "critical_physical":
        return 0
    return max(0, int(effect.get("amount", 0) or 0))


def _reduce_components(
    components: list[tuple[str, int]],
    *,
    allowed_types: set[str],
    reduction: int,
) -> tuple[list[tuple[str, int]], int]:
    left = max(0, int(reduction or 0))
    if left <= 0:
        return list(components), 0
    reduced: list[tuple[str, int]] = []
    spent = 0
    for dtype, amount in components:
        damage_type = str(dtype or "").strip().lower()
        current = max(0, int(amount or 0))
        if left > 0 and damage_type in allowed_types:
            taken = min(current, left)
            current -= taken
            left -= taken
            spent += taken
        reduced.append((damage_type, current))
    return reduced, spent


def apply_critical_damage_reduction(
    actor,
    components: list[tuple[str, int]],
    *,
    critical: bool,
) -> tuple[list[tuple[str, int]], list[str]]:
    armor = get_equipped_armor(actor)
    if armor is None:
        return list(components), []

    reduced = [(str(dtype or "").strip().lower(), max(0, int(amount or 0))) for dtype, amount in components]
    notes: list[str] = []

    effect = _armor_specialization_effect(actor, armor=armor)
    if not bool(effect.get("enabled")):
        return reduced, notes
    amount = max(0, int(effect.get("amount", 0) or 0))
    if amount <= 0:
        return reduced, notes

    kind = str(effect.get("kind", "") or "")
    if kind == "critical_physical" and critical:
        reduced, spent = _reduce_components(
            reduced,
            allowed_types=set(_PHYSICAL_DAMAGE_TYPES),
            reduction=amount,
        )
        if spent > 0:
            notes.append(f"Armor Specialization (chain): -{spent} obrazen z critical.")
    elif kind == "piercing_resistance":
        reduced, spent = _reduce_components(
            reduced,
            allowed_types={"piercing"},
            reduction=amount,
        )
        if spent > 0:
            notes.append(f"Armor Specialization (composite): odpornosc na klute -{spent}.")
    elif kind == "bludgeoning_resistance":
        reduced, spent = _reduce_components(
            reduced,
            allowed_types={"bludgeoning"},
            reduction=amount,
        )
        if spent > 0:
            notes.append(f"Armor Specialization (leather): odpornosc na obuchowe -{spent}.")
    elif kind == "slashing_resistance":
        reduced, spent = _reduce_components(
            reduced,
            allowed_types={"slashing"},
            reduction=amount,
        )
        if spent > 0:
            notes.append(f"Armor Specialization (plate): odpornosc na sieczne -{spent}.")

    return reduced, notes


__all__ = [
    "BaseArmor",
    "PaddedArmor",
    "LeatherArmor",
    "StuddedLeatherArmor",
    "ChainShirtArmor",
    "HideArmor",
    "ScaleMailArmor",
    "BreastplateArmor",
    "ChainMailArmor",
    "SplintMailArmor",
    "HalfPlateArmor",
    "FullPlateArmor",
    "create_armor",
    "list_armor_ids",
    "normalize_armor_id",
    "armor_profile",
    "get_equipped_armor",
    "equipped_armor_traits",
    "armor_has_trait",
    "armor_ac_bonus",
    "armor_skill_check_penalty",
    "armor_stealth_penalty",
    "bulwark_reflex_bonus",
    "armor_specialization_reduction",
    "apply_critical_damage_reduction",
]
