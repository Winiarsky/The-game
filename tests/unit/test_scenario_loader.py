import json

import pytest

from dnd_board_game.actors import Faction
from dnd_board_game.combat import AttackSourceType, DamageType, EnvironmentSetupType, SceneObjectiveCondition, SetupVisibility
from dnd_board_game.exploration import SceneMode
from dnd_board_game.scenarios import build_encounter_from_scenario, build_exploration_from_scenario, load_scenario
from dnd_board_game.world import Coordinate


def test_load_scenario_builds_actors_and_attack_sources():
    loaded = load_scenario("content/scenarios/goblin_ambush.json")
    encounter = build_encounter_from_scenario(loaded)

    assert encounter.scenario_id == "goblin_ambush"
    assert encounter.scenario_name == "Zasadzka goblina"
    assert encounter.board.dimensions.cols == 20
    assert encounter.board.dimensions.rows == 30

    hero = next(actor for actor in encounter.actors if actor.id == "hero")
    goblin = next(actor for actor in encounter.actors if actor.id == "goblin")
    assert hero.name == "Bohater"
    assert hero.faction == Faction.ALLY
    assert hero.ac == 14
    assert hero.hp == 20
    assert hero.position == Coordinate(0, 0)
    assert hero.ability_scores.strength == 16
    assert goblin.name == "Goblin"
    assert goblin.faction == Faction.ENEMY
    assert goblin.position == Coordinate(1, 0)

    hero_source = encounter.attack_sources_by_actor[hero.id]
    assert hero_source.name == "Miecz"
    assert hero_source.source_type == AttackSourceType.WEAPON
    assert hero_source.attack_roll_request.modifiers[0].value == 5
    assert hero_source.damage_die_sides == 6
    assert hero_source.damage_type == DamageType.SLASHING.value

    goblin_source = encounter.attack_sources_by_actor[goblin.id]
    assert goblin_source.name == "Szabla"
    assert goblin_source.attack_roll_request.modifiers[0].value == 4
    assert goblin_source.damage_die_sides == 6
    assert goblin_source.damage_modifier == 2


def test_load_multi_actor_scenario_builds_separate_actors_and_sources():
    encounter = build_encounter_from_scenario(load_scenario("content/scenarios/multi_actor_skirmish.json"))

    assert encounter.scenario_id == "multi_actor_skirmish"
    assert len(encounter.actors) == 5
    ids = {str(actor.id) for actor in encounter.actors}
    assert ids == {"hero", "rogue", "goblin_a", "goblin_b", "goblin_c"}
    assert set(str(actor_id) for actor_id in encounter.attack_sources_by_actor) == ids

    goblin_a = next(actor for actor in encounter.actors if actor.id == "goblin_a")
    goblin_b = next(actor for actor in encounter.actors if actor.id == "goblin_b")
    rogue = next(actor for actor in encounter.actors if actor.id == "rogue")
    assert goblin_a.name == "Goblin A"
    assert goblin_b.name == "Goblin B"
    assert goblin_a.position == Coordinate(1, 0)
    assert goblin_b.position == Coordinate(1, 1)
    assert encounter.attack_sources_by_actor[rogue.id].name == "Sztylet"


def test_load_scenario_builds_environment_entries():
    encounter = build_encounter_from_scenario(load_scenario("content/scenarios/goblin_ambush.json"))

    assert len(encounter.environment) == 1
    entry = encounter.environment[0]
    assert entry.id == "broken_crate"
    assert entry.setup_type == EnvironmentSetupType.CONTAINER
    assert entry.visibility == SetupVisibility.VISIBLE
    assert entry.positions == (Coordinate(3, 1),)


def test_load_first_playable_scene_builds_setup_objective_and_scene_object():
    encounter = build_encounter_from_scenario(load_scenario("content/scenarios/first_playable_scene.json"))

    assert encounter.scenario_id == "first_playable_scene"
    assert len(encounter.actors) == 5
    assert encounter.player_start_zones == (
        (Coordinate(0, 0), Coordinate(1, 0), Coordinate(0, 1), Coordinate(1, 1)),
    )
    assert len(encounter.objectives) == 1
    assert encounter.objectives[0].id == "secure_crate"
    assert encounter.objectives[0].condition == SceneObjectiveCondition.FLAG_EQUALS
    assert encounter.objectives[0].flag_key == "crate_secured"
    assert encounter.objectives[0].flag_value is True
    assert len(encounter.scene_objects) == 1
    scene_object = encounter.scene_objects[0]
    assert scene_object.id == "ancient_crate"
    assert scene_object.interaction_label == "Zbadaj skrzynię"
    assert scene_object.blocks_movement is False
    assert scene_object.allow_interaction_when_occupied_by_enemy is True
    assert scene_object.cover_bonus == 2
    assert scene_object.interactions[0].id == "inspect_crate"
    assert scene_object.interactions[0].ability_check is not None
    assert scene_object.interactions[0].ability_check.dc == 12
    assert scene_object.interactions[0].success_flag == "crate_secured"
    assert encounter.board.terrain_at(Coordinate(3, 1)).blocks_movement is True
    assert encounter.board.terrain_at(Coordinate(2, 2)).is_difficult is True


def test_load_abandoned_watchtower_builds_exploration_scene():
    loaded = load_scenario("content/scenarios/abandoned_watchtower.json")
    exploration = build_exploration_from_scenario(loaded)

    assert loaded.definition.scene_mode == SceneMode.EXPLORATION
    assert exploration.scenario_id == "abandoned_watchtower"
    assert exploration.party_position.zone_id == "gate"
    assert len(exploration.actors) == 2
    assert len(exploration.zones) == 4
    assert len(exploration.challenges) == 1
    assert exploration.challenges[0].completed_flag == "gate_passed"
    assert {resource.id for resource in exploration.resources} == {"rope", "wedge", "saw"}
    assert exploration.initial_resource_ids == ("rope", "wedge")
    courtyard = next(zone for zone in exploration.zones if zone.id == "courtyard")
    assert courtyard.search_dc == 12
    assert courtyard.search_reveals == ("hidden_cache",)


def test_missing_required_field_reports_field_name(tmp_path):
    scenario_path = tmp_path / "broken.json"
    scenario_path.write_text(json.dumps({"id": "broken", "board": {"cols": 20, "rows": 30}}), encoding="utf-8")

    with pytest.raises(ValueError, match="scenario.actors"):
        load_scenario(scenario_path)


def test_unknown_enum_value_reports_field_name(tmp_path):
    root = tmp_path
    (root / "scenarios").mkdir()
    scenario_path = root / "scenarios" / "bad.json"
    scenario_path.write_text(
        json.dumps(
            {
                "id": "bad",
                "name": "Bad",
                "board": {"cols": 20, "rows": 30},
                "actors": [
                    {
                        "id": "hero",
                        "name": "Hero",
                        "kind": "player_character",
                        "faction": "unknown",
                        "ac": 10,
                        "hp": 10,
                        "speed_feet": 30,
                        "position": [0, 0],
                        "ability_scores": {},
                        "attacks": [
                            {
                                "id": "hit",
                                "name": "Hit",
                                "source_type": "weapon",
                                "range_feet": 5,
                                "attack_modifier": 1,
                                "damage": {"dice": "1d4", "damage_type": "slashing"},
                            }
                        ],
                    },
                    {
                        "id": "enemy",
                        "name": "Enemy",
                        "kind": "monster",
                        "faction": "enemy",
                        "ac": 10,
                        "hp": 10,
                        "speed_feet": 30,
                        "position": [1, 0],
                        "ability_scores": {},
                        "attacks": [
                            {
                                "id": "hit",
                                "name": "Hit",
                                "source_type": "weapon",
                                "range_feet": 5,
                                "attack_modifier": 1,
                                "damage": {"dice": "1d4", "damage_type": "slashing"},
                            }
                        ],
                    },
                ],
                "environment": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="actor hero.faction"):
        load_scenario(scenario_path)


def test_scenario_requires_ally_and_enemy(tmp_path):
    scenario_path = tmp_path / "only_ally.json"
    scenario_path.write_text(
        json.dumps(
            {
                "id": "only_ally",
                "name": "Only Ally",
                "board": {"cols": 20, "rows": 30},
                "actors": [
                    {
                        "id": "hero",
                        "name": "Hero",
                        "kind": "player_character",
                        "faction": "ally",
                        "ac": 10,
                        "hp": 10,
                        "speed_feet": 30,
                        "position": [0, 0],
                        "ability_scores": {},
                        "attacks": [
                            {
                                "id": "hit",
                                "name": "Hit",
                                "source_type": "weapon",
                                "range_feet": 5,
                                "attack_modifier": 1,
                                "damage": {"dice": "1d4", "damage_type": "slashing"},
                            }
                        ],
                    }
                ],
                "environment": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="at least one enemy"):
        load_scenario(scenario_path)
