"""Deterministic collection of concrete exploration sources."""

from __future__ import annotations

from dataclasses import dataclass, replace

from dnd_board_game.actors import Actor, Faction
from dnd_board_game.inventory import (
    InventoryItem,
    ItemCollectionDestination,
    add_inventory_item,
)
from dnd_board_game.inventory.economy import carried_weight_lb, carrying_capacity_lb

from .crafting_sources import (
    CraftingSource,
    CraftingSourceKind,
    build_crafting_source_registry,
)
from .models import ExplorationState, SceneSourceCollection


@dataclass(frozen=True, slots=True)
class CollectionPlan:
    source: CraftingSource
    quantity: int
    destination: ItemCollectionDestination
    owner_actor_id: str | None = None

    def as_payload(self) -> dict[str, object]:
        return {
            "source_id": self.source.id,
            "label": self.source.label,
            "kind": self.source.kind.value,
            "quantity": self.quantity,
            "available_quantity": self.source.quantity,
            "condition": self.source.condition,
            "zone_id": self.source.zone_id,
            "destination": self.destination.value,
            "owner_actor_id": self.owner_actor_id,
            "properties": list(self.source.properties),
            "portable": self.source.portable,
            "weight_lb": self.source.weight_lb,
            "value_cp": self.source.value_cp,
        }


@dataclass(frozen=True, slots=True)
class CollectionResult:
    state: ExplorationState
    actors: tuple[Actor, ...]
    collection: SceneSourceCollection
    inventory_item: InventoryItem | None = None


def plan_source_collection(
    source: CraftingSource,
    *,
    quantity: int = 1,
    owner_actor_id: str | None = None,
) -> CollectionPlan:
    """Validate a proposed transfer without changing exploration state."""

    if source.kind == CraftingSourceKind.SCENE_FIXTURE:
        if source.detachable:
            raise ValueError(
                f"{source.label} jest nadal przytwierdzony. Najpierw odłącz go przez /akcja."
            )
        raise ValueError(f"{source.label} jest stałym elementem sceny i nie można go zabrać.")
    if source.kind == CraftingSourceKind.EXPLORATION_RESOURCE:
        raise ValueError(f"{source.label} jest już wspólnym zasobem drużyny.")
    if source.kind == CraftingSourceKind.ACTOR_INVENTORY:
        raise ValueError(f"{source.label} znajduje się już w ekwipunku.")
    if source.kind not in {CraftingSourceKind.SCENE_ITEM, CraftingSourceKind.TEMPORARY_ITEM}:
        raise ValueError("Tego rodzaju elementu nie można przenieść do ekwipunku.")
    if not source.usable:
        raise ValueError(f"{source.label} nie jest już dostępny w tej scenie.")
    if not source.portable:
        raise ValueError(f"{source.label} nie jest przedmiotem przenośnym.")
    if quantity < 1:
        raise ValueError("Liczba zabieranych przedmiotów musi być dodatnia.")
    if quantity > source.quantity:
        raise ValueError(
            f"Dostępna liczba elementów {source.label}: {source.quantity}; wybrano {quantity}."
        )
    destination = source.collection_destination or ItemCollectionDestination.ACTOR_INVENTORY
    if destination == ItemCollectionDestination.ACTOR_INVENTORY and not owner_actor_id:
        raise ValueError("Wybierz bohatera, który zabiera przedmiot.")
    return CollectionPlan(
        source=source,
        quantity=quantity,
        destination=destination,
        owner_actor_id=owner_actor_id if destination == ItemCollectionDestination.ACTOR_INVENTORY else None,
    )


def collect_source(
    state: ExplorationState,
    actors: tuple[Actor, ...],
    plan: CollectionPlan,
) -> CollectionResult:
    """Apply a previously previewed collection against current state."""

    current = build_crafting_source_registry(
        state,
        actors,
        zone_id=plan.source.zone_id,
    ).source_by_id(plan.source.id)
    if current is None:
        raise ValueError("Zabierany element nie istnieje już w tej lokacji.")
    validated = plan_source_collection(
        current,
        quantity=plan.quantity,
        owner_actor_id=plan.owner_actor_id,
    )
    collection = SceneSourceCollection(
        source_id=current.id,
        zone_id=current.zone_id or state.party_position.zone_id,
        quantity=validated.quantity,
        destination=validated.destination.value,
        label=current.label,
        owner_actor_id=validated.owner_actor_id,
    )
    previous = next(
        (
            item
            for item in state.source_collections
            if item.source_id == collection.source_id
            and item.destination == collection.destination
            and item.owner_actor_id == collection.owner_actor_id
        ),
        None,
    )
    remaining = tuple(
        item
        for item in state.source_collections
        if previous is None or item is not previous
    )
    if previous is not None:
        collection = replace(previous, quantity=previous.quantity + collection.quantity)
    updated_state = replace(state, source_collections=(*remaining, collection))

    inventory_item: InventoryItem | None = None
    updated_actors = actors
    if validated.destination == ItemCollectionDestination.ACTOR_INVENTORY:
        owner = next(
            (
                actor
                for actor in actors
                if str(actor.id) == validated.owner_actor_id and actor.faction == Faction.ALLY
            ),
            None,
        )
        if owner is None:
            raise ValueError("Wybrany bohater nie może zabrać tego przedmiotu.")
        inventory_item = InventoryItem(
            id=f"collected:{current.zone_id or 'scene'}:{current.reference_id}",
            name=current.label,
            kind=current.item_kind,
            quantity=validated.quantity,
            equipped=False,
            source_ref=current.definition_id or current.reference_id,
            description=current.description,
            properties=current.properties,
            portable=current.portable,
            weight_lb=current.weight_lb,
            value_cp=current.value_cp,
            ammunition_type=current.ammunition_type,
        )
        updated_owner = add_inventory_item(owner, inventory_item)
        if carried_weight_lb(updated_owner) > carrying_capacity_lb(updated_owner):
            raise ValueError(
                f"{owner.name} nie uniesie tego przedmiotu "
                f"({carried_weight_lb(updated_owner):g}/{carrying_capacity_lb(updated_owner):g} lb)."
            )
        updated_actors = tuple(
            updated_owner if actor.id == updated_owner.id else actor for actor in actors
        )
    return CollectionResult(
        state=updated_state,
        actors=updated_actors,
        collection=collection,
        inventory_item=inventory_item,
    )


__all__ = [
    "CollectionPlan",
    "CollectionResult",
    "collect_source",
    "plan_source_collection",
]
