from __future__ import annotations

from dataclasses import dataclass

from dnd_board_game.core.damage_types import DamageType


@dataclass(frozen=True, slots=True)
class DamageAffinityProfile:
    resistances: tuple[DamageType, ...] = ()
    immunities: tuple[DamageType, ...] = ()
    vulnerabilities: tuple[DamageType, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "resistances", _unique(self.resistances))
        object.__setattr__(self, "immunities", _unique(self.immunities))
        object.__setattr__(self, "vulnerabilities", _unique(self.vulnerabilities))

    def is_resistant_to(self, damage_type: DamageType) -> bool:
        return damage_type in self.resistances

    def is_immune_to(self, damage_type: DamageType) -> bool:
        return damage_type in self.immunities

    def is_vulnerable_to(self, damage_type: DamageType) -> bool:
        return damage_type in self.vulnerabilities


def _unique(values: tuple[DamageType, ...]) -> tuple[DamageType, ...]:
    return tuple(dict.fromkeys(DamageType(value) for value in values))


__all__ = ["DamageAffinityProfile"]
