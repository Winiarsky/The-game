from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
for path in (PROJECT_ROOT, PROJECT_ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from board import connection as connection_module  # noqa: E402
from board.connection import _SimulatorBackend  # noqa: E402


class _Response:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return dict(self.payload)


def test_simulator_scan_board_waits_without_client_timeout(monkeypatch):
    timeouts: list[object] = []

    def _get(_url: str, *, timeout=None):
        timeouts.append(timeout)
        return _Response({"event": "press", "col": 2, "row": 3})

    monkeypatch.setattr(connection_module.requests, "get", _get)

    backend = _SimulatorBackend("http://board.local")

    assert backend.scan_board([(1, 2)]) == (1, 2)
    assert timeouts == [None]


def test_simulator_scan_board_respects_explicit_timeout(monkeypatch):
    timeouts: list[object] = []

    def _get(_url: str, *, timeout=None):
        timeouts.append(timeout)
        return _Response({"event": "press", "col": 2, "row": 3})

    monkeypatch.setattr(connection_module.requests, "get", _get)

    backend = _SimulatorBackend("http://board.local")

    assert backend.scan_board([(1, 2)], timeout_s=1.5) == (1, 2)
    assert timeouts == [1.5]
