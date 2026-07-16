from __future__ import annotations

from enum import StrEnum


class DamageType(StrEnum):
    ACID = "acid"
    BLUDGEONING = "bludgeoning"
    COLD = "cold"
    FIRE = "fire"
    FORCE = "force"
    LIGHTNING = "lightning"
    NECROTIC = "necrotic"
    PIERCING = "piercing"
    POISON = "poison"
    PSYCHIC = "psychic"
    RADIANT = "radiant"
    SLASHING = "slashing"
    THUNDER = "thunder"
    CUSTOM = "custom"


_DAMAGE_TYPE_LABELS_PL: dict[DamageType, str] = {
    DamageType.ACID: "od kwasu",
    DamageType.BLUDGEONING: "obuchowe",
    DamageType.COLD: "od zimna",
    DamageType.FIRE: "od ognia",
    DamageType.FORCE: "od mocy",
    DamageType.LIGHTNING: "od błyskawic",
    DamageType.NECROTIC: "nekrotyczne",
    DamageType.PIERCING: "kłute",
    DamageType.POISON: "od trucizny",
    DamageType.PSYCHIC: "psychiczne",
    DamageType.RADIANT: "promieniste",
    DamageType.SLASHING: "cięte",
    DamageType.THUNDER: "od dźwięku",
    DamageType.CUSTOM: "specjalne",
}


def damage_type_label_pl(damage_type: DamageType) -> str:
    return _DAMAGE_TYPE_LABELS_PL[damage_type]


__all__ = ["DamageType", "damage_type_label_pl"]
