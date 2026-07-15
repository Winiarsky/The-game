from dataclasses import replace

import pytest

from dnd_board_game.actors import Actor
from dnd_board_game.exploration import (
    CraftingSourceKind,
    ExplorationState,
    TemporaryItem,
    build_crafting_source_registry,
)
from dnd_board_game.scenarios import build_exploration_from_scenario, load_scenario


def _watchtower_state_and_actors() -> tuple[ExplorationState, tuple[Actor, ...]]:
    exploration = build_exploration_from_scenario(
        load_scenario("content/scenarios/abandoned_watchtower")
    )
    state = ExplorationState(
        zones=exploration.zones,
        points=exploration.points,
        party_position=exploration.party_position,
        challenges=exploration.challenges,
        resources=exploration.resources,
        inventory_resource_ids=exploration.initial_resource_ids,
    )
    return state, exploration.actors


def test_registry_combines_current_zone_resources_fixtures_and_party_inventory() -> None:
    state, actors = _watchtower_state_and_actors()

    registry = build_crafting_source_registry(state, actors)

    assert registry.source_by_id("zone:gate:item:gate_rotten_planks").kind == CraftingSourceKind.SCENE_ITEM
    assert registry.source_by_id("zone:gate:fixture:gate_corroded_hinges").detachable is True
    assert registry.source_by_id("resource:rope").kind == CraftingSourceKind.EXPLORATION_RESOURCE
    thieves_tools = registry.source_by_id("actor:rogue:item:thieves_tools")
    assert thieves_tools is not None
    assert thieves_tools.owner_actor_id == "rogue"
    assert set(thieves_tools.properties) >= {"metallic", "prying"}


def test_registry_only_exposes_owned_exploration_resources_as_sources() -> None:
    state, actors = _watchtower_state_and_actors()

    registry = build_crafting_source_registry(state, actors)

    assert registry.source_by_id("resource:rope") is not None
    assert registry.source_by_id("resource:wedge") is not None
    assert registry.source_by_id("resource:saw") is None


def test_registry_matches_available_sources_by_structured_properties() -> None:
    state, actors = _watchtower_state_and_actors()
    registry = build_crafting_source_registry(state, actors)

    binding_sources = registry.matching_properties(("long", "binding"))
    fragile_wood = registry.matching_properties(("wooden", "fragile"))

    assert [source.id for source in binding_sources] == ["resource:rope"]
    assert [source.id for source in fragile_wood] == ["zone:gate:item:gate_rotten_planks"]


def test_registry_rejects_unknown_zone() -> None:
    state, actors = _watchtower_state_and_actors()

    with pytest.raises(ValueError, match="Unknown exploration zone"):
        build_crafting_source_registry(state, actors, zone_id="missing_zone")


def test_registry_exposes_available_temporary_item_for_use_command() -> None:
    state, actors = _watchtower_state_and_actors()
    item = TemporaryItem(
        id="crafted:ram",
        template_id=None,
        label="Prowizoryczny taran",
        description="Taran z desek.",
        bonus_tags=("heavy_force",),
        modifier=1,
        advantage=False,
        uses_remaining=2,
        created_in_zone_id="gate",
    )

    registry = build_crafting_source_registry(
        replace(state, temporary_items=(item,)),
        actors,
    )

    source = registry.source_by_id("temporary:crafted:ram")
    assert source is not None
    assert source.kind == CraftingSourceKind.TEMPORARY_ITEM
    assert source.reference_id == item.id
