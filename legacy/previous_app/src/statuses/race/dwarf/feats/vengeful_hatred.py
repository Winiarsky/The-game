from __future__ import annotations

from dataclasses import replace
from typing import Any

from statuses.base import Status

VENGEFUL_HATRED_DESCRIPTION = (
    "Wybierz wroga rodowego (np. orc). Dostajesz +1 do obrażeń za każdą kość broni/unarmed "
    "przeciw temu typowi.\n"
    "Jeśli przeciwnik krytycznie cię trafi i zada obrażenia, dostajesz ten sam bonus przeciw niemu "
    "przez 10 rund.\n"
    "Przykład: atak 2k8 przeciw orcowi -> +2 obrażeń."
)


def _normalize_enemy_type(value: Any) -> str:
    raw = getattr(value, "value", value)
    return str(raw or "").strip().lower()


def _target_id(target) -> str:
    return str(getattr(target, "object_id", "") or getattr(target, "name", "") or id(target)).strip()


def _find_status_with_index(actor) -> tuple[int | None, Status | None]:
    statuses = getattr(actor, "statuses", None) or []
    for idx, status in enumerate(statuses):
        if getattr(status, "id", None) == "vengeful_hatred":
            return idx, status
    return None, None


def _active_revenge_targets(data: dict[str, Any]) -> dict[str, int]:
    raw = data.get("revenge_targets") or {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, int] = {}
    for key, value in raw.items():
        try:
            rounds = int(value)
        except Exception:
            rounds = 0
        if rounds > 0:
            out[str(key)] = rounds
    return out


def vengeful_hatred_damage_bonus(attacker, target, *, weapon_dice: int = 1) -> int:
    """Zwróć automatyczny bonus do obrażeń wynikający z Vengeful Hatred."""
    _idx, status = _find_status_with_index(attacker)
    if status is None or target is None:
        return 0
    data = getattr(status, "data", None) or {}
    chosen_type = _normalize_enemy_type(data.get("enemy_type"))
    target_type = _normalize_enemy_type(getattr(target, "enemy_type", None))
    target_id = _target_id(target)
    revenge_targets = _active_revenge_targets(data)

    type_match = bool(chosen_type and target_type and chosen_type == target_type)
    revenge_match = target_id in revenge_targets
    if not (type_match or revenge_match):
        return 0

    per_die = int(data.get("damage_bonus_per_die", data.get("damage_bonus", 1)) or 1)
    dice = max(1, int(weapon_dice or 1))
    return max(0, per_die) * dice


def grant_vengeful_hatred_revenge(defender, attacker, *, rounds: int = 10) -> bool:
    """Aktywuj 10-rundowy bonus odwetu przeciw konkretnemu napastnikowi."""
    idx, status = _find_status_with_index(defender)
    if status is None or attacker is None or idx is None:
        return False
    statuses = getattr(defender, "statuses", None)
    if not isinstance(statuses, list):
        return False
    data = dict(getattr(status, "data", None) or {})
    revenge_targets = _active_revenge_targets(data)
    target_id = _target_id(attacker)
    revenge_targets[target_id] = max(int(rounds), int(revenge_targets.get(target_id, 0)))
    data["revenge_targets"] = revenge_targets
    statuses[idx] = replace(status, data=data)
    return True


def tick_vengeful_hatred_rounds(actor) -> None:
    """Zmniejsz licznik rund bonusu odwetu i usuń wygasłe wpisy."""
    idx, status = _find_status_with_index(actor)
    if status is None or idx is None:
        return
    statuses = getattr(actor, "statuses", None)
    if not isinstance(statuses, list):
        return
    data = dict(getattr(status, "data", None) or {})
    revenge_targets = _active_revenge_targets(data)
    if not revenge_targets:
        return
    updated: dict[str, int] = {}
    for target_id, turns in revenge_targets.items():
        left = int(turns) - 1
        if left > 0:
            updated[target_id] = left
    data["revenge_targets"] = updated
    statuses[idx] = replace(status, data=data)


def VengefulHatredStatus(enemy_type: Any) -> Status:
    """Feat: Vengeful Hatred."""
    return Status(
        id="vengeful_hatred",
        label="Vengeful Hatred",
        data={
            "ui_description": VENGEFUL_HATRED_DESCRIPTION,
            "enemy_type": enemy_type,
            "damage_bonus_per_die": 1,
            "revenge_targets": {},
            "revenge_duration_rounds": 10,
        },
    )


__all__ = [
    "VengefulHatredStatus",
    "VENGEFUL_HATRED_DESCRIPTION",
    "vengeful_hatred_damage_bonus",
    "grant_vengeful_hatred_revenge",
    "tick_vengeful_hatred_rounds",
]
