"""Typed D&D 5e 2014 weapon catalog primitives."""

from __future__ import annotations

from enum import StrEnum


class WeaponCategory(StrEnum):
    SIMPLE = "simple"
    MARTIAL = "martial"

    @property
    def proficiency_id(self) -> str:
        return f"{self.value}_weapons"


class WeaponProperty(StrEnum):
    AMMUNITION = "ammunition"
    FINESSE = "finesse"
    HEAVY = "heavy"
    LIGHT = "light"
    LOADING = "loading"
    REACH = "reach"
    SPECIAL = "special"
    THROWN = "thrown"
    TWO_HANDED = "two_handed"
    VERSATILE = "versatile"


class WeaponSpecialRule(StrEnum):
    LANCE = "lance"
    NET = "net"


__all__ = ["WeaponCategory", "WeaponProperty", "WeaponSpecialRule"]
