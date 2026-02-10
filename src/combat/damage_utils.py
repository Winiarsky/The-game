from __future__ import annotations

from typing import Any, Iterable

from statuses import Status


def _status_list(target: Any) -> Iterable[Status]:
    statuses = getattr(target, "statuses", None)
    if not isinstance(statuses, list):
        return []
    result: list[Status] = []
    for status in statuses:
        if isinstance(status, Status):
            result.append(status)
    return result


def damage_resistance(target: Any, damage_type: str) -> int:
    """Maksymalna redukcja obrażeń danego typu wynikająca ze statusów."""
    best = 0
    for status in _status_list(target):
        res_map = status.data.get("damage_resistance")
        if not isinstance(res_map, dict):
            continue
        val = res_map.get(damage_type)
        if isinstance(val, (int, float)):
            best = max(best, int(val))
    return best


def apply_damage_resistance(target: Any, amount: int, damage_type: str) -> tuple[int, int]:
    """Zwraca (obrażenia_po_redukcji, zredukowano_o)."""
    reduction = damage_resistance(target, damage_type)
    effective = max(0, int(amount) - reduction)
    return effective, reduction
