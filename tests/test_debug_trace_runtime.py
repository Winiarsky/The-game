from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.game import Game
from src.ui_client import UIClient, set_default_ui_client


class _DummyConnection:
    def set_leds(self, *_args, **_kwargs):
        return True

    def scan_board(self, *_args, **_kwargs):
        return None

    def leds_off(self, *_args, **_kwargs):
        return True


def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.strip():
            rows.append(json.loads(raw))
    return rows


def test_debug_trace_writes_action_snapshot_and_prompt_events(tmp_path, monkeypatch):
    monkeypatch.setenv("GAME_DEBUG_TRACE", "1")
    monkeypatch.setenv("GAME_DEBUG_TRACE_DIR", str(tmp_path))
    monkeypatch.delenv("PLAYER_UI_URL", raising=False)
    set_default_ui_client(UIClient(base_url=None))

    game = Game(conn=_DummyConnection(), scenario="test_chameleon_gnome")

    class DummyState:
        def ping(self):
            return {"ok": True}

    game.state = DummyState()
    game.run_action("ping")
    game.ui.prompt_choice("Debug prompt", choices=["A", "B"], source="test")

    files = list(tmp_path.glob("*.jsonl"))
    assert len(files) == 1
    rows = _read_jsonl(files[0])
    event_types = [str(item.get("event_type")) for item in rows]

    assert "run_action_start" in event_types
    assert "run_action_end" in event_types
    assert "prompt_start" in event_types
    assert "prompt_answer" in event_types

    run_end = next(item for item in rows if item.get("event_type") == "run_action_end")
    payload = dict(run_end.get("payload") or {})
    snapshot = dict(payload.get("snapshot") or {})
    assert payload.get("action_name") == "ping"
    assert snapshot.get("state") == "DummyState"


def test_debug_trace_logs_run_action_exception(tmp_path, monkeypatch):
    monkeypatch.setenv("GAME_DEBUG_TRACE", "1")
    monkeypatch.setenv("GAME_DEBUG_TRACE_DIR", str(tmp_path))
    monkeypatch.delenv("PLAYER_UI_URL", raising=False)
    set_default_ui_client(UIClient(base_url=None))

    game = Game(conn=_DummyConnection(), scenario="test_chameleon_gnome")

    class DummyState:
        def boom(self):
            raise ValueError("expected-test-error")

    game.state = DummyState()
    with pytest.raises(ValueError):
        game.run_action("boom")

    files = list(tmp_path.glob("*.jsonl"))
    assert len(files) == 1
    rows = _read_jsonl(files[0])
    exception_rows = [item for item in rows if item.get("event_type") == "exception"]
    assert exception_rows
    assert any(
        str((entry.get("payload") or {}).get("where")) == "run_action"
        and str((entry.get("payload") or {}).get("error_type")) == "ValueError"
        for entry in exception_rows
    )
