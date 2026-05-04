from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from board.connection import Connection, _HardwareBackend


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

    def cancel_scan(self):
        self.cancelled = True

    def rearm_scan(self):
        self.rearmed = True


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

    def cancel_scan(self):
        self.cancelled = True

    def reset_connection(self):
        self.reset = True

    def rearm_scan(self):
        self.rearmed = True

    def close(self):
        self.closed = True


class _FakeSerial:
    def __init__(self):
        self.writes = []
        self.reset_input_calls = 0

    def write(self, data):
        self.writes.append(data.decode("ascii").strip())

    def flush(self):
        return None

    def reset_input_buffer(self):
        self.reset_input_calls += 1


def test_connection_uses_simulator_backend_for_http_target(monkeypatch):
    monkeypatch.setattr("board.connection._SimulatorBackend", _FakeSimulatorBackend)

    conn = Connection("http://127.0.0.1:5000/")

    assert conn.backend == "simulator"
    assert conn.simulator_url == "http://127.0.0.1:5000"
    assert conn.scan_board([(3, 4)]) == (3, 4)


def test_connection_allows_cancelled_scan_from_backend(monkeypatch):
    class _CancelSimulatorBackend:
        def __init__(self, base_url: str):
            self.base_url = base_url

        def scan_board(self, acceptable_responses=None, *, timeout_s=None):  # noqa: ARG002
            return None

        def set_leds(self, led_updates):  # noqa: ARG002
            return None

        def leds_off(self):
            return None

    monkeypatch.setattr("board.connection._SimulatorBackend", _CancelSimulatorBackend)

    conn = Connection("http://127.0.0.1:5000/")

    assert conn.scan_board([(3, 4)]) is None


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


def test_connection_forwards_cancel_scan_to_simulator_backend(monkeypatch):
    monkeypatch.setattr("board.connection._SimulatorBackend", _FakeSimulatorBackend)

    conn = Connection("http://127.0.0.1:5000/")
    conn.cancel_scan()

    assert getattr(conn._backend, "cancelled", False) is True


def test_connection_forwards_cancel_scan_to_hardware_backend(monkeypatch):
    monkeypatch.setattr("board.connection._HardwareBackend", _FakeHardwareBackend)

    conn = Connection(backend="hardware")
    conn.cancel_scan()

    assert getattr(conn._backend, "cancelled", False) is True


def test_connection_forwards_rearm_scan_to_backend(monkeypatch):
    monkeypatch.setattr("board.connection._HardwareBackend", _FakeHardwareBackend)

    conn = Connection(backend="hardware")
    conn.rearm_scan()

    assert getattr(conn._backend, "rearmed", False) is True


def test_connection_forwards_reset_connection_to_backend(monkeypatch):
    monkeypatch.setattr("board.connection._HardwareBackend", _FakeHardwareBackend)

    conn = Connection(backend="hardware")
    conn.reset_connection()

    assert getattr(conn._backend, "reset", False) is True


def test_hardware_backend_stops_previous_scan_before_new_scan():
    backend = _HardwareBackend.__new__(_HardwareBackend)
    fake_serial = _FakeSerial()
    backend.ser = fake_serial
    backend.scan_command = "SCAN"
    backend.stop_command = "STOP"
    backend.stop_before_scan = True
    backend.pre_scan_stop_s = 0.0
    backend.pre_scan_delay_s = 0.0

    backend._send_scan_command()

    assert fake_serial.writes == ["STOP", "SCAN"]
    assert fake_serial.reset_input_calls == 1


def test_hardware_backend_rearm_scan_sends_stop_then_scan():
    backend = _HardwareBackend.__new__(_HardwareBackend)
    fake_serial = _FakeSerial()
    backend.ser = fake_serial
    backend.scan_command = "SCAN"
    backend.stop_command = "STOP"
    backend.stop_before_scan = True
    backend.pre_scan_stop_s = 0.0
    backend.pre_scan_delay_s = 0.0

    backend.rearm_scan()

    assert fake_serial.writes == ["STOP", "SCAN"]
    assert fake_serial.reset_input_calls == 1


def test_hardware_backend_stops_scan_after_rejected_press():
    backend = _HardwareBackend.__new__(_HardwareBackend)
    fake_serial = _FakeSerial()
    backend.ser = fake_serial
    backend.protocol_name = "board_scan_usb_v1"
    backend.scan_command = "SCAN"
    backend.stop_command = "STOP"
    backend.stop_before_scan = False
    backend.pre_scan_delay_s = 0.0
    payloads = iter(
        [
            {"protocol": "board_scan_usb_v1", "event": "press", "col": 1, "row": 1},
            {"protocol": "board_scan_usb_v1", "event": "press", "col": 2, "row": 2},
        ]
    )
    backend._read_protocol_payload = lambda *, timeout_s=None: next(payloads)  # noqa: ARG005

    result = backend.scan_board([(2, 2)])

    assert result == (2, 2)
    assert fake_serial.writes == ["SCAN", "STOP", "SCAN"]


def test_hardware_backend_recovers_idle_scan_with_soft_reset():
    class _IdleSerial(_FakeSerial):
        def readline(self):
            if self.writes.count("SCAN") < 2:
                time.sleep(0.002)
                return b""
            return b'{"protocol":"board_scan_usb_v1","event":"press","col":2,"row":2}\n'

    backend = _HardwareBackend.__new__(_HardwareBackend)
    fake_serial = _IdleSerial()
    backend.ser = fake_serial
    backend.protocol_name = "board_scan_usb_v1"
    backend.scan_command = "SCAN"
    backend.stop_command = "STOP"
    backend.stop_before_scan = False
    backend.pre_scan_delay_s = 0.0
    backend.scan_recovery_timeout_s = 0.001

    result = backend.scan_board([(2, 2)])

    assert result == (2, 2)
    assert fake_serial.writes == ["SCAN", "STOP", "SCAN"]
