from __future__ import annotations

from dataclasses import dataclass

from .base_shield import BaseShield
from .standard_shield import StandardShield


@dataclass
class BucklerShield(BaseShield):
    item_id: str = "buckler"
    name: str = "Puklerz"
    description: str = "Mala tarcza."
    price_cp: int = 100
    bulk: str | int = "L"
    ac_bonus: int = 1
    take_cover_ac_bonus: int = 1
    hardness: int = 3
    max_hp: int = 6
    broken_threshold: int = 3
    traits: tuple[str, ...] = ("light_shield",)


@dataclass
class WoodenShield(BaseShield):
    item_id: str = "wooden_shield"
    name: str = "Tarcza drewniana"
    description: str = "Podstawowa drewniana tarcza."
    price_cp: int = 100
    bulk: str | int = 1
    ac_bonus: int = 2
    take_cover_ac_bonus: int = 2
    hardness: int = 3
    max_hp: int = 12
    broken_threshold: int = 6
    traits: tuple[str, ...] = ("shield_block",)


@dataclass
class SteelShield(StandardShield):
    item_id: str = "steel_shield"
    name: str = "Tarcza stalowa"
    price_cp: int = 200
    bulk: str | int = 1


@dataclass
class TowerShield(BaseShield):
    item_id: str = "tower_shield"
    name: str = "Tarcza wiezowa"
    description: str = "Ciezka tarcza zapewniajaca wysoki poziom oslony."
    price_cp: int = 1000
    bulk: str | int = 4
    ac_bonus: int = 2
    take_cover_ac_bonus: int = 4
    speed_penalty_feet: int = 5
    hardness: int = 5
    max_hp: int = 20
    broken_threshold: int = 10
    traits: tuple[str, ...] = ("tower_shield", "shield_block")


_SHIELD_FACTORIES = {
    "buckler": BucklerShield,
    "wooden_shield": WoodenShield,
    "steel_shield": SteelShield,
    "standard_shield": StandardShield,
    "tower_shield": TowerShield,
}

_ALIASES = {
    "buckler": "buckler",
    "buckler_shield": "buckler",
    "wooden_shield": "wooden_shield",
    "wooden": "wooden_shield",
    "steel_shield": "steel_shield",
    "steelshield": "steel_shield",
    "shield": "steel_shield",
    "standard_shield": "standard_shield",
    "standard": "standard_shield",
    "tower_shield": "tower_shield",
    "tower": "tower_shield",
    "tarcza": "steel_shield",
    "buckler_pl": "buckler",
    "drewniana_tarcza": "wooden_shield",
    "stalowa_tarcza": "steel_shield",
    "wiezowa_tarcza": "tower_shield",
}


def normalize_shield_id(value: object) -> str | None:
    raw = str(value or "").strip().lower()
    if not raw:
        return None
    key = raw.replace("-", "_").replace(" ", "_")
    shield_id = _ALIASES.get(key, key)
    if shield_id in _SHIELD_FACTORIES:
        return shield_id
    return None


def create_shield(shield_id: object) -> BaseShield | None:
    normalized = normalize_shield_id(shield_id)
    if not normalized:
        return None
    cls = _SHIELD_FACTORIES.get(normalized)
    if cls is None:
        return None
    return cls()


def shield_profile(shield_id: object) -> BaseShield | None:
    return create_shield(shield_id)


def list_shield_ids() -> list[str]:
    return sorted(_SHIELD_FACTORIES.keys())


__all__ = [
    "BaseShield",
    "BucklerShield",
    "WoodenShield",
    "SteelShield",
    "StandardShield",
    "TowerShield",
    "create_shield",
    "normalize_shield_id",
    "shield_profile",
    "list_shield_ids",
]
