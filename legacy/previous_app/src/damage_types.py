from __future__ import annotations

from enum import Enum


class DamageType(str, Enum):
    """Central list of supported damage types."""

    NORMAL = "normal"
    SLASHING = "slashing"
    PIERCING = "piercing"
    BLUDGEONING = "bludgeoning"
    FORCE = "force"
    ACID = "acid"
    COLD = "cold"
    FIRE = "fire"
    ELECTRIC = "electric"
    SONIC = "sonic"
    NEGATIVE = "negative"
    POSITIVE = "positive"
    CHAOTIC = "chaotic"
    LAWFUL = "lawful"
    GOOD = "good"
    EVIL = "evil"
    MENTAL = "mental"
    POISON = "poison"
    BLEED = "bleed"


__all__ = ["DamageType"]
