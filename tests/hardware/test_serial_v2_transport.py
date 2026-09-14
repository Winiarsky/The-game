"""Run the real Python transport against the compiled production C++ firmware."""
import json
import os
from pathlib import Path
import select
import subprocess
import threading
import time

import pytest

from board.serial_v2 import BoardProtocolError, FrameReader, SerialV2, coordinates, encode_mask, parse_frame
from tests.hardware.test_firmware_scan import firmware  # noqa: F401


class ProcessPort:
    def __init__(self, binary: Path) -> None:
        self.process = subprocess.Popen([str(binary)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, bufsize=0)
        self.writes: list[dict] = []
        self.writer_threads: set[str] = set()
        self.reader_threads: set[str] = set()
        self._lock = threading.Lock()
        self.extra = bytearray()

    @property
    def in_waiting(self) -> int:
        return 512

    def read(self, size: int) -> bytes:
        self.reader_threads.add(threading.current_thread().name)
        with self._lock:
            if self.extra:
                result = bytes(self.extra[:size])
                del self.extra[:size]
                return result
        if select.select([self.process.stdout], [], [], .01)[0]:
            return os.read(self.process.stdout.fileno(), size)
        return b''

    def write(self, data: bytes) -> int:
        self.writer_threads.add(threading.current_thread().name)
        self.writes.append(json.loads(data))
        self.inject(data.decode().rstrip('\n'))
        return len(data)

    def inject(self, *lines: str) -> None:
        with self._lock:
            self.process.stdin.write(('\n'.join(lines) + '\n').encode())
            self.process.stdin.flush()

    def malformed_event(self, frame: dict) -> None:
        with self._lock:
            self.extra.extend((json.dumps(frame) + '\n').encode())

    def close(self) -> None:
        if self.process.poll() is None:
            self.process.stdin.close()
            self.process.wait(timeout=2)
        assert self.process.returncode == 0, self.process.stderr.read().decode()
        self.process.stdout.close()
        self.process.stderr.close()


@pytest.fixture
def transport(firmware: Path):
    port = ProcessPort(firmware)
    reader = FrameReader()
    info = None
    deadline = time.monotonic() + 2
    while info is None and time.monotonic() < deadline:
        for frame in reader.feed(port.read(512)):
            if frame.get('type') == 'info':
                info = frame
    assert info is not None
    port.reader_threads.clear()
    client = SerialV2(port, info, heartbeat_s=.05, response_s=.15, health_s=.6)
    try:
        yield client, port
    finally:
        client.close()


def prepare(client: SerialV2, key: str = 'die1'):
    return client.prepare_input([(19, 1), (19, 2), (19, 3)], context_key=key,
                                mode='stream', finish_positions=((19, 1),))


def click(port: ProcessPort, row: int = 2) -> None:
    port.inject(f'@contact 19 {row} 1', '@tick 30', f'@contact 19 {row} 0', '@tick 30')


def test_stream_queues_clicks_and_deduplicates_with_one_set_input(transport) -> None:
    client, port = transport
    wait = prepare(client)
    client.command('PING')  # Barrier: SET_INPUT has been processed.
    port.inject('@tick 30')
    click(port)
    click(port)
    click(port, 1)
    assert wait(1) == (19, 2)
    assert prepare(client)(1) == (19, 2)
    assert prepare(client)(1) == (19, 1)
    assert len([x for x in port.writes if x['type'] == 'SET_INPUT']) == 1
    assert port.reader_threads == port.writer_threads == {'board-usb-v2'}
    next_wait = prepare(client, 'die2')
    client.command('PING')
    port.inject('@tick 30')
    click(port)
    assert next_wait(1) == (19, 2)
    assert len([x for x in port.writes if x['type'] == 'SET_INPUT']) == 2


def test_cancel_before_wait_does_not_rearm_stale_context(transport) -> None:
    client, port = transport
    wait = prepare(client)
    client.cancel()
    port.inject('@tick 30')
    click(port)
    assert wait(.1) is None
    assert [x['type'] for x in port.writes if x['type'] in {'SET_INPUT', 'STOP'}] == ['SET_INPUT', 'STOP']


def test_hardware_fault_propagates_and_marks_disconnected(transport) -> None:
    client, port = transport
    wait = prepare(client)
    client.command('PING')
    port.inject('@i2c_error', '@tick 1')
    with pytest.raises(BoardProtocolError, match='i2c_error'):
        wait(1)
    assert not client.connected


def test_timeout_stops_exact_context_without_reconnecting(transport) -> None:
    client, port = transport
    wait = prepare(client)
    with pytest.raises(TimeoutError):
        wait(.06)
    assert client.connected
    assert len([x for x in port.writes if x['type'] == 'HELLO']) == 1
    assert any(x['type'] == 'STOP' and x['context'] == 1 for x in port.writes)


def test_heartbeat_runs_without_browser_polling(transport) -> None:
    client, port = transport
    prepare(client)
    client.command('PING')
    deadline = time.monotonic() + .3
    while time.monotonic() < deadline:
        time.sleep(.01)
    assert len([x for x in port.writes if x['type'] == 'PING']) >= 3
    assert client.connected


@pytest.mark.parametrize('field,value', [('col', True), ('row', 2.1), ('seq', True), ('final', 1), ('uptime_ms', -1)])
def test_invalid_press_is_not_coerced_to_a_real_click(transport, field: str, value: object) -> None:
    client, port = transport
    wait = prepare(client)
    client.command('PING')
    frame = dict(v=2, type='press', boot=client.boot, session=client.session,
                 context=1, seq=1, col=19, row=2, final=False, uptime_ms=100)
    frame[field] = value
    port.malformed_event(frame)
    with pytest.raises(BoardProtocolError):
        wait(1)


def test_old_context_press_cannot_change_new_die(transport) -> None:
    client, port = transport
    prepare(client)
    client.command('PING')
    wait = prepare(client, 'die2')
    client.command('PING')
    port.malformed_event(dict(v=2, type='press', boot=client.boot, session=client.session,
                             context=1, seq=1, col=19, row=2, final=False, uptime_ms=100))
    port.inject('@tick 30')
    click(port, 3)
    assert wait(1) == (19, 3)


def test_strict_frames_and_masks() -> None:
    assert parse_frame('{"v":2,"v":2}') is None
    assert parse_frame('noise {"v":2}') is None
    assert parse_frame('{"v":NaN}') is None
    with pytest.raises(ValueError):
        coordinates([(True, 2)])
    assert coordinates([]) == ()
    assert encode_mask(coordinates([(19, 3), (19, 1), (19, 2)])) == [[19, '0000000e']]
    reader = FrameReader()
    assert not reader.feed(b'x' * 2049 + b'{"v":2}\n')
    assert reader.feed(b'{"v":2}\n') == [{'v': 2}]
