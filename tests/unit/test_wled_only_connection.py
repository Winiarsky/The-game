"""LED-only output owns no serial scanner and keeps retry diagnostics independent."""

from __future__ import annotations

import threading
from typing import Any

import pytest

from board.connection import Connection
from board.led_output import LedOutputError
from dnd_board_game.hardware.board_session import BoardSessionAdapter
from dnd_board_game.hardware.led_feedback import LedFeedback, LedFrame, LedRole
from dnd_board_game.world import Coordinate


class FakeWled:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = dict(config)
        self.last_error = "WLED offline"
        self.online = True
        self.frames: list[tuple[list[tuple[int, list[int]]], dict[str, Any]]] = []
        self.clears = 0
        self.attempted = threading.Event()

    def clear(self) -> bool:
        self.clears += 1
        self.attempted.set()
        return self.online

    def set_leds(self, updates: list[tuple[int, list[int]]], **kwargs: Any) -> bool:
        self.frames.append((updates, kwargs))
        self.attempted.set()
        return self.online


@pytest.fixture
def wled_only(monkeypatch: pytest.MonkeyPatch) -> list[FakeWled]:
    clients: list[FakeWled] = []

    def forbidden(*args: Any, **kwargs: Any) -> None:
        pytest.fail("LED-only profile tried to create or probe serial input")

    def create(config: dict[str, Any]) -> FakeWled:
        client = FakeWled(config)
        clients.append(client)
        return client

    monkeypatch.setattr("board.connection._open_serial_probe", forbidden)
    monkeypatch.setattr("board.connection._candidate_ports", forbidden)
    monkeypatch.setattr("board.connection.SerialV2", forbidden)
    monkeypatch.setattr("board.connection._WledClient", create)
    return clients


def applied(connection: Connection) -> None:
    output = connection._backend.output
    assert output.wait_applied(output.revision, threading.Event(), timeout_s=1)


def test_wled_backend_never_creates_serial_and_maps_led_frames(wled_only: list[FakeWled]) -> None:
    connection = Connection(backend="wled", wled_url="http://led-test/", serial_port="ignored")
    try:
        assert connection.backend == "wled"
        assert connection.serial_port is None
        assert connection.connected and connection.can_display_leds
        assert not connection.can_scan
        assert wled_only[0].config["base_url"] == "http://led-test/"
        assert connection.wled_url == "http://led-test"
        connection.set_leds([(2, 3)], [10, 20, 30], brightness=90, replace=True, transition_ms=80)
        applied(connection)
        updates, options = wled_only[0].frames[-1]
        assert updates == [(int(connection.led_config["2"]["3"]), [10, 20, 30])]
        assert options == dict(brightness=90, replace=True, transition_ms=80)
        assert not connection.led_status["pending"]
        assert not connection.led_status["error"]
    finally:
        connection.close()
    assert not connection.connected and not connection.can_display_leds
    assert wled_only[0].clears >= 1
    connection.close()


def test_adapter_rejects_scan_but_reset_cancel_and_leds_remain_usable(wled_only: list[FakeWled]) -> None:
    adapter = BoardSessionAdapter.connect(backend="wled", wled_url="http://led-test")
    connection = adapter.connection
    try:
        assert adapter.connected and adapter.can_display_leds
        assert not adapter.can_scan
        with pytest.raises(ValueError, match="nie obsługuje skanowania"):
            connection.scan_board([(2, 3)])
        with pytest.raises(ValueError, match="nie obsługuje skanowania"):
            connection.prepare_scan([(2, 3)], context_key="test", mode="single", finish_positions=())
        with pytest.raises(ValueError, match="nie obsługuje skanowania"):
            adapter.scan((Coordinate(2, 3),), timeout_s=1)
        with pytest.raises(ValueError, match="nie obsługuje skanowania"):
            adapter.prepare_scan((Coordinate(2, 3),), context_key="test", mode="single", finish_positions=())
        adapter.cancel_input()
        assert adapter.reset_scan() == "not_required"
        connection.cancel_scan()
        connection.rearm_scan()
        connection.reset_connection()
        feedback = LedFeedback((LedFrame((Coordinate(2, 3),), (10, 20, 30), LedRole.MARKER),))
        adapter.show_scan_feedback(feedback)
        applied(connection)
        assert wled_only[0].frames[-1][1]["brightness"] is None
    finally:
        adapter.close()
    assert not adapter.connected


def test_offline_wled_keeps_profile_connected_and_recovers_latest_frame(wled_only: list[FakeWled]) -> None:
    connection = Connection(backend="wled", wled_url="http://led-test")
    client = wled_only[0]
    try:
        applied(connection)
        client.online = False
        client.attempted.clear()
        connection.set_leds([(1, 2)], [255, 0, 0])
        assert client.attempted.wait(1)
        with pytest.raises(LedOutputError):
            connection._backend.output.wait_applied(connection._backend.output.revision,
                                                    threading.Event(), timeout_s=.05)
        assert connection.connected and not connection.can_scan
        assert connection.led_status["pending"]
        assert connection.led_status["error"] == "WLED offline"
        client.online = True
        connection.set_leds([(3, 4)], [0, 255, 0])
        applied(connection)
        assert client.frames[-1][0] == [(int(connection.led_config["3"]["4"]), [0, 255, 0])]
        assert not connection.led_status["pending"]
        assert connection.led_status["error"] == ""
    finally:
        client.online = True
        connection.close()


def test_unknown_backend_does_not_fall_back_to_serial(wled_only: list[FakeWled]) -> None:
    with pytest.raises(ValueError, match="Unsupported board backend"):
        Connection(backend="wlled")
    assert not wled_only


@pytest.mark.parametrize("target", ["wled", None])
def test_wled_can_be_selected_as_target_or_config_default(
    target: str | None, wled_only: list[FakeWled], monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("board.connection.connection_backend", lambda config: "wled")
    connection = Connection(target, wled_url="http://led-test")
    try:
        assert connection.backend == "wled"
        assert not connection.can_scan
    finally:
        connection.close()


@pytest.mark.parametrize("backend", ["hardware", "simulator"])
def test_existing_backends_keep_input_and_output_capabilities(
    backend: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Device:
        connected = True

        def __init__(self, *args: Any) -> None:
            pass

    monkeypatch.setattr("board.connection._HardwareBackend", Device)
    monkeypatch.setattr("board.connection._SimulatorBackend", Device)
    connection = Connection(backend=backend)
    assert connection.connected and connection.can_scan and connection.can_display_leds
