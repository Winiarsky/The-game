from __future__ import annotations

from dataclasses import dataclass

from damage_types import DamageType

from .base_weapon import BaseWeapon


@dataclass
class SwordWeapon(BaseWeapon):
    # Kompatybilność wsteczna: "sword" pozostaje domyślnym longswordem.
    item_id: str = "sword"
    name: str = "Sword"
    event_name: str = "sword"
    damage_prompt: str = "1k8 + STR"
    damage_type: str = DamageType.SLASHING.value
    proficiency_category: str = "martial"
    weapon_group: str = "sword"
    hands_required: int = 1
    price_cp: int = 100
    bulk: str | int = 1
    traits: tuple[str, ...] = ("versatile:p",)


@dataclass
class LongswordWeapon(BaseWeapon):
    item_id: str = "longsword"
    name: str = "Longsword"
    event_name: str = "longsword"
    damage_prompt: str = "1k8 + STR"
    damage_type: str = DamageType.SLASHING.value
    proficiency_category: str = "martial"
    weapon_group: str = "sword"
    hands_required: int = 1
    price_cp: int = 100
    bulk: str | int = 1
    traits: tuple[str, ...] = ("versatile:p",)


@dataclass
class DaggerWeapon(BaseWeapon):
    item_id: str = "dagger"
    name: str = "Dagger"
    event_name: str = "dagger"
    damage_prompt: str = "1k4 + STR"
    damage_type: str = DamageType.PIERCING.value
    proficiency_category: str = "simple"
    weapon_group: str = "knife"
    hands_required: int = 1
    price_cp: int = 20
    bulk: str | int = "L"
    traits: tuple[str, ...] = ("agile", "finesse", "thrown:10", "versatile:s")


@dataclass
class ClubWeapon(BaseWeapon):
    item_id: str = "club"
    name: str = "Club"
    event_name: str = "club"
    damage_prompt: str = "1k6 + STR"
    damage_type: str = DamageType.BLUDGEONING.value
    proficiency_category: str = "simple"
    weapon_group: str = "club"
    hands_required: int = 1
    price_cp: int = 0
    bulk: str | int = 1
    traits: tuple[str, ...] = ("thrown:10",)


@dataclass
class SpearWeapon(BaseWeapon):
    item_id: str = "spear"
    name: str = "Spear"
    event_name: str = "spear"
    damage_prompt: str = "1k6 + STR"
    damage_type: str = DamageType.PIERCING.value
    proficiency_category: str = "simple"
    weapon_group: str = "spear"
    hands_required: int = 1
    price_cp: int = 10
    bulk: str | int = 1
    traits: tuple[str, ...] = ("thrown:20",)


@dataclass
class ShortswordWeapon(BaseWeapon):
    item_id: str = "shortsword"
    name: str = "Shortsword"
    event_name: str = "shortsword"
    damage_prompt: str = "1k6 + STR"
    damage_type: str = DamageType.PIERCING.value
    proficiency_category: str = "martial"
    weapon_group: str = "sword"
    hands_required: int = 1
    price_cp: int = 90
    bulk: str | int = "L"
    traits: tuple[str, ...] = ("agile", "finesse", "versatile:s")


@dataclass
class RapierWeapon(BaseWeapon):
    item_id: str = "rapier"
    name: str = "Rapier"
    event_name: str = "rapier"
    damage_prompt: str = "1k6 + STR"
    damage_type: str = DamageType.PIERCING.value
    proficiency_category: str = "martial"
    weapon_group: str = "sword"
    hands_required: int = 1
    price_cp: int = 200
    bulk: str | int = 1
    traits: tuple[str, ...] = ("deadly:d8", "disarm", "finesse")


@dataclass
class GreataxeWeapon(BaseWeapon):
    item_id: str = "greataxe"
    name: str = "Greataxe"
    event_name: str = "greataxe"
    damage_prompt: str = "1k12 + STR"
    damage_type: str = DamageType.SLASHING.value
    proficiency_category: str = "martial"
    weapon_group: str = "axe"
    hands_required: int = 2
    price_cp: int = 200
    bulk: str | int = 2
    traits: tuple[str, ...] = ("sweep",)


@dataclass
class WarhammerWeapon(BaseWeapon):
    item_id: str = "warhammer"
    name: str = "Warhammer"
    event_name: str = "warhammer"
    damage_prompt: str = "1k8 + STR"
    damage_type: str = DamageType.BLUDGEONING.value
    proficiency_category: str = "martial"
    weapon_group: str = "hammer"
    hands_required: int = 1
    price_cp: int = 100
    bulk: str | int = 1
    traits: tuple[str, ...] = ("shove",)


@dataclass
class HalberdWeapon(BaseWeapon):
    item_id: str = "halberd"
    name: str = "Halberd"
    event_name: str = "halberd"
    damage_prompt: str = "1k10 + STR"
    damage_type: str = DamageType.SLASHING.value
    proficiency_category: str = "martial"
    weapon_group: str = "polearm"
    hands_required: int = 2
    price_cp: int = 200
    bulk: str | int = 2
    traits: tuple[str, ...] = ("reach:10", "trip", "versatile:p")


@dataclass
class GlaiveWeapon(BaseWeapon):
    item_id: str = "glaive"
    name: str = "Glaive"
    event_name: str = "glaive"
    damage_prompt: str = "1k8 + STR"
    damage_type: str = DamageType.SLASHING.value
    proficiency_category: str = "martial"
    weapon_group: str = "polearm"
    hands_required: int = 2
    price_cp: int = 100
    bulk: str | int = 2
    traits: tuple[str, ...] = ("deadly:d8", "forceful", "reach:10")


@dataclass
class MaceWeapon(BaseWeapon):
    item_id: str = "mace"
    name: str = "Mace"
    event_name: str = "mace"
    damage_prompt: str = "1k6 + STR"
    damage_type: str = DamageType.BLUDGEONING.value
    proficiency_category: str = "simple"
    weapon_group: str = "club"
    hands_required: int = 1
    price_cp: int = 10
    bulk: str | int = 1
    traits: tuple[str, ...] = ("shove",)


@dataclass
class JavelinWeapon(BaseWeapon):
    item_id: str = "javelin"
    name: str = "Javelin"
    event_name: str = "javelin"
    damage_prompt: str = "1k6 + STR"
    damage_type: str = DamageType.PIERCING.value
    proficiency_category: str = "simple"
    weapon_group: str = "spear"
    hands_required: int = 1
    ranged: bool = True
    range_increment_ft: int = 30
    price_cp: int = 10
    bulk: str | int = "L"
    traits: tuple[str, ...] = ("thrown:30",)


@dataclass
class ShortbowWeapon(BaseWeapon):
    item_id: str = "shortbow"
    name: str = "Shortbow"
    event_name: str = "shortbow"
    damage_prompt: str = "1k6 + DEX"
    damage_type: str = DamageType.PIERCING.value
    proficiency_category: str = "martial"
    weapon_group: str = "bow"
    hands_required: int = 2
    ranged: bool = True
    range_increment_ft: int = 60
    price_cp: int = 300
    bulk: str | int = 1
    traits: tuple[str, ...] = ("deadly:d10",)


@dataclass
class LongbowWeapon(BaseWeapon):
    item_id: str = "longbow"
    name: str = "Longbow"
    event_name: str = "longbow"
    damage_prompt: str = "1k8 + DEX"
    damage_type: str = DamageType.PIERCING.value
    proficiency_category: str = "martial"
    weapon_group: str = "bow"
    hands_required: int = 2
    ranged: bool = True
    range_increment_ft: int = 100
    price_cp: int = 600
    bulk: str | int = 1
    traits: tuple[str, ...] = ("deadly:d10", "volley:30")


@dataclass
class CrossbowWeapon(BaseWeapon):
    # Kompatybilność wsteczna: "crossbow" = lekka kusza.
    item_id: str = "crossbow"
    name: str = "Crossbow"
    event_name: str = "crossbow"
    damage_prompt: str = "1k8"
    damage_type: str = DamageType.PIERCING.value
    proficiency_category: str = "simple"
    weapon_group: str = "crossbow"
    hands_required: int = 2
    ranged: bool = True
    range_increment_ft: int = 120
    reload: int = 1
    price_cp: int = 300
    bulk: str | int = 1
    traits: tuple[str, ...] = ("crossbow", "simple_crossbow", "reload:1")


@dataclass
class LightCrossbowWeapon(BaseWeapon):
    item_id: str = "light_crossbow"
    name: str = "Light Crossbow"
    event_name: str = "light_crossbow"
    damage_prompt: str = "1k8"
    damage_type: str = DamageType.PIERCING.value
    proficiency_category: str = "simple"
    weapon_group: str = "crossbow"
    hands_required: int = 2
    ranged: bool = True
    range_increment_ft: int = 120
    reload: int = 1
    price_cp: int = 300
    bulk: str | int = 1
    traits: tuple[str, ...] = ("crossbow", "simple_crossbow", "reload:1")


@dataclass
class UnarmedWeapon(BaseWeapon):
    item_id: str = "unarmed"
    name: str = "Unarmed"
    event_name: str = "unarmed"
    damage_prompt: str = "1k4 + STR"
    damage_type: str = DamageType.BLUDGEONING.value
    proficiency_category: str = "unarmed"
    weapon_group: str = "brawling"
    hands_required: int = 0
    price_cp: int = 0
    bulk: str | int = "-"
    traits: tuple[str, ...] = ("agile", "finesse", "unarmed", "free_hand")


@dataclass
class RazortoothJawsWeapon(BaseWeapon):
    item_id: str = "razortooth_jaws"
    name: str = "Razortooth Jaws"
    event_name: str = "razortooth_jaws"
    damage_prompt: str = "1k6 + STR"
    damage_type: str = DamageType.PIERCING.value
    proficiency_category: str = "unarmed"
    weapon_group: str = "brawling"
    hands_required: int = 1
    price_cp: int = 0
    bulk: str | int = "-"
    traits: tuple[str, ...] = ("finesse", "unarmed", "jaws")


_EXTRA_WEAPON_DEFS: dict[str, dict[str, object]] = {
    "bastard_sword": {
        "name": "Bastard Sword",
        "damage_prompt": "1k8 + STR",
        "damage_type": DamageType.SLASHING.value,
        "proficiency_category": "martial",
        "weapon_group": "sword",
        "hands_required": 1,
        "price_cp": 400,
        "bulk": 1,
        "traits": ("two_hand:d12",),
    },
    "battle_axe": {
        "name": "Battle Axe",
        "damage_prompt": "1k8 + STR",
        "damage_type": DamageType.SLASHING.value,
        "proficiency_category": "martial",
        "weapon_group": "axe",
        "hands_required": 1,
        "price_cp": 100,
        "bulk": 1,
        "traits": ("sweep",),
    },
    "blowgun": {
        "name": "Blowgun",
        "damage_prompt": "1k1",
        "damage_type": DamageType.PIERCING.value,
        "proficiency_category": "simple",
        "weapon_group": "dart",
        "hands_required": 1,
        "ranged": True,
        "range_increment_ft": 20,
        "reload": 1,
        "price_cp": 10,
        "bulk": "L",
        "traits": ("agile", "nonlethal", "reload:1"),
    },
    "bo_staff": {
        "name": "Bo Staff",
        "damage_prompt": "1k8 + STR",
        "damage_type": DamageType.BLUDGEONING.value,
        "proficiency_category": "martial",
        "weapon_group": "club",
        "hands_required": 2,
        "price_cp": 20,
        "bulk": 2,
        "traits": ("monk", "parry", "reach:10", "trip"),
    },
    "clan_dagger": {
        "name": "Clan Dagger",
        "damage_prompt": "1k4 + STR",
        "damage_type": DamageType.PIERCING.value,
        "proficiency_category": "simple",
        "weapon_group": "knife",
        "hands_required": 1,
        "price_cp": 200,
        "bulk": "L",
        "traits": ("agile", "dwarf", "parry", "versatile:b"),
    },
    "composite_longbow": {
        "name": "Composite Longbow",
        "damage_prompt": "1k8 + DEX",
        "damage_type": DamageType.PIERCING.value,
        "proficiency_category": "martial",
        "weapon_group": "bow",
        "hands_required": 2,
        "ranged": True,
        "range_increment_ft": 100,
        "price_cp": 2000,
        "bulk": 1,
        "traits": ("deadly:d10", "propulsive", "volley:30"),
    },
    "composite_shortbow": {
        "name": "Composite Shortbow",
        "damage_prompt": "1k6 + DEX",
        "damage_type": DamageType.PIERCING.value,
        "proficiency_category": "martial",
        "weapon_group": "bow",
        "hands_required": 2,
        "ranged": True,
        "range_increment_ft": 60,
        "price_cp": 1400,
        "bulk": 1,
        "traits": ("deadly:d10", "propulsive"),
    },
    "dart": {
        "name": "Dart",
        "damage_prompt": "1k4 + DEX",
        "damage_type": DamageType.PIERCING.value,
        "proficiency_category": "simple",
        "weapon_group": "dart",
        "hands_required": 1,
        "ranged": True,
        "range_increment_ft": 20,
        "price_cp": 1,
        "bulk": "L",
        "traits": ("agile", "thrown:20"),
    },
    "dogslicer": {
        "name": "Dogslicer",
        "damage_prompt": "1k6 + STR",
        "damage_type": DamageType.SLASHING.value,
        "proficiency_category": "martial",
        "weapon_group": "sword",
        "hands_required": 1,
        "price_cp": 10,
        "bulk": "L",
        "traits": ("agile", "backstabber", "finesse", "goblin"),
    },
    "dwarven_waraxe": {
        "name": "Dwarven Waraxe",
        "damage_prompt": "1k8 + STR",
        "damage_type": DamageType.SLASHING.value,
        "proficiency_category": "advanced",
        "weapon_group": "axe",
        "hands_required": 1,
        "price_cp": 300,
        "bulk": 2,
        "traits": ("dwarf", "sweep", "two_hand:d12"),
    },
    "elven_curve_blade": {
        "name": "Elven Curve Blade",
        "damage_prompt": "1k8 + STR",
        "damage_type": DamageType.SLASHING.value,
        "proficiency_category": "martial",
        "weapon_group": "sword",
        "hands_required": 2,
        "price_cp": 400,
        "bulk": 2,
        "traits": ("elf", "finesse", "forceful"),
    },
    "falchion": {
        "name": "Falchion",
        "damage_prompt": "1k10 + STR",
        "damage_type": DamageType.SLASHING.value,
        "proficiency_category": "martial",
        "weapon_group": "sword",
        "hands_required": 2,
        "price_cp": 300,
        "bulk": 2,
        "traits": ("forceful", "sweep"),
    },
    "filchers_fork": {
        "name": "Filcher's Fork",
        "damage_prompt": "1k4 + STR",
        "damage_type": DamageType.PIERCING.value,
        "proficiency_category": "martial",
        "weapon_group": "spear",
        "hands_required": 1,
        "price_cp": 100,
        "bulk": "L",
        "traits": ("agile", "backstabber", "deadly:d6", "finesse", "halfling", "thrown:20"),
    },
    "flail": {
        "name": "Flail",
        "damage_prompt": "1k6 + STR",
        "damage_type": DamageType.BLUDGEONING.value,
        "proficiency_category": "martial",
        "weapon_group": "flail",
        "hands_required": 1,
        "price_cp": 80,
        "bulk": 1,
        "traits": ("disarm", "sweep", "trip"),
    },
    "gauntlet": {
        "name": "Gauntlet",
        "damage_prompt": "1k4 + STR",
        "damage_type": DamageType.BLUDGEONING.value,
        "proficiency_category": "simple",
        "weapon_group": "brawling",
        "hands_required": 1,
        "price_cp": 20,
        "bulk": "L",
        "traits": ("agile", "free_hand"),
    },
    "gnome_flickmace": {
        "name": "Gnome Flickmace",
        "damage_prompt": "1k6 + STR",
        "damage_type": DamageType.BLUDGEONING.value,
        "proficiency_category": "advanced",
        "weapon_group": "flail",
        "hands_required": 1,
        "price_cp": 300,
        "bulk": 1,
        "traits": ("gnome", "reach:10", "sweep"),
    },
    "gnome_hooked_hammer": {
        "name": "Gnome Hooked Hammer",
        "damage_prompt": "1k6 + STR",
        "damage_type": DamageType.BLUDGEONING.value,
        "proficiency_category": "martial",
        "weapon_group": "hammer",
        "hands_required": 1,
        "price_cp": 200,
        "bulk": 1,
        "traits": ("gnome", "trip", "two_hand:d10", "versatile:p"),
    },
    "greatclub": {
        "name": "Greatclub",
        "damage_prompt": "1k10 + STR",
        "damage_type": DamageType.BLUDGEONING.value,
        "proficiency_category": "martial",
        "weapon_group": "club",
        "hands_required": 2,
        "price_cp": 100,
        "bulk": 2,
        "traits": ("backswing", "shove"),
    },
    "greatpick": {
        "name": "Greatpick",
        "damage_prompt": "1k10 + STR",
        "damage_type": DamageType.PIERCING.value,
        "proficiency_category": "martial",
        "weapon_group": "pick",
        "hands_required": 2,
        "price_cp": 100,
        "bulk": 2,
        "traits": ("fatal:d12",),
    },
    "greatsword": {
        "name": "Greatsword",
        "damage_prompt": "1k12 + STR",
        "damage_type": DamageType.SLASHING.value,
        "proficiency_category": "martial",
        "weapon_group": "sword",
        "hands_required": 2,
        "price_cp": 200,
        "bulk": 2,
        "traits": ("versatile:p",),
    },
    "guisarme": {
        "name": "Guisarme",
        "damage_prompt": "1k10 + STR",
        "damage_type": DamageType.SLASHING.value,
        "proficiency_category": "martial",
        "weapon_group": "polearm",
        "hands_required": 2,
        "price_cp": 200,
        "bulk": 2,
        "traits": ("reach:10", "trip"),
    },
    "halfling_sling_staff": {
        "name": "Halfling Sling Staff",
        "damage_prompt": "1k10 + DEX",
        "damage_type": DamageType.BLUDGEONING.value,
        "proficiency_category": "martial",
        "weapon_group": "sling",
        "hands_required": 2,
        "ranged": True,
        "range_increment_ft": 80,
        "reload": 1,
        "price_cp": 500,
        "bulk": 1,
        "traits": ("halfling", "propulsive", "reload:1"),
    },
    "hand_crossbow": {
        "name": "Hand Crossbow",
        "damage_prompt": "1k6",
        "damage_type": DamageType.PIERCING.value,
        "proficiency_category": "simple",
        "weapon_group": "crossbow",
        "hands_required": 1,
        "ranged": True,
        "range_increment_ft": 60,
        "reload": 1,
        "price_cp": 300,
        "bulk": "L",
        "traits": ("crossbow", "reload:1"),
    },
    "hatchet": {
        "name": "Hatchet",
        "damage_prompt": "1k6 + STR",
        "damage_type": DamageType.SLASHING.value,
        "proficiency_category": "martial",
        "weapon_group": "axe",
        "hands_required": 1,
        "price_cp": 40,
        "bulk": "L",
        "traits": ("agile", "sweep", "thrown:10"),
    },
    "heavy_crossbow": {
        "name": "Heavy Crossbow",
        "damage_prompt": "1k10",
        "damage_type": DamageType.PIERCING.value,
        "proficiency_category": "simple",
        "weapon_group": "crossbow",
        "hands_required": 2,
        "ranged": True,
        "range_increment_ft": 120,
        "reload": 2,
        "price_cp": 400,
        "bulk": 2,
        "traits": ("crossbow", "reload:2"),
    },
    "horsechopper": {
        "name": "Horsechopper",
        "damage_prompt": "1k8 + STR",
        "damage_type": DamageType.SLASHING.value,
        "proficiency_category": "martial",
        "weapon_group": "polearm",
        "hands_required": 2,
        "price_cp": 90,
        "bulk": 2,
        "traits": ("goblin", "reach:10", "trip", "versatile:p"),
    },
    "kama": {
        "name": "Kama",
        "damage_prompt": "1k6 + STR",
        "damage_type": DamageType.SLASHING.value,
        "proficiency_category": "martial",
        "weapon_group": "knife",
        "hands_required": 1,
        "price_cp": 100,
        "bulk": "L",
        "traits": ("agile", "monk", "trip"),
    },
    "katana": {
        "name": "Katana",
        "damage_prompt": "1k6 + STR",
        "damage_type": DamageType.SLASHING.value,
        "proficiency_category": "martial",
        "weapon_group": "sword",
        "hands_required": 1,
        "price_cp": 200,
        "bulk": 1,
        "traits": ("deadly:d8", "two_hand:d10", "versatile:p"),
    },
    "katar": {
        "name": "Katar",
        "damage_prompt": "1k4 + STR",
        "damage_type": DamageType.PIERCING.value,
        "proficiency_category": "simple",
        "weapon_group": "knife",
        "hands_required": 1,
        "price_cp": 30,
        "bulk": "L",
        "traits": ("agile", "deadly:d6", "monk"),
    },
    "kukri": {
        "name": "Kukri",
        "damage_prompt": "1k6 + STR",
        "damage_type": DamageType.SLASHING.value,
        "proficiency_category": "martial",
        "weapon_group": "knife",
        "hands_required": 1,
        "price_cp": 60,
        "bulk": "L",
        "traits": ("agile", "finesse", "trip"),
    },
    "lance": {
        "name": "Lance",
        "damage_prompt": "1k8 + STR",
        "damage_type": DamageType.PIERCING.value,
        "proficiency_category": "martial",
        "weapon_group": "spear",
        "hands_required": 2,
        "price_cp": 100,
        "bulk": 2,
        "traits": ("deadly:d8", "jousting:d6", "reach:10"),
    },
    "light_hammer": {
        "name": "Light Hammer",
        "damage_prompt": "1k6 + STR",
        "damage_type": DamageType.BLUDGEONING.value,
        "proficiency_category": "martial",
        "weapon_group": "hammer",
        "hands_required": 1,
        "price_cp": 30,
        "bulk": "L",
        "traits": ("agile", "thrown:20"),
    },
    "light_mace": {
        "name": "Light Mace",
        "damage_prompt": "1k4 + STR",
        "damage_type": DamageType.BLUDGEONING.value,
        "proficiency_category": "simple",
        "weapon_group": "club",
        "hands_required": 1,
        "price_cp": 40,
        "bulk": "L",
        "traits": ("agile", "finesse", "shove"),
    },
    "light_pick": {
        "name": "Light Pick",
        "damage_prompt": "1k4 + STR",
        "damage_type": DamageType.PIERCING.value,
        "proficiency_category": "martial",
        "weapon_group": "pick",
        "hands_required": 1,
        "price_cp": 40,
        "bulk": "L",
        "traits": ("agile", "fatal:d8"),
    },
    "longspear": {
        "name": "Longspear",
        "damage_prompt": "1k8 + STR",
        "damage_type": DamageType.PIERCING.value,
        "proficiency_category": "simple",
        "weapon_group": "spear",
        "hands_required": 2,
        "price_cp": 50,
        "bulk": 2,
        "traits": ("reach:10",),
    },
    "main_gauche": {
        "name": "Main-Gauche",
        "damage_prompt": "1k4 + STR",
        "damage_type": DamageType.PIERCING.value,
        "proficiency_category": "martial",
        "weapon_group": "knife",
        "hands_required": 1,
        "price_cp": 50,
        "bulk": "L",
        "traits": ("agile", "disarm", "finesse", "parry", "versatile:s"),
    },
    "maul": {
        "name": "Maul",
        "damage_prompt": "1k12 + STR",
        "damage_type": DamageType.BLUDGEONING.value,
        "proficiency_category": "martial",
        "weapon_group": "hammer",
        "hands_required": 2,
        "price_cp": 300,
        "bulk": 2,
        "traits": ("shove",),
    },
    "morningstar": {
        "name": "Morningstar",
        "damage_prompt": "1k6 + STR",
        "damage_type": DamageType.BLUDGEONING.value,
        "proficiency_category": "simple",
        "weapon_group": "club",
        "hands_required": 1,
        "price_cp": 100,
        "bulk": 1,
        "traits": ("versatile:p",),
    },
    "nunchaku": {
        "name": "Nunchaku",
        "damage_prompt": "1k6 + STR",
        "damage_type": DamageType.BLUDGEONING.value,
        "proficiency_category": "martial",
        "weapon_group": "club",
        "hands_required": 1,
        "price_cp": 20,
        "bulk": "L",
        "traits": ("backswing", "disarm", "finesse", "monk"),
    },
    "orc_knuckle_dagger": {
        "name": "Orc Knuckle Dagger",
        "damage_prompt": "1k6 + STR",
        "damage_type": DamageType.PIERCING.value,
        "proficiency_category": "martial",
        "weapon_group": "knife",
        "hands_required": 1,
        "price_cp": 70,
        "bulk": "L",
        "traits": ("agile", "disarm", "orc"),
    },
    "orc_necksplitter": {
        "name": "Orc Necksplitter",
        "damage_prompt": "1k8 + STR",
        "damage_type": DamageType.SLASHING.value,
        "proficiency_category": "advanced",
        "weapon_group": "axe",
        "hands_required": 1,
        "price_cp": 200,
        "bulk": 1,
        "traits": ("forceful", "orc", "sweep"),
    },
    "pick": {
        "name": "Pick",
        "damage_prompt": "1k6 + STR",
        "damage_type": DamageType.PIERCING.value,
        "proficiency_category": "martial",
        "weapon_group": "pick",
        "hands_required": 1,
        "price_cp": 70,
        "bulk": 1,
        "traits": ("fatal:d10",),
    },
    "ranseur": {
        "name": "Ranseur",
        "damage_prompt": "1k10 + STR",
        "damage_type": DamageType.PIERCING.value,
        "proficiency_category": "martial",
        "weapon_group": "polearm",
        "hands_required": 2,
        "price_cp": 200,
        "bulk": 2,
        "traits": ("disarm", "reach:10"),
    },
    "sai": {
        "name": "Sai",
        "damage_prompt": "1k4 + STR",
        "damage_type": DamageType.PIERCING.value,
        "proficiency_category": "martial",
        "weapon_group": "knife",
        "hands_required": 1,
        "price_cp": 60,
        "bulk": "L",
        "traits": ("agile", "disarm", "finesse", "monk", "versatile:b"),
    },
    "sap": {
        "name": "Sap",
        "damage_prompt": "1k6 + STR",
        "damage_type": DamageType.BLUDGEONING.value,
        "proficiency_category": "martial",
        "weapon_group": "club",
        "hands_required": 1,
        "price_cp": 10,
        "bulk": "L",
        "traits": ("agile", "nonlethal"),
    },
    "sawtooth_saber": {
        "name": "Sawtooth Saber",
        "damage_prompt": "1k6 + STR",
        "damage_type": DamageType.SLASHING.value,
        "proficiency_category": "advanced",
        "weapon_group": "sword",
        "hands_required": 1,
        "price_cp": 500,
        "bulk": "L",
        "traits": ("agile", "finesse", "twin"),
    },
    "scimitar": {
        "name": "Scimitar",
        "damage_prompt": "1k6 + STR",
        "damage_type": DamageType.SLASHING.value,
        "proficiency_category": "martial",
        "weapon_group": "sword",
        "hands_required": 1,
        "price_cp": 100,
        "bulk": 1,
        "traits": ("forceful", "sweep"),
    },
    "scythe": {
        "name": "Scythe",
        "damage_prompt": "1k10 + STR",
        "damage_type": DamageType.SLASHING.value,
        "proficiency_category": "martial",
        "weapon_group": "polearm",
        "hands_required": 2,
        "price_cp": 200,
        "bulk": 2,
        "traits": ("deadly:d10", "trip"),
    },
    "shield_bash": {
        "name": "Shield Bash",
        "damage_prompt": "1k4 + STR",
        "damage_type": DamageType.BLUDGEONING.value,
        "proficiency_category": "martial",
        "weapon_group": "shield",
        "hands_required": 1,
        "price_cp": 0,
        "bulk": "-",
        "traits": (),
    },
    "shield_boss": {
        "name": "Shield Boss",
        "damage_prompt": "1k6 + STR",
        "damage_type": DamageType.BLUDGEONING.value,
        "proficiency_category": "martial",
        "weapon_group": "shield",
        "hands_required": 1,
        "price_cp": 50,
        "bulk": "-",
        "traits": ("attached_to_shield",),
    },
    "shield_spikes": {
        "name": "Shield Spikes",
        "damage_prompt": "1k6 + STR",
        "damage_type": DamageType.PIERCING.value,
        "proficiency_category": "martial",
        "weapon_group": "shield",
        "hands_required": 1,
        "price_cp": 50,
        "bulk": "-",
        "traits": ("attached_to_shield",),
    },
    "shuriken": {
        "name": "Shuriken",
        "damage_prompt": "1k4 + DEX",
        "damage_type": DamageType.PIERCING.value,
        "proficiency_category": "martial",
        "weapon_group": "dart",
        "hands_required": 1,
        "ranged": True,
        "range_increment_ft": 20,
        "reload": 0,
        "price_cp": 1,
        "bulk": "-",
        "traits": ("agile", "monk", "thrown:20"),
    },
    "sickle": {
        "name": "Sickle",
        "damage_prompt": "1k4 + STR",
        "damage_type": DamageType.SLASHING.value,
        "proficiency_category": "simple",
        "weapon_group": "knife",
        "hands_required": 1,
        "price_cp": 20,
        "bulk": "L",
        "traits": ("agile", "finesse", "trip"),
    },
    "sling": {
        "name": "Sling",
        "damage_prompt": "1k6 + DEX",
        "damage_type": DamageType.BLUDGEONING.value,
        "proficiency_category": "simple",
        "weapon_group": "sling",
        "hands_required": 1,
        "ranged": True,
        "range_increment_ft": 50,
        "price_cp": 0,
        "bulk": "L",
        "traits": ("propulsive",),
    },
    "spiked_chain": {
        "name": "Spiked Chain",
        "damage_prompt": "1k8 + STR",
        "damage_type": DamageType.SLASHING.value,
        "proficiency_category": "martial",
        "weapon_group": "flail",
        "hands_required": 2,
        "price_cp": 300,
        "bulk": 1,
        "traits": ("disarm", "finesse", "trip"),
    },
    "spiked_gauntlet": {
        "name": "Spiked Gauntlet",
        "damage_prompt": "1k4 + STR",
        "damage_type": DamageType.PIERCING.value,
        "proficiency_category": "simple",
        "weapon_group": "brawling",
        "hands_required": 1,
        "price_cp": 30,
        "bulk": "L",
        "traits": ("agile", "free_hand"),
    },
    "staff": {
        "name": "Staff",
        "damage_prompt": "1k4 + STR",
        "damage_type": DamageType.BLUDGEONING.value,
        "proficiency_category": "simple",
        "weapon_group": "club",
        "hands_required": 2,
        "price_cp": 0,
        "bulk": 1,
        "traits": ("two_hand:d8",),
    },
    "starknife": {
        "name": "Starknife",
        "damage_prompt": "1k4 + STR",
        "damage_type": DamageType.PIERCING.value,
        "proficiency_category": "martial",
        "weapon_group": "knife",
        "hands_required": 1,
        "price_cp": 200,
        "bulk": "L",
        "traits": ("agile", "deadly:d6", "finesse", "thrown:20", "versatile:s"),
    },
    "temple_sword": {
        "name": "Temple Sword",
        "damage_prompt": "1k8 + STR",
        "damage_type": DamageType.SLASHING.value,
        "proficiency_category": "martial",
        "weapon_group": "sword",
        "hands_required": 1,
        "price_cp": 200,
        "bulk": 1,
        "traits": ("monk", "trip"),
    },
    "trident": {
        "name": "Trident",
        "damage_prompt": "1k8 + STR",
        "damage_type": DamageType.PIERCING.value,
        "proficiency_category": "martial",
        "weapon_group": "spear",
        "hands_required": 1,
        "price_cp": 100,
        "bulk": 1,
        "traits": ("thrown:20",),
    },
    "war_flail": {
        "name": "War Flail",
        "damage_prompt": "1k10 + STR",
        "damage_type": DamageType.BLUDGEONING.value,
        "proficiency_category": "martial",
        "weapon_group": "flail",
        "hands_required": 2,
        "price_cp": 200,
        "bulk": 2,
        "traits": ("disarm", "sweep", "trip"),
    },
    "whip": {
        "name": "Whip",
        "damage_prompt": "1k4 + STR",
        "damage_type": DamageType.SLASHING.value,
        "proficiency_category": "martial",
        "weapon_group": "flail",
        "hands_required": 1,
        "price_cp": 10,
        "bulk": 1,
        "traits": ("disarm", "finesse", "nonlethal", "reach:10", "trip"),
    },
}


def _weapon_from_def(item_id: str, data: dict[str, object]) -> BaseWeapon:
    return BaseWeapon(
        item_id=item_id,
        name=str(data.get("name") or item_id.replace("_", " ").title()),
        event_name=str(data.get("event_name") or item_id),
        damage_prompt=str(data.get("damage_prompt") or "1k4 + STR"),
        damage_type=str(data.get("damage_type") or DamageType.BLUDGEONING.value),
        proficiency_category=str(data.get("proficiency_category") or "simple"),
        weapon_group=str(data.get("weapon_group") or "weapon"),
        hands_required=max(0, int(data.get("hands_required", 1) or 1)),
        ranged=bool(data.get("ranged", False)),
        range_increment_ft=max(0, int(data.get("range_increment_ft", 0) or 0)),
        reload=max(0, int(data.get("reload", 0) or 0)),
        price_cp=max(0, int(data.get("price_cp", 0) or 0)),
        bulk=data.get("bulk", 1),
        traits=tuple(data.get("traits") or ()),
    )


_WEAPON_FACTORIES = {
    "sword": SwordWeapon,
    "longsword": LongswordWeapon,
    "dagger": DaggerWeapon,
    "club": ClubWeapon,
    "spear": SpearWeapon,
    "shortsword": ShortswordWeapon,
    "rapier": RapierWeapon,
    "greataxe": GreataxeWeapon,
    "warhammer": WarhammerWeapon,
    "halberd": HalberdWeapon,
    "glaive": GlaiveWeapon,
    "mace": MaceWeapon,
    "javelin": JavelinWeapon,
    "shortbow": ShortbowWeapon,
    "longbow": LongbowWeapon,
    "crossbow": CrossbowWeapon,
    "light_crossbow": LightCrossbowWeapon,
    "unarmed": UnarmedWeapon,
    "razortooth_jaws": RazortoothJawsWeapon,
    **{
        wid: (lambda _wid=wid, _data=dict(wdef): _weapon_from_def(_wid, _data))
        for wid, wdef in _EXTRA_WEAPON_DEFS.items()
    },
}

_ALIASES = {
    "sword": "sword",
    "longsword": "longsword",
    "miecz": "sword",
    "dlugi_miecz": "longsword",
    "dagger": "dagger",
    "sztylet": "dagger",
    "club": "club",
    "maczuga": "club",
    "spear": "spear",
    "wlocznia": "spear",
    "shortsword": "shortsword",
    "krotki_miecz": "shortsword",
    "rapier": "rapier",
    "greataxe": "greataxe",
    "wielki_topor": "greataxe",
    "warhammer": "warhammer",
    "mlot_wojenny": "warhammer",
    "halberd": "halberd",
    "halabarda": "halberd",
    "glaive": "glaive",
    "glewia": "glaive",
    "mace": "mace",
    "buzdygan": "mace",
    "javelin": "javelin",
    "oszczep": "javelin",
    "shortbow": "shortbow",
    "krotki_luk": "shortbow",
    "longbow": "longbow",
    "bow": "longbow",
    "luk": "longbow",
    "dlugi_luk": "longbow",
    "crossbow": "crossbow",
    "simple_crossbow": "crossbow",
    "light_crossbow": "light_crossbow",
    "kusza": "crossbow",
    "lekka_kusza": "light_crossbow",
    "unarmed": "unarmed",
    "fist": "unarmed",
    "fists": "unarmed",
    "piesci": "unarmed",
    "razortooth_jaws": "razortooth_jaws",
    "jaws": "razortooth_jaws",
    "razortooth": "razortooth_jaws",
    "szczeki": "razortooth_jaws",
    "gauntlet": "gauntlet",
    "rekawica": "gauntlet",
    "sickle": "sickle",
    "sierp": "sickle",
    "staff": "staff",
    "kostur": "staff",
    "dart": "dart",
    "rzutka": "dart",
    "sling": "sling",
    "proca": "sling",
    "battle_axe": "battle_axe",
    "topor_bitewny": "battle_axe",
    "flail": "flail",
    "korbacz": "flail",
    "morningstar": "morningstar",
    "gwiazda_poranna": "morningstar",
    "pick": "pick",
    "kilof": "pick",
    "scimitar": "scimitar",
    "sejmitar": "scimitar",
    "trident": "trident",
    "trojzab": "trident",
    "whip": "whip",
    "bicz": "whip",
    "falchion": "falchion",
    "greatsword": "greatsword",
    "wielki_miecz": "greatsword",
    "maul": "maul",
    "hand_crossbow": "hand_crossbow",
    "reczna_kusza": "hand_crossbow",
    "heavy_crossbow": "heavy_crossbow",
    "ciezka_kusza": "heavy_crossbow",
    "composite_shortbow": "composite_shortbow",
    "kompozytowy_krotki_luk": "composite_shortbow",
    "composite_longbow": "composite_longbow",
    "kompozytowy_dlugi_luk": "composite_longbow",
}


def normalize_weapon_id(value: object) -> str | None:
    raw = str(value or "").strip().lower()
    if not raw:
        return None
    key = raw.replace("-", "_").replace(" ", "_")
    weapon_id = _ALIASES.get(key, key)
    if weapon_id in _WEAPON_FACTORIES:
        return weapon_id
    return None


def create_weapon(weapon_id: object) -> BaseWeapon | None:
    normalized = normalize_weapon_id(weapon_id)
    if not normalized:
        return None
    cls = _WEAPON_FACTORIES.get(normalized)
    if cls is None:
        return None
    return cls()


def weapon_profile(weapon_id: object) -> BaseWeapon | None:
    return create_weapon(weapon_id)


def list_weapon_ids() -> list[str]:
    return sorted(_WEAPON_FACTORIES.keys())


__all__ = [
    "BaseWeapon",
    "SwordWeapon",
    "LongswordWeapon",
    "DaggerWeapon",
    "ClubWeapon",
    "SpearWeapon",
    "ShortswordWeapon",
    "RapierWeapon",
    "GreataxeWeapon",
    "WarhammerWeapon",
    "HalberdWeapon",
    "GlaiveWeapon",
    "MaceWeapon",
    "JavelinWeapon",
    "ShortbowWeapon",
    "LongbowWeapon",
    "CrossbowWeapon",
    "LightCrossbowWeapon",
    "UnarmedWeapon",
    "RazortoothJawsWeapon",
    "create_weapon",
    "normalize_weapon_id",
    "weapon_profile",
    "list_weapon_ids",
]
