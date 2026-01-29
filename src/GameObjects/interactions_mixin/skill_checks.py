def resolve_skill_check(dc: int, roll: int) -> str:
    """Zwraca outcome: critical_success, success, failure, critical_failure."""
    if roll >= dc + 10:
        return "critical_success"
    if roll >= dc:
        return "success"
    if roll <= dc - 10:
        return "critical_failure"
    return "failure"
