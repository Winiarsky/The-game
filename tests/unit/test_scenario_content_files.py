from pathlib import Path

from dnd_board_game.actors import Faction
from dnd_board_game.scenarios import load_scenario


def test_default_scenario_file_exists_and_loads():
    scenario_path = Path("content/scenarios/goblin_ambush.json")

    loaded = load_scenario(scenario_path)

    assert scenario_path.exists()
    assert loaded.definition.id == "goblin_ambush"


def test_default_scenario_has_ally_and_enemy():
    loaded = load_scenario("content/scenarios/goblin_ambush.json")

    factions = {actor.faction for actor in loaded.definition.actors}

    assert Faction.ALLY in factions
    assert Faction.ENEMY in factions


def test_default_scenario_references_existing_content_files():
    text = Path("content/scenarios/goblin_ambush.json").read_text(encoding="utf-8")

    assert Path("content/monsters/goblin.json").exists()
    assert Path("content/items/longsword.json").exists()
    assert '"source_ref": "goblin"' in text
    assert '"longsword"' in text


def test_default_scenario_positions_are_in_bounds():
    loaded = load_scenario("content/scenarios/goblin_ambush.json")
    dimensions = loaded.definition.board_dimensions

    for actor in loaded.definition.actors:
        assert dimensions.in_bounds(actor.position)
    for entry in loaded.definition.environment:
        for position in entry.positions:
            assert dimensions.in_bounds(position)


def test_multi_actor_scenario_file_exists_and_loads():
    scenario_path = Path("content/scenarios/multi_actor_skirmish.json")

    loaded = load_scenario(scenario_path)

    assert scenario_path.exists()
    assert loaded.definition.id == "multi_actor_skirmish"
    assert len(loaded.definition.actors) == 5


def test_multi_actor_scenario_references_existing_content_files():
    text = Path("content/scenarios/multi_actor_skirmish.json").read_text(encoding="utf-8")

    assert Path("content/monsters/goblin.json").exists()
    assert Path("content/items/longsword.json").exists()
    assert Path("content/items/dagger.json").exists()
    assert text.count('"source_ref": "goblin"') == 3
    assert '"longsword"' in text
    assert '"dagger"' in text


def test_first_playable_scene_file_exists_and_loads():
    scenario_path = Path("content/scenarios/first_playable_scene.json")

    loaded = load_scenario(scenario_path)

    assert scenario_path.exists()
    assert loaded.definition.id == "first_playable_scene"
    assert len(loaded.definition.player_start_zones) == 1
    assert len(loaded.definition.objectives) == 1


def test_first_playable_scene_references_existing_content_files():
    text = Path("content/scenarios/first_playable_scene.json").read_text(encoding="utf-8")

    assert Path("content/monsters/goblin.json").exists()
    assert Path("content/items/longsword.json").exists()
    assert Path("content/items/dagger.json").exists()
    assert text.count('"source_ref": "goblin"') == 3
    assert '"longsword"' in text
    assert '"dagger"' in text


def test_first_playable_scene_positions_are_in_bounds():
    loaded = load_scenario("content/scenarios/first_playable_scene.json")
    dimensions = loaded.definition.board_dimensions

    for actor in loaded.definition.actors:
        assert dimensions.in_bounds(actor.position)
    for zone in loaded.definition.player_start_zones:
        for position in zone:
            assert dimensions.in_bounds(position)
    for entry in loaded.definition.environment:
        for position in entry.positions:
            assert dimensions.in_bounds(position)


def test_abandoned_watchtower_file_exists_and_loads():
    scenario_path = Path("content/scenarios/abandoned_watchtower.json")

    loaded = load_scenario(scenario_path)

    assert scenario_path.exists()
    assert loaded.definition.id == "abandoned_watchtower"
    assert loaded.definition.scene_mode.value == "exploration"
    assert len(loaded.definition.exploration_zones) == 4


def test_abandoned_watchtower_references_existing_content_files():
    text = Path("content/scenarios/abandoned_watchtower.json").read_text(encoding="utf-8")

    assert Path("content/items/longsword.json").exists()
    assert Path("content/items/dagger.json").exists()
    assert '"longsword"' in text
    assert '"dagger"' in text


def test_abandoned_watchtower_positions_are_in_bounds():
    loaded = load_scenario("content/scenarios/abandoned_watchtower.json")
    dimensions = loaded.definition.board_dimensions

    for actor in loaded.definition.actors:
        assert dimensions.in_bounds(actor.position)
    for zone in loaded.definition.exploration_zones:
        for position in zone.positions:
            assert dimensions.in_bounds(position)
    for point in loaded.definition.exploration_points:
        for position in point.positions:
            assert dimensions.in_bounds(position)
