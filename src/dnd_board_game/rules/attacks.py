from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .dice import D20RollResult


class AttackRollOutcome(StrEnum):
    CRITICAL_HIT = "critical_hit"
    HIT = "hit"
    MISS = "miss"
    CRITICAL_MISS = "critical_miss"


@dataclass(frozen=True, slots=True)
class AttackRollResult:
    roll: D20RollResult
    target_ac: int
    outcome: AttackRollOutcome

    @property
    def hits(self) -> bool:
        return self.outcome in {AttackRollOutcome.CRITICAL_HIT, AttackRollOutcome.HIT}


def resolve_attack_roll(roll: D20RollResult, target_ac: int) -> AttackRollResult:
    if target_ac < 0:
        raise ValueError("Target AC cannot be negative.")
    if roll.is_natural_20:
        outcome = AttackRollOutcome.CRITICAL_HIT
    elif roll.is_natural_1:
        outcome = AttackRollOutcome.CRITICAL_MISS
    elif roll.total >= target_ac:
        outcome = AttackRollOutcome.HIT
    else:
        outcome = AttackRollOutcome.MISS
    return AttackRollResult(roll=roll, target_ac=target_ac, outcome=outcome)
