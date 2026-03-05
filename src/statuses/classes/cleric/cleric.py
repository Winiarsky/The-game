from __future__ import annotations

from statuses.base import Status
from statuses.general.shield_block import SHIELD_BLOCK_STATUS

CLERIC_KEY_ABILITY_CHOICES = ["wisdom"]
CLERIC_DOCTRINE_CHOICES = ["cloistered_cleric", "warpriest"]
CLERIC_FAVORED_WEAPON_CHOICES = [
    "crossbow",
    "dagger",
    "falchion",
    "fist",
    "glaive",
    "greataxe",
    "greatsword",
    "longbow",
    "longsword",
    "mace",
    "rapier",
    "scimitar",
    "scythe",
    "shortsword",
    "spiked_chain",
    "staff",
    "starknife",
    "trident",
    "warhammer",
    "whip",
]
CLERIC_FONT_CHOICES = ["heal", "harm"]
CLERIC_WEAPON_GROUPS = {
    "crossbow": "simple",
    "dagger": "simple",
    "falchion": "martial",
    "fist": "unarmed",
    "glaive": "martial",
    "greataxe": "martial",
    "greatsword": "martial",
    "longbow": "martial",
    "longsword": "martial",
    "mace": "simple",
    "rapier": "martial",
    "scimitar": "martial",
    "scythe": "martial",
    "shortsword": "martial",
    "spiked_chain": "martial",
    "staff": "simple",
    "starknife": "martial",
    "trident": "martial",
    "warhammer": "martial",
    "whip": "martial",
}

# Domeny i ich initial domain spells (Table 8-2).
CLERIC_DOMAIN_INITIAL_SPELLS = {
    "air": "pushing_gust",
    "ambition": "blind_ambition",
    "cities": "face_in_the_crowd",
    "confidence": "veil_of_confidence",
    "creation": "splash_of_art",
    "darkness": "cloak_of_shadow",
    "death": "deaths_call",
    "destruction": "cry_of_destruction",
    "dreams": "sweet_dream",
    "earth": "hurtling_stone",
    "family": "soothing_words",
    "fate": "read_fate",
    "fire": "fire_ray",
    "freedom": "unimpeded_stride",
    "healing": "healers_blessing",
    "indulgence": "overstuff",
    "knowledge": "scholarly_recollection",
    "luck": "bit_of_luck",
    "magic": "magics_vessel",
    "might": "athletic_rush",
    "moon": "moonbeam",
    "nature": "vibrant_thorns",
    "nightmares": "waking_nightmare",
    "pain": "savor_the_sting",
    "passion": "charming_touch",
    "perfection": "perfected_mind",
    "protection": "protectors_sacrifice",
    "secrecy": "forced_quiet",
    "sun": "dazzling_flash",
    "travel": "agile_feet",
    "trickery": "sudden_shift",
    "truth": "word_of_truth",
    "tyranny": "touch_of_obedience",
    "undeath": "touch_of_undeath",
    "water": "tidal_surge",
    "wealth": "appearance_of_wealth",
    "zeal": "weapon_surge",
    "custom_domain_a": "custom_domain_spell_a",
    "custom_domain_b": "custom_domain_spell_b",
    "custom_domain_c": "custom_domain_spell_c",
}

CLERIC_DEITY_OPTIONS = {
    "abadar": {
        "favored_weapon": "crossbow",
        "favored_weapon_group": "simple",
        "font_options": ["heal", "harm"],
        "domain_choices": ["cities", "earth", "travel", "wealth"],
    },
    "asmodeus": {
        "favored_weapon": "mace",
        "favored_weapon_group": "simple",
        "font_options": ["harm"],
        "domain_choices": ["confidence", "fire", "trickery", "tyranny"],
    },
    "calistria": {
        "favored_weapon": "whip",
        "favored_weapon_group": "martial",
        "font_options": ["heal", "harm"],
        "domain_choices": ["pain", "passion", "secrecy", "trickery"],
    },
    "cayden_cailean": {
        "favored_weapon": "rapier",
        "favored_weapon_group": "martial",
        "font_options": ["heal"],
        "domain_choices": ["cities", "freedom", "indulgence", "might"],
    },
    "desna": {
        "favored_weapon": "starknife",
        "favored_weapon_group": "martial",
        "font_options": ["heal"],
        "domain_choices": ["dreams", "luck", "moon", "travel"],
    },
    "erastil": {
        "favored_weapon": "longbow",
        "favored_weapon_group": "martial",
        "font_options": ["heal"],
        "domain_choices": ["earth", "family", "nature", "wealth"],
    },
    "gorum": {
        "favored_weapon": "greatsword",
        "favored_weapon_group": "martial",
        "font_options": ["heal", "harm"],
        "domain_choices": ["confidence", "destruction", "might", "zeal"],
    },
    "gozreh": {
        "favored_weapon": "trident",
        "favored_weapon_group": "martial",
        "font_options": ["heal"],
        "domain_choices": ["air", "nature", "travel", "water"],
    },
    "iomedae": {
        "favored_weapon": "longsword",
        "favored_weapon_group": "martial",
        "font_options": ["heal"],
        "domain_choices": ["confidence", "might", "truth", "zeal"],
    },
    "irori": {
        "favored_weapon": "fist",
        "favored_weapon_group": "unarmed",
        "font_options": ["heal", "harm"],
        "domain_choices": ["knowledge", "might", "perfection", "truth"],
    },
    "lamashtu": {
        "favored_weapon": "falchion",
        "favored_weapon_group": "martial",
        "font_options": ["heal", "harm"],
        "domain_choices": ["family", "might", "nightmares", "trickery"],
    },
    "nethys": {
        "favored_weapon": "staff",
        "favored_weapon_group": "simple",
        "font_options": ["heal", "harm"],
        "domain_choices": ["destruction", "knowledge", "magic", "protection"],
    },
    "norgorber": {
        "favored_weapon": "shortsword",
        "favored_weapon_group": "martial",
        "font_options": ["harm"],
        "domain_choices": ["death", "secrecy", "trickery", "wealth"],
    },
    "pharasma": {
        "favored_weapon": "dagger",
        "favored_weapon_group": "simple",
        "font_options": ["heal"],
        "domain_choices": ["death", "fate", "healing", "knowledge"],
    },
    "rovagug": {
        "favored_weapon": "greataxe",
        "favored_weapon_group": "martial",
        "font_options": ["harm"],
        "domain_choices": ["air", "destruction", "earth", "zeal"],
    },
    "sarenrae": {
        "favored_weapon": "scimitar",
        "favored_weapon_group": "martial",
        "font_options": ["heal"],
        "domain_choices": ["fire", "healing", "sun", "truth"],
    },
    "shelyn": {
        "favored_weapon": "glaive",
        "favored_weapon_group": "martial",
        "font_options": ["heal"],
        "domain_choices": ["creation", "family", "passion", "protection"],
    },
    "torag": {
        "favored_weapon": "warhammer",
        "favored_weapon_group": "martial",
        "font_options": ["heal"],
        "domain_choices": ["creation", "earth", "family", "protection"],
    },
    "urgathoa": {
        "favored_weapon": "scythe",
        "favored_weapon_group": "martial",
        "font_options": ["harm"],
        "domain_choices": ["indulgence", "magic", "might", "undeath"],
    },
    "zon_kuthon": {
        "favored_weapon": "spiked_chain",
        "favored_weapon_group": "martial",
        "font_options": ["harm"],
        "domain_choices": ["ambition", "darkness", "destruction", "pain"],
    },
    "custom": {
        "favored_weapon": None,
        "favored_weapon_group": None,
        "font_options": ["heal", "harm"],
        "domain_choices": ["custom_domain_a", "custom_domain_b", "custom_domain_c"],
    },
}

CLERIC_PROMPT = (
    "KEY ABILITY: WISDOM\n"
    "At 1st level, your class gives you an ability boost to Wisdom.\n"
    "HIT POINTS: 8 plus your Constitution Modifier\n\n"
    "INITIAL PROFICIENCIES:\n"
    "PERCEPTION\n"
    "Trained in Perception\n"
    "SAVING THROWS\n"
    "Trained in Fortitude\n"
    "Trained in Reflex\n"
    "Expert in Will\n"
    "SKILLS\n"
    "Trained in Religion\n"
    "Trained in a number of additional skills equal to 2 plus your Intelligence modifier\n"
    "ATTACKS\n"
    "Trained in simple weapons\n"
    "Trained in unarmed attacks\n"
    "DEFENSES\n"
    "Trained in unarmored defense\n\n"
    "DIVINE FONT:\n"
    "Podczas setupu wybierasz heal/harm zgodnie z deity (lub custom).\n"
    "Przygotowywanie listy czarow i slotow zostaje po stronie gracza.\n\n"
    "DOCTRINE:\n"
    "Cloistered Cleric: automatycznie dostajesz Domain Initiate.\n"
    "Warpriest: Shield Block, a dla favored weapon simple/unarmed takze Deadly Simplicity."
)


def ClericStatus() -> Status:
    """Class: Cleric (setup deity/doctrine/font + domeny + initial domain spells)."""
    return Status(
        id="cleric",
        label="Cleric",
        data={
            "ui_prompt": CLERIC_PROMPT,
            "class_hp": 8,
            "ui_choice_kind": "cleric_setup",
            "cleric_key_ability_choices": list(CLERIC_KEY_ABILITY_CHOICES),
            "cleric_doctrine_choices": list(CLERIC_DOCTRINE_CHOICES),
            "cleric_favored_weapon_choices": list(CLERIC_FAVORED_WEAPON_CHOICES),
            "cleric_font_choices": list(CLERIC_FONT_CHOICES),
            "cleric_weapon_groups": dict(CLERIC_WEAPON_GROUPS),
            "cleric_deity_choices": list(CLERIC_DEITY_OPTIONS.keys()),
            "cleric_deity_options": dict(CLERIC_DEITY_OPTIONS),
            "cleric_domain_spell_placeholders": dict(CLERIC_DOMAIN_INITIAL_SPELLS),
            "set_actor_attrs": {"class_name": "cleric"},
            "grants_statuses": [SHIELD_BLOCK_STATUS],
        },
    )


CLERIC_STATUS = ClericStatus()

__all__ = [
    "CLERIC_KEY_ABILITY_CHOICES",
    "CLERIC_DOCTRINE_CHOICES",
    "CLERIC_FAVORED_WEAPON_CHOICES",
    "CLERIC_FONT_CHOICES",
    "CLERIC_WEAPON_GROUPS",
    "CLERIC_DOMAIN_INITIAL_SPELLS",
    "CLERIC_DEITY_OPTIONS",
    "CLERIC_PROMPT",
    "ClericStatus",
    "CLERIC_STATUS",
]
