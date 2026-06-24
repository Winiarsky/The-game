from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, NewType

if TYPE_CHECKING:
    from dnd_board_game.world.coordinates import Coordinate


ActorId = NewType("ActorId", str)


class Faction(StrEnum):
    ALLY = "ally"
    ENEMY = "enemy"
    NEUTRAL = "neutral"


@dataclass(frozen=True, slots=True)
class AbilityScores:
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10


@dataclass(frozen=True, slots=True)
class Actor:
    id: ActorId
    name: str
    ac: int
    hp: int
    temp_hp: int
    speed_feet: int
    position: Coordinate
    faction: Faction
    ability_scores: AbilityScores = field(default_factory=AbilityScores)

    def is_defeated(self) -> bool:
        return self.hp <= 0


def is_ally_or_neutral(mover: Actor, other: Actor) -> bool:
    if other.faction == Faction.NEUTRAL:
        return True
    if mover.faction == Faction.NEUTRAL:
        return other.faction == Faction.NEUTRAL
    return mover.faction == other.faction
