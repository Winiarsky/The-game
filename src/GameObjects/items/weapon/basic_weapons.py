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
    traits: tuple[str, ...] = ()


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
    traits: tuple[str, ...] = ("reach:10", "deadly:d8")


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
    hands_required: int = 1
    traits: tuple[str, ...] = ("agile", "finesse", "unarmed")


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
    traits: tuple[str, ...] = ("finesse", "unarmed", "jaws")


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
]
