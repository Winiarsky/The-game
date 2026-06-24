from __future__ import annotations

from statuses.base import Status

SORCERER_KEY_ABILITY_CHOICES = ["charisma"]
SORCERER_BLOODLINE_CHOICES = [
    "aberrant",
    "angelic",
    "demonic",
    "diabolic",
    "draconic",
    "elemental",
    "fey",
    "hag",
    "imperial",
    "undead",
]
SORCERER_FEAT_CHOICES = [
    "counterspell",
    "dangerous_sorcery",
    "familiar",
    "reach_spell",
    "widen_spell",
]

SORCERER_KNOWN_CANTRIPS_AT_LEVEL1 = 5
SORCERER_KNOWN_RANK1_AT_LEVEL1 = 2
SORCERER_RANK1_SLOTS_PER_DAY_AT_LEVEL1 = 3

# Table 3-17: Sorcerer spells per day.
SORCERER_SPELLS_PER_DAY = {
    1: {"cantrip": 5, "rank_1": 3},
    2: {"cantrip": 5, "rank_1": 4},
    3: {"cantrip": 5, "rank_1": 4, "rank_2": 3},
    4: {"cantrip": 5, "rank_1": 4, "rank_2": 4},
    5: {"cantrip": 5, "rank_1": 4, "rank_2": 4, "rank_3": 3},
    6: {"cantrip": 5, "rank_1": 4, "rank_2": 4, "rank_3": 4},
    7: {"cantrip": 5, "rank_1": 4, "rank_2": 4, "rank_3": 4, "rank_4": 3},
    8: {"cantrip": 5, "rank_1": 4, "rank_2": 4, "rank_3": 4, "rank_4": 4},
    9: {"cantrip": 5, "rank_1": 4, "rank_2": 4, "rank_3": 4, "rank_4": 4, "rank_5": 3},
    10: {"cantrip": 5, "rank_1": 4, "rank_2": 4, "rank_3": 4, "rank_4": 4, "rank_5": 4},
    11: {"cantrip": 5, "rank_1": 4, "rank_2": 4, "rank_3": 4, "rank_4": 4, "rank_5": 4, "rank_6": 3},
    12: {"cantrip": 5, "rank_1": 4, "rank_2": 4, "rank_3": 4, "rank_4": 4, "rank_5": 4, "rank_6": 4},
    13: {"cantrip": 5, "rank_1": 4, "rank_2": 4, "rank_3": 4, "rank_4": 4, "rank_5": 4, "rank_6": 4, "rank_7": 3},
    14: {"cantrip": 5, "rank_1": 4, "rank_2": 4, "rank_3": 4, "rank_4": 4, "rank_5": 4, "rank_6": 4, "rank_7": 4},
    15: {"cantrip": 5, "rank_1": 4, "rank_2": 4, "rank_3": 4, "rank_4": 4, "rank_5": 4, "rank_6": 4, "rank_7": 4, "rank_8": 3},
    16: {"cantrip": 5, "rank_1": 4, "rank_2": 4, "rank_3": 4, "rank_4": 4, "rank_5": 4, "rank_6": 4, "rank_7": 4, "rank_8": 4},
    17: {"cantrip": 5, "rank_1": 4, "rank_2": 4, "rank_3": 4, "rank_4": 4, "rank_5": 4, "rank_6": 4, "rank_7": 4, "rank_8": 4, "rank_9": 3},
    18: {"cantrip": 5, "rank_1": 4, "rank_2": 4, "rank_3": 4, "rank_4": 4, "rank_5": 4, "rank_6": 4, "rank_7": 4, "rank_8": 4, "rank_9": 4},
    19: {"cantrip": 5, "rank_1": 4, "rank_2": 4, "rank_3": 4, "rank_4": 4, "rank_5": 4, "rank_6": 4, "rank_7": 4, "rank_8": 4, "rank_9": 4, "rank_10": 1},
    20: {"cantrip": 5, "rank_1": 4, "rank_2": 4, "rank_3": 4, "rank_4": 4, "rank_5": 4, "rank_6": 4, "rank_7": 4, "rank_8": 4, "rank_9": 4, "rank_10": 1},
}

SORCERER_BLOODLINE_TRADITIONS = {
    "aberrant": "occult",
    "angelic": "divine",
    "demonic": "divine",
    "diabolic": "divine",
    "draconic": "arcane",
    "elemental": "primal",
    "fey": "primal",
    "hag": "occult",
    "imperial": "arcane",
    "undead": "divine",
}

SORCERER_BLOODLINE_SKILLS = {
    "aberrant": ["intimidation", "occultism"],
    "angelic": ["diplomacy", "religion"],
    "demonic": ["intimidation", "religion"],
    "diabolic": ["deception", "religion"],
    "draconic": ["arcana", "intimidation"],
    "elemental": ["intimidation", "nature"],
    "fey": ["deception", "nature"],
    "hag": ["deception", "occultism"],
    "imperial": ["arcana", "society"],
    "undead": ["intimidation", "religion"],
}

SORCERER_BLOODLINE_GRANTED_SPELLS = {
    "aberrant": {
        "cantrip": "daze",
        "rank_1": "spider_sting",
        "rank_2": "touch_of_idiocy",
        "rank_3": "vampiric_touch",
        "rank_4": "confusion",
        "rank_5": "black_tentacles",
        "rank_6": "feeblemind",
        "rank_7": "warp_mind",
        "rank_8": "uncontrollable_dance",
        "rank_9": "unfathomable_song",
    },
    "angelic": {
        "cantrip": "light",
        "rank_1": "heal",
        "rank_2": "spiritual_weapon",
        "rank_3": "searing_light",
        "rank_4": "divine_wrath",
        "rank_5": "flame_strike",
        "rank_6": "blade_barrier",
        "rank_7": "divine_decree",
        "rank_8": "divine_aura",
        "rank_9": "foresight",
    },
    "demonic": {
        "cantrip": "acid_splash",
        "rank_1": "fear",
        "rank_2": "enlarge",
        "rank_3": "slow",
        "rank_4": "divine_wrath",
        "rank_5": "abyssal_plague",
        "rank_6": "disintegrate",
        "rank_7": "divine_decree",
        "rank_8": "divine_aura",
        "rank_9": "implosion",
    },
    "diabolic": {
        "cantrip": "produce_flame",
        "rank_1": "charm",
        "rank_2": "flaming_sphere",
        "rank_3": "enthrall",
        "rank_4": "suggestion",
        "rank_5": "crushing_despair",
        "rank_6": "true_seeing",
        "rank_7": "divine_decree",
        "rank_8": "divine_aura",
        "rank_9": "meteor_swarm",
    },
    "draconic": {
        "cantrip": "shield",
        "rank_1": "true_strike",
        "rank_2": "resist_energy",
        "rank_3": "haste",
        "rank_4": "spell_immunity",
        "rank_5": "chromatic_wall",
        "rank_6": "dragon_form",
        "rank_7": "mask_of_terror",
        "rank_8": "prismatic_wall",
        "rank_9": "overwhelming_presence",
    },
    "elemental": {
        "cantrip": "produce_flame",
        "rank_1": "burning_hands",
        "rank_2": "resist_energy",
        "rank_3": "fireball",
        "rank_4": "freedom_of_movement",
        "rank_5": "elemental_form",
        "rank_6": "repulsion",
        "rank_7": "energy_aegis",
        "rank_8": "prismatic_wall",
        "rank_9": "storm_of_vengeance",
    },
    "fey": {
        "cantrip": "ghost_sound",
        "rank_1": "charm",
        "rank_2": "hideous_laughter",
        "rank_3": "enthrall",
        "rank_4": "suggestion",
        "rank_5": "cloak_of_colors",
        "rank_6": "mislead",
        "rank_7": "visions_of_danger",
        "rank_8": "uncontrollable_dance",
        "rank_9": "resplendent_mansion",
    },
    "hag": {
        "cantrip": "daze",
        "rank_1": "illusory_disguise",
        "rank_2": "touch_of_idiocy",
        "rank_3": "blindness",
        "rank_4": "outcasts_curse",
        "rank_5": "mariners_curse",
        "rank_6": "baleful_polymorph",
        "rank_7": "warp_mind",
        "rank_8": "spiritual_epidemic",
        "rank_9": "natures_enmity",
    },
    "imperial": {
        "cantrip": "detect_magic",
        "rank_1": "magic_missile",
        "rank_2": "dispel_magic",
        "rank_3": "haste",
        "rank_4": "dimension_door",
        "rank_5": "prying_eye",
        "rank_6": "disintegrate",
        "rank_7": "prismatic_spray",
        "rank_8": "maze",
        "rank_9": "prismatic_sphere",
    },
    "undead": {
        "cantrip": "chill_touch",
        "rank_1": "harm",
        "rank_2": "false_life",
        "rank_3": "bind_undead",
        "rank_4": "talking_corpse",
        "rank_5": "cloudkill",
        "rank_6": "vampiric_exsanguination",
        "rank_7": "finger_of_death",
        "rank_8": "horrid_wilting",
        "rank_9": "wail_of_the_banshee",
    },
}

SORCERER_BLOODLINE_INITIAL_FOCUS_SPELLS = {
    "aberrant": "tentacular_limbs",
    "angelic": "angelic_halo",
    "demonic": "gluttons_jaws",
    "diabolic": "diabolic_edict",
    "draconic": "dragon_claws",
    "elemental": "elemental_toss",
    "fey": "faerie_dust",
    "hag": "jealous_hex",
    "imperial": "ancestral_memories",
    "undead": "undeaths_blessing",
}

SORCERER_BLOODLINE_BLOOD_MAGIC = {
    "aberrant": "Will saves +2 status (1 runda) dla ciebie lub 1 celu.",
    "angelic": "Saving throws +1 status (1 runda) dla ciebie lub 1 celu.",
    "demonic": "Cel: -1 status do AC (1 runda) albo ty: +1 status do Intimidation (1 runda).",
    "diabolic": "Cel: +1 fire damage/level albo ty: +1 status do Deception (1 runda).",
    "draconic": "AC +1 status (1 runda) dla ciebie lub 1 celu.",
    "elemental": "Ty: +1 status do Intimidation (1 runda) albo cel: 1 damage/level (typ zalezny od elementu).",
    "fey": "Concealed (1 runda) dla ciebie lub 1 celu (bez mozliwosci Hide).",
    "hag": "Pierwszy przeciwnik, ktory zada ci damage, otrzymuje 2 mental damage/level (basic Will).",
    "imperial": "Skill checks +1 status (1 runda) dla ciebie lub 1 celu.",
    "undead": "Ty: temp HP = spell level (1 runda) albo cel: 1 negative damage/level.",
}

SORCERER_DRACONIC_TYPE_DAMAGE = {
    "black": "acid",
    "blue": "electricity",
    "brass": "fire",
    "bronze": "electricity",
    "copper": "acid",
    "gold": "fire",
    "green": "poison",
    "red": "fire",
    "silver": "cold",
    "white": "cold",
}

SORCERER_ELEMENTAL_TYPE_CHOICES = ["air", "earth", "fire", "water"]
SORCERER_ELEMENTAL_TYPE_DAMAGE = {
    "air": "bludgeoning",
    "earth": "bludgeoning",
    "fire": "fire",
    "water": "bludgeoning",
}

SORCERER_PROMPT = (
    "KEY ABILITY: CHARISMA\n"
    "At 1st level, your class gives you an ability boost to Charisma.\n"
    "HIT POINTS: 6 plus your Constitution Modifier\n\n"
    "INITIAL PROFICIENCIES (summary):\n"
    "Perception: Trained\n"
    "Saving Throws: Trained Fortitude, Trained Reflex, Expert Will\n"
    "Attacks: Trained simple weapons + unarmed\n"
    "Defenses: Trained unarmored defense\n\n"
    "CLASS FEATURES:\n"
    "Bloodline: wybierasz source mocy, tradycje czarow, bloodline skills oraz granted spells.\n"
    "Spellcasting: spontaniczne czary z spell repertoire.\n"
    "Na 1. poziomie wybierasz 5 cantripow i 2 czary 1. rangi z tradycji bloodline.\n"
    "Bloodline cantrip/rank1 sa dopisywane jako dodatkowe znane czary.\n"
    "Sloty na dzien: zgodnie z tabela Sorcerer Spells per Day (CRB Table 3-17).\n"
    "Focus Pool: 1 Focus Point.\n"
    "Podczas setupu wybierasz bloodline i 1 class feat poziomu 1."
)


def SorcererStatus() -> Status:
    return Status(
        id="sorcerer",
        label="Sorcerer",
        data={
            "ui_prompt": SORCERER_PROMPT,
            "class_hp": 6,
            "ui_choice_kind": "sorcerer_setup",
            "sorcerer_key_ability_choices": list(SORCERER_KEY_ABILITY_CHOICES),
            "sorcerer_bloodline_choices": list(SORCERER_BLOODLINE_CHOICES),
            "sorcerer_feat_choices": list(SORCERER_FEAT_CHOICES),
            "sorcerer_bloodline_traditions": dict(SORCERER_BLOODLINE_TRADITIONS),
            "sorcerer_bloodline_skills": {
                key: list(values) for key, values in SORCERER_BLOODLINE_SKILLS.items()
            },
            "sorcerer_bloodline_granted_spells": {
                key: dict(values) for key, values in SORCERER_BLOODLINE_GRANTED_SPELLS.items()
            },
            "sorcerer_bloodline_initial_focus_spells": dict(SORCERER_BLOODLINE_INITIAL_FOCUS_SPELLS),
            "sorcerer_bloodline_blood_magic": dict(SORCERER_BLOODLINE_BLOOD_MAGIC),
            "sorcerer_known_cantrips_at_level1": int(SORCERER_KNOWN_CANTRIPS_AT_LEVEL1),
            "sorcerer_known_rank_1_spells_at_level1": int(SORCERER_KNOWN_RANK1_AT_LEVEL1),
            "sorcerer_rank_1_slots_per_day": int(SORCERER_RANK1_SLOTS_PER_DAY_AT_LEVEL1),
            "sorcerer_spells_per_day": {level: dict(slots) for level, slots in SORCERER_SPELLS_PER_DAY.items()},
            "sorcerer_draconic_type_choices": list(SORCERER_DRACONIC_TYPE_DAMAGE.keys()),
            "sorcerer_draconic_type_damage": dict(SORCERER_DRACONIC_TYPE_DAMAGE),
            "sorcerer_elemental_type_choices": list(SORCERER_ELEMENTAL_TYPE_CHOICES),
            "sorcerer_elemental_type_damage": dict(SORCERER_ELEMENTAL_TYPE_DAMAGE),
            "set_actor_attrs": {"class_name": "sorcerer", "focus_point": 1},
        },
    )


SORCERER_STATUS = SorcererStatus()

__all__ = [
    "SORCERER_KEY_ABILITY_CHOICES",
    "SORCERER_BLOODLINE_CHOICES",
    "SORCERER_FEAT_CHOICES",
    "SORCERER_KNOWN_CANTRIPS_AT_LEVEL1",
    "SORCERER_KNOWN_RANK1_AT_LEVEL1",
    "SORCERER_RANK1_SLOTS_PER_DAY_AT_LEVEL1",
    "SORCERER_SPELLS_PER_DAY",
    "SORCERER_BLOODLINE_TRADITIONS",
    "SORCERER_BLOODLINE_SKILLS",
    "SORCERER_BLOODLINE_GRANTED_SPELLS",
    "SORCERER_BLOODLINE_INITIAL_FOCUS_SPELLS",
    "SORCERER_BLOODLINE_BLOOD_MAGIC",
    "SORCERER_DRACONIC_TYPE_DAMAGE",
    "SORCERER_ELEMENTAL_TYPE_CHOICES",
    "SORCERER_ELEMENTAL_TYPE_DAMAGE",
    "SORCERER_PROMPT",
    "SorcererStatus",
    "SORCERER_STATUS",
]
