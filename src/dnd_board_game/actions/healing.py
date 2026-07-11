from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .base import ActionResource, CombatActionMechanic, MechanicScope, TargetingMode


@dataclass(frozen=True, slots=True)
class HealingMechanic(CombatActionMechanic):
    pass


@dataclass(frozen=True, slots=True)
class SpellHealing(HealingMechanic):
    pass


@dataclass(frozen=True, slots=True)
class ItemHealing(HealingMechanic):
    pass


@dataclass(frozen=True, slots=True)
class CustomHealing(HealingMechanic):
    pass


def healing_mechanic_from_source(source: Any) -> HealingMechanic:
    source_type = getattr(getattr(source, "source_type", None), "value", str(getattr(source, "source_type", "")))
    source_id = str(getattr(source, "id", "") or getattr(source, "name", "healing")).strip() or "healing"
    name = str(getattr(source, "name", "Leczenie"))
    tags = ["healing"]
    if source_type:
        tags.append(source_type)
    if getattr(source, "spell_level", 0):
        tags.append("spell_slot")
    cls: type[HealingMechanic]
    if source_type == "spell":
        cls = SpellHealing
    elif source_type == "item":
        cls = ItemHealing
    else:
        cls = CustomHealing
    return cls(
        id=f"healing.{source_id}",
        name=name,
        scope=MechanicScope.COMBAT,
        resource=ActionResource.ACTION,
        targeting=TargetingMode.ALLY,
        summary="Leczenie wybiera rannego sojusznika w zasięgu i przywraca HP do limitu max HP.",
        tags=tuple(tags),
    )
