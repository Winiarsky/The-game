"""Simple combat traps: ordinary checks, position and one action per attempt."""
from __future__ import annotations

from dataclasses import dataclass, replace

from dnd_board_game.actors import Actor, Faction, actor_has_feature
from dnd_board_game.actors.skills import ability_check_roll_modifiers
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll, resolve_ability_check
from dnd_board_game.world import Coordinate
from .session import CombatState, current_actor, use_turn_action


@dataclass(frozen=True, slots=True)
class SimpleTrap:
    id: str
    name: str
    position: Coordinate
    detection_dc: int = 12
    disarm_dc: int = 13
    tool: str = "thieves_tools"
    status: str = "hidden"

    def __post_init__(self) -> None:
        if self.status not in {"hidden", "revealed", "disarmed", "triggered"}:
            raise ValueError("Nieprawidłowy stan pułapki.")
        if min(self.detection_dc, self.disarm_dc) < 1:
            raise ValueError("ST pułapki musi być dodatni.")


@dataclass(frozen=True, slots=True)
class SimpleTrapOutcome:
    state: CombatState
    trap: SimpleTrap
    success: bool
    total: int
    triggered: bool


def trap_request(actor: Actor, trap: SimpleTrap, action: str) -> D20RollRequest:
    if action == "detect":
        return D20RollRequest(ability="wisdom", modifiers=ability_check_roll_modifiers(actor, "wisdom", skill="perception"))
    if action == "disarm":
        return D20RollRequest(ability="dexterity", modifiers=ability_check_roll_modifiers(actor, "dexterity", tool=trap.tool or None))
    raise ValueError("Wybierz wykrywanie albo dezaktywację.")


def validate_trap_action(state: CombatState, trap: SimpleTrap, action: str, *, tools_available: bool) -> Actor:
    actor = current_actor(state)
    if actor.faction != Faction.ALLY:
        raise ValueError("Poczekaj na turę bohatera.")
    action_use = use_turn_action(state)
    if not action_use.accepted:
        raise ValueError(action_use.message)
    distance = max(abs(actor.position.col-trap.position.col), abs(actor.position.row-trap.position.row))*5
    if action == "detect":
        radius = 45 if actor_has_feature(actor, "combat_trap_detection") else 10
        if trap.status != "hidden" or distance > radius:
            raise ValueError("Przeszukaj obszar w zasięgu. Ta pułapka może już być ujawniona.")
    elif action == "disarm":
        if trap.status != "revealed":
            raise ValueError("Najpierw wykryj pułapkę.")
        if distance > 5:
            raise ValueError("Podejdź na sąsiednie pole pułapki.")
        if trap.tool and not tools_available:
            raise ValueError("Potrzebne są narzędzia do dezaktywacji.")
    else:
        raise ValueError("Nieznane działanie przy pułapce.")
    return actor


def resolve_trap_check(state: CombatState, trap: SimpleTrap, action: str, natural: int, *, tools_available: bool) -> SimpleTrapOutcome:
    actor = validate_trap_action(state, trap, action, tools_available=tools_available)
    if type(natural) is not int or not 1 <= natural <= 20:
        raise ValueError("Wpisz naturalny wynik k20 od 1 do 20.")
    roll = resolve_d20_roll(D20RollInput(trap_request(actor, trap, action), natural))
    success = resolve_ability_check(roll, trap.detection_dc if action == "detect" else trap.disarm_dc).success
    status = ("revealed" if success else "hidden") if action == "detect" else ("disarmed" if success else "triggered")
    return SimpleTrapOutcome(use_turn_action(state).state, replace(trap, status=status), success, roll.total,
                             action == "disarm" and not success)
