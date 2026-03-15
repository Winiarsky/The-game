from __future__ import annotations

from dataclasses import dataclass
import importlib
import pkgutil
import re
from typing import Any

from statuses.base import Status
from statuses.backgrounds.backgrounds import BACKGROUND_DEFINITIONS, BACKGROUND_STATUS_BY_KEY


ABILITY_IDS: tuple[str, ...] = (
    "strength",
    "dexterity",
    "constitution",
    "intelligence",
    "wisdom",
    "charisma",
)

CORE_SKILL_IDS: tuple[str, ...] = (
    "acrobatics",
    "arcana",
    "athletics",
    "crafting",
    "deception",
    "diplomacy",
    "intimidation",
    "medicine",
    "nature",
    "occultism",
    "performance",
    "religion",
    "society",
    "stealth",
    "survival",
    "thievery",
)

ANCESTRY_IDS: tuple[str, ...] = ("human", "elf", "dwarf", "gnome", "goblin", "halfling")

HERITAGE_IDS_BY_ANCESTRY: dict[str, list[str]] = {
    "human": ["half_elf", "half_orc", "skilled_heritage", "versatile_heritage"],
    "elf": ["arctic_elf", "cavern_elf", "seer_elf", "whisper_elf", "woodland_elf"],
    "dwarf": ["ancient_blooded_dwarf", "forge_dwarf", "rock_dwarf", "strong_blooded_dwarf"],
    "gnome": ["chameleon_gnome", "fey_touched_gnome", "sensate_gnome", "umbral_gnome", "wellspring_gnome"],
    "goblin": ["charhide_goblin", "irongut_goblin", "razortooth_goblin", "snow_goblin", "unbreakable_goblin"],
    "halfling": ["gutsy_halfling", "hillock_halfling", "nomadic_halfling", "twilight_halfling", "wildwood_halfling"],
}

ANCESTRY_FEAT_IDS_BY_ANCESTRY: dict[str, list[str]] = {
    "human": [
        "adapted_cantrip",
        "cooperative_nature",
        "general_training",
        "haughty_obstinacy",
        "natural_ambition",
        "natural_skill",
        "unconventional_weaponry",
        "monstrous_peacemaker",
        "orc_ferocity",
        "orc_sight",
        "orc_superstition",
        "orc_weapon_familiarity",
        "elf_atavism",
    ],
    "elf": [
        "ancestral_longevity",
        "elven_lore",
        "elven_weapon_familiarity",
        "forlorn",
        "nimble_elf",
        "otherworldly_magic",
        "unwavering_mien",
    ],
    "dwarf": [
        "dwarven_lore",
        "dwarven_weapon_familiarity",
        "rock_runner",
        "stonecunning",
        "unburdened_iron",
        "vengeful_hatred",
    ],
    "gnome": [
        "animal_accomplice",
        "burrow_elocutionist",
        "fey_fellowship",
        "first_world_magic",
        "gnome_obsession",
        "gnome_weapon_familiarity",
        "illusion_sense",
    ],
    "goblin": [
        "burn_it",
        "city_scavenger",
        "goblin_lore",
        "goblin_scuttle",
        "goblin_song",
        "goblin_weapon_familiarity",
        "junk_tinker",
        "rough_rider",
        "very_sneaky",
    ],
    "halfling": [
        "distracting_shadows",
        "halfling_lore",
        "halfling_luck",
        "halfling_weapon_familiarity",
        "sure_feet",
        "titan_slinger",
        "unfettered_halfling",
        "watchful_halfling",
    ],
}

CLASS_IDS: tuple[str, ...] = (
    "fighter",
    "rogue",
    "wizard",
    "cleric",
    "barbarian",
    "ranger",
    "bard",
    "alchemist",
    "champion",
    "druid",
    "monk",
    "sorcerer",
)

CLASS_FEAT_CHOICES_MANUAL: dict[str, list[str]] = {
    "fighter": [
        "double_slice",
        "exacting_strike",
        "point_blank_shot",
        "power_attack",
        "reactive_shield",
        "snagging_strike",
        "sudden_charge",
    ],
    "barbarian": [
        "cute_vision",
        "moment_of_clarity",
        "raging_intimidation",
        "raging_thrower",
        "sudden_charge",
    ],
    "champion": [
        "deitys_domain",
        "ranged_reprisal",
        "unimpeded_step",
        "weight_of_guilt",
    ],
}

CLASS_KEY_ABILITY_DEFAULT: dict[str, str] = {
    "fighter": "strength",
    "rogue": "dexterity",
    "wizard": "intelligence",
    "cleric": "wisdom",
    "barbarian": "strength",
    "ranger": "strength",
    "bard": "charisma",
    "alchemist": "intelligence",
    "champion": "strength",
    "druid": "wisdom",
    "monk": "strength",
    "sorcerer": "charisma",
}

CLASS_PERCEPTION_RANK: dict[str, str] = {
    "fighter": "expert",
    "rogue": "expert",
    "wizard": "trained",
    "cleric": "trained",
    "barbarian": "expert",
    "ranger": "expert",
    "bard": "expert",
    "alchemist": "trained",
    "champion": "trained",
    "druid": "trained",
    "monk": "expert",
    "sorcerer": "trained",
}

CLASS_SAVE_RANKS: dict[str, dict[str, str]] = {
    "fighter": {"fortitude": "expert", "reflex": "expert", "will": "trained"},
    "rogue": {"fortitude": "trained", "reflex": "expert", "will": "trained"},
    "wizard": {"fortitude": "trained", "reflex": "trained", "will": "expert"},
    "cleric": {"fortitude": "trained", "reflex": "trained", "will": "expert"},
    "barbarian": {"fortitude": "expert", "reflex": "trained", "will": "expert"},
    "ranger": {"fortitude": "expert", "reflex": "expert", "will": "trained"},
    "bard": {"fortitude": "trained", "reflex": "trained", "will": "expert"},
    "alchemist": {"fortitude": "expert", "reflex": "expert", "will": "trained"},
    "champion": {"fortitude": "expert", "reflex": "trained", "will": "expert"},
    "druid": {"fortitude": "trained", "reflex": "trained", "will": "expert"},
    "monk": {"fortitude": "expert", "reflex": "expert", "will": "expert"},
    "sorcerer": {"fortitude": "trained", "reflex": "trained", "will": "expert"},
}

CLASS_WEAPON_PROFICIENCY: dict[str, dict[str, str]] = {
    # PF2: Fighter startuje z Expert w prostych/martial/unarmed.
    "fighter": {"simple": "expert", "martial": "expert", "unarmed": "expert"},
    "rogue": {"simple": "trained", "martial": "trained", "unarmed": "trained"},
    "wizard": {"simple": "trained", "unarmed": "trained"},
    "cleric": {"simple": "trained", "unarmed": "trained"},
    "barbarian": {"simple": "trained", "martial": "trained", "unarmed": "trained"},
    "ranger": {"simple": "trained", "martial": "trained", "unarmed": "trained"},
    "bard": {"simple": "trained", "unarmed": "trained"},
    "alchemist": {"simple": "trained", "martial": "trained", "unarmed": "trained"},
    "champion": {"simple": "trained", "martial": "trained", "unarmed": "trained"},
    "druid": {"simple": "trained", "unarmed": "trained"},
    "monk": {"simple": "trained", "unarmed": "trained"},
    "sorcerer": {"simple": "trained", "unarmed": "trained"},
}

CLASS_DEFENSE_PROFICIENCY: dict[str, dict[str, str]] = {
    "fighter": {"unarmored": "trained", "light": "trained", "medium": "trained", "heavy": "trained"},
    "rogue": {"unarmored": "trained", "light": "trained"},
    "wizard": {"unarmored": "trained"},
    "cleric": {"unarmored": "trained"},
    "barbarian": {"unarmored": "trained", "light": "trained", "medium": "trained"},
    "ranger": {"unarmored": "trained", "light": "trained", "medium": "trained"},
    "bard": {"unarmored": "trained", "light": "trained"},
    "alchemist": {"unarmored": "trained", "light": "trained", "medium": "trained"},
    "champion": {"unarmored": "trained", "light": "trained", "medium": "trained", "heavy": "trained"},
    "druid": {"unarmored": "trained", "light": "trained", "medium": "trained"},
    "monk": {"unarmored": "trained"},
    "sorcerer": {"unarmored": "trained"},
}

CLASS_SKILL_RULES: dict[str, dict[str, Any]] = {
    "fighter": {"fixed": [], "additional": 3},
    "rogue": {"fixed": ["stealth"], "additional": 7},
    "wizard": {"fixed": ["arcana"], "additional": 2},
    "cleric": {"fixed": ["religion"], "additional": 2},
    "barbarian": {"fixed": ["athletics"], "additional": 3},
    "ranger": {"fixed": ["nature", "survival"], "additional": 4},
    "bard": {"fixed": ["performance"], "additional": 4},
    "alchemist": {"fixed": ["crafting"], "additional": 3},
    "champion": {"fixed": ["religion"], "additional": 2},
    "druid": {"fixed": ["nature"], "additional": 2},
    "monk": {"fixed": ["acrobatics", "athletics"], "additional": 2},
    "sorcerer": {"fixed": [], "additional": 2},
}


@dataclass(frozen=True)
class BackgroundTraining:
    skill_choices: list[str]
    lore_template: str
    requires_lore_input: bool = False


_BG_TRAINING: dict[str, BackgroundTraining] = {
    "acolyte": BackgroundTraining(["religion"], "Scribing Lore"),
    "acrobat": BackgroundTraining(["acrobatics"], "Circus Lore"),
    "animal_whisperer": BackgroundTraining(["nature"], "{terrain} Lore", True),
    "artisan": BackgroundTraining(["crafting"], "Guild Lore"),
    "artist": BackgroundTraining(["crafting"], "Art Lore"),
    "barkeep": BackgroundTraining(["diplomacy"], "Alcohol Lore"),
    "barrister": BackgroundTraining(["diplomacy"], "Legal Lore"),
    "bounty_hunter": BackgroundTraining(["survival"], "Legal Lore"),
    "charlatan": BackgroundTraining(["deception"], "Underworld Lore"),
    "criminal": BackgroundTraining(["stealth"], "Underworld Lore"),
    "detective": BackgroundTraining(["society"], "Underworld Lore"),
    "emissary": BackgroundTraining(["society"], "{city} Lore", True),
    "entertainer": BackgroundTraining(["performance"], "Theater Lore"),
    "farmhand": BackgroundTraining(["athletics"], "Farming Lore"),
    "field_medic": BackgroundTraining(["medicine"], "Warfare Lore"),
    "fortune_teller": BackgroundTraining(["occultism"], "Fortune-Telling Lore"),
    "gambler": BackgroundTraining(["deception"], "Games Lore"),
    "gladiator": BackgroundTraining(["performance"], "Gladiatorial Lore"),
    "guard": BackgroundTraining(["intimidation"], "{legal_or_warfare}", True),
    "herbalist": BackgroundTraining(["nature"], "Herbalism Lore"),
    "hermit": BackgroundTraining(["nature", "occultism"], "{terrain} Lore", True),
    "hunter": BackgroundTraining(["survival"], "Tanning Lore"),
    "laborer": BackgroundTraining(["athletics"], "Labor Lore"),
    "martial_disciple": BackgroundTraining(["acrobatics", "athletics"], "Warfare Lore"),
    "merchant": BackgroundTraining(["diplomacy"], "Mercantile Lore"),
    "miner": BackgroundTraining(["survival"], "Mining Lore"),
    "noble": BackgroundTraining(["society"], "{genealogy_or_heraldry}", True),
    "nomad": BackgroundTraining(["survival"], "{terrain} Lore", True),
    "prisoner": BackgroundTraining(["stealth"], "Underworld Lore"),
    "sailor": BackgroundTraining(["athletics"], "Sailing Lore"),
    "scholar": BackgroundTraining(["arcana", "nature", "occultism", "religion"], "Academia Lore"),
    "scout": BackgroundTraining(["survival"], "{terrain} Lore", True),
    "street_urchin": BackgroundTraining(["thievery"], "{city} Lore", True),
    "tinker": BackgroundTraining(["crafting"], "Engineering Lore"),
    "warrior": BackgroundTraining(["intimidation"], "Warfare Lore"),
}


_STATUS_REGISTRY: dict[str, Status] | None = None


def _collect_statuses_from_package(package_name: str) -> dict[str, Status]:
    out: dict[str, Status] = {}
    try:
        pkg = importlib.import_module(package_name)
    except Exception:
        return out
    package_path = getattr(pkg, "__path__", None)
    if package_path is None:
        return out
    for module_info in pkgutil.walk_packages(package_path, prefix=f"{package_name}."):
        module_name = module_info.name
        if ".__pycache__." in module_name:
            continue
        try:
            module = importlib.import_module(module_name)
        except Exception:
            continue
        for value in vars(module).values():
            if isinstance(value, Status):
                sid = str(getattr(value, "id", "") or "").strip().lower()
                if sid and sid not in out:
                    out[sid] = value
    return out


def get_status_registry() -> dict[str, Status]:
    global _STATUS_REGISTRY
    if _STATUS_REGISTRY is not None:
        return _STATUS_REGISTRY
    registry: dict[str, Status] = {}
    for package_name in (
        "statuses.race",
        "statuses.classes",
        "statuses.backgrounds",
        "statuses.general",
    ):
        registry.update(_collect_statuses_from_package(package_name))
    for key, status in BACKGROUND_STATUS_BY_KEY.items():
        registry[str(status.id).strip().lower()] = status
        registry[f"background_{key}"] = status
    _STATUS_REGISTRY = registry
    return _STATUS_REGISTRY


def resolve_status(status_id: str) -> Status | None:
    sid = str(status_id or "").strip().lower()
    if not sid:
        return None
    return get_status_registry().get(sid)


def background_id_to_key(background_status_id: str) -> str:
    raw = str(background_status_id or "").strip().lower()
    if raw.startswith("background_"):
        return raw.replace("background_", "", 1)
    return raw


def background_boost_options(background_status_id: str) -> tuple[list[str], int]:
    key = background_id_to_key(background_status_id)
    definition = next((item for item in BACKGROUND_DEFINITIONS if item.key == key), None)
    if definition is None:
        return [], 0
    text = str(definition.ability_boosts_ui or "")
    matches = re.findall(
        r"(strength|dexterity|constitution|intelligence|wisdom|charisma)",
        text.lower(),
    )
    restricted = list(dict.fromkeys(matches[:2]))
    free_count = 1 if "free boost" in text.lower() else 0
    return restricted, free_count


def background_training(background_status_id: str) -> BackgroundTraining | None:
    key = background_id_to_key(background_status_id)
    return _BG_TRAINING.get(key)


def list_background_status_ids() -> list[str]:
    return [f"background_{item.key}" for item in BACKGROUND_DEFINITIONS]


__all__ = [
    "ABILITY_IDS",
    "CORE_SKILL_IDS",
    "ANCESTRY_IDS",
    "HERITAGE_IDS_BY_ANCESTRY",
    "ANCESTRY_FEAT_IDS_BY_ANCESTRY",
    "CLASS_IDS",
    "CLASS_FEAT_CHOICES_MANUAL",
    "CLASS_KEY_ABILITY_DEFAULT",
    "CLASS_PERCEPTION_RANK",
    "CLASS_SAVE_RANKS",
    "CLASS_WEAPON_PROFICIENCY",
    "CLASS_DEFENSE_PROFICIENCY",
    "CLASS_SKILL_RULES",
    "BackgroundTraining",
    "get_status_registry",
    "resolve_status",
    "background_id_to_key",
    "background_boost_options",
    "background_training",
    "list_background_status_ids",
]
