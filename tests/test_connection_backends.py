from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from board.connection import Connection


class _FakeSimulatorBackend:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def scan_board(self, acceptable_responses=None):
        if acceptable_responses:
            return acceptable_responses[0]
        return (0, 0)

    def set_leds(self, led_updates):
        self.last_led_updates = list(led_updates)

    def leds_off(self):
        self.cleared = True


class _FakeHardwareBackend:
    def __init__(self, scan_cfg, wled_cfg):
        self.scan_cfg = dict(scan_cfg)
        self.wled_cfg = dict(wled_cfg)
        self.serial_port = self.scan_cfg.get("serial_port") or "/dev/fakeUSB0"

    def scan_board(self, acceptable_responses=None):
        if acceptable_responses:
            return acceptable_responses[-1]
        return (1, 1)

    def set_leds(self, led_updates):
        self.last_led_updates = list(led_updates)

    def leds_off(self):
        self.cleared = True

    def close(self):
        self.closed = True


def test_connection_uses_simulator_backend_for_http_target(monkeypatch):
    monkeypatch.setattr("board.connection._SimulatorBackend", _FakeSimulatorBackend)

    conn = Connection("http://127.0.0.1:5000/")

    assert conn.backend == "simulator"
    assert conn.simulator_url == "http://127.0.0.1:5000"
    assert conn.scan_board([(3, 4)]) == (3, 4)


def test_connection_passes_hardware_overrides_to_backend(monkeypatch):
    monkeypatch.setattr("board.connection._HardwareBackend", _FakeHardwareBackend)

    conn = Connection(
        backend="hardware",
        serial_port="/dev/ttyUSB9",
        wled_url="http://192.168.0.99",
    )

    assert conn.backend == "hardware"
    assert conn.serial_port == "/dev/ttyUSB9"
    assert conn.wled_url == "http://192.168.0.99"
    assert conn._backend.scan_cfg["serial_port"] == "/dev/ttyUSB9"
    assert conn._backend.wled_cfg["base_url"] == "http://192.168.0.99"


def test_connection_maps_board_positions_to_new_led_indexes(monkeypatch):
    monkeypatch.setattr("board.connection._HardwareBackend", _FakeHardwareBackend)
    conn = Connection(backend="hardware")

    conn.set_leds([(0, 0), (0, 29), (1, 29), (1, 0)], [0, 255, 0])

    assert conn._backend.last_led_updates == [
        (0, [0, 255, 0]),
        (29, [0, 255, 0]),
        (31, [0, 255, 0]),
        (60, [0, 255, 0]),
    ]


def test_connection_supports_per_cell_colors(monkeypatch):
    monkeypatch.setattr("board.connection._HardwareBackend", _FakeHardwareBackend)
    conn = Connection(backend="hardware")

    conn.set_leds([(0, 0), (1, 29)], [[255, 0, 0], [0, 0, 255]])

    assert conn._backend.last_led_updates == [
        (0, [255, 0, 0]),
        (31, [0, 0, 255]),
    ]
