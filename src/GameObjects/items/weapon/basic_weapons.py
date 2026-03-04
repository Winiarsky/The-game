from __future__ import annotations

from dataclasses import dataclass

from damage_types import DamageType

from .base_weapon import BaseWeapon


@dataclass
class SwordWeapon(BaseWeapon):
    item_id: str = "sword"
    name: str = "Sword"
    event_name: str = "sword"
    damage_prompt: str = "1k8 + STR"
    damage_type: str = DamageType.SLASHING.value
    hands_required: int = 1
    traits: tuple[str, ...] = ()


@dataclass
class DaggerWeapon(BaseWeapon):
    item_id: str = "dagger"
    name: str = "Dagger"
    event_name: str = "dagger"
    damage_prompt: str = "1k4 + STR"
    damage_type: str = DamageType.SLASHING.value
    hands_required: int = 1
    traits: tuple[str, ...] = ("finesse",)


@dataclass
class LongbowWeapon(BaseWeapon):
    item_id: str = "longbow"
    name: str = "Longbow"
    event_name: str = "longbow"
    damage_prompt: str = "1k8 + DEX"
    damage_type: str = DamageType.PIERCING.value
    hands_required: int = 2
    ranged: bool = True
    range_increment_ft: int = 100
    traits: tuple[str, ...] = ("volley",)


@dataclass
class CrossbowWeapon(BaseWeapon):
    item_id: str = "crossbow"
    name: str = "Crossbow"
    event_name: str = "crossbow"
    damage_prompt: str = "1k8"
    damage_type: str = DamageType.PIERCING.value
    hands_required: int = 2
    ranged: bool = True
    range_increment_ft: int = 120
    reload: int = 1
    traits: tuple[str, ...] = ("crossbow", "simple_crossbow")


@dataclass
class UnarmedWeapon(BaseWeapon):
    item_id: str = "unarmed"
    name: str = "Unarmed"
    event_name: str = "unarmed"
    damage_prompt: str = "1k4 + STR"
    damage_type: str = DamageType.BLUDGEONING.value
    hands_required: int = 1
    traits: tuple[str, ...] = ("agile", "finesse", "unarmed")


@dataclass
class RazortoothJawsWeapon(BaseWeapon):
    item_id: str = "razortooth_jaws"
    name: str = "Razortooth Jaws"
    event_name: str = "razortooth_jaws"
    damage_prompt: str = "1k6 + STR"
    damage_type: str = DamageType.PIERCING.value
    hands_required: int = 1
    traits: tuple[str, ...] = ("finesse", "unarmed", "jaws")


_WEAPON_FACTORIES = {
    "sword": SwordWeapon,
    "dagger": DaggerWeapon,
    "longbow": LongbowWeapon,
    "crossbow": CrossbowWeapon,
    "unarmed": UnarmedWeapon,
    "razortooth_jaws": RazortoothJawsWeapon,
}

_ALIASES = {
    "sword": "sword",
    "miecz": "sword",
    "dagger": "dagger",
    "sztylet": "dagger",
    "longbow": "longbow",
    "bow": "longbow",
    "luk": "longbow",
    "dlugi_luk": "longbow",
    "crossbow": "crossbow",
    "simple_crossbow": "crossbow",
    "kusza": "crossbow",
    "lekka_kusza": "crossbow",
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
    "DaggerWeapon",
    "LongbowWeapon",
    "CrossbowWeapon",
    "UnarmedWeapon",
    "RazortoothJawsWeapon",
    "create_weapon",
    "normalize_weapon_id",
    "weapon_profile",
]
