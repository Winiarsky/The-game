from dataclasses import replace

import pytest

from dnd_board_game.combat import SceneFlags
from dnd_board_game.exploration import (
    CraftingSource,
    CraftingSourceKind,
    ExplorationState,
    build_crafting_source_registry,
    collect_source,
    plan_source_collection,
)
from dnd_board_game.inventory import ItemCollectionDestination
from dnd_board_game.scenarios import build_exploration_from_scenario, load_scenario


def _loaded_state():
    exploration = build_exploration_from_scenario(
        load_scenario("content/scenarios/abandoned_watchtower.json")
    )
    state = ExplorationState(
        exploration.zones,
        exploration.points,
        exploration.party_position,
        SceneFlags(),
        challenges=exploration.challenges,
        resources=exploration.resources,
        inventory_resource_ids=exploration.initial_resource_ids,
    )
    return exploration, state


def test_collects_selected_scene_quantity_into_actor_inventory() -> None:
    exploration, state = _loaded_state()
    source = build_crafting_source_registry(state, exploration.actors).source_by_id(
        "zone:gate:item:gate_rotten_planks"
    )
    assert source is not None

    plan = plan_source_collection(source, quantity=2, owner_actor_id="hero")
    result = collect_source(state, exploration.actors, plan)

    remaining = build_crafting_source_registry(result.state, result.actors).source_by_id(source.id)
    assert remaining is not None and remaining.quantity == 2
    hero = next(actor for actor in result.actors if str(actor.id) == "hero")
    collected = next(item for item in hero.inventory if item.name == "Drewniana deska")
    assert collected.quantity == 2
    assert collected.equipped is False
    assert collected.weight_lb == 8
    assert result.collection.destination == "actor_inventory"


def test_actor_inventory_collection_rejects_weight_over_capacity() -> None:
    exploration, state = _loaded_state()
    source = build_crafting_source_registry(state, exploration.actors).source_by_id(
        "zone:gate:item:gate_rotten_planks"
    )
    assert source is not None
    hero = next(actor for actor in exploration.actors if str(actor.id) == "hero")
    weakened_hero = replace(
        hero,
        ability_scores=replace(hero.ability_scores, strength=1),
    )
    actors = tuple(
        weakened_hero if actor.id == hero.id else actor
        for actor in exploration.actors
    )

    with pytest.raises(ValueError, match="nie uniesie"):
        collect_source(
            state,
            actors,
            plan_source_collection(source, quantity=2, owner_actor_id="hero"),
        )


def test_collection_revalidates_remaining_quantity() -> None:
    exploration, state = _loaded_state()
    source = build_crafting_source_registry(state, exploration.actors).source_by_id(
        "zone:gate:item:gate_rotten_planks"
    )
    assert source is not None
    first = collect_source(
        state,
        exploration.actors,
        plan_source_collection(source, quantity=3, owner_actor_id="hero"),
    )

    with pytest.raises(ValueError, match="Dostępna liczba"):
        collect_source(
            first.state,
            first.actors,
            plan_source_collection(source, quantity=2, owner_actor_id="hero"),
        )


def test_attached_fixture_requires_separate_action_before_collection() -> None:
    exploration, state = _loaded_state()
    source = build_crafting_source_registry(state, exploration.actors).source_by_id(
        "zone:gate:fixture:gate_corroded_hinges"
    )
    assert source is not None

    with pytest.raises(ValueError, match="Najpierw odłącz"):
        plan_source_collection(source, owner_actor_id="hero")


@pytest.mark.parametrize(
    "destination",
    [ItemCollectionDestination.PARTY_TREASURE, ItemCollectionDestination.SCENARIO_QUEST],
)
def test_group_collection_destinations_do_not_create_actor_inventory_items(destination) -> None:
    exploration, state = _loaded_state()
    source = CraftingSource(
        id="zone:gate:item:special",
        reference_id="special",
        kind=CraftingSourceKind.SCENE_ITEM,
        label="Znalezisko",
        properties=(),
        zone_id="gate",
        collection_destination=destination,
    )
    zone = next(zone for zone in state.zones if zone.id == "gate")
    base_item = zone.item_instances[0]
    item = replace(
        base_item,
        id="special",
        definition=replace(
            base_item.definition,
            id="special",
            name="Znalezisko",
            collection_destination=destination,
        ),
        quantity=1,
    )
    state = replace(
        state,
        zones=tuple(
            replace(candidate, item_instances=(*candidate.item_instances, item))
            if candidate.id == zone.id
            else candidate
            for candidate in state.zones
        ),
    )

    result = collect_source(state, exploration.actors, plan_source_collection(source))

    assert result.inventory_item is None
    assert result.actors == exploration.actors
    assert result.collection.destination == destination.value
