import json

from dnd_board_game.runtime.demo_initiative_setup import build_parser, run_demo


class FakeConnection:
    def __init__(self):
        self.events = []

    def set_leds(self, positions, rgb_color):
        self.events.append(("set_leds", list(positions), list(rgb_color)))

    def leds_off(self):
        self.events.append(("leds_off",))


def _args(tmp_path, *extra):
    parser = build_parser()
    return parser.parse_args(
        [
            "--board-backend",
            "simulator",
            "--session-id",
            "initiative_demo",
            "--observation-dir",
            str(tmp_path),
            "--step-delay",
            "0",
            *extra,
        ]
    )


def _events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_demo_initiative_setup_none_backend_runs_without_board(tmp_path):
    parser = build_parser()
    args = parser.parse_args(
        [
            "--board-backend",
            "none",
            "--session-id",
            "none_demo",
            "--observation-dir",
            str(tmp_path),
        ]
    )

    result = run_demo(args)

    assert result.active_actor_id
    assert result.feedback_events == 0
    assert any("Rozpoczyna się walka" in message for message in result.messages)
    assert result.observation_path.exists()


def test_demo_initiative_setup_synchronizes_led_steps_and_observer(tmp_path):
    connection = FakeConnection()

    result = run_demo(
        _args(tmp_path, "--show-leds"),
        connection_factory=lambda args: connection,
    )

    assert result.feedback_events > 0
    assert connection.events[0][0] == "leds_off" or connection.events[0][0] == "set_leds"
    assert ("leds_off",) in connection.events
    set_indexes = [index for index, event in enumerate(connection.events) if event[0] == "set_leds"]
    for index in set_indexes[:-1]:
        assert any(event == ("leds_off",) for event in connection.events[index + 1 :])

    event_types = [event["event_type"] for event in _events(result.observation_path)]
    assert "setup_step_started" in event_types
    assert "roll_requested" in event_types
    assert "enemy_initiative_rolled" in event_types
    assert "initiative_set" in event_types
    assert "turn_started" in event_types
