"""Typed creature senses shared by exploration and combat visibility."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ActorSenseProfile:
    darkvision_feet: int = 0
    blindsight_feet: int = 0
    tremorsense_feet: int = 0
    truesight_feet: int = 0

    def __post_init__(self) -> None:
        values = (
            self.darkvision_feet,
            self.blindsight_feet,
            self.tremorsense_feet,
            self.truesight_feet,
        )
        if any(value < 0 or value % 5 for value in values):
            raise ValueError(
                "Actor sense distances must be non-negative multiples of 5 feet."
            )

    def as_payload(self) -> dict[str, int]:
        return {
            "darkvision_feet": self.darkvision_feet,
            "blindsight_feet": self.blindsight_feet,
            "tremorsense_feet": self.tremorsense_feet,
            "truesight_feet": self.truesight_feet,
        }
