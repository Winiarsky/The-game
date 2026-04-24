from __future__ import annotations

import threading
import time
from pathlib import Path
import sys
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from game import Game  # noqa: E402


class _FakeConn:
    def __init__(self):
        self.cancel_calls = 0
        self.cancel_event = threading.Event()

    def scan_board(self, acceptable_responses=None, *, timeout_s=None):  # noqa: ARG002
        self.cancel_event.wait(timeout=1.0)
        if self.cancel_event.is_set():
            return None
        return (0, 0)

    def cancel_scan(self):
        self.cancel_calls += 1
        self.cancel_event.set()


def test_game_scan_wrapper_sends_stop_when_cancel_prompt_is_answered():
    game = Game.__new__(Game)
    fake_conn = _FakeConn()
    cancelled_scopes: list[str] = []
    created_prompts: list[dict[str, object]] = []

    game.conn = fake_conn
    game.ui = SimpleNamespace(
        enabled=True,
        _create_prompt=lambda *_args, **kwargs: created_prompts.append(dict(kwargs)) or "prompt-1",
        _wait_for_text_answer=lambda *_args, **_kwargs: "__cancel_board_scan__",
    )
    game.player_prompt = SimpleNamespace(cancel_scope=lambda scope_key: cancelled_scopes.append(scope_key) or True)
    game._board_scan_prompt_lock = threading.Lock()
    game._board_scan_prompt_seq = 0
    game._raw_conn_scan_board = fake_conn.scan_board

    result = Game._scan_board_with_cancel_prompt(game, [(1, 1)], timeout_s=None)

    assert result is None
    assert fake_conn.cancel_calls == 1
    assert cancelled_scopes and cancelled_scopes[0].startswith("board_scan:")
    assert created_prompts and created_prompts[0]["source"] == "board_scan_cancel"


def test_game_scan_wrapper_closes_prompt_with_technical_answer_after_success():
    game = Game.__new__(Game)
    answered_prompts: list[tuple[str, object]] = []

    game.conn = SimpleNamespace(scan_board=lambda *_args, **_kwargs: (1, 1))
    game.ui = SimpleNamespace(
        enabled=True,
        _create_prompt=lambda *_args, **_kwargs: "prompt-42",
        _wait_for_text_answer=lambda *_args, **_kwargs: None,
    )
    game.player_prompt = SimpleNamespace(
        answer=lambda prompt_id, answer: answered_prompts.append((prompt_id, answer)) or True,
        cancel_scope=lambda *_args, **_kwargs: False,
    )
    game._board_scan_prompt_lock = threading.Lock()
    game._board_scan_prompt_seq = 0
    game._raw_conn_scan_board = game.conn.scan_board

    result = Game._scan_board_with_cancel_prompt(game, [(1, 1)], timeout_s=None)

    assert result == (1, 1)
    assert answered_prompts == [("prompt-42", "__board_scan_closed__")]
