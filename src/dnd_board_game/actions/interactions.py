from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .base import ActionResource, CombatActionMechanic, MechanicScope, TargetingMode


@dataclass(frozen=True, slots=True)
class SceneInteractionMechanic(CombatActionMechanic):
    pass


@dataclass(frozen=True, slots=True)
class ObjectInteraction(SceneInteractionMechanic):
    pass


def object_interaction_mechanic(interaction: Any, object_name: str = "Obiekt sceny") -> ObjectInteraction:
    interaction_id = str(getattr(interaction, "id", "") or "object_interaction")
    label = str(getattr(interaction, "label", "") or f"Interakcja: {object_name}")
    conditions = tuple(str(condition) for condition in getattr(interaction, "conditions", ()) or ())
    return ObjectInteraction(
        id=f"interaction.{interaction_id}",
        name=label,
        scope=MechanicScope.COMBAT,
        resource=ActionResource.ACTION,
        targeting=TargetingMode.OBJECT,
        summary="Interakcja sceny jest data-driven: warunki i efekty pochodzą z contentu obiektu.",
        tags=("scene_object", "interaction", *conditions),
    )
