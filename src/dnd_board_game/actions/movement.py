from __future__ import annotations

from dataclasses import dataclass

from .base import ActionResource, CombatActionMechanic, MechanicScope, TargetingMode


@dataclass(frozen=True, slots=True)
class MovementMechanic(CombatActionMechanic):
    pass


@dataclass(frozen=True, slots=True)
class BasicMove(MovementMechanic):
    pass


@dataclass(frozen=True, slots=True)
class DashAction(MovementMechanic):
    pass


def basic_move_mechanic() -> BasicMove:
    return BasicMove(
        id="movement.basic_move",
        name="Ruch",
        scope=MechanicScope.COMBAT,
        resource=ActionResource.MOVEMENT,
        targeting=TargetingMode.PATH,
        summary="Ruch zużywa pulę speed/extra movement i przesuwa aktora po legalnej ścieżce.",
        tags=("movement", "path"),
    )


def dash_mechanic() -> DashAction:
    return DashAction(
        id="action.dash",
        name="Dash",
        scope=MechanicScope.COMBAT,
        resource=ActionResource.ACTION,
        targeting=TargetingMode.SELF,
        summary="Dash zużywa akcję główną i zwiększa pulę ruchu o speed aktora do końca tury.",
        tags=("movement", "action_economy"),
    )
