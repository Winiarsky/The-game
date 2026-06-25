import json

from dnd_board_game.runtime.demo_mini_combat import build_parser, run_demo


class FakeConnection:
    def __init__(self, scanned=None):
        self.events = []
        self.scanned = scanned

    def set_leds(self, positions, rgb_color):
        self.events.append(("set_leds", list(positions), list(rgb_color)))

    def leds_off(self):
        self.events.append(("leds_off",))

    def scan_board(self, acceptable_responses=None, *, timeout_s=None):
        self.events.append(("scan_board", list(acceptable_responses or [])))
        return self.scanned


def _args(tmp_path, *extra):
    parser = build_parser()
    return parser.parse_args(
        [
            "--board-backend",
            "simulator",
            "--session-id",
            "mini_combat",
            "--observation-dir",
            str(tmp_path),
            "--step-delay",
            "0",
            "--scan-timeout",
            "0.1",
            *extra,
        ]
    )


def _events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_demo_mini_combat_none_backend_hit_applies_damage(tmp_path):
    parser = build_parser()
    args = parser.parse_args(
        [
            "--board-backend",
            "none",
            "--target-id",
            "goblin",
            "--hero-attack-roll",
            "14",
            "--hero-damage",
            "6",
            "--session-id",
            "none_combat",
            "--observation-dir",
            str(tmp_path),
            "--step-delay",
            "0",
        ]
    )

    result = run_demo(args)

    assert result.attack_hit is True
    assert result.target_hp == 4
    event_types = [event["event_type"] for event in _events(result.observation_path)]
    assert "attack_declared" in event_types
    assert "attack_resolved" in event_types
    assert "damage_applied" in event_types


def test_demo_mini_combat_miss_does_not_apply_damage(tmp_path):
    result = run_demo(_args(tmp_path, "--hero-attack-roll", "2"))

    assert result.attack_hit is False
    assert result.target_hp == 10
    event_types = [event["event_type"] for event in _events(result.observation_path)]
    assert "attack_resolved" in event_types
    assert "damage_applied" not in event_types


def test_demo_mini_combat_fake_board_synchronizes_leds_and_scan_selection(tmp_path):
    connection = FakeConnection(scanned=(1, 0))

    result = run_demo(
        _args(tmp_path, "--show-leds", "--hero-attack-roll", "14"),
        connection_factory=lambda args: connection,
    )

    assert result.feedback_events >= 3
    assert ("leds_off",) in connection.events
    assert connection.events[0][0] == "set_leds"
    assert any(event[0] == "set_leds" and event[1] == [(1, 0)] for event in connection.events)
    assert ("scan_board", []) in connection.events
    assert connection.events.index(("scan_board", [])) < connection.events.index(("leds_off",))


def test_demo_mini_combat_illegal_scan_position_falls_back_to_target_id(tmp_path):
    connection = FakeConnection(scanned=(9, 9))

    result = run_demo(
        _args(tmp_path, "--show-leds", "--target-id", "goblin", "--hero-attack-roll", "14"),
        connection_factory=lambda args: connection,
    )

    assert result.attack_hit is True
    event_types = [event["event_type"] for event in _events(result.observation_path)]
    assert "attack_target_rejected" in event_types


def test_demo_mini_combat_scan_error_falls_back_to_target_id(tmp_path):
    class FailingConnection(FakeConnection):
        def scan_board(self, acceptable_responses=None, *, timeout_s=None):
            raise TimeoutError("timeout")

    result = run_demo(
        _args(tmp_path, "--show-leds", "--target-id", "goblin", "--hero-attack-roll", "14"),
        connection_factory=lambda args: FailingConnection(),
    )

    assert result.attack_hit is True
    event_types = [event["event_type"] for event in _events(result.observation_path)]
    assert "board_scan_error" in event_types
    assert "attack_declared" in event_types


def test_demo_mini_combat_wait_for_enter_uses_entered_attack_roll(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "12")

    result = run_demo(
        _args(
            tmp_path,
            "--show-leds",
            "--wait-for-enter",
            "--target-id",
            "goblin",
            "--hero-attack-roll",
            "14",
        ),
        connection_factory=lambda args: FakeConnection(scanned=(1, 0)),
    )

    attack_event = next(event for event in _events(result.observation_path) if event["event_type"] == "attack_resolved")
    assert attack_event["payload"]["natural_roll"] == 12
    assert attack_event["payload"]["total"] == 17
