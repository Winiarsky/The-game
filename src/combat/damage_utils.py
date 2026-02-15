from __future__ import annotations

from typing import Any, Iterable, Optional, Sequence, Tuple

from statuses import Status
from ui_client import get_ui_client


def _status_list(target: Any) -> Iterable[Status]:
    statuses = getattr(target, "statuses", None)
    if not isinstance(statuses, list):
        return []
    result: list[Status] = []
    for status in statuses:
        if isinstance(status, Status):
            result.append(status)
    return result


def _compute_resistance_value(target: Any, raw_val: object) -> Optional[int]:
    if isinstance(raw_val, (int, float)):
        return int(raw_val)
    if isinstance(raw_val, dict):
        if "value" in raw_val:
            try:
                return int(raw_val.get("value"))
            except Exception:
                return None
        if "per_2_levels" in raw_val:
            try:
                per_2 = int(raw_val.get("per_2_levels", 0))
            except Exception:
                per_2 = 0
            level = getattr(target, "level", 1) or 1
            try:
                level = int(level)
            except Exception:
                level = 1
            reduction = max(1, (level + 1) // 2) * per_2 if per_2 else 0
            try:
                minimum = int(raw_val.get("minimum", 0))
            except Exception:
                minimum = 0
            return max(minimum, reduction)
    return None


def damage_resistance_info(target: Any, damage_type: str) -> Tuple[int, Optional[str]]:
    """Zwraca (redukcja, źródło) dla obrażeń danego typu."""
    best = 0
    best_label: Optional[str] = None
    for status in _status_list(target):
        res_map = status.data.get("damage_resistance")
        if not isinstance(res_map, dict):
            continue
        val = _compute_resistance_value(target, res_map.get(damage_type))
        if isinstance(val, int) and val > best:
            best = val
            best_label = status.display_label
    return best, best_label


def damage_resistance(target: Any, damage_type: str) -> int:
    """Maksymalna redukcja obrażeń danego typu wynikająca ze statusów."""
    best, _ = damage_resistance_info(target, damage_type)
    return best


def apply_damage_resistance(target: Any, amount: int, damage_type: str) -> tuple[int, int]:
    """Zwraca (obrażenia_po_redukcji, zredukowano_o)."""
    reduction = damage_resistance(target, damage_type)
    effective = max(0, int(amount) - reduction)
    return effective, reduction


def format_damage_prompt(target: Any, components: Sequence[tuple[str, int]]) -> str:
    """Zbuduj opis obrażeń po redukcjach dla promptu/UI."""
    parts: list[str] = []
    notes: list[str] = []
    for idx, (dmg_type, amount) in enumerate(components):
        reduction, source = damage_resistance_info(target, dmg_type)
        effective = max(0, int(amount) - reduction)
        if idx == 0:
            parts.append(f"obrazenia {dmg_type} {effective}")
        else:
            parts.append(f"i od {dmg_type} {effective}")
        if reduction:
            src_label = source or "status"
            notes.append(f"-{reduction} za odpornosc z {src_label}")
    notes_text = f" ({'; '.join(notes)})" if notes else ""
    return " ".join(parts) + notes_text


def prompt_damage_summary(target: Any, components: Sequence[tuple[str, int]]) -> str:
    """Wyślij prompt informacyjny z obrażeniami po redukcjach."""
    summary = format_damage_prompt(target, components)
    try:
        get_ui_client().prompt_info(
            "Obrazenia",
            prompt_long=summary,
            source="damage",
        )
    except Exception:
        pass
    return summary
