from __future__ import annotations

from .base_shield import BaseShield, ShieldBlockOutcome
from .basic_shields import (
    BucklerShield,
    SteelShield,
    TowerShield,
    WoodenShield,
    create_shield,
    list_shield_ids,
    normalize_shield_id,
    shield_profile,
)
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


def has_raised_tower_shield_cover(actor) -> bool:
    """Czy aktor ma aktywną osłonę z podniesionej tarczy wieżowej."""
    shield = get_equipped_shield(actor, create_default=False)
    if shield is None:
        return False
    if bool(getattr(shield, "is_destroyed", False)):
        return False
    traits = {str(item or "").strip().lower() for item in (getattr(shield, "traits", ()) or ())}
    if "tower_shield" not in traits:
        return False
    bonuses = getattr(actor, "bonuses", None)
    if not isinstance(bonuses, list):
        return False
    for effect in bonuses:
        source = str(getattr(effect, "source", "") or "")
        if source.startswith("raise_shield:"):
            return True
    return False


def tower_shield_cover_owner_key(actor) -> str:
    """Stabilny klucz aktora używany jako source efektów osłony z tarczy wieżowej."""
    raw = str(getattr(actor, "object_id", "") or "").strip()
    if raw:
        return f"actor:{raw}"
    return f"obj:{id(actor)}"


__all__ = [
    "BaseShield",
    "ShieldBlockOutcome",
    "BucklerShield",
    "WoodenShield",
    "SteelShield",
    "StandardShield",
    "TowerShield",
    "create_shield",
    "list_shield_ids",
    "normalize_shield_id",
    "shield_profile",
    "get_equipped_shield",
    "ensure_standard_shield",
    "has_raised_tower_shield_cover",
    "tower_shield_cover_owner_key",
]
