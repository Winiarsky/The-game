from __future__ import annotations

from enum import Enum


class Skill(str, Enum):
    """Central list of supported skill identifiers."""

    THIEVERY = "thievery"
    DIPLOMACY = "diplomacy"
    STEALTH = "stealth"
    PERCEPTION = "perception"
    ATHLETICS = "athletics"


__all__ = ["Skill"]
