import pytest

from dnd_board_game.actors import Actor
from dnd_board_game.exploration import (
    CraftingComponentDisposition,
    CraftingComponentSelection,
    CraftingDraft,
    CraftingPolicy,
    CraftingValidationError,
    ExplorationState,
    build_crafting_source_registry,
    craft_temporary_item,
    dismantle_crafted_item,
)
from dnd_board_game.scenarios import build_exploration_from_scenario, load_scenario


def _crafting_context() -> tuple[ExplorationState, tuple[Actor, ...], CraftingPolicy]:
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
    return state, exploration.actors, exploration.crafting_policy


def test_crafts_battering_ram_from_properties_without_named_item_template() -> None:
    state, actors, policy = _crafting_context()
    registry = build_crafting_source_registry(state, actors)
    draft = CraftingDraft(
        label="Prowizoryczny taran",
        description="Deska obciążona kamieniem, przeznaczona do wyważenia bramy.",
        purpose_id="heavy_force",
        components=(
            CraftingComponentSelection("zone:gate:item:gate_rotten_planks"),
            CraftingComponentSelection("zone:gate:item:gate_loose_stones"),
        ),
    )

    crafted_state, item = craft_temporary_item(state, draft, registry, policy)

    assert item.template_id is None
    assert item.purpose_id == "heavy_force"
    assert item.bonus_tags == ("heavy_force", "noise")
    assert item.modifier == 1
    assert item.uses_remaining == 2
    assert crafted_state.elapsed_minutes == 10
    assert {component.disposition for component in item.component_uses} == {
        CraftingComponentDisposition.CONSUMED
    }


def test_engine_selects_missing_components_for_function_first_draft() -> None:
    state, actors, policy = _crafting_context()
    draft = CraftingDraft(
        label="Prowizoryczna drabina",
        description="Pomoc pozwalająca wejść na mur.",
        purpose_id="climbing_aid",
        components=(),
        auto_select_missing_components=True,
    )

    crafted_state, item = craft_temporary_item(
        state,
        draft,
        build_crafting_source_registry(state, actors),
        policy,
    )

    assert item.template_id is None
    assert item.source_materials == (
        "zone:gate:item:gate_rotten_planks",
        "resource:rope",
    )
    assert next(
        component
        for component in item.component_uses
        if component.source_id == "zone:gate:item:gate_rotten_planks"
    ).quantity == 2
    assert build_crafting_source_registry(crafted_state, actors).source_by_id("resource:rope").usable is False


def test_crafts_ladder_and_releases_reserved_rope_after_dismantling() -> None:
    state, actors, policy = _crafting_context()
    draft = CraftingDraft(
        label="Prowizoryczna drabina",
        description="Dwie długie deski związane liną w pomoc do wspinaczki.",
        purpose_id="climbing_aid",
        components=(
            CraftingComponentSelection("zone:gate:item:gate_rotten_planks", quantity=2),
            CraftingComponentSelection("resource:rope"),
        ),
    )

    crafted_state, item = craft_temporary_item(
        state,
        draft,
        build_crafting_source_registry(state, actors),
        policy,
    )
    allocated_registry = build_crafting_source_registry(crafted_state, actors)

    assert allocated_registry.source_by_id("resource:rope").usable is False
    assert allocated_registry.source_by_id("zone:gate:item:gate_rotten_planks").quantity == 2
    assert next(
        component for component in item.component_uses if component.source_id == "resource:rope"
    ).disposition == CraftingComponentDisposition.RESERVED

    dismantled_state, dismantled = dismantle_crafted_item(crafted_state, item.id)
    released_registry = build_crafting_source_registry(dismantled_state, actors)

    assert dismantled.dismantled is True
    assert released_registry.source_by_id("resource:rope").usable is True
    assert released_registry.source_by_id("zone:gate:item:gate_rotten_planks").quantity == 2


def test_cannot_build_second_ladder_while_the_only_rope_is_reserved() -> None:
    state, actors, policy = _crafting_context()
    first = CraftingDraft(
        label="Pierwsza drabina",
        description="Dwie deski związane liną.",
        purpose_id="climbing_aid",
        components=(
            CraftingComponentSelection("zone:gate:item:gate_rotten_planks", quantity=2),
            CraftingComponentSelection("resource:rope"),
        ),
    )
    state, _item = craft_temporary_item(
        state,
        first,
        build_crafting_source_registry(state, actors),
        policy,
    )
    second = CraftingDraft(
        label="Druga drabina",
        description="Kolejna pomoc do wspinaczki.",
        purpose_id="climbing_aid",
        components=(),
        auto_select_missing_components=True,
    )

    with pytest.raises(CraftingValidationError, match=r"binding, load_bearing"):
        craft_temporary_item(
            state,
            second,
            build_crafting_source_registry(state, actors),
            policy,
        )


def test_crafts_lever_through_same_property_based_pipeline() -> None:
    state, actors, policy = _crafting_context()
    draft = CraftingDraft(
        label="Prowizoryczna dźwignia",
        description="Długa deska oparta na twardym drewnianym klinie.",
        purpose_id="leverage",
        components=(
            CraftingComponentSelection("zone:gate:item:gate_rotten_planks"),
            CraftingComponentSelection("resource:wedge"),
        ),
    )

    crafted_state, item = craft_temporary_item(
        state,
        draft,
        build_crafting_source_registry(state, actors),
        policy,
    )

    assert item.bonus_tags == ("lever", "quiet")
    assert crafted_state.elapsed_minutes == 10
    assert all(
        component.disposition == CraftingComponentDisposition.CONSUMED
        for component in item.component_uses
    )


def test_rejects_ladder_when_selected_components_do_not_satisfy_requirements() -> None:
    state, actors, policy = _crafting_context()
    draft = CraftingDraft(
        label="Kamienna drabina",
        description="Próba zbudowania drabiny wyłącznie z luźnych kamieni.",
        purpose_id="climbing_aid",
        components=(
            CraftingComponentSelection("zone:gate:item:gate_loose_stones", quantity=3),
        ),
    )

    with pytest.raises(CraftingValidationError, match=r"long, rigid"):
        craft_temporary_item(
            state,
            draft,
            build_crafting_source_registry(state, actors),
            policy,
        )


def test_detachable_fixture_can_be_acquired_as_part_of_crafting() -> None:
    state, actors, policy = _crafting_context()
    draft = CraftingDraft(
        label="Prowizoryczny wytrych",
        description="Krótki metalowy element odłączony od skorodowanego zawiasu.",
        purpose_id="precision_tool",
        components=(
            CraftingComponentSelection("zone:gate:fixture:gate_corroded_hinges"),
        ),
    )

    updated, item = craft_temporary_item(
        state,
        draft,
        build_crafting_source_registry(state, actors),
        policy,
    )

    assert item.purpose_id == "precision_tool"
    assert item.modifier == -1
    assert updated.elapsed_minutes == 10


def test_rejects_nonportable_fixture_that_cannot_be_detached() -> None:
    state, actors, policy = _crafting_context()
    draft = CraftingDraft(
        label="Fragment bramy",
        description="Próba użycia całej, nadal zamocowanej bramy jako komponentu.",
        purpose_id="precision_tool",
        components=(CraftingComponentSelection("zone:gate:fixture:watchtower_gate"),),
    )

    with pytest.raises(CraftingValidationError, match="trwale związany"):
        craft_temporary_item(
            state,
            draft,
            build_crafting_source_registry(state, actors),
            policy,
        )
