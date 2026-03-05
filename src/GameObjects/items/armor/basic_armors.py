from __future__ import annotations

from dataclasses import dataclass

from .base_armor import BaseArmor


@dataclass
class PaddedArmor(BaseArmor):
    item_id: str = "padded_armor"
    name: str = "Padded Armor"
    description: str = "Najprostsza lekka zbroja."
    armor_category: str = "light"
    ac_bonus: int = 1
    dex_cap: int = 3
    strength_requirement: int = 10
    traits: tuple[str, ...] = ("comfort",)


@dataclass
class LeatherArmor(BaseArmor):
    item_id: str = "leather_armor"
    name: str = "Leather Armor"
    description: str = "Lekka, elastyczna zbroja."
    armor_category: str = "light"
    ac_bonus: int = 1
    dex_cap: int = 4
    strength_requirement: int = 10
    traits: tuple[str, ...] = ("flexible",)


@dataclass
class StuddedLeatherArmor(BaseArmor):
    item_id: str = "studded_leather"
    name: str = "Studded Leather"
    description: str = "Wzmocniona lekka zbroja."
    armor_category: str = "light"
    ac_bonus: int = 2
    dex_cap: int = 3
    strength_requirement: int = 12
    traits: tuple[str, ...] = ("flexible",)


@dataclass
class HideArmor(BaseArmor):
    item_id: str = "hide_armor"
    name: str = "Hide Armor"
    description: str = "Solidna średnia zbroja."
    armor_category: str = "medium"
    ac_bonus: int = 3
    dex_cap: int = 2
    strength_requirement: int = 14
    traits: tuple[str, ...] = ()


@dataclass
class ScaleMailArmor(BaseArmor):
    item_id: str = "scale_mail"
    name: str = "Scale Mail"
    description: str = "Średnia zbroja o wysokiej ochronie."
    armor_category: str = "medium"
    ac_bonus: int = 3
    dex_cap: int = 2
    strength_requirement: int = 14
    traits: tuple[str, ...] = ("noisy",)


@dataclass
class BreastplateArmor(BaseArmor):
    item_id: str = "breastplate"
    name: str = "Breastplate"
    description: str = "Defensywna średnia zbroja."
    armor_category: str = "medium"
    ac_bonus: int = 4
    dex_cap: int = 1
    strength_requirement: int = 16
    traits: tuple[str, ...] = ()


@dataclass
class ChainMailArmor(BaseArmor):
    item_id: str = "chain_mail"
    name: str = "Chain Mail"
    description: str = "Popularna ciężka zbroja."
    armor_category: str = "heavy"
    ac_bonus: int = 4
    dex_cap: int = 1
    strength_requirement: int = 16
    traits: tuple[str, ...] = ("noisy",)


@dataclass
class SplintMailArmor(BaseArmor):
    item_id: str = "splint_mail"
    name: str = "Splint Mail"
    description: str = "Ciężka zbroja o bardzo wysokiej ochronie."
    armor_category: str = "heavy"
    ac_bonus: int = 5
    dex_cap: int = 0
    strength_requirement: int = 18
    traits: tuple[str, ...] = ("noisy",)


@dataclass
class FullPlateArmor(BaseArmor):
    item_id: str = "full_plate"
    name: str = "Full Plate"
    description: str = "Najlepsza obrona fizyczna."
    armor_category: str = "heavy"
    ac_bonus: int = 6
    dex_cap: int = 0
    strength_requirement: int = 18
    bulwark_reflex_floor: int | None = 3
    traits: tuple[str, ...] = ("bulwark",)


_ARMOR_FACTORIES = {
    "padded_armor": PaddedArmor,
    "leather_armor": LeatherArmor,
    "studded_leather": StuddedLeatherArmor,
    "hide_armor": HideArmor,
    "scale_mail": ScaleMailArmor,
    "breastplate": BreastplateArmor,
    "chain_mail": ChainMailArmor,
    "splint_mail": SplintMailArmor,
    "full_plate": FullPlateArmor,
}

_ALIASES = {
    "padded_armor": "padded_armor",
    "padded": "padded_armor",
    "leather_armor": "leather_armor",
    "leather": "leather_armor",
    "studded_leather": "studded_leather",
    "studded": "studded_leather",
    "hide_armor": "hide_armor",
    "hide": "hide_armor",
    "scale_mail": "scale_mail",
    "scale": "scale_mail",
    "breastplate": "breastplate",
    "chain_mail": "chain_mail",
    "chainmail": "chain_mail",
    "splint_mail": "splint_mail",
    "splint": "splint_mail",
    "full_plate": "full_plate",
    "plate": "full_plate",
    "fullplate": "full_plate",
    "padded_armor_pl": "padded_armor",
    "skorzana": "leather_armor",
    "skorzana_nabijana": "studded_leather",
    "kolczuga": "chain_mail",
    "zbroja_luskowa": "scale_mail",
    "napiersnik": "breastplate",
    "plytowa": "full_plate",
}


def normalize_armor_id(value: object) -> str | None:
    raw = str(value or "").strip().lower()
    if not raw:
        return None
    key = raw.replace("-", "_").replace(" ", "_")
    armor_id = _ALIASES.get(key, key)
    if armor_id in _ARMOR_FACTORIES:
        return armor_id
    return None


def create_armor(armor_id: object) -> BaseArmor | None:
    normalized = normalize_armor_id(armor_id)
    if not normalized:
        return None
    cls = _ARMOR_FACTORIES.get(normalized)
    if cls is None:
        return None
    return cls()


def armor_profile(armor_id: object) -> BaseArmor | None:
    return create_armor(armor_id)


__all__ = [
    "BaseArmor",
    "PaddedArmor",
    "LeatherArmor",
    "StuddedLeatherArmor",
    "HideArmor",
    "ScaleMailArmor",
    "BreastplateArmor",
    "ChainMailArmor",
    "SplintMailArmor",
    "FullPlateArmor",
    "create_armor",
    "normalize_armor_id",
    "armor_profile",
]
