from __future__ import annotations

from dataclasses import dataclass

from .base_shield import BaseShield
from .standard_shield import StandardShield


@dataclass
class BucklerShield(BaseShield):
    item_id: str = "buckler"
    name: str = "Buckler"
    description: str = "Mała tarcza."
    ac_bonus: int = 1
    hardness: int = 3
    max_hp: int = 6
    broken_threshold: int = 3
    traits: tuple[str, ...] = ("light_shield",)


@dataclass
class SteelShield(StandardShield):
    item_id: str = "steel_shield"
    name: str = "Steel Shield"


@dataclass
class TowerShield(BaseShield):
    item_id: str = "tower_shield"
    name: str = "Tower Shield"
    description: str = "Ciężka tarcza zapewniająca wysoki poziom osłony."
    ac_bonus: int = 2
    hardness: int = 5
    max_hp: int = 20
    broken_threshold: int = 10
    traits: tuple[str, ...] = ("tower_shield", "shield_block")


_SHIELD_FACTORIES = {
    "buckler": BucklerShield,
    "steel_shield": SteelShield,
    "standard_shield": StandardShield,
    "tower_shield": TowerShield,
}

_ALIASES = {
    "buckler": "buckler",
    "buckler_shield": "buckler",
    "steel_shield": "steel_shield",
    "steelshield": "steel_shield",
    "shield": "steel_shield",
    "standard_shield": "standard_shield",
    "standard": "standard_shield",
    "tower_shield": "tower_shield",
    "tower": "tower_shield",
    "tarcza": "steel_shield",
    "buckler_pl": "buckler",
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


__all__ = [
    "BaseShield",
    "BucklerShield",
    "SteelShield",
    "StandardShield",
    "TowerShield",
    "create_shield",
    "normalize_shield_id",
    "shield_profile",
]
