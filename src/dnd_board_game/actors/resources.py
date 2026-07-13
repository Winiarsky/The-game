from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RecoveryPeriod(StrEnum):
    SHORT_REST = "short_rest"
    LONG_REST = "long_rest"
    NEVER = "never"


@dataclass(frozen=True, slots=True)
class ActorResourcePool:
    id: str
    label: str
    current: int
    maximum: int
    recovery: RecoveryPeriod

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Actor resource id cannot be empty.")
        if not self.label.strip():
            raise ValueError("Actor resource label cannot be empty.")
        if self.maximum < 1:
            raise ValueError("Actor resource maximum must be positive.")
        if not 0 <= self.current <= self.maximum:
            raise ValueError("Actor resource current value must be between zero and maximum.")


@dataclass(frozen=True, slots=True)
class HitDicePool:
    die_sides: int
    remaining: int
    maximum: int

    def __post_init__(self) -> None:
        if self.die_sides not in {6, 8, 10, 12}:
            raise ValueError("Hit Die must be d6, d8, d10, or d12.")
        if self.maximum < 1:
            raise ValueError("Hit Dice maximum must be positive.")
        if not 0 <= self.remaining <= self.maximum:
            raise ValueError("Hit Dice remaining value must be between zero and maximum.")
