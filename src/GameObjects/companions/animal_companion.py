from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from combat.hp_engine import apply_damage as hp_apply_damage
from combat.hp_engine import heal as hp_heal
from GameObjects.interactions_mixin.bonus_mixin import BonusMixin
from damage_types import DamageType
from GameObjects.interactions_mixin.status_mixin import StatusMixin
from object_registry import assign_id


ANIMAL_COMPANION_TYPES: dict[str, dict[str, object]] = {
    "badger": {
        "label": "Badger",
        "size": "small",
        "hp_ancestry": 8,
        "land_speed_feet": 25,
        "ability_mods": {"str": 2, "dex": 2, "con": 2, "int": -4, "wis": 2, "cha": 0},
        "attacks": [
            {"id": "jaws", "label": "Jaws", "damage": "1d8", "damage_type": DamageType.PIERCING.value, "traits": []},
            {"id": "claw", "label": "Claw", "damage": "1d6", "damage_type": DamageType.SLASHING.value, "traits": ["agile"]},
        ],
        "support_benefit": "Trafiony cel w zasiegu badgera nie moze Stepowac do startu twojej nastepnej tury.",
    },
    "bear": {
        "label": "Bear",
        "size": "small",
        "hp_ancestry": 8,
        "land_speed_feet": 35,
        "ability_mods": {"str": 3, "dex": 2, "con": 2, "int": -4, "wis": 1, "cha": 0},
        "attacks": [
            {"id": "jaws", "label": "Jaws", "damage": "1d8", "damage_type": DamageType.PIERCING.value, "traits": []},
            {"id": "claw", "label": "Claw", "damage": "1d6", "damage_type": DamageType.SLASHING.value, "traits": ["agile"]},
        ],
        "support_benefit": "Przy twoim trafieniu celu w zasiegu niedzwiedzia cel dostaje dodatkowe 1d8 slashing.",
    },
    "bird": {
        "label": "Bird",
        "size": "small",
        "hp_ancestry": 4,
        "land_speed_feet": 10,
        "ability_mods": {"str": 2, "dex": 3, "con": 1, "int": -4, "wis": 2, "cha": 0},
        "attacks": [
            {"id": "jaws", "label": "Jaws", "damage": "1d6", "damage_type": DamageType.PIERCING.value, "traits": ["finesse"]},
            {"id": "talon", "label": "Talon", "damage": "1d4", "damage_type": DamageType.SLASHING.value, "traits": ["agile", "finesse"]},
        ],
        "support_benefit": "Twoje trafienia na celu zagrozonym przez ptaka moga nakladac persistent bleed 1d4 (manual).",
    },
    "cat": {
        "label": "Cat",
        "size": "small",
        "hp_ancestry": 4,
        "land_speed_feet": 35,
        "ability_mods": {"str": 2, "dex": 3, "con": 1, "int": -4, "wis": 2, "cha": 0},
        "attacks": [
            {"id": "jaws", "label": "Jaws", "damage": "1d6", "damage_type": DamageType.PIERCING.value, "traits": ["finesse"]},
            {"id": "claw", "label": "Claw", "damage": "1d4", "damage_type": DamageType.SLASHING.value, "traits": ["agile", "finesse"]},
        ],
        "support_benefit": "Trafiony przez ciebie cel w zasiegu kota staje sie flat-footed do konca twojej nastepnej tury.",
        "special": "Cat: +1d4 precision przeciw flat-footed (manual).",
    },
    "dromaeosaur": {
        "label": "Dromaeosaur",
        "size": "small",
        "hp_ancestry": 6,
        "land_speed_feet": 50,
        "ability_mods": {"str": 2, "dex": 3, "con": 2, "int": -4, "wis": 1, "cha": 0},
        "attacks": [
            {"id": "jaws", "label": "Jaws", "damage": "1d8", "damage_type": DamageType.PIERCING.value, "traits": ["finesse"]},
            {"id": "talon", "label": "Talon", "damage": "1d6", "damage_type": DamageType.SLASHING.value, "traits": ["agile", "finesse"]},
        ],
        "support_benefit": "Raptor wspiera flankowanie: traktuj go jako pozycje flankujaca (manual).",
    },
    "horse": {
        "label": "Horse",
        "size": "medium",
        "hp_ancestry": 8,
        "land_speed_feet": 40,
        "ability_mods": {"str": 3, "dex": 2, "con": 2, "int": -4, "wis": 1, "cha": 0},
        "attacks": [
            {"id": "hoof", "label": "Hoof", "damage": "1d6", "damage_type": DamageType.BLUDGEONING.value, "traits": ["agile"]},
        ],
        "support_benefit": "Mounted: po ruchu >=10 ft przed melee Strike owner dostaje bonus do obrazen (manual).",
        "special": "Mount",
    },
    "snake": {
        "label": "Snake",
        "size": "small",
        "hp_ancestry": 6,
        "land_speed_feet": 20,
        "ability_mods": {"str": 3, "dex": 3, "con": 1, "int": -4, "wis": 1, "cha": 0},
        "attacks": [
            {"id": "jaws", "label": "Jaws", "damage": "1d8", "damage_type": DamageType.PIERCING.value, "traits": ["finesse"]},
        ],
        "support_benefit": "Cele zagrozone przez weza nie moga triggerowac reakcji na twoje akcje (manual).",
    },
    "wolf": {
        "label": "Wolf",
        "size": "small",
        "hp_ancestry": 6,
        "land_speed_feet": 40,
        "ability_mods": {"str": 2, "dex": 3, "con": 2, "int": -4, "wis": 1, "cha": 0},
        "attacks": [
            {"id": "jaws", "label": "Jaws", "damage": "1d8", "damage_type": DamageType.PIERCING.value, "traits": ["finesse"]},
        ],
        "support_benefit": "Twoje trafienia celu w zasiegu wilka daja -5ft status do Speed na 1 minute (manual).",
    },
}


def animal_companion_type_ids() -> list[str]:
    return list(ANIMAL_COMPANION_TYPES.keys())


def companion_type_data(companion_type: str) -> dict[str, object]:
    normalized = str(companion_type or "").strip().lower().replace("-", "_").replace(" ", "_")
    if normalized not in ANIMAL_COMPANION_TYPES:
        normalized = "wolf"
    return dict(ANIMAL_COMPANION_TYPES[normalized])


def resolve_animal_companion_type(owner) -> str:
    raw = str(getattr(owner, "animal_companion_type", "") or "").strip().lower().replace("-", "_").replace(" ", "_")
    if raw in ANIMAL_COMPANION_TYPES:
        return raw
    getter = getattr(owner, "get_status_data", None)
    if callable(getter):
        try:
            choice = str(getter("animal_companion", "animal_companion_type", "") or "").strip().lower()
            if choice in ANIMAL_COMPANION_TYPES:
                return choice
        except Exception:
            pass
    for status in getattr(owner, "statuses", []) or []:
        if getattr(status, "id", None) != "animal_companion":
            continue
        data = getattr(status, "data", None) or {}
        choice = str(data.get("animal_companion_type", "") or "").strip().lower()
        if choice in ANIMAL_COMPANION_TYPES:
            return choice
    return "wolf"


@dataclass
class AnimalCompanion(StatusMixin, BonusMixin):
    object_id: str = field(init=False)
    owner_id: str = ""
    owner_name: str = ""
    companion_type: str = "wolf"
    name: str = "Animal Companion"
    level: int = 1
    size: str = "small"
    land_speed_feet: int = 25
    reach_cells: int = 1
    attack_profiles: list[dict[str, object]] = field(default_factory=list)
    support_benefit: str = ""
    special: str | None = None
    hp: int = 1
    max_hp: int = 1
    ac: int = 10
    position: tuple[int, int] | None = None
    blocks_movement: bool = True

    def __post_init__(self) -> None:
        self.object_id = assign_id(self)
        self.land_speed_feet = max(5, int(self.land_speed_feet or 25))
        self.level = max(1, int(self.level or 1))
        self.max_hp = max(1, int(self.max_hp or self.hp or 1))
        self.hp = max(0, min(int(self.hp or self.max_hp), self.max_hp))
        self.ac = max(10, int(self.ac or 10))

    def __hash__(self) -> int:
        return hash(self.object_id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AnimalCompanion):
            return False
        return self.object_id == other.object_id

    def set_position(self, position: tuple[int, int] | None) -> None:
        self.position = position

    def apply_damage(self, amount: int, _damage_type: str = DamageType.NORMAL.value) -> tuple[int, bool]:
        info = hp_apply_damage(self, amount, _damage_type, source="animal_companion:damage")
        defeated = bool(info.get("defeated", False)) or int(getattr(self, "hp", 0) or 0) <= 0
        if defeated:
            try:
                from statuses import mark_dead

                mark_dead(self, source="animal_companion:damage", reason="hp_zero")
            except Exception:
                pass
        return int(getattr(self, "hp", 0) or 0), defeated

    def heal(self, amount: int) -> int:
        hp_heal(self, amount, source="animal_companion:heal")
        if self.hp > 0:
            try:
                from statuses import on_heal

                on_heal(self, source="animal_companion:heal")
            except Exception:
                pass
        return self.hp

    def is_dead(self) -> bool:
        try:
            from statuses import is_dead

            return bool(is_dead(self))
        except Exception:
            return self.hp <= 0


def build_animal_companion(owner, companion_type: str | None = None) -> AnimalCompanion:
    chosen_type = resolve_animal_companion_type(owner) if companion_type is None else str(companion_type).strip().lower()
    if chosen_type not in ANIMAL_COMPANION_TYPES:
        chosen_type = "wolf"
    data = companion_type_data(chosen_type)
    ability_mods = dict(data.get("ability_mods", {}) or {})
    con_mod = int(ability_mods.get("con", 1) or 1)
    owner_level = max(1, int(getattr(owner, "level", 1) or 1))
    ancestry_hp = max(1, int(data.get("hp_ancestry", 6) or 6))
    max_hp = ancestry_hp + (6 + con_mod) * owner_level
    owner_name = str(getattr(owner, "name", "Owner") or "Owner")
    owner_id = str(getattr(owner, "object_id", id(owner)))
    type_label = str(data.get("label", chosen_type.title()) or chosen_type.title())
    companion_name = f"{owner_name} Companion ({type_label})"
    attack_profiles = deepcopy(list(data.get("attacks", []) or []))
    ac = 10 + owner_level + max(0, int(ability_mods.get("dex", 0) or 0))
    return AnimalCompanion(
        owner_id=owner_id,
        owner_name=owner_name,
        companion_type=chosen_type,
        name=companion_name,
        level=owner_level,
        size=str(data.get("size", "small") or "small"),
        land_speed_feet=int(data.get("land_speed_feet", 25) or 25),
        reach_cells=1,
        attack_profiles=attack_profiles,
        support_benefit=str(data.get("support_benefit", "") or ""),
        special=str(data.get("special", "") or "") or None,
        hp=max_hp,
        max_hp=max_hp,
        ac=ac,
    )


__all__ = [
    "ANIMAL_COMPANION_TYPES",
    "AnimalCompanion",
    "animal_companion_type_ids",
    "build_animal_companion",
    "companion_type_data",
    "resolve_animal_companion_type",
]
