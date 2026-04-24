from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from board.connection import Connection


class _FakeSimulatorBackend:
    def __init__(self, base_url):
        self.base_url = base_url
        self.last_led_updates = []
        self.cleared = False

    def scan_board(self, acceptable_responses=None):
        if acceptable_responses:
            return acceptable_responses[-1]
        return (4, 5)

    def set_leds(self, led_updates):
        self.last_led_updates = list(led_updates)

    def leds_off(self):
        self.cleared = True

    def cancel_scan(self):
        self.cancelled = True


@pytest.fixture
def conn(monkeypatch):
    monkeypatch.setattr("board.connection._SimulatorBackend", _FakeSimulatorBackend)
    return Connection("http://127.0.0.1:5000/")


def test_connection_builds_simulator_backend(conn):
    assert conn is not None
    assert conn.backend == "simulator"
    assert conn.simulator_url == "http://127.0.0.1:5000"


def test_scan_board_returns_expected_position(conn):
    assert conn.scan_board([(1, 1), (2, 2)]) == (2, 2)


def test_leds_set_and_off(conn):
    conn.set_leds([(0, 0), (1, 29)], [0, 200, 0])
    assert conn._backend.last_led_updates == [
        (0, [0, 200, 0]),
        (31, [0, 200, 0]),
    ]

    conn.leds_off()
    assert conn._backend.cleared is True


def test_cancel_scan_is_forwarded(conn):
    conn.cancel_scan()
    assert conn._backend.cancelled is True
