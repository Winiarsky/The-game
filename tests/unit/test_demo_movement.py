import argparse
import json

import pytest

from dnd_board_game.runtime.demo_movement import build_parser, parse_coordinate, run_demo
from dnd_board_game.world import Coordinate


def _args(tmp_path, *extra):
    parser = build_parser()
    return parser.parse_args(
        [
            "--board-backend",
            "none",
            "--session-id",
            "test_demo",
            "--observation-dir",
            str(tmp_path),
            *extra,
        ]
    )


def _events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_parse_coordinate_accepts_col_row_format():
    assert parse_coordinate("3,4") == Coordinate(3, 4)


def test_parse_coordinate_rejects_invalid_format():
    with pytest.raises(argparse.ArgumentTypeError):
        parse_coordinate("3:4")


def test_run_demo_with_none_backend_creates_valid_path_and_observation(tmp_path):
    result = run_demo(_args(tmp_path, "--destination", "3,3"))

    assert result.path.valid is True
    assert result.path.destination == Coordinate(3, 3)
    assert result.feedback_sent is False
    assert result.observation_path.exists()

    event_types = [event["event_type"] for event in _events(result.observation_path)]
    assert event_types == [
        "session_started",
        "board_backend_selected",
        "movement_range_requested",
        "movement_range_calculated",
        "movement_path_selected",
        "session_finished",
    ]


def test_run_demo_records_rejected_movement_for_blocked_destination(tmp_path):
    result = run_demo(_args(tmp_path, "--destination", "1,0"))

    assert result.path.valid is False
    event_types = [event["event_type"] for event in _events(result.observation_path)]
    assert "movement_rejected" in event_types
    assert "movement_path_selected" not in event_types

