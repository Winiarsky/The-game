from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .dice import D20RollInput, D20RollResult, resolve_d20_roll


class ContestOutcome(StrEnum):
    INITIATOR_WINS = "initiator_wins"
    DEFENDER_WINS = "defender_wins"
    TIE = "tie"


@dataclass(frozen=True, slots=True)
class ContestantRollInput:
    actor_id: str
    label: str
    roll: D20RollInput


@dataclass(frozen=True, slots=True)
class ContestantRoll:
    actor_id: str
    label: str
    roll: D20RollResult


@dataclass(frozen=True, slots=True)
class ContestResult:
    initiator: ContestantRoll
    defender: ContestantRoll
    outcome: ContestOutcome

    @property
    def winner_actor_id(self) -> str | None:
        if self.outcome == ContestOutcome.INITIATOR_WINS:
            return self.initiator.actor_id
        if self.outcome == ContestOutcome.DEFENDER_WINS:
            return self.defender.actor_id
        return None


def resolve_contest(
    initiator: ContestantRollInput,
    defender: ContestantRollInput,
) -> ContestResult:
    if not initiator.actor_id or not defender.actor_id:
        raise ValueError("Contest actors require stable ids.")
    if initiator.actor_id == defender.actor_id:
        raise ValueError("An actor cannot contest itself.")
    initiator_roll = ContestantRoll(
        initiator.actor_id,
        initiator.label,
        resolve_d20_roll(initiator.roll),
    )
    defender_roll = ContestantRoll(
        defender.actor_id,
        defender.label,
        resolve_d20_roll(defender.roll),
    )
    if initiator_roll.roll.total > defender_roll.roll.total:
        outcome = ContestOutcome.INITIATOR_WINS
    elif defender_roll.roll.total > initiator_roll.roll.total:
        outcome = ContestOutcome.DEFENDER_WINS
    else:
        outcome = ContestOutcome.TIE
    return ContestResult(initiator_roll, defender_roll, outcome)
