from dnd_board_game.hardware import LedRole
from dnd_board_game.runtime.demo_movement import (
    build_demo_scenario,
    build_parser,
    demo_movement_led_feedback,
    run_demo,
)
from dnd_board_game.world import Coordinate, find_path, movement_range


class FakeConnection:
    def __init__(self):
        self.calls = []
        self.cleared = False

    def set_leds(self, positions, rgb_color):
        self.calls.append((list(positions), list(rgb_color)))

    def leds_off(self):
        self.cleared = True


def _args(tmp_path, *extra):
    parser = build_parser()
    return parser.parse_args(
        [
            "--board-backend",
            "simulator",
            "--session-id",
            "led_demo",
            "--observation-dir",
            str(tmp_path),
            *extra,
        ]
    )


def test_run_demo_sends_led_feedback_when_requested(tmp_path):
    connection = FakeConnection()

    result = run_demo(
        _args(tmp_path, "--destination", "3,3", "--show-leds"),
        connection_factory=lambda args: connection,
    )

    assert result.feedback_sent is True
    assert connection.cleared is True
    assert connection.calls
    sent_colors = []
    for _positions, color in connection.calls:
        if color and isinstance(color[0], list):
            sent_colors.extend(color)
        else:
            sent_colors.append(color)
    assert [180, 0, 0] in sent_colors
    assert [0, 220, 255] in sent_colors
    assert [255, 0, 80] in sent_colors


def test_run_demo_does_not_send_led_feedback_without_show_leds(tmp_path):
    connection = FakeConnection()

    result = run_demo(
        _args(tmp_path, "--destination", "3,3"),
        connection_factory=lambda args: connection,
    )

    assert result.feedback_sent is False
    assert connection.cleared is False
    assert connection.calls == []


def test_demo_movement_led_feedback_marks_debug_terrain_and_actors():
    scenario = build_demo_scenario()
    movement = movement_range(scenario.board, scenario.actor, scenario.actors)
    path = find_path(scenario.board, scenario.actor, scenario.actors, Coordinate(3, 3))

    feedback = demo_movement_led_feedback(scenario, movement, path)

    roles = [frame.role for frame in feedback.frames]
    assert LedRole.DIFFICULT_TERRAIN in roles
    assert LedRole.BLOCKING_TERRAIN in roles
    assert LedRole.ALLY in roles
    assert LedRole.ENEMY in roles
    assert roles[-1] == LedRole.ACTIVE_ACTOR
