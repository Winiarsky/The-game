from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from damage_types import DamageType
from GameObjects.items.shield import get_equipped_shield

from .base import Reaction

_PHYSICAL_DAMAGE_TYPES = {
    DamageType.NORMAL.value,
    DamageType.SLASHING.value,
    DamageType.PIERCING.value,
    DamageType.BLUDGEONING.value,
}


def _has_status(actor, status_id: str) -> bool:
    if actor is None:
        return False
    checker = getattr(actor, "has_status", None)
    if callable(checker):
        try:
            return bool(checker(status_id))
        except Exception:
            return False
    for status in getattr(actor, "statuses", []) or []:
        if getattr(status, "id", status) == status_id:
            return True
    return False


def _has_raised_shield(actor) -> bool:
    bonuses = getattr(actor, "bonuses", None)
    if not isinstance(bonuses, list):
        return False
    for effect in bonuses:
        source = str(getattr(effect, "source", "") or "")
        if source.startswith("raise_shield:"):
            return True
    return False


def _event_damage(event: dict[str, Any]) -> int:
    raw = event.get("damage")
    try:
        return max(0, int(raw))
    except Exception:
        return 0


def _blockable_physical_damage(event: dict[str, Any]) -> int:
    components = event.get("damage_components") or []
    if isinstance(components, list) and components:
        total = 0
        for comp in components:
            if not isinstance(comp, (list, tuple)) or len(comp) < 2:
                continue
            dtype = str(comp[0] or "").strip().lower()
            if dtype not in _PHYSICAL_DAMAGE_TYPES:
                continue
            try:
                total += max(0, int(comp[1]))
            except Exception:
                continue
        return max(0, int(total))

    dtype = str(event.get("damage_type") or DamageType.NORMAL.value).strip().lower()
    if dtype not in _PHYSICAL_DAMAGE_TYPES:
        return 0
    return _event_damage(event)


def _heal_prevented_damage(target, amount: int) -> None:
    if target is None or amount <= 0:
        return
    healer = getattr(target, "heal", None)
    if callable(healer):
        try:
            healer(amount)
            return
        except Exception:
            pass
    try:
        wounds = int(getattr(target, "wounds", 0) or 0)
        setattr(target, "wounds", max(0, wounds - int(amount)))
    except Exception:
        pass


@dataclass
class ShieldBlockReaction(Reaction):
    id: str = "shield_block"
    label: str = "Shield Block"
    priority: int = 35
    action_cost: int = 1
    requires_reach: bool = False
    blocks_range_attacker: bool = False

    def triggers(self, actor, event: dict[str, Any]) -> bool:
        if actor is None:
            return False
        if not _has_status(actor, "shield_block"):
            return False
        target = event.get("target")
        if target is None or target is not actor:
            return False
        if not _has_raised_shield(actor):
            return False
        blockable = _blockable_physical_damage(event)
        if blockable <= 0:
            return False
        shield = get_equipped_shield(actor, create_default=False)
        if shield is None:
            return False
        return bool(getattr(shield, "can_block", False))

    def reason(self, actor, event: dict[str, Any]) -> str:
        shield = get_equipped_shield(actor, create_default=False)
        shield_name = getattr(shield, "name", "tarcza")
        return f"blok obrazen ({shield_name})"

    def execute(self, actor, event: dict[str, Any], ctx) -> bool:
        shield = get_equipped_shield(actor, create_default=False)
        if shield is None:
            return False
        blockable = _blockable_physical_damage(event)
        if blockable <= 0:
            return False
        apply_block = getattr(shield, "apply_shield_block", None)
        if not callable(apply_block):
            return False
        result = apply_block(blockable)
        blocked = int(getattr(result, "blocked_damage", 0) or 0)
        if blocked <= 0:
            return False

        _heal_prevented_damage(actor, blocked)
        game = ctx.game
        try:
            game.ui_log(
                f"Shield Block: redukujesz obrazenia o {blocked} "
                f"(Hardness {getattr(shield, 'hardness', 0)})."
            )
        except Exception:
            pass
        shield_damage = int(getattr(result, "damage_to_shield", 0) or 0)
        hp_after = int(getattr(result, "shield_hp_after", getattr(shield, "current_hp", 0)) or 0)
        hp_max = int(getattr(shield, "max_hp", hp_after) or hp_after)
        if shield_damage > 0:
            try:
                game.ui_log(
                    f"{getattr(shield, 'name', 'Tarcza')} otrzymuje {shield_damage} obrazen "
                    f"({hp_after}/{hp_max} HP)."
                )
            except Exception:
                pass
        if bool(getattr(result, "became_broken", False)):
            try:
                game.ui_log(f"{getattr(shield, 'name', 'Tarcza')} jest BROKEN.")
            except Exception:
                pass
        if bool(getattr(result, "became_destroyed", False)):
            try:
                game.ui_log(f"{getattr(shield, 'name', 'Tarcza')} zostala ZNISZCZONA.")
            except Exception:
                pass
        return True
