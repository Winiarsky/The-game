from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AuraTarget(StrEnum):
    SELF_AND_ALLIES = "self_and_allies"
    ALLIES = "allies"
    ENEMIES = "enemies"
    ALL_CREATURES = "all_creatures"


class AuraEffectKind(StrEnum):
    SAVING_THROW_BONUS = "saving_throw_bonus"


@dataclass(frozen=True, slots=True)
class ActorAura:
    id: str
    label: str
    radius_feet: int
    target: AuraTarget
    effect_kind: AuraEffectKind
    value: int

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Aura id cannot be empty.")
        if not self.label.strip():
            raise ValueError("Aura label cannot be empty.")
        if self.radius_feet < 0 or self.radius_feet % 5 != 0:
            raise ValueError("Aura radius must be a non-negative multiple of 5 feet.")
