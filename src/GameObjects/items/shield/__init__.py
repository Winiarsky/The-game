from __future__ import annotations

from .base_shield import BaseShield, ShieldBlockOutcome
from .standard_shield import StandardShield


def get_equipped_shield(actor, *, create_default: bool = False) -> BaseShield | None:
    if actor is None:
        return None

    equipped = getattr(actor, "equipped_shield", None)
    if isinstance(equipped, BaseShield):
        return equipped

    if create_default:
        shield = StandardShield()
        try:
            setattr(actor, "equipped_shield", shield)
        except Exception:
            pass
        return shield

    raw_hardness = getattr(actor, "shield_hardness", None)
    if raw_hardness is None:
        return None
    try:
        hardness = max(0, int(raw_hardness))
        max_hp = max(1, int(getattr(actor, "shield_hp", 20) or 20))
        bt = max(1, min(int(getattr(actor, "shield_bt", max_hp // 2) or (max_hp // 2)), max_hp))
    except Exception:
        return None
    shield = BaseShield(
        item_id="fallback_shield",
        name="Fallback Shield",
        hardness=hardness,
        max_hp=max_hp,
        broken_threshold=bt,
    )
    try:
        setattr(actor, "equipped_shield", shield)
    except Exception:
        pass
    return shield


def ensure_standard_shield(actor) -> BaseShield | None:
    if actor is None:
        return None
    shield = get_equipped_shield(actor, create_default=False)
    if shield is not None:
        return shield
    try:
        shield = StandardShield()
        setattr(actor, "equipped_shield", shield)
        return shield
    except Exception:
        return None


__all__ = [
    "BaseShield",
    "ShieldBlockOutcome",
    "StandardShield",
    "get_equipped_shield",
    "ensure_standard_shield",
]
