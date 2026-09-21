"""Discovery diagnostics use fake ports and never access attached hardware."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

import board.connection as connection
from board.serial_v2 import BoardProtocolError, MAPPING, PROTOCOL


class FakeSerialError(OSError):
    pass


class FakePort:
    def __init__(self, payload: bytes = b"", error: FakeSerialError | None = None) -> None:
        self.port: str | None = None
        self.dtr = self.rts = True
        self.data = bytearray(payload)
        self.error = error
        self.writes: list[bytes] = []
        self.closed = False

    @property
    def in_waiting(self) -> int:
        return len(self.data)

    def open(self) -> None:
        assert not self.dtr and not self.rts
        if self.error is not None:
            raise self.error

    def read(self, size: int) -> bytes:
        chunk = bytes(self.data[:size])
        del self.data[:size]
        return chunk

    def write(self, data: bytes) -> int:
        self.writes.append(data)
        return len(data)

    def close(self) -> None:
        self.closed = True


def info(**overrides: Any) -> bytes:
    frame = dict(protocol=PROTOCOL, v=2, type="info", firmware="board_scan_protocol_v2_2",
                 cols=20, rows=30, mapping_id=MAPPING, boot="a18b920000000001",
                 ready=True, max_frame=2048, event_capacity=32)
    frame.update(overrides)
    return (json.dumps(frame) + "\n").encode()


def install_ports(monkeypatch: pytest.MonkeyPatch, *ports: FakePort) -> list[dict[str, Any]]:
    remaining = iter(ports)
    calls: list[dict[str, Any]] = []

    def factory(**kwargs: Any) -> FakePort:
        calls.append(kwargs)
        return next(remaining)

    ticks = iter(number / 10 for number in range(1000))
    monkeypatch.setattr(connection, "serial", SimpleNamespace(Serial=factory,
                                                             SerialException=FakeSerialError))
    monkeypatch.setattr(connection, "time", SimpleNamespace(monotonic=lambda: next(ticks)))
    return calls


@pytest.mark.parametrize("number,reason", [(2, "No such file or directory"),
                                           (13, "Permission denied"), (16, "Device or resource busy")])
def test_explicit_port_open_failure_reports_actual_cause_without_fallback(
    monkeypatch: pytest.MonkeyPatch, number: int, reason: str,
) -> None:
    error = FakeSerialError(number, reason)
    port = FakePort(error=error)
    calls = install_ports(monkeypatch, port)

    def unexpected_discovery() -> list[Any]:
        pytest.fail("An explicit port must not fall back to a different device.")

    monkeypatch.setattr(connection, "_candidate_ports", unexpected_discovery)
    with pytest.raises(RuntimeError, match="Nie można otworzyć portu planszy /dev/missing-board") as caught:
        connection._open_serial_probe({"serial_port": "/dev/missing-board"})

    assert caught.value.__cause__ is error
    assert reason in str(caught.value)
    assert "nie odpowiedział" not in str(caught.value)
    assert len(calls) == 1
    assert not port.writes


def test_open_port_without_protocol_response_keeps_timeout_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    port = FakePort(b"unrelated serial device\n")
    install_ports(monkeypatch, port)
    with pytest.raises(RuntimeError, match=f"Port /dev/silent nie odpowiedział protokołem {PROTOCOL}"):
        connection._open_serial_probe({"serial_port": "/dev/silent", "probe_timeout_s": 2.5})

    assert port.closed
    assert len(port.writes) >= 2
    assert set(port.writes) == {b"PING\n"}


def test_autodetection_skips_unavailable_ports_and_keeps_successful_port_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unavailable = FakePort(error=FakeSerialError(13, "Permission denied"))
    silent = FakePort()
    working = FakePort(info())
    calls = install_ports(monkeypatch, unavailable, silent, working)
    monkeypatch.setattr(connection, "_candidate_ports", lambda: [
        SimpleNamespace(device=name) for name in ("/dev/denied", "/dev/silent", "/dev/board")
    ])

    result = connection._open_serial_probe({"probe_timeout_s": .5})

    assert result.port == "/dev/board"
    assert result.serial_handle is working
    assert result.info["firmware"] == "board_scan_protocol_v2_2"
    assert len(calls) == 3
    assert silent.closed and not working.closed
    assert working.writes == [b"PING\n"]
    assert calls[-1]["baudrate"] == 115200


@pytest.mark.parametrize("payload,diagnostic", [
    (info(protocol="board_scan_usb_v1"), "stary protokół"),
    (info(ready=False), "czujniki planszy nie są gotowe"),
    (info(cols=21), "niezgodne wymiary lub mapowanie"),
])
def test_protocol_failures_remain_specific_and_close_port(
    monkeypatch: pytest.MonkeyPatch, payload: bytes, diagnostic: str,
) -> None:
    port = FakePort(payload)
    install_ports(monkeypatch, port)
    with pytest.raises(BoardProtocolError, match=diagnostic):
        connection._open_serial_probe({"serial_port": "/dev/board"})
    assert port.closed


@pytest.mark.parametrize("payload", [info(protocol="board_scan_usb_v1"), info(cols=21), info(ready=False)])
def test_autodetection_continues_after_incompatible_board(
    monkeypatch: pytest.MonkeyPatch, payload: bytes,
) -> None:
    other, working = FakePort(payload), FakePort(info())
    install_ports(monkeypatch, other, working)
    monkeypatch.setattr(connection, "_candidate_ports", lambda: [
        SimpleNamespace(device=name) for name in ("/dev/ttyUSB0", "/dev/ttyUSB2")
    ])
    result = connection._open_serial_probe({"serial_port": ""})
    assert result.port == "/dev/ttyUSB2"
    assert other.closed and not working.closed


def test_autodetection_continues_after_disconnect_during_read(monkeypatch: pytest.MonkeyPatch) -> None:
    class DisconnectedPort(FakePort):
        def read(self, size: int) -> bytes:
            raise FakeSerialError("USB disconnected")

    disconnected, working = DisconnectedPort(), FakePort(info())
    install_ports(monkeypatch, disconnected, working)
    monkeypatch.setattr(connection, "_candidate_ports", lambda: [
        SimpleNamespace(device=name) for name in ("/dev/lost", "/dev/board")
    ])
    result = connection._open_serial_probe({})
    assert result.serial_handle is working
    assert disconnected.closed


def test_autodetection_failure_lists_checked_ports_and_protocol_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    silent, old = FakePort(), FakePort(info(protocol="board_scan_usb_v1"))
    install_ports(monkeypatch, silent, old)
    monkeypatch.setattr(connection, "_candidate_ports", lambda: [
        SimpleNamespace(device=name) for name in ("/dev/silent", "/dev/old")
    ])
    with pytest.raises(RuntimeError) as caught:
        connection._open_serial_probe({"probe_timeout_s": .5})
    assert "Sprawdzone porty: /dev/silent, /dev/old" in str(caught.value)
    assert "stary protokół" in str(caught.value)
    assert silent.closed and old.closed


def test_autodetection_enumerates_ports_again_on_reconnect(monkeypatch: pytest.MonkeyPatch) -> None:
    first, reconnected = FakePort(info()), FakePort(info())
    install_ports(monkeypatch, first, reconnected)
    devices = iter(("/dev/ttyUSB1", "/dev/ttyUSB0"))
    monkeypatch.setattr(connection, "_candidate_ports", lambda: [SimpleNamespace(device=next(devices))])
    initial = connection._open_serial_probe({})
    initial.serial_handle.close()
    later = connection._open_serial_probe({})
    assert initial.port == "/dev/ttyUSB1"
    assert later.port == "/dev/ttyUSB0"
    assert later.serial_handle is reconnected
