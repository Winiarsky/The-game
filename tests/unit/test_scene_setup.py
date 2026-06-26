from dnd_board_game.combat import scene_setup_led_feedback
from dnd_board_game.hardware import LedColor
from dnd_board_game.scenarios import build_encounter_from_scenario, load_scenario
from dnd_board_game.world import Coordinate


def test_scenario_loads_player_start_zones():
    encounter = build_encounter_from_scenario(load_scenario("content/scenarios/first_playable_scene.json"))

    assert encounter.player_start_zones == (
        (Coordinate(0, 0), Coordinate(1, 0), Coordinate(0, 1), Coordinate(1, 1)),
    )


def test_scene_setup_led_feedback_highlights_start_zone():
    encounter = build_encounter_from_scenario(load_scenario("content/scenarios/first_playable_scene.json"))

    feedback = scene_setup_led_feedback(encounter.player_start_zones)

    assert len(feedback.frames) == 1
    assert set(feedback.frames[0].positions) == {Coordinate(0, 0), Coordinate(1, 0), Coordinate(0, 1), Coordinate(1, 1)}
    assert feedback.frames[0].color == LedColor.PLAYER_START_ZONE
