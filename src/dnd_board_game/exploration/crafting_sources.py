"""Unified read-only view of components available during exploration."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from dnd_board_game.actors import Actor, Faction
from dnd_board_game.inventory import ItemCollectionDestination

from .models import CraftingComponentDisposition, ExplorationState


class CraftingSourceKind(StrEnum):
    SCENE_ITEM = "scene_item"
    SCENE_FIXTURE = "scene_fixture"
    EXPLORATION_RESOURCE = "exploration_resource"
    ACTOR_INVENTORY = "actor_inventory"
    TEMPORARY_ITEM = "temporary_item"


@dataclass(frozen=True, slots=True)
class CraftingSource:
    id: str
    reference_id: str
    kind: CraftingSourceKind
    label: str
    properties: tuple[str, ...]
    quantity: int = 1
    condition: str = "normal"
    zone_id: str | None = None
    owner_actor_id: str | None = None
    definition_id: str | None = None
    visible: bool = True
    available: bool = True
    portable: bool = True
    detachable: bool = False
    destructible: bool = False
    consumed_on_use: bool = False
    description: str = ""
    item_kind: str = "item"
    collection_destination: ItemCollectionDestination | None = None

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.reference_id.strip():
            raise ValueError("Crafting source ids cannot be empty.")
        if not self.label.strip():
            raise ValueError("Crafting source label cannot be empty.")
        if self.quantity < 0:
            raise ValueError("Crafting source quantity cannot be negative.")
        if len(self.properties) != len(set(self.properties)):
            raise ValueError(f"Crafting source {self.id}.properties cannot contain duplicate ids.")

    @property
    def usable(self) -> bool:
        return self.visible and self.available and self.quantity > 0


@dataclass(frozen=True, slots=True)
class CraftingSourceRegistry:
    sources: tuple[CraftingSource, ...]

    def __post_init__(self) -> None:
        ids = tuple(source.id for source in self.sources)
        if len(ids) != len(set(ids)):
            raise ValueError("Crafting source registry cannot contain duplicate ids.")

    @property
    def available_sources(self) -> tuple[CraftingSource, ...]:
        return tuple(source for source in self.sources if source.usable)

    def source_by_id(self, source_id: str) -> CraftingSource | None:
        return next((source for source in self.sources if source.id == source_id), None)

    def matching_properties(self, required_properties: tuple[str, ...]) -> tuple[CraftingSource, ...]:
        required = set(required_properties)
        return tuple(
            source
            for source in self.available_sources
            if required.issubset(source.properties)
        )


def build_crafting_source_registry(
    state: ExplorationState,
    actors: tuple[Actor, ...],
    *,
    zone_id: str | None = None,
) -> CraftingSourceRegistry:
    active_zone_id = zone_id or state.party_position.zone_id
    zone = next((candidate for candidate in state.zones if candidate.id == active_zone_id), None)
    if zone is None:
        raise ValueError(f"Unknown exploration zone for crafting sources: {active_zone_id}.")

    sources: list[CraftingSource] = []
    for item in zone.item_instances:
        sources.append(
            CraftingSource(
                id=f"zone:{zone.id}:item:{item.id}",
                reference_id=item.id,
                kind=CraftingSourceKind.SCENE_ITEM,
                label=item.definition.name,
                properties=tuple(sorted(item.properties)),
                quantity=item.quantity,
                condition=item.condition,
                zone_id=zone.id,
                definition_id=item.definition_id,
                visible=item.visible,
                available=item.available,
                portable=item.definition.portable,
                description=item.definition.description,
                item_kind=item.definition.kind,
                collection_destination=item.definition.collection_destination,
            )
        )
    for fixture in zone.fixtures:
        runtime = next(
            (
                item
                for item in state.fixture_states
                if item.zone_id == zone.id and item.fixture_id == fixture.id
            ),
            None,
        )
        fixture_available = not (
            runtime is not None
            and (runtime.unavailable or runtime.detached or runtime.destroyed)
        )
        sources.append(
            CraftingSource(
                id=f"zone:{zone.id}:fixture:{fixture.id}",
                reference_id=fixture.id,
                kind=CraftingSourceKind.SCENE_FIXTURE,
                label=fixture.name,
                properties=fixture.properties,
                condition=runtime.condition if runtime is not None else fixture.condition,
                zone_id=zone.id,
                visible=fixture.visible,
                available=fixture_available,
                portable=fixture.portable,
                detachable=fixture.detachable,
                destructible=fixture.destructible,
                description=fixture.description,
            )
        )
        released_item_ids = set(runtime.released_item_ids) if runtime is not None else set()
        for item in fixture.yield_items:
            released = item.id in released_item_ids
            sources.append(
                CraftingSource(
                    id=f"zone:{zone.id}:item:{item.id}",
                    reference_id=item.id,
                    kind=CraftingSourceKind.SCENE_ITEM,
                    label=item.definition.name,
                    properties=tuple(sorted(item.properties)),
                    quantity=item.quantity,
                    condition=item.condition,
                    zone_id=zone.id,
                    definition_id=item.definition_id,
                    visible=item.visible or released,
                    available=item.available or released,
                    portable=item.definition.portable,
                    description=item.definition.description,
                    item_kind=item.definition.kind,
                    collection_destination=item.definition.collection_destination,
                )
            )

    owned_resource_ids = set(state.inventory_resource_ids)
    for resource in state.resources:
        if resource.id not in owned_resource_ids:
            continue
        sources.append(
            CraftingSource(
                id=f"resource:{resource.id}",
                reference_id=resource.id,
                kind=CraftingSourceKind.EXPLORATION_RESOURCE,
                label=resource.label,
                properties=resource.properties,
                portable=resource.portable,
                consumed_on_use=resource.consume_on_use,
                item_kind="resource",
            )
        )

    for item in state.temporary_items:
        if not item.available:
            continue
        sources.append(
            CraftingSource(
                id=f"temporary:{item.id}",
                reference_id=item.id,
                kind=CraftingSourceKind.TEMPORARY_ITEM,
                label=item.label,
                properties=item.bonus_tags,
                quantity=1,
                condition="improvised",
                zone_id=item.created_in_zone_id,
                portable=True,
                description=item.description,
                item_kind="temporary_item",
                collection_destination=ItemCollectionDestination.ACTOR_INVENTORY,
            )
        )

    for actor in actors:
        if actor.faction != Faction.ALLY:
            continue
        for item in actor.inventory:
            sources.append(
                CraftingSource(
                    id=f"actor:{actor.id}:item:{item.id}",
                    reference_id=item.id,
                    kind=CraftingSourceKind.ACTOR_INVENTORY,
                    label=item.name,
                    properties=item.properties,
                    quantity=item.quantity,
                    owner_actor_id=str(actor.id),
                    definition_id=item.source_ref or item.id,
                    available=item.available,
                    portable=item.portable,
                    description=item.description,
                    item_kind=item.kind,
                    collection_destination=ItemCollectionDestination.ACTOR_INVENTORY,
                )
            )
    return CraftingSourceRegistry(_apply_existing_component_allocations(tuple(sources), state))


def _apply_existing_component_allocations(
    sources: tuple[CraftingSource, ...],
    state: ExplorationState,
) -> tuple[CraftingSource, ...]:
    unavailable_quantities: dict[str, int] = {}
    for collection in state.source_collections:
        unavailable_quantities[collection.source_id] = (
            unavailable_quantities.get(collection.source_id, 0) + collection.quantity
        )
    for item in state.temporary_items:
        for component in item.component_uses:
            remains_allocated = (
                component.disposition == CraftingComponentDisposition.CONSUMED
                or not item.dismantled
            )
            if remains_allocated:
                unavailable_quantities[component.source_id] = (
                    unavailable_quantities.get(component.source_id, 0) + component.quantity
                )
    result: list[CraftingSource] = []
    for source in sources:
        remaining = max(0, source.quantity - unavailable_quantities.get(source.id, 0))
        result.append(
            replace(
                source,
                quantity=remaining,
                available=source.available and remaining > 0,
            )
        )
    return tuple(result)


__all__ = [
    "CraftingSource",
    "CraftingSourceKind",
    "CraftingSourceRegistry",
    "build_crafting_source_registry",
]
