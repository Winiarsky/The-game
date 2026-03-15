from __future__ import annotations

from enum import Enum
from typing import Iterable


class WeaponCategory(str, Enum):
    SIMPLE = "simple"
    MARTIAL = "martial"
    ADVANCED = "advanced"
    UNARMED = "unarmed"


class ProficiencyRank(str, Enum):
    UNTRAINED = "untrained"
    TRAINED = "trained"
    EXPERT = "expert"
    MASTER = "master"
    LEGENDARY = "legendary"


_RANK_BONUS_STEP = {
    ProficiencyRank.UNTRAINED: 0,
    ProficiencyRank.TRAINED: 2,
    ProficiencyRank.EXPERT: 4,
    ProficiencyRank.MASTER: 6,
    ProficiencyRank.LEGENDARY: 8,
}

_RANK_ALIASES = {
    "u": ProficiencyRank.UNTRAINED,
    "t": ProficiencyRank.TRAINED,
    "e": ProficiencyRank.EXPERT,
    "m": ProficiencyRank.MASTER,
    "l": ProficiencyRank.LEGENDARY,
    "untrained": ProficiencyRank.UNTRAINED,
    "trained": ProficiencyRank.TRAINED,
    "expert": ProficiencyRank.EXPERT,
    "master": ProficiencyRank.MASTER,
    "legendary": ProficiencyRank.LEGENDARY,
}

_RANK_FROM_INT = {
    0: ProficiencyRank.UNTRAINED,
    2: ProficiencyRank.TRAINED,
    4: ProficiencyRank.EXPERT,
    6: ProficiencyRank.MASTER,
    8: ProficiencyRank.LEGENDARY,
}

_DEFAULT_TAG_CATEGORY = {
    "unarmed": WeaponCategory.UNARMED,
    "sword": WeaponCategory.MARTIAL,
    "longsword": WeaponCategory.MARTIAL,
    "shortsword": WeaponCategory.MARTIAL,
    "rapier": WeaponCategory.MARTIAL,
    "greataxe": WeaponCategory.MARTIAL,
    "warhammer": WeaponCategory.MARTIAL,
    "halberd": WeaponCategory.MARTIAL,
    "glaive": WeaponCategory.MARTIAL,
    "longbow": WeaponCategory.MARTIAL,
    "shortbow": WeaponCategory.MARTIAL,
    "bow": WeaponCategory.MARTIAL,
    "crossbow": WeaponCategory.SIMPLE,
    "simple_crossbow": WeaponCategory.SIMPLE,
    "light_crossbow": WeaponCategory.SIMPLE,
    "dagger": WeaponCategory.SIMPLE,
    "club": WeaponCategory.SIMPLE,
    "mace": WeaponCategory.SIMPLE,
    "spear": WeaponCategory.SIMPLE,
    "javelin": WeaponCategory.SIMPLE,
    "battle_axe": WeaponCategory.MARTIAL,
    "pick": WeaponCategory.MARTIAL,
}

_GENERIC_TAGS = {"attack", "attack_melee", "attack_ranged", "ranged_attack", "melee_attack", "weapon"}
_NON_WEAPON_KEY_TAGS = {
    "dwarf",
    "elf",
    "gnome",
    "goblin",
    "halfling",
    "orc",
    "simple",
    "martial",
    "advanced",
}


def _safe_int(value, default=0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _norm_token(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _iter_status_data(actor):
    for status in getattr(actor, "statuses", None) or []:
        data = getattr(status, "data", None)
        if isinstance(data, dict):
            yield data


def _normalize_weapon_tags(weapon_tags: Iterable[str] | None) -> list[str]:
    out: list[str] = []
    for item in weapon_tags or []:
        tag = str(item or "").strip().lower().replace("-", "_").replace(" ", "_")
        if not tag:
            continue
        out.append(tag)
    return list(dict.fromkeys(out))


def _weapon_key_from_tags(tags: list[str]) -> str | None:
    for tag in tags:
        if tag in _GENERIC_TAGS:
            continue
        if tag in _NON_WEAPON_KEY_TAGS:
            continue
        if tag in _DEFAULT_TAG_CATEGORY:
            return tag
    for tag in tags:
        if tag in _GENERIC_TAGS:
            continue
        if tag in _NON_WEAPON_KEY_TAGS:
            continue
        return tag
    return None


def _category_from_tags(tags: list[str]) -> WeaponCategory:
    for tag in tags:
        if tag in WeaponCategory._value2member_map_:
            return WeaponCategory(tag)
        category = _DEFAULT_TAG_CATEGORY.get(tag)
        if category is not None:
            return category
    return WeaponCategory.SIMPLE


def _normalize_rank(value) -> ProficiencyRank:
    if isinstance(value, ProficiencyRank):
        return value
    if isinstance(value, int):
        return _RANK_FROM_INT.get(int(value), ProficiencyRank.UNTRAINED)
    raw = str(value or "").strip().lower()
    return _RANK_ALIASES.get(raw, ProficiencyRank.UNTRAINED)


def _apply_category_adjustments(actor, category: WeaponCategory, tags: list[str]) -> WeaponCategory:
    current = category
    for data in _iter_status_data(actor):
        adjustments = data.get("weapon_category_adjustments") or []
        if not isinstance(adjustments, list):
            continue
        for entry in adjustments:
            if not isinstance(entry, dict):
                continue
            required = str(entry.get("required_tag", "") or "").strip().lower().replace("-", "_")
            if required and required not in tags:
                continue
            src = str(entry.get("from", "") or "").strip().lower()
            dst = str(entry.get("to", "") or "").strip().lower()
            if src != current.value or dst not in WeaponCategory._value2member_map_:
                continue
            current = WeaponCategory(dst)
    return current


def _rank_override_for_weapon(actor, weapon_key: str | None) -> ProficiencyRank | None:
    if not weapon_key:
        return None
    raw = None
    actor_map = getattr(actor, "weapon_proficiency_overrides", None)
    if isinstance(actor_map, dict) and weapon_key in actor_map:
        raw = actor_map.get(weapon_key)
    for data in _iter_status_data(actor):
        mapping = data.get("weapon_proficiency_overrides")
        if isinstance(mapping, dict) and weapon_key in mapping:
            raw = mapping.get(weapon_key)
    if raw is None:
        return None
    return _normalize_rank(raw)


def _rank_for_category(actor, category: WeaponCategory) -> ProficiencyRank:
    raw = None
    actor_map = getattr(actor, "weapon_proficiency_ranks", None)
    if isinstance(actor_map, dict):
        raw = actor_map.get(category.value, raw)
    for data in _iter_status_data(actor):
        mapping = data.get("weapon_proficiency_ranks")
        if isinstance(mapping, dict):
            raw = mapping.get(category.value, raw)
    return _normalize_rank(raw)


def _ability_mod_value(actor, ability_key: str) -> int:
    key = str(ability_key or "").strip().lower()
    if key in {"strength", "str"}:
        direct_keys = ("str_mod", "strength_mod")
        dict_keys = ("strength", "str")
    elif key in {"dexterity", "dex"}:
        direct_keys = ("dex_mod", "dexterity_mod")
        dict_keys = ("dexterity", "dex")
    else:
        direct_keys = ()
        dict_keys = (key,)

    for attr in direct_keys:
        raw = getattr(actor, attr, None)
        if raw is not None:
            return _safe_int(raw, 0)

    ability_modifiers = getattr(actor, "ability_modifiers", None)
    if isinstance(ability_modifiers, dict):
        for dict_key in dict_keys:
            if dict_key in ability_modifiers:
                return _safe_int(ability_modifiers.get(dict_key), 0)
    return 0


def _ability_modifier(actor, *, is_ranged: bool, finesse: bool, brutal: bool) -> tuple[int, str]:
    # PF2: finesse pozwala użyć DEX zamiast STR do ataku (wybieramy korzystniejszy).
    str_mod = _ability_mod_value(actor, "strength")
    dex_mod = _ability_mod_value(actor, "dexterity")
    if brutal:
        return str_mod, "strength"
    if is_ranged and not finesse:
        return dex_mod, "dexterity"
    if finesse:
        if dex_mod >= str_mod:
            return dex_mod, "dexterity"
        return str_mod, "strength"
    return str_mod, "strength"


def _equipped_weapon_item_bonus(actor, weapon_key: str | None) -> int:
    try:
        from GameObjects.items.inventory import get_equipped_weapons
        from GameObjects.items.weapon import normalize_weapon_id
    except Exception:
        return 0

    best = 0
    for weapon in list(get_equipped_weapons(actor) or []):
        item_weapon_id = _norm_token(normalize_weapon_id(getattr(weapon, "item_id", None)))
        if weapon_key and item_weapon_id and item_weapon_id != _norm_token(weapon_key):
            continue
        for attr in ("potency_bonus", "potency_rune", "weapon_potency", "attack_item_bonus", "item_bonus"):
            raw = getattr(weapon, attr, None)
            if raw is None:
                continue
            best = max(best, _safe_int(raw, 0))
    return max(0, best)


def _item_bonus(actor, weapon_key: str | None) -> int:
    bonus = 0
    raw = getattr(actor, "weapon_attack_item_bonus", None)
    if isinstance(raw, int):
        bonus = max(bonus, int(raw))
    elif isinstance(raw, dict):
        if weapon_key and weapon_key in raw:
            bonus = max(bonus, _safe_int(raw.get(weapon_key), 0))
        bonus = max(bonus, _safe_int(raw.get("default"), 0))
    for data in _iter_status_data(actor):
        item_data = data.get("weapon_attack_item_bonus")
        if isinstance(item_data, int):
            bonus = max(bonus, int(item_data))
        elif isinstance(item_data, dict):
            if weapon_key and weapon_key in item_data:
                bonus = max(bonus, _safe_int(item_data.get(weapon_key), 0))
            bonus = max(bonus, _safe_int(item_data.get("default"), 0))
    bonus = max(bonus, _equipped_weapon_item_bonus(actor, weapon_key))
    return max(0, bonus)


def proficiency_bonus(rank: ProficiencyRank, *, level: int) -> int:
    if rank == ProficiencyRank.UNTRAINED:
        return 0
    return max(0, int(level)) + _RANK_BONUS_STEP.get(rank, 0)


def compute_weapon_attack_roll_bonus(
    actor,
    *,
    weapon_tags: Iterable[str] | None,
    is_ranged: bool = False,
    finesse: bool = False,
    brutal: bool = False,
) -> dict[str, object]:
    """Policz mechaniczny bonus do ataku bronią."""
    tags = _normalize_weapon_tags(weapon_tags)
    weapon_key = _weapon_key_from_tags(tags)
    base_category = _category_from_tags(tags)
    category = _apply_category_adjustments(actor, base_category, tags)

    rank = _rank_override_for_weapon(actor, weapon_key)
    if rank is None:
        rank = _rank_for_category(actor, category)
    level = max(0, _safe_int(getattr(actor, "level", 1), 1))
    prof_bonus = proficiency_bonus(rank, level=level)
    ability_bonus, ability_key = _ability_modifier(actor, is_ranged=is_ranged, finesse=finesse, brutal=brutal)
    item_bonus = _item_bonus(actor, weapon_key)
    total = int(prof_bonus) + int(ability_bonus) + int(item_bonus)

    return {
        "total": total,
        "weapon_key": weapon_key,
        "category": category.value,
        "rank": rank.value,
        "rank_step": int(_RANK_BONUS_STEP.get(rank, 0) or 0),
        "level": int(level),
        "proficiency_bonus": prof_bonus,
        "ability_bonus": ability_bonus,
        "ability_key": ability_key,
        "item_bonus": item_bonus,
    }


__all__ = [
    "WeaponCategory",
    "ProficiencyRank",
    "proficiency_bonus",
    "compute_weapon_attack_roll_bonus",
]
