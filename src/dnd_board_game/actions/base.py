from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MechanicScope(StrEnum):
    COMBAT = "combat"
    EXPLORATION = "exploration"


class ActionResource(StrEnum):
    NONE = "none"
    ACTION = "action"
    BONUS_ACTION = "bonus_action"
    REACTION = "reaction"
    MOVEMENT = "movement"


class TargetingMode(StrEnum):
    NONE = "none"
    SELF = "self"
    ACTOR = "actor"
    ALLY = "ally"
    ENEMY = "enemy"
    TILE = "tile"
    PATH = "path"
    AREA = "area"
    OBJECT = "object"


@dataclass(frozen=True, slots=True)
class ActionMechanic:
    id: str
    name: str
    scope: MechanicScope
    resource: ActionResource
    targeting: TargetingMode
    summary: str
    tags: tuple[str, ...] = ()

    @property
    def mechanic_type(self) -> str:
        return self.__class__.__name__

    def inheritance_path(self) -> tuple[str, ...]:
        classes = []
        for cls in reversed(self.__class__.mro()):
            if cls is object:
                continue
            if not issubclass(cls, ActionMechanic):
                continue
            classes.append(cls.__name__)
        return tuple(classes)

    def as_payload(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.mechanic_type,
            "scope": self.scope.value,
            "resource": self.resource.value,
            "targeting": self.targeting.value,
            "summary": self.summary,
            "tags": list(self.tags),
            "inheritance": list(self.inheritance_path()),
        }


@dataclass(frozen=True, slots=True)
class CombatActionMechanic(ActionMechanic):
    pass


@dataclass(frozen=True, slots=True)
class ExplorationActionMechanic(ActionMechanic):
    pass
