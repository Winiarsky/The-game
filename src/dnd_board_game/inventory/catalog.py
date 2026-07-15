"""Data-driven item definitions and concrete item instances."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


def _validated_ids(values: tuple[str, ...], field: str) -> tuple[str, ...]:
    normalized = tuple(value.strip() for value in values)
    if any(not value for value in normalized):
        raise ValueError(f"{field} cannot contain empty ids.")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field} cannot contain duplicate ids.")
    return normalized


class ItemCollectionDestination(StrEnum):
    """Engine-owned destination used when a scene item is explicitly collected."""

    ACTOR_INVENTORY = "actor_inventory"
    PARTY_TREASURE = "party_treasure"
    SCENARIO_QUEST = "scenario_quest"


@dataclass(frozen=True, slots=True)
class ItemPropertyDefinition:
    id: str
    label: str
    description: str = ""

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Item property id cannot be empty.")
        if not self.label.strip():
            raise ValueError("Item property label cannot be empty.")


@dataclass(frozen=True, slots=True)
class ItemPropertyCatalog:
    schema_version: int
    properties: tuple[ItemPropertyDefinition, ...]

    def __post_init__(self) -> None:
        if self.schema_version < 1:
            raise ValueError("Item property catalog schema_version must be positive.")
        ids = tuple(item.id for item in self.properties)
        _validated_ids(ids, "Item property catalog")

    @property
    def known_ids(self) -> frozenset[str]:
        return frozenset(item.id for item in self.properties)

    def validate(self, properties: tuple[str, ...], field: str = "properties") -> None:
        normalized = _validated_ids(properties, field)
        unknown = set(normalized) - self.known_ids
        if unknown:
            raise ValueError(f"{field} contains unknown item properties: {', '.join(sorted(unknown))}.")


@dataclass(frozen=True, slots=True)
class ItemDefinition:
    id: str
    name: str
    kind: str
    description: str = ""
    properties: tuple[str, ...] = ()
    portable: bool = True
    default_weight_lb: float | None = None
    collection_destination: ItemCollectionDestination = ItemCollectionDestination.ACTOR_INVENTORY

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Item definition id cannot be empty.")
        if not self.name.strip():
            raise ValueError("Item definition name cannot be empty.")
        if not self.kind.strip():
            raise ValueError("Item definition kind cannot be empty.")
        _validated_ids(self.properties, f"Item definition {self.id}.properties")
        if self.default_weight_lb is not None and self.default_weight_lb < 0:
            raise ValueError("Item definition default_weight_lb cannot be negative.")


@dataclass(frozen=True, slots=True)
class ItemInstance:
    id: str
    definition: ItemDefinition
    quantity: int = 1
    condition: str = "normal"
    added_properties: tuple[str, ...] = ()
    removed_properties: tuple[str, ...] = ()
    owner_id: str | None = None
    visible: bool = True
    available: bool = True

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Item instance id cannot be empty.")
        if self.quantity < 0:
            raise ValueError("Item instance quantity cannot be negative.")
        if not self.condition.strip():
            raise ValueError("Item instance condition cannot be empty.")
        added = _validated_ids(self.added_properties, f"Item instance {self.id}.added_properties")
        removed = _validated_ids(self.removed_properties, f"Item instance {self.id}.removed_properties")
        overlap = set(added) & set(removed)
        if overlap:
            raise ValueError(
                f"Item instance {self.id} cannot add and remove the same properties: "
                f"{', '.join(sorted(overlap))}."
            )

    @property
    def definition_id(self) -> str:
        return self.definition.id

    @property
    def properties(self) -> frozenset[str]:
        return (frozenset(self.definition.properties) | frozenset(self.added_properties)) - frozenset(
            self.removed_properties
        )

    @property
    def usable(self) -> bool:
        return self.available and self.quantity > 0


__all__ = [
    "ItemDefinition",
    "ItemCollectionDestination",
    "ItemInstance",
    "ItemPropertyCatalog",
    "ItemPropertyDefinition",
]
