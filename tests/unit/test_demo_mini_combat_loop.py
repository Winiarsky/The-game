import json

from dnd_board_game.actors import Faction
from dnd_board_game.combat import CombatStatus
from dnd_board_game.runtime.demo_mini_combat_loop import build_parser, run_demo


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
            "none",
            "--session-id",
            "mini_combat_loop",
            "--observation-dir",
            str(tmp_path),
            "--step-delay",
            "0",
            "--max-rounds",
            "2",
            *extra,
        ]
    )


def _events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_demo_mini_combat_loop_none_backend_runs_hero_and_enemy_turns(tmp_path):
    result = run_demo(_args(tmp_path, "--hero-attack-roll", "14", "--hero-damage", "1", "--enemy-seed", "7"))

    assert any("Tura: Bohater" in message for message in result.messages)
    assert any("Tura: Goblin" in message for message in result.messages)
    event_types = [event["event_type"] for event in _events(result.observation_path)]
    assert "turn_started" in event_types
    assert "action_used" in event_types
    assert "enemy_action_selected" in event_types
    assert "turn_finished" in event_types


def test_demo_mini_combat_loop_finishes_when_goblin_is_defeated(tmp_path):
    result = run_demo(_args(tmp_path, "--hero-attack-roll", "14", "--hero-damage", "10", "--enemy-seed", "7"))

    assert result.final_state.status == CombatStatus.FINISHED
    assert result.final_state.winner == Faction.ALLY
    event_types = [event["event_type"] for event in _events(result.observation_path)]
    assert "combat_finished" in event_types


def test_demo_mini_combat_loop_stops_at_max_rounds(tmp_path):
    result = run_demo(_args(tmp_path, "--hero-attack-roll", "2", "--max-rounds", "1", "--enemy-seed", "7"))

    assert result.final_state.status == CombatStatus.STOPPED
    event_types = [event["event_type"] for event in _events(result.observation_path)]
    assert "combat_stopped" in event_types


def test_demo_mini_combat_loop_fake_led_sequence_and_scan_selection(tmp_path):
    connection = FakeConnection(scanned=(1, 0))
    args = _args(
        tmp_path,
        "--board-backend",
        "simulator",
        "--show-leds",
        "--hero-attack-roll",
        "14",
        "--hero-damage",
        "10",
    )

    result = run_demo(args, connection_factory=lambda args: connection)

    assert result.feedback_events >= 4
    assert connection.events[0][0] == "set_leds"
    assert ("scan_board", [(1, 0)]) in connection.events
    assert ("leds_off",) in connection.events
    event_types = [event["event_type"] for event in _events(result.observation_path)]
    assert "led_feedback_sent" in event_types
    assert "combat_finished" in event_types
