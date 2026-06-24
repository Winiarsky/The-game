from __future__ import annotations

from dataclasses import dataclass

from .base_armor import BaseArmor


@dataclass
class PaddedArmor(BaseArmor):
    item_id: str = "padded_armor"
    name: str = "Padded Armor"
    description: str = "Najprostsza lekka zbroja."
    armor_category: str = "light"
    armor_group: str = "cloth"
    ac_bonus: int = 1
    price_cp: int = 20
    bulk: str | int = "L"
    dex_cap: int = 3
    strength_requirement: int = 10
    check_penalty: int = 0
    speed_penalty_feet: int = 0
    traits: tuple[str, ...] = ("comfort",)


@dataclass
class LeatherArmor(BaseArmor):
    item_id: str = "leather_armor"
    name: str = "Leather Armor"
    description: str = "Lekka, elastyczna zbroja."
    armor_category: str = "light"
    armor_group: str = "leather"
    ac_bonus: int = 1
    price_cp: int = 200
    bulk: str | int = 1
    dex_cap: int = 4
    strength_requirement: int = 10
    check_penalty: int = 1
    speed_penalty_feet: int = 0
    traits: tuple[str, ...] = ()


@dataclass
class StuddedLeatherArmor(BaseArmor):
    item_id: str = "studded_leather"
    name: str = "Studded Leather"
    description: str = "Wzmocniona lekka zbroja."
    armor_category: str = "light"
    armor_group: str = "leather"
    ac_bonus: int = 2
    price_cp: int = 300
    bulk: str | int = 1
    dex_cap: int = 3
    strength_requirement: int = 12
    check_penalty: int = 1
    speed_penalty_feet: int = 0
    traits: tuple[str, ...] = ()


@dataclass
class ChainShirtArmor(BaseArmor):
    item_id: str = "chain_shirt"
    name: str = "Chain Shirt"
    description: str = "Lekka zbroja z kolczych ogniw."
    armor_category: str = "light"
    armor_group: str = "chain"
    ac_bonus: int = 2
    price_cp: int = 500
    bulk: str | int = 1
    dex_cap: int = 3
    strength_requirement: int = 12
    check_penalty: int = 1
    speed_penalty_feet: int = 0
    traits: tuple[str, ...] = ("flexible", "noisy")


@dataclass
class HideArmor(BaseArmor):
    item_id: str = "hide_armor"
    name: str = "Hide Armor"
    description: str = "Solidna średnia zbroja."
    armor_category: str = "medium"
    armor_group: str = "leather"
    ac_bonus: int = 3
    price_cp: int = 200
    bulk: str | int = 2
    dex_cap: int = 2
    strength_requirement: int = 14
    check_penalty: int = 2
    speed_penalty_feet: int = 5
    traits: tuple[str, ...] = ()


@dataclass
class ScaleMailArmor(BaseArmor):
    item_id: str = "scale_mail"
    name: str = "Scale Mail"
    description: str = "Średnia zbroja o wysokiej ochronie."
    armor_category: str = "medium"
    armor_group: str = "composite"
    ac_bonus: int = 3
    price_cp: int = 400
    bulk: str | int = 2
    dex_cap: int = 2
    strength_requirement: int = 14
    check_penalty: int = 2
    speed_penalty_feet: int = 5
    traits: tuple[str, ...] = ()


@dataclass
class BreastplateArmor(BaseArmor):
    item_id: str = "breastplate"
    name: str = "Breastplate"
    description: str = "Defensywna średnia zbroja."
    armor_category: str = "medium"
    armor_group: str = "plate"
    ac_bonus: int = 4
    price_cp: int = 800
    bulk: str | int = 2
    dex_cap: int = 1
    strength_requirement: int = 16
    check_penalty: int = 2
    speed_penalty_feet: int = 5
    traits: tuple[str, ...] = ()


@dataclass
class ChainMailArmor(BaseArmor):
    item_id: str = "chain_mail"
    name: str = "Chain Mail"
    description: str = "Solidna średnia zbroja z ogniw."
    armor_category: str = "medium"
    armor_group: str = "chain"
    ac_bonus: int = 4
    price_cp: int = 600
    bulk: str | int = 2
    dex_cap: int = 1
    strength_requirement: int = 16
    check_penalty: int = 2
    speed_penalty_feet: int = 5
    traits: tuple[str, ...] = ("flexible", "noisy")


@dataclass
class SplintMailArmor(BaseArmor):
    item_id: str = "splint_mail"
    name: str = "Splint Mail"
    description: str = "Ciężka zbroja o bardzo wysokiej ochronie."
    armor_category: str = "heavy"
    armor_group: str = "composite"
    ac_bonus: int = 5
    price_cp: int = 1300
    bulk: str | int = 3
    dex_cap: int = 1
    strength_requirement: int = 16
    check_penalty: int = 3
    speed_penalty_feet: int = 10
    traits: tuple[str, ...] = ()


@dataclass
class HalfPlateArmor(BaseArmor):
    item_id: str = "half_plate"
    name: str = "Half Plate"
    description: str = "Ciężka zbroja z połowicznymi płytami."
    armor_category: str = "heavy"
    armor_group: str = "plate"
    ac_bonus: int = 5
    price_cp: int = 1800
    bulk: str | int = 3
    dex_cap: int = 1
    strength_requirement: int = 16
    check_penalty: int = 3
    speed_penalty_feet: int = 10
    traits: tuple[str, ...] = ()


@dataclass
class FullPlateArmor(BaseArmor):
    item_id: str = "full_plate"
    name: str = "Full Plate"
    description: str = "Najlepsza obrona fizyczna."
    armor_category: str = "heavy"
    armor_group: str = "plate"
    ac_bonus: int = 6
    price_cp: int = 3000
    bulk: str | int = 4
    dex_cap: int = 0
    strength_requirement: int = 18
    check_penalty: int = 3
    speed_penalty_feet: int = 10
    bulwark_reflex_floor: int | None = 3
    traits: tuple[str, ...] = ("bulwark",)


_ARMOR_FACTORIES = {
    "padded_armor": PaddedArmor,
    "leather_armor": LeatherArmor,
    "studded_leather": StuddedLeatherArmor,
    "chain_shirt": ChainShirtArmor,
    "hide_armor": HideArmor,
    "scale_mail": ScaleMailArmor,
    "breastplate": BreastplateArmor,
    "chain_mail": ChainMailArmor,
    "splint_mail": SplintMailArmor,
    "half_plate": HalfPlateArmor,
    "full_plate": FullPlateArmor,
}

_ALIASES = {
    "padded_armor": "padded_armor",
    "padded": "padded_armor",
    "leather_armor": "leather_armor",
    "leather": "leather_armor",
    "studded_leather": "studded_leather",
    "studded": "studded_leather",
    "chain_shirt": "chain_shirt",
    "chainshirt": "chain_shirt",
    "hide_armor": "hide_armor",
    "hide": "hide_armor",
    "scale_mail": "scale_mail",
    "scale": "scale_mail",
    "breastplate": "breastplate",
    "chain_mail": "chain_mail",
    "chainmail": "chain_mail",
    "splint_mail": "splint_mail",
    "splint": "splint_mail",
    "half_plate": "half_plate",
    "halfplate": "half_plate",
    "full_plate": "full_plate",
    "plate": "full_plate",
    "fullplate": "full_plate",
    "padded_armor_pl": "padded_armor",
    "skorzana": "leather_armor",
    "skorzana_nabijana": "studded_leather",
    "kolcza_koszula": "chain_shirt",
    "kolczuga": "chain_mail",
    "zbroja_luskowa": "scale_mail",
    "napiersnik": "breastplate",
    "polplytowa": "half_plate",
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


def list_armor_ids() -> list[str]:
    return sorted(_ARMOR_FACTORIES.keys())


__all__ = [
    "BaseArmor",
    "PaddedArmor",
    "LeatherArmor",
    "StuddedLeatherArmor",
    "ChainShirtArmor",
    "HideArmor",
    "ScaleMailArmor",
    "BreastplateArmor",
    "ChainMailArmor",
    "SplintMailArmor",
    "HalfPlateArmor",
    "FullPlateArmor",
    "create_armor",
    "normalize_armor_id",
    "armor_profile",
    "list_armor_ids",
]
