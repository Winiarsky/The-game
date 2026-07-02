import json
from pathlib import Path

import pytest

from dnd_board_game.actors import Faction
from dnd_board_game.combat import AttackSourceType, DamageType, EnvironmentSetupType, SceneObjectiveCondition, SetupVisibility
from dnd_board_game.exploration import SceneMode
from dnd_board_game.scenarios import build_encounter_from_scenario, build_exploration_from_scenario, load_scenario
from dnd_board_game.world import Coordinate


def _abandoned_watchtower_data_without_refs():
    base = Path("content/scenarios/abandoned_watchtower")
    data = json.loads((base / "scenario.json").read_text(encoding="utf-8"))
    data.pop("parts", None)
    data["actors"] = json.loads((base / "actors.json").read_text(encoding="utf-8"))["actors"]
    data["objectives"] = json.loads((base / "objectives.json").read_text(encoding="utf-8"))["objectives"]
    data["llm_context"] = json.loads((base / "llm_context.json").read_text(encoding="utf-8"))["llm_context"]
    data["exploration"] = {
        "party_start_zone": json.loads((base / "exploration/party_start_zone.json").read_text(encoding="utf-8"))["party_start_zone"],
        "zones": json.loads((base / "exploration/zones.json").read_text(encoding="utf-8"))["zones"],
        "points": json.loads((base / "exploration/points.json").read_text(encoding="utf-8"))["points"],
        "challenges": json.loads((base / "exploration/challenges.json").read_text(encoding="utf-8"))["challenges"],
        "resources": json.loads((base / "exploration/resources.json").read_text(encoding="utf-8"))["resources"],
        "initial_resources": json.loads((base / "exploration/initial_resources.json").read_text(encoding="utf-8"))["initial_resources"],
    }
    attack = {
        "id": "test_attack",
        "name": "Test Attack",
        "source_type": "weapon",
        "range_feet": 5,
        "attack_modifier": 1,
        "damage": {"fixed": 1, "damage_type": "bludgeoning"},
    }
    for actor in data["actors"]:
        actor.pop("item_refs", None)
        actor["attacks"] = [attack]
    return data


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
    assert len(exploration.challenges) == 2
    challenge = next(item for item in exploration.challenges if item.id == "closed_gate")
    assert challenge.completed_flag == "gate_passed"
    assert challenge.reveals_on_complete == ("wounded_scout",)
    assert challenge.llm_policy.allowed_local_skills == ("crafting", "lockpicking")
    assert "heavy_force" in challenge.llm_policy.allowed_approach_tags
    assert "bribe" not in challenge.llm_policy.allowed_approach_tags
    assert challenge.llm_policy.dc_min == 8
    assert challenge.llm_policy.dc_max == 18
    assert challenge.llm_policy.max_resources_per_attempt == 1
    assert "Opuszczona" in exploration.llm_context.summary
    assert "brak działającego mechanizmu lotu" in exploration.llm_context.forbidden_assumptions
    gate = next(zone for zone in exploration.zones if zone.id == "gate")
    assert "lina nie pozwala latać" in gate.llm_context.forbidden_assumptions
    assert "przelot na linie bez magii" in challenge.llm_context.impossible_approaches
    assert {resource.id for resource in exploration.resources} == {"rope", "wedge", "saw"}
    assert exploration.initial_resource_ids == ("rope", "wedge")
    courtyard = next(zone for zone in exploration.zones if zone.id == "courtyard")
    assert courtyard.search_dc == 12
    assert courtyard.search_reveals == ("hidden_cache",)
    courtyard_challenge = next(item for item in exploration.challenges if item.id == "courtyard_search")
    assert courtyard_challenge.zone_id == "courtyard"
    assert courtyard_challenge.completed_flag == "courtyard_searched"
    assert courtyard_challenge.reveals_on_complete == ()
    assert "listening" in courtyard_challenge.llm_policy.allowed_approach_tags
    assert "heavy_force" not in courtyard_challenge.llm_policy.allowed_approach_tags
    wounded_scout = next(point for point in exploration.points if point.id == "wounded_scout")
    assert wounded_scout.zone_id == "courtyard"
    assert wounded_scout.visibility == SetupVisibility.HIDDEN
    assert wounded_scout.npc_interaction is not None
    assert wounded_scout.npc_interaction.name == "Ranny zwiadowca"
    assert "scout_stabilized" in wounded_scout.npc_interaction.policy.allowed_flags
    assert {info.id for info in wounded_scout.npc_interaction.locked_information} == {"tower_hint", "hidden_cache_hint"}


def test_load_abandoned_watchtower_folder_manifest_matches_alias_file():
    from_alias = build_exploration_from_scenario(load_scenario("content/scenarios/abandoned_watchtower.json"))
    from_folder = build_exploration_from_scenario(load_scenario("content/scenarios/abandoned_watchtower"))

    assert from_alias.scenario_id == from_folder.scenario_id == "abandoned_watchtower"
    assert [zone.id for zone in from_alias.zones] == [zone.id for zone in from_folder.zones]
    assert [challenge.id for challenge in from_alias.challenges] == [challenge.id for challenge in from_folder.challenges]
    assert [point.id for point in from_alias.points] == [point.id for point in from_folder.points]
    assert from_folder.initial_resource_ids == ("rope", "wedge")


def test_load_abandoned_watchtower_folder_keeps_monster_and_item_refs_working():
    loaded = load_scenario("content/scenarios/abandoned_watchtower")
    exploration = build_exploration_from_scenario(loaded)

    hero = next(actor for actor in exploration.actors if actor.id == "hero")
    assert hero.name == "Bohater"
    assert loaded.path == Path("content/scenarios/abandoned_watchtower/scenario.json")


def test_exploration_challenge_reveal_rejects_unknown_point(tmp_path):
    data = _abandoned_watchtower_data_without_refs()
    data["exploration"]["challenges"][0]["reveals_on_complete"] = ["missing_point"]
    scenario_path = tmp_path / "bad_reveal_point.json"
    scenario_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="reveals_on_complete"):
        load_scenario(scenario_path)


def test_exploration_challenge_reveal_rejects_point_from_other_zone(tmp_path):
    data = _abandoned_watchtower_data_without_refs()
    data["exploration"]["zones"].append(
        {
            "id": "remote_cellar",
            "name": "Odległa piwnica",
            "positions": [[19, 20]],
            "available_if_flag": "cellar_found",
        }
    )
    data["exploration"]["points"].append(
        {
            "id": "remote_secret",
            "name": "Odległy sekret",
            "zone_id": "remote_cellar",
            "positions": [[19, 20]],
            "visibility": "hidden",
        }
    )
    data["exploration"]["challenges"][0]["reveals_on_complete"] = ["remote_secret"]
    scenario_path = tmp_path / "bad_reveal_zone.json"
    scenario_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="outside challenge zone"):
        load_scenario(scenario_path)


def test_exploration_challenge_llm_policy_rejects_bad_range(tmp_path):
    data = _abandoned_watchtower_data_without_refs()
    data["exploration"]["challenges"][0]["llm_policy"]["dc_range"] = [18, 8]
    scenario_path = tmp_path / "bad_policy_range.json"
    scenario_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="dc_range"):
        load_scenario(scenario_path)


def test_exploration_challenge_llm_policy_rejects_unknown_consequence_type(tmp_path):
    data = _abandoned_watchtower_data_without_refs()
    data["exploration"]["challenges"][0]["llm_policy"]["allowed_consequence_types"] = ["add_noise", "summon_dragon"]
    scenario_path = tmp_path / "bad_policy_consequence.json"
    scenario_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="allowed_consequence_types"):
        load_scenario(scenario_path)


def test_load_village_square_mvp_builds_exploration_locations_setup_points_and_objective():
    loaded = load_scenario("content/scenarios/village_square_mvp.json")
    exploration = build_exploration_from_scenario(loaded)

    assert loaded.definition.scene_mode == SceneMode.EXPLORATION
    assert exploration.scenario_id == "village_square_mvp"
    assert exploration.party_position.zone_id == "market"
    assert {zone.id for zone in exploration.zones} == {"market", "tavern", "elder_house", "forest_road"}
    assert len(exploration.objectives) == 1
    assert exploration.objectives[0].condition == SceneObjectiveCondition.FLAG_EQUALS
    assert exploration.objectives[0].flag_key == "quest_hook_found"

    market = next(zone for zone in exploration.zones if zone.id == "market")
    assert market.marker_position == Coordinate(8, 4)
    assert {option.id for option in market.options} >= {"talk_to_elder", "read_notice_board", "ask_for_rumors"}
    assert next(option for option in market.options if option.id == "talk_to_elder").success_flag == "quest_hook_found"

    visible_setup_points = {point.id for point in exploration.points if point.visibility == SetupVisibility.VISIBLE and point.requires_setup}
    assert visible_setup_points == {"elder_npc", "notice_board", "tavern_keeper"}
    hidden_point = next(point for point in exploration.points if point.id == "lost_pouch")
    assert hidden_point.visibility == SetupVisibility.HIDDEN
    assert hidden_point.requires_setup is False


def test_exploration_point_requires_setup_can_be_disabled(tmp_path):
    scenario_path = tmp_path / "exploration_points.json"
    scenario_path.write_text(
        json.dumps(
            {
                "id": "exploration_points",
                "name": "Exploration Points",
                "scene_mode": "exploration",
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
                "exploration": {
                    "party_start_zone": "square",
                    "zones": [
                        {
                            "id": "square",
                            "name": "Square",
                            "positions": [[0, 0], [1, 0]],
                            "anchor_position": [0, 0],
                        }
                    ],
                    "points": [
                        {
                            "id": "notice",
                            "name": "Notice Board",
                            "zone_id": "square",
                            "positions": [[1, 0]],
                            "requires_setup": False,
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )

    exploration = build_exploration_from_scenario(load_scenario(scenario_path))

    assert exploration.points[0].requires_setup is False


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
