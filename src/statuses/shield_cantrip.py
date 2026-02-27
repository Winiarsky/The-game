from __future__ import annotations

from bonuses import BonusEffect, BonusType
from .base import Status


def ShieldCantripStatus(*, value: int = 5, duration: int | None = 1) -> Status:
    absorb = max(0, int(value))
    return Status(
        id="shield_cantrip",
        label="Shield Cantrip",
        duration=duration,
        data={"shield_remaining_absorb": absorb},
    )


def apply_shield_cantrip_absorb(actor, damage: int) -> tuple[int, int, bool]:
    if damage <= 0:
        return 0, 0, False
    statuses = getattr(actor, "statuses", None)
    if not isinstance(statuses, list) or not statuses:
        return int(damage), 0, False
    shield = None
    for status in statuses:
        if getattr(status, "id", None) == "shield_cantrip":
            shield = status
            break
    if shield is None:
        return int(damage), 0, False
    data = getattr(shield, "data", None) or {}
    try:
        remaining = max(0, int(data.get("shield_remaining_absorb", 0)))
    except Exception:
        remaining = 0
    absorbed = min(remaining, int(damage))
    remaining -= absorbed
    damage_after = int(damage) - absorbed
    broken = remaining <= 0
    if broken:
        remover = getattr(actor, "remove_status", None)
        if callable(remover):
            try:
                remover("shield_cantrip")
            except Exception:
                pass
        remove_bonus = getattr(actor, "remove_bonuses_with_prefix", None)
        if callable(remove_bonus):
            try:
                remove_bonus("shield_cantrip:")
            except Exception:
                pass
    else:
        data["shield_remaining_absorb"] = remaining
    return max(0, damage_after), int(absorbed), bool(broken)


def shield_cantrip_ac_bonus() -> BonusEffect:
    return BonusEffect(
        type=BonusType.STATUS,
        value=1,
        tag="ac",
        source="shield_cantrip:ac",
        label="shield cantrip",
        duration_turns=1,
    )


__all__ = ["ShieldCantripStatus", "apply_shield_cantrip_absorb", "shield_cantrip_ac_bonus"]

