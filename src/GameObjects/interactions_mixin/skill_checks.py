from combat.degree_of_success import resolve_outcome


def resolve_skill_check(dc: int, roll: int, natural_shift: int = 0) -> str:
    """Zwraca outcome: critical_success, success, failure, critical_failure."""
    return resolve_outcome(roll, dc, natural_shift=natural_shift)
