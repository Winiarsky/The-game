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
