from dnd_board_game.combat import SceneFlags
from dnd_board_game.exploration import (
    ExplorationState,
    build_crafting_source_registry,
    discover_scene_source,
    describes_direct_source_use,
    is_source_lookup_only,
    match_available_sources,
    match_scene_sources_by_properties,
    match_visible_scene_sources,
    validate_source_property_query,
)
from dnd_board_game.scenarios import build_exploration_from_scenario, load_scenario


def _registry():
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
    return build_crafting_source_registry(state, exploration.actors)


def test_matches_visible_planks_by_inflected_label() -> None:
    matches = match_visible_scene_sources(_registry(), "szukam cienkiej spróchniałej deski")

    assert [match.source.reference_id for match in matches] == ["gate_rotten_planks"]
    assert matches[0].direct_label_match is True


def test_plain_label_match_does_not_contain_hardcoded_functional_aliases() -> None:
    matches = match_visible_scene_sources(_registry(), "szukam kija, którym dosięgnę rygla")

    assert matches == ()


def test_explicit_use_matching_can_resolve_party_inventory_source() -> None:
    matches = match_available_sources(_registry(), "używam narzędzi złodziejskich")

    assert any(match.source.reference_id == "thieves_tools" for match in matches)


def test_matches_abstract_function_to_existing_source_properties() -> None:
    matches = match_scene_sources_by_properties(
        _registry(),
        required_properties=("long",),
        preferred_properties=("rigid", "prying"),
    )

    assert [match.source.reference_id for match in matches] == ["gate_rotten_planks"]
    assert matches[0].direct_label_match is False
    assert matches[0].matched_preferred_properties == ("rigid",)


def test_property_match_returns_no_source_when_required_function_is_absent() -> None:
    matches = match_scene_sources_by_properties(
        _registry(),
        required_properties=("container", "metallic"),
    )

    assert matches == ()


def test_preferred_only_query_does_not_fall_back_to_unrelated_scene_objects() -> None:
    matches = match_scene_sources_by_properties(
        _registry(),
        required_properties=(),
        preferred_properties=("container",),
    )

    assert matches == ()


def test_property_query_rejects_values_outside_content_catalog() -> None:
    try:
        validate_source_property_query(
            required_properties=("telepathic",),
            preferred_properties=(),
            allowed_property_ids=("long", "rigid"),
        )
    except ValueError as exc:
        assert "telepathic" in str(exc)
    else:
        raise AssertionError("Unknown semantic properties must be rejected.")


def test_separates_source_lookup_from_immediate_scene_action() -> None:
    assert is_source_lookup_only("szukam jakiejś deski", explicit_search=True) is True
    assert (
        is_source_lookup_only(
            "szukam deski i staram się zdjąć nią rygiel",
            explicit_search=True,
        )
        is False
    )
    assert describes_direct_source_use("używam deski, żeby zdjąć rygiel") is True


def test_discovery_records_scene_knowledge_without_granting_inventory_resource() -> None:
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
    source = build_crafting_source_registry(state, exploration.actors).source_by_id(
        "zone:gate:item:gate_rotten_planks"
    )
    assert source is not None

    discovered = discover_scene_source(
        state,
        source,
        requested_as="kij",
        purpose="dosięgnięcie rygla",
        matched_properties=("long", "rigid"),
        semantic_substitution=True,
    )

    assert discovered.source_discoveries[0].source_id == source.id
    assert discovered.source_discoveries[0].semantic_substitution is True
    assert discovered.inventory_resource_ids == state.inventory_resource_ids
