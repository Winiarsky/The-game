from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
from typing import Any

from .catalog import ABILITY_IDS, CORE_SKILL_IDS


SKILL_TO_ABILITY: dict[str, str] = {
    "acrobatics": "dexterity",
    "arcana": "intelligence",
    "athletics": "strength",
    "crafting": "intelligence",
    "deception": "charisma",
    "diplomacy": "charisma",
    "intimidation": "charisma",
    "medicine": "wisdom",
    "nature": "wisdom",
    "occultism": "intelligence",
    "performance": "charisma",
    "religion": "wisdom",
    "society": "intelligence",
    "stealth": "dexterity",
    "survival": "wisdom",
    "thievery": "dexterity",
    "perception": "wisdom",
    "fortitude": "constitution",
    "reflex": "dexterity",
    "will": "wisdom",
}

RANK_ORDER = ("untrained", "trained", "expert", "master", "legendary")
RANK_BONUS = {
    "untrained": 0,
    "trained": 2,
    "expert": 4,
    "master": 6,
    "legendary": 8,
}

RANK_INDEX = {rank: index for index, rank in enumerate(RANK_ORDER)}


@dataclass
class CharacterMath:
    ability_scores: dict[str, int]
    ability_modifiers: dict[str, int]
    skill_ranks: dict[str, str]
    skill_modifiers: dict[str, int]
    perception_rank: str
    perception_bonus: int
    save_ranks: dict[str, str]
    save_modifiers: dict[str, int]
    max_hp: int
    speed_feet: int
    ac: int


def _clamp_rank(rank: str) -> str:
    raw = str(rank or "").strip().lower()
    if raw in RANK_BONUS:
        return raw
    return "untrained"


def rank_priority(rank: str) -> int:
    return int(RANK_INDEX.get(_clamp_rank(rank), 0))


def higher_rank(current_rank: str, incoming_rank: str) -> str:
    current = _clamp_rank(current_rank)
    incoming = _clamp_rank(incoming_rank)
    if rank_priority(incoming) > rank_priority(current):
        return incoming
    return current


def normalize_rank_map(
    rank_map: dict[str, str] | None,
    *,
    allowed_keys: Iterable[str] | None = None,
    sparse: bool = False,
) -> dict[str, str]:
    out: dict[str, str] = {}
    allowed: set[str] | None = None
    if allowed_keys is not None:
        allowed = {
            str(item).strip().lower()
            for item in allowed_keys
            if str(item).strip()
        }
    for raw_key, raw_rank in dict(rank_map or {}).items():
        key = str(raw_key or "").strip().lower()
        if not key:
            continue
        if allowed is not None and key not in allowed:
            continue
        rank = _clamp_rank(str(raw_rank or "untrained"))
        if sparse and rank == "untrained":
            continue
        previous = out.get(key, "untrained")
        out[key] = higher_rank(previous, rank)
    return out


def compress_rank_map(
    rank_map: dict[str, str] | None,
    *,
    allowed_keys: Iterable[str] | None = None,
) -> dict[str, str]:
    return normalize_rank_map(rank_map, allowed_keys=allowed_keys, sparse=True)


def merge_rank_maps(
    base_map: dict[str, str] | None,
    incoming_map: dict[str, str] | None,
    *,
    allowed_keys: Iterable[str] | None = None,
    sparse: bool = True,
) -> dict[str, str]:
    merged = normalize_rank_map(base_map, allowed_keys=allowed_keys, sparse=False)
    incoming = normalize_rank_map(incoming_map, allowed_keys=allowed_keys, sparse=False)
    for key, rank in incoming.items():
        merged[key] = higher_rank(merged.get(key, "untrained"), rank)
    if sparse:
        return compress_rank_map(merged, allowed_keys=allowed_keys)
    return merged


def base_ability_scores() -> dict[str, int]:
    return {key: 10 for key in ABILITY_IDS}


def apply_ability_boost(scores: dict[str, int], ability: str) -> None:
    key = str(ability or "").strip().lower()
    if key not in scores:
        return
    current = int(scores.get(key, 10))
    scores[key] = current + (1 if current >= 18 else 2)


def apply_character_creation_ability_boost(scores: dict[str, int], ability: str) -> None:
    """Apply a level-1 creation boost, which cannot increase a score above 18."""
    key = str(ability or "").strip().lower()
    if key not in scores:
        return
    current = int(scores.get(key, 10))
    if current >= 18:
        return
    scores[key] = min(18, current + 2)


def apply_ability_flaw(scores: dict[str, int], ability: str) -> None:
    key = str(ability or "").strip().lower()
    if key not in scores:
        return
    scores[key] = int(scores.get(key, 10)) - 2


def ability_modifier(score: int) -> int:
    return (int(score) - 10) // 2


def proficiency_bonus(level: int, rank: str) -> int:
    rank_id = _clamp_rank(rank)
    if rank_id == "untrained":
        return 0
    return max(0, int(level)) + int(RANK_BONUS.get(rank_id, 0))


def _actor_ability_modifier(actor: Any, ability_id: str) -> int:
    ability_key = str(ability_id or "").strip().lower()
    if not ability_key:
        return 0
    ability_modifiers = getattr(actor, "ability_modifiers", None)
    if isinstance(ability_modifiers, dict):
        try:
            return int(ability_modifiers.get(ability_key, 0) or 0)
        except Exception:
            return 0
    short_key = f"{ability_key[:3]}_mod"
    try:
        return int(getattr(actor, short_key, 0) or 0)
    except Exception:
        return 0


def _actor_defense_rank(actor: Any, category: str) -> str:
    key = str(category or "").strip().lower()
    if not key:
        return "untrained"

    current_rank = getattr(actor, "_current_defense_rank", None)
    if callable(current_rank):
        try:
            return _clamp_rank(current_rank(key))
        except Exception:
            pass

    raw = None
    mapping = getattr(actor, "defense_proficiency_ranks", None)
    if isinstance(mapping, dict):
        raw = mapping.get(key, raw)
    for status in getattr(actor, "statuses", None) or []:
        data = getattr(status, "data", None) or {}
        status_mapping = data.get("defense_proficiency_ranks")
        if isinstance(status_mapping, dict) and key in status_mapping:
            raw = status_mapping.get(key, raw)
    return _clamp_rank(str(raw or "untrained"))


def compute_actor_base_ac(actor: Any) -> int:
    """Policz bazowe PF2e AC aktora z uwzględnieniem biegłości, Dex capu i bonusu pancerza."""
    level = max(0, int(getattr(actor, "level", 0) or 0))
    dexterity_modifier = _actor_ability_modifier(actor, "dexterity")
    armor_bonus = 0
    dexterity_contribution = dexterity_modifier
    defense_category = "unarmored"

    try:
        from GameObjects.items.armor import get_equipped_armor

        armor = get_equipped_armor(actor)
    except Exception:
        armor = None

    if armor is not None:
        defense_category = str(getattr(armor, "armor_category", "light") or "light").strip().lower() or "light"
        try:
            armor_bonus = max(0, int(getattr(armor, "ac_bonus", 0) or 0))
        except Exception:
            armor_bonus = 0
        try:
            dex_cap = int(getattr(armor, "dex_cap", dexterity_modifier) or dexterity_modifier)
        except Exception:
            dex_cap = dexterity_modifier
        dexterity_contribution = min(dexterity_modifier, dex_cap)

    proficiency = proficiency_bonus(level, _actor_defense_rank(actor, defense_category))
    return 10 + int(proficiency) + int(dexterity_contribution) + int(armor_bonus)


def refresh_actor_ac(actor: Any) -> int:
    """Przelicz i zapisz bazowe AC aktora zgodnie z PF2e."""
    ac_value = compute_actor_base_ac(actor)
    try:
        actor.ac = int(ac_value)
    except Exception:
        pass
    try:
        actor.ac_includes_armor_bonus = True
    except Exception:
        pass
    return int(ac_value)


def compute_math(
    *,
    level: int,
    ability_scores: dict[str, int],
    skill_ranks: dict[str, str],
    perception_rank: str,
    save_ranks: dict[str, str],
    ancestry_hp: int,
    class_hp: int,
    speed_feet: int,
    unarmored_rank: str,
    armor_bonus: int = 0,
) -> CharacterMath:
    scores = {key: int(ability_scores.get(key, 10)) for key in ABILITY_IDS}
    mods = {key: ability_modifier(value) for key, value in scores.items()}

    normalized_skill_ranks: dict[str, str] = {}
    for skill_id in CORE_SKILL_IDS:
        normalized_skill_ranks[skill_id] = _clamp_rank(skill_ranks.get(skill_id, "untrained"))

    skill_mods: dict[str, int] = {}
    for skill_id, rank in normalized_skill_ranks.items():
        ability_id = SKILL_TO_ABILITY.get(skill_id, "intelligence")
        skill_mods[skill_id] = mods.get(ability_id, 0) + proficiency_bonus(level, rank)

    p_rank = _clamp_rank(perception_rank)
    p_bonus = mods.get(SKILL_TO_ABILITY["perception"], 0) + proficiency_bonus(level, p_rank)

    normalized_save_ranks = {
        "fortitude": _clamp_rank(save_ranks.get("fortitude", "untrained")),
        "reflex": _clamp_rank(save_ranks.get("reflex", "untrained")),
        "will": _clamp_rank(save_ranks.get("will", "untrained")),
    }
    save_mods = {
        "fortitude": mods.get("constitution", 0) + proficiency_bonus(level, normalized_save_ranks["fortitude"]),
        "reflex": mods.get("dexterity", 0) + proficiency_bonus(level, normalized_save_ranks["reflex"]),
        "will": mods.get("wisdom", 0) + proficiency_bonus(level, normalized_save_ranks["will"]),
    }

    hp = int(ancestry_hp) + int(class_hp) + mods.get("constitution", 0)
    hp = max(1, hp)
    ac = 10 + mods.get("dexterity", 0) + proficiency_bonus(level, _clamp_rank(unarmored_rank)) + int(armor_bonus)

    return CharacterMath(
        ability_scores=scores,
        ability_modifiers=mods,
        skill_ranks=normalized_skill_ranks,
        skill_modifiers=skill_mods,
        perception_rank=p_rank,
        perception_bonus=p_bonus,
        save_ranks=normalized_save_ranks,
        save_modifiers=save_mods,
        max_hp=hp,
        speed_feet=max(5, int(speed_feet or 25)),
        ac=ac,
    )


def apply_math_to_hero(
    hero: Any,
    math: CharacterMath,
    *,
    weapon_proficiency_ranks: dict[str, str] | None = None,
    defense_proficiency_ranks: dict[str, str] | None = None,
    trained_skills: list[str] | None = None,
    lore_skills: list[str] | None = None,
) -> None:
    hero.ability_scores = dict(math.ability_scores)
    hero.ability_modifiers = dict(math.ability_modifiers)
    hero.level = int(getattr(hero, "level", 1) or 1)

    hero.str_mod = int(math.ability_modifiers.get("strength", 0))
    hero.dex_mod = int(math.ability_modifiers.get("dexterity", 0))
    hero.con_mod = int(math.ability_modifiers.get("constitution", 0))
    hero.int_mod = int(math.ability_modifiers.get("intelligence", 0))
    hero.wis_mod = int(math.ability_modifiers.get("wisdom", 0))
    hero.cha_mod = int(math.ability_modifiers.get("charisma", 0))

    hero.skill_ranks = compress_rank_map(math.skill_ranks, allowed_keys=CORE_SKILL_IDS)
    hero.skill_modifiers = dict(math.skill_modifiers)
    trained_from_ranks = {skill_id for skill_id, rank in dict(math.skill_ranks).items() if _clamp_rank(rank) != "untrained"}
    trained_from_input = {
        str(item).strip().lower()
        for item in (trained_skills or [])
        if str(item).strip()
    }
    hero.trained_skills = sorted((trained_from_ranks | trained_from_input) & set(CORE_SKILL_IDS))
    hero.lore_skills = sorted(set(str(item).strip() for item in (lore_skills or [] if lore_skills else [])))

    for skill_id in CORE_SKILL_IDS:
        rank = _clamp_rank(dict(math.skill_ranks).get(skill_id, "untrained"))
        setattr(hero, f"{skill_id}_trained", rank != "untrained" or skill_id in set(hero.trained_skills))
        setattr(hero, f"{skill_id}_bonus", int(math.skill_modifiers.get(skill_id, 0)))

    hero.perception_rank = str(math.perception_rank)
    hero.perception_bonus = int(math.perception_bonus)

    hero.save_ranks = compress_rank_map(math.save_ranks, allowed_keys=("fortitude", "reflex", "will"))
    hero.fortitude_bonus = int(math.save_modifiers.get("fortitude", 0))
    hero.reflex_bonus = int(math.save_modifiers.get("reflex", 0))
    hero.will_bonus = int(math.save_modifiers.get("will", 0))

    hero.base_speed_feet = int(math.speed_feet)
    hero.max_hp = int(math.max_hp)
    hero.temp_hp = int(getattr(hero, "temp_hp", 0) or 0)
    hero.ac = int(math.ac)

    if isinstance(weapon_proficiency_ranks, dict):
        hero.weapon_proficiency_ranks = compress_rank_map(weapon_proficiency_ranks)
    if isinstance(defense_proficiency_ranks, dict):
        hero.defense_proficiency_ranks = compress_rank_map(defense_proficiency_ranks)

    refresh_actor_ac(hero)


__all__ = [
    "SKILL_TO_ABILITY",
    "RANK_ORDER",
    "RANK_BONUS",
    "CharacterMath",
    "base_ability_scores",
    "apply_ability_boost",
    "apply_character_creation_ability_boost",
    "apply_ability_flaw",
    "ability_modifier",
    "proficiency_bonus",
    "rank_priority",
    "higher_rank",
    "normalize_rank_map",
    "compress_rank_map",
    "merge_rank_maps",
    "compute_math",
    "compute_actor_base_ac",
    "refresh_actor_ac",
    "apply_math_to_hero",
]
