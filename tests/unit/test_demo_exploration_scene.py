import json
import sys
import time

from dnd_board_game.hardware import BoardLedAdapter
from dnd_board_game.runtime import demo_exploration_scene
from dnd_board_game.runtime.demo_exploration_scene import build_parser, run_demo
from dnd_board_game.world import Coordinate


class FakeConnection:
    def __init__(self, scanned=None):
        self.events = []
        self.scanned = list(scanned or [])

    def set_leds(self, positions, rgb_color):
        self.events.append(("set_leds", list(positions), list(rgb_color)))

    def leds_off(self):
        self.events.append(("leds_off",))

    def scan_board(self, acceptable_responses=None, *, timeout_s=None):
        self.events.append(("scan_board", list(acceptable_responses or [])))
        if not self.scanned:
            return None
        return self.scanned.pop(0)

    def cancel_scan(self):
        self.events.append(("cancel_scan",))


def _args(tmp_path, *extra):
    parser = build_parser()
    return parser.parse_args(
        [
            "--board-backend",
            "none",
            "--session-id",
            "exploration_test",
            "--observation-dir",
            str(tmp_path),
            "--step-delay",
            "0",
            "--max-steps",
            "6",
            *extra,
        ]
    )


def _events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_demo_exploration_scene_runs_scripted_zone_travel_and_search(tmp_path):
    result = run_demo(
        _args(
            tmp_path,
            "--exploration-script",
            "zone:gate",
            "--exploration-script",
            "confirm",
            "--exploration-script",
            "zone:courtyard",
            "--exploration-script",
            "zone:courtyard",
            "--exploration-script",
            "zone:courtyard",
            "--exploration-script",
            "confirm",
            "--party-check-roll",
            "hero=10",
            "--party-check-roll",
            "rogue=10",
        )
    )

    events = _events(result.observation_path)
    event_types = [event["event_type"] for event in events]
    assert result.final_state.party_position.zone_id == "courtyard"
    assert "party_zone_changed" in event_types
    assert "party_check_resolved" in event_types
    assert "zone_search_revealed" in event_types
    assert any(point.visibility.value == "visible" for point in result.final_state.points if point.id == "hidden_cache")
    party_check = [event for event in events if event["event_type"] == "party_check_resolved"][-1]
    assert party_check["payload"]["winning_total"] == 12


def test_demo_exploration_scene_rejects_non_adjacent_zone_travel(tmp_path):
    result = run_demo(
        _args(
            tmp_path,
            "--exploration-script",
            "zone:gate",
            "--exploration-script",
            "confirm",
            "--exploration-script",
            "zone:tower",
            "--exploration-script",
            "end",
        )
    )

    events = _events(result.observation_path)
    event_types = [event["event_type"] for event in events]
    assert result.final_state.party_position.zone_id == "gate"
    assert "zone_travel_rejected" in event_types


def test_demo_exploration_scene_inspects_non_anchor_tile_without_options(tmp_path):
    result = run_demo(
        _args(
            tmp_path,
            "--exploration-script",
            "tile:gate",
            "--exploration-script",
            "end",
        )
    )

    events = _events(result.observation_path)
    event_types = [event["event_type"] for event in events]
    assert result.final_state.party_position.zone_id == "gate"
    assert "zone_tile_inspected" in event_types
    assert "zone_option_previewed" not in event_types


def test_demo_exploration_scene_setup_sends_leds_with_fake_connection(tmp_path):
    connection = FakeConnection(scanned=[(1, 1), (1, 1), None])
    args = _args(tmp_path, "--board-backend", "simulator", "--show-leds", "--max-steps", "1")

    result = run_demo(args, connection_factory=lambda args: connection)

    assert result.feedback_events > 0
    assert any(event[0] == "set_leds" for event in connection.events)
    event_types = [event["event_type"] for event in _events(result.observation_path)]
    assert "exploration_setup_started" in event_types
    assert "party_position_set" in event_types


def test_wait_for_scan_or_enter_returns_click():
    connection = FakeConnection(scanned=[(2, 3)])

    event, position = demo_exploration_scene._wait_for_scan_or_enter(
        BoardLedAdapter(connection),
        [(2, 3)],
        timeout_s=1,
    )

    assert event == "click"
    assert position == Coordinate(2, 3)


def test_wait_for_scan_or_enter_cancels_scan_on_enter(monkeypatch):
    class BlockingConnection(FakeConnection):
        def scan_board(self, acceptable_responses=None, *, timeout_s=None):
            self.events.append(("scan_board", list(acceptable_responses or [])))
            time.sleep(0.2)
            return None

    connection = BlockingConnection()

    class _ReadableStdin:
        def fileno(self):
            return sys.stdin.fileno()

        def readline(self):
            return "\n"

    monkeypatch.setattr(demo_exploration_scene.select, "select", lambda *_args, **_kwargs: ([_ReadableStdin()], [], []))
    monkeypatch.setattr(demo_exploration_scene.sys, "stdin", _ReadableStdin())

    event, position = demo_exploration_scene._wait_for_scan_or_enter(
        BoardLedAdapter(connection),
        [(2, 3)],
        timeout_s=1,
    )

    assert event == "enter"
    assert position is None
    assert ("cancel_scan",) in connection.events
