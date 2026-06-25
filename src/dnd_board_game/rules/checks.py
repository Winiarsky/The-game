from __future__ import annotations

from dataclasses import dataclass

from .dice import D20RollResult


@dataclass(frozen=True, slots=True)
class CheckResult:
    roll: D20RollResult
    dc: int
    success: bool


def resolve_ability_check(roll: D20RollResult, dc: int) -> CheckResult:
    _validate_dc(dc)
    return CheckResult(roll=roll, dc=dc, success=roll.total >= dc)


def resolve_saving_throw(roll: D20RollResult, dc: int) -> CheckResult:
    _validate_dc(dc)
    return CheckResult(roll=roll, dc=dc, success=roll.total >= dc)


def _validate_dc(dc: int) -> None:
    if dc < 0:
        raise ValueError("DC cannot be negative.")
