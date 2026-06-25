import json

import pytest

from dnd_board_game.runtime.session_observer import SessionObserver


def test_session_observer_writes_jsonl_events_with_sequence(tmp_path):
    observer = SessionObserver("manual_demo", tmp_path)

    observer.record("session_started", {"backend": "none"})
    observer.record("session_finished")

    lines = observer.path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2

    first = json.loads(lines[0])
    second = json.loads(lines[1])
    assert first["session_id"] == "manual_demo"
    assert first["seq"] == 1
    assert first["event_type"] == "session_started"
    assert first["payload"] == {"backend": "none"}
    assert first["ts"].endswith("Z")
    assert second["seq"] == 2
    assert second["event_type"] == "session_finished"
    assert second["payload"] == {}


def test_session_observer_rejects_path_like_session_id(tmp_path):
    with pytest.raises(ValueError):
        SessionObserver("../outside", tmp_path)

