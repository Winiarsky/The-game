from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from board.connection import Connection


class _FakeHardwareBackend:
    def __init__(self, scan_cfg, wled_cfg):
        self.scan_cfg = dict(scan_cfg)
        self.wled_cfg = dict(wled_cfg)
        self.serial_port = self.scan_cfg.get("serial_port") or "/dev/fakeUSB0"
        self.led_updates = []
        self.closed = False

    def scan_board(self, acceptable_responses=None, *, timeout_s=None):
        if acceptable_responses:
            return acceptable_responses[0]
        return (0, 0)

    def set_leds(self, led_updates):
        self.led_updates = list(led_updates)

    def leds_off(self):
        self.led_updates = []

    def close(self):
        self.closed = True


@pytest.fixture
def conn(monkeypatch):
    monkeypatch.setattr("board.connection._HardwareBackend", _FakeHardwareBackend)
    return Connection(backend="hardware", serial_port="/dev/ttyUSB0", wled_url="http://192.168.0.77")


def test_connection_builds_hardware_backend(conn):
    assert conn is not None
    assert conn.backend == "hardware"
    assert conn.serial_port == "/dev/ttyUSB0"
    assert conn.wled_url == "http://192.168.0.77"


def test_scan_board_returns_board_position(conn):
    assert conn.scan_board([(2, 3)]) == (2, 3)


def test_scan_board_forwards_timeout(conn):
    assert conn.scan_board([(2, 3)], timeout_s=4.0) == (2, 3)


def test_leds_set_and_off(conn):
    conn.set_leds([(0, 0), (1, 29)], [0, 200, 0])
    assert conn._backend.led_updates == [
        (0, [0, 200, 0]),
        (31, [0, 200, 0]),
    ]

    conn.leds_off()
    assert conn._backend.led_updates == []
