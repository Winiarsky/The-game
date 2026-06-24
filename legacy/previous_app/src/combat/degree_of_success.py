from __future__ import annotations

from typing import Literal


DegreeOutcome = Literal["critical_success", "success", "failure", "critical_failure"]


def clamp_natural_shift(value: int | None) -> int:
    try:
        parsed = int(value or 0)
    except Exception:
        parsed = 0
    if parsed > 0:
        return 1
    if parsed < 0:
        return -1
    return 0


def natural_shift_from_mode(mode: object) -> int:
    raw = str(mode or "").strip().lower()
    if raw in {"nat20", "natural20", "20", "critical_success", "crit_success"}:
        return 1
    if raw in {"nat1", "natural1", "1", "critical_failure", "crit_failure"}:
        return -1
    return 0


def natural_mode_from_shift(shift: int) -> str:
    if int(shift) > 0:
        return "nat20"
    if int(shift) < 0:
        return "nat1"
    return "none"


def natural_shift_from_roll(roll: int | None) -> int:
    try:
        value = int(roll or 0)
    except Exception:
        return 0
    if value == 20:
        return 1
    if value == 1:
        return -1
    return 0


def degree_from_total(total: int, dc: int) -> int:
    if total >= dc + 10:
        return 3
    if total >= dc:
        return 2
    if total <= dc - 10:
        return 0
    return 1


def outcome_from_degree(degree: int) -> DegreeOutcome:
    mapping: dict[int, DegreeOutcome] = {
        3: "critical_success",
        2: "success",
        1: "failure",
        0: "critical_failure",
    }
    return mapping[max(0, min(3, int(degree)))]


def resolve_outcome(total: int, dc: int, *, natural_shift: int = 0) -> DegreeOutcome:
    degree = degree_from_total(int(total), int(dc))
    shifted = max(0, min(3, degree + clamp_natural_shift(natural_shift)))
    return outcome_from_degree(shifted)


def is_hit(outcome: DegreeOutcome) -> bool:
    return outcome in {"success", "critical_success"}


def is_critical_success(outcome: DegreeOutcome) -> bool:
    return outcome == "critical_success"


__all__ = [
    "DegreeOutcome",
    "clamp_natural_shift",
    "natural_shift_from_mode",
    "natural_mode_from_shift",
    "natural_shift_from_roll",
    "degree_from_total",
    "outcome_from_degree",
    "resolve_outcome",
    "is_hit",
    "is_critical_success",
]
