"""Strict v2 serial transport: one port owner, bounded events, stable input contexts."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import json
import secrets
import threading
import time
from typing import Any, Callable

PROTOCOL = 'board_scan_usb_v2'
MAPPING = 'mcp20_21_rows_mcp22_23_cols_20x30_v1'
MAX_FRAME = 2048


class BoardProtocolError(ConnectionError):
    pass


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def parse_frame(raw: bytes | str) -> dict[str, Any] | None:
    try:
        value = json.loads(raw, object_pairs_hook=_unique_object,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Non-finite number')))
    except (ValueError, UnicodeError):
        return None
    return value if isinstance(value, dict) else None


def is_uint(value: object, *, positive: bool = False) -> bool:
    return type(value) is int and (1 if positive else 0) <= value <= 0xffffffff


def is_identifier(value: object) -> bool:
    return isinstance(value, str) and len(value) == 16 and all(c in '0123456789abcdef' for c in value)


def validate_info(frame: dict[str, Any]) -> None:
    if (frame.get('protocol') != PROTOCOL or type(frame.get('v')) is not int or frame.get('v') != 2
            or frame.get('type') not in {'info', 'hello'}):
        raise BoardProtocolError('Plansza wymaga firmware protokołu v2. Wgraj aktualny szkic ESP.')
    if (type(frame.get('cols')) is not int or frame['cols'] != 20
            or type(frame.get('rows')) is not int or frame['rows'] != 30
            or frame.get('mapping_id') != MAPPING or not is_identifier(frame.get('boot'))):
        raise BoardProtocolError('Firmware planszy ma niezgodne wymiary lub mapowanie.')
    if frame.get('ready') is not True:
        raise BoardProtocolError('ESP odpowiada, ale czujniki planszy nie są gotowe.')
    if frame.get('max_frame') != MAX_FRAME or frame.get('event_capacity') != 32:
        raise BoardProtocolError('Firmware ma niezgodne limity protokołu v2.')


def coordinates(positions: list[tuple[int, int]] | tuple[tuple[int, int], ...] | None) -> tuple[tuple[int, int], ...]:
    if positions is None:
        return tuple((col, row) for col in range(20) for row in range(30))
    result = set()
    for position in positions:
        if len(position) != 2:
            raise ValueError('Pole planszy wymaga kolumny i wiersza.')
        col, row = position
        if type(col) is not int or type(row) is not int or not (0 <= col < 20 and 0 <= row < 30):
            raise ValueError('Pole planszy jest poza zakresem 20×30.')
        result.add((col, row))
    return tuple(sorted(result))


def encode_mask(positions: tuple[tuple[int, int], ...]) -> list[list[int | str]]:
    masks: dict[int, int] = {}
    for col, row in positions:
        masks[col] = masks.get(col, 0) | (1 << row)
    return [[col, f'{bits:08x}'] for col, bits in sorted(masks.items())]


class FrameReader:
    def __init__(self) -> None:
        self.buffer = bytearray()
        self.discard = False
        self.last_byte = time.monotonic()

    def feed(self, data: bytes) -> list[dict[str, Any]]:
        now = time.monotonic()
        if self.buffer and now - self.last_byte > 1:
            self.discard = True
        frames = []
        for byte in data:
            self.last_byte = now
            if byte == 10:
                if not self.discard:
                    frame = parse_frame(self.buffer)
                    if frame is not None:
                        frames.append(frame)
                self.buffer.clear()
                self.discard = False
            elif not self.discard:
                if len(self.buffer) >= MAX_FRAME and not (len(self.buffer) == MAX_FRAME and byte == 13):
                    self.discard = True
                else:
                    self.buffer.append(byte)
        return frames


@dataclass
class _Command:
    kind: str
    fields: dict[str, Any]
    done: threading.Event = field(default_factory=threading.Event)
    reply: dict[str, Any] | None = None
    error: Exception | None = None
    id: int = 0
    wire: bytes = b''
    sent: float = 0
    attempts: int = 0


@dataclass
class _Input:
    number: int
    key: object
    positions: tuple[tuple[int, int], ...]
    mode: str
    finish: tuple[tuple[int, int], ...]
    received: int = 0
    final_received: bool = False
    final_consumed: bool = False


class SerialV2:
    """After discovery, the worker is the sole reader AND writer of the port."""

    def __init__(self, port: Any, info: dict[str, Any], *, heartbeat_s: float = 1,
                 response_s: float = .5, health_s: float = 3) -> None:
        validate_info(info)
        self.port = port
        self.info = info
        self.boot = info['boot']
        self.session = secrets.token_hex(8)
        self.heartbeat_s = heartbeat_s
        self.response_s = response_s
        self.health_s = health_s
        self._condition = threading.Condition(threading.RLock())
        self._input_lock = threading.Lock()
        self._commands: deque[_Command] = deque()
        self._events: deque[tuple[int, int]] = deque()
        self._input: _Input | None = None
        self._context = 0
        self._generation = 0
        self._next_id = 0
        self._pending: _Command | None = None
        self._failure: Exception | None = None
        self._closed = False
        self._reader = FrameReader()
        self._last_valid = time.monotonic()
        self._last_ping = self._last_valid
        self.status: dict[str, Any] = {}
        self._thread = threading.Thread(target=self._work, name='board-usb-v2', daemon=True)
        self._thread.start()
        try:
            hello = self.command('HELLO')
            validate_info(hello)
        except Exception:
            self.close()
            raise

    @property
    def connected(self) -> bool:
        with self._condition:
            return not self._closed and self._failure is None

    def _check(self) -> None:
        if self._failure is not None:
            raise BoardProtocolError(str(self._failure)) from self._failure
        if self._closed:
            raise BoardProtocolError('Połączenie z planszą jest zamknięte.')

    def _enqueue(self, kind: str, fields: dict[str, Any]) -> _Command:
        self._check()
        if len(self._commands) >= 32:
            raise BoardProtocolError('Przepełnienie kolejki poleceń planszy.')
        cmd = _Command(kind, fields)
        self._commands.append(cmd)
        self._condition.notify_all()
        return cmd

    def _wait_command(self, cmd: _Command) -> dict[str, Any]:
        if not cmd.done.wait(max(5, self.response_s * 4)):
            self._fail(BoardProtocolError('Przekroczono czas kolejki poleceń planszy.'))
        self._check()
        if cmd.error:
            raise BoardProtocolError(str(cmd.error)) from cmd.error
        if cmd.reply is None:
            raise BoardProtocolError('Plansza nie potwierdziła polecenia.')
        return cmd.reply

    def command(self, kind: str, **fields: Any) -> dict[str, Any]:
        with self._condition:
            cmd = self._enqueue(kind, fields)
        return self._wait_command(cmd)

    def prepare_input(self, positions: list[tuple[int, int]] | None, *,
                      context_key: str = '', mode: str = 'single',
                      finish_positions: tuple[tuple[int, int], ...] = ()) -> Callable[..., tuple[int, int] | None]:
        allowed = coordinates(positions)
        finish = coordinates(finish_positions)
        if mode not in {'single', 'stream'} or not set(finish) <= set(allowed) or (mode == 'single' and finish):
            raise ValueError('Nieprawidłowy kontrakt wejścia planszy.')
        if not allowed:
            self.cancel()
            return lambda timeout_s=None: None
        with self._condition:
            self._check()
            generation = self._generation
            key = (context_key, allowed, mode, finish)
            active = self._input
            if active is None or active.key != key or active.final_consumed:
                self._context += 1
                if self._context > 0xffffffff:
                    raise BoardProtocolError('Wyczerpano konteksty; połącz planszę ponownie.')
                active = _Input(self._context, key, allowed, mode, finish)
                self._input = active
                self._events.clear()
                cmd = self._enqueue('SET_INPUT', dict(context=active.number, mode=mode,
                                                     mask=encode_mask(allowed), finish=encode_mask(finish)))
            else:
                cmd = None

        def wait(timeout_s: float | None = None) -> tuple[int, int] | None:
            if cmd is not None:
                self._wait_command(cmd)
            deadline = None if timeout_s is None else time.monotonic() + max(0, timeout_s)
            with self._condition:
                while True:
                    self._check()
                    if generation != self._generation or self._input is not active:
                        return None
                    if self._events:
                        result = self._events.popleft()
                        if active.mode == 'single' or result in active.finish:
                            active.final_consumed = True
                        return result
                    remaining = None if deadline is None else deadline - time.monotonic()
                    if remaining is not None and remaining <= 0:
                        break
                    self._condition.wait(remaining)
            self.cancel()
            raise TimeoutError('Upłynął czas oczekiwania na wybór gracza.')
        return wait

    def read_input(self, positions: list[tuple[int, int]] | None, *, timeout_s: float | None = None,
                   context_key: str = '', mode: str = 'single',
                   finish_positions: tuple[tuple[int, int], ...] = ()) -> tuple[int, int] | None:
        with self._input_lock:
            wait = self.prepare_input(positions, context_key=context_key, mode=mode, finish_positions=finish_positions)
            return wait(timeout_s)

    def cancel(self) -> None:
        with self._condition:
            self._generation += 1
            active, self._input = self._input, None
            self._events.clear()
            self._condition.notify_all()
            if active is None or not self.connected:
                return
            cmd = self._enqueue('STOP', dict(context=active.number))
        self._wait_command(cmd)

    def close(self) -> None:
        try:
            if self.connected:
                self.cancel()
        except (ConnectionError, TimeoutError):
            pass
        with self._condition:
            self._closed = True
            self._condition.notify_all()
        if threading.current_thread() is not self._thread:
            self._thread.join(timeout=2)
        self.port.close()

    def _fail(self, exc: Exception) -> None:
        with self._condition:
            self._failure = exc
            self._events.clear()
            for cmd in (*self._commands, *([self._pending] if self._pending else [])):
                cmd.error = exc
                cmd.done.set()
            self._commands.clear()
            self._condition.notify_all()

    def _wire(self, kind: str, **fields: Any) -> bytes:
        return (json.dumps(dict(v=2, type=kind, boot=self.boot, session=self.session, **fields),
                           separators=(',', ':')) + '\n').encode('ascii')

    def _write(self, data: bytes) -> None:
        if self.port.write(data) != len(data):
            raise BoardProtocolError('Niepełny zapis do portu planszy.')

    def _work(self) -> None:
        try:
            while not self._closed and self._failure is None:
                with self._condition:
                    now = time.monotonic()
                    if self._pending is None:
                        if self._commands:
                            self._pending = self._commands.popleft()
                        elif self._next_id and now - self._last_ping >= self.heartbeat_s:
                            self._pending = _Command('PING', {})
                        if self._pending:
                            self._next_id += 1
                            self._pending.id = self._next_id
                            self._pending.wire = self._wire(self._pending.kind, id=self._next_id, **self._pending.fields)
                    pending = self._pending
                    if pending and (not pending.attempts or now - pending.sent >= self.response_s):
                        if pending.attempts >= 3:
                            raise BoardProtocolError(f'Brak potwierdzenia {pending.kind} z planszy.')
                        self._write(pending.wire)
                        pending.attempts += 1
                        pending.sent = now
                        if pending.kind == 'PING':
                            self._last_ping = now
                data = self.port.read(min(512, max(1, self.port.in_waiting)))
                for frame in self._reader.feed(data):
                    with self._condition:
                        self._receive(frame)
                if time.monotonic() - self._last_valid > self.health_s:
                    raise BoardProtocolError('Utracono połączenie z planszą (brak statusu v2).')
        except Exception as exc:
            self._fail(exc)

    def _receive(self, frame: dict[str, Any]) -> None:
        if frame.get('protocol') == PROTOCOL and frame.get('type') == 'info':
            validate_info(frame)
            if frame['boot'] != self.boot:
                raise BoardProtocolError('ESP uruchomiło się ponownie; połącz planszę ponownie.')
            return  # Discovery broadcasts do not keep an established session alive.
        if type(frame.get('v')) is not int or frame.get('v') != 2 or frame.get('boot') != self.boot or frame.get('session') != self.session:
            return
        kind = frame.get('type')
        if kind == 'fault' or (kind == 'status' and frame.get('fault')):
            raise BoardProtocolError(f"Awaria planszy: {frame.get('code', frame.get('fault'))}")
        pending = self._pending
        if pending and frame.get('id') == pending.id and type(frame.get('id')) is int:
            expected = {'HELLO': 'hello', 'SET_INPUT': 'input_set', 'STOP': 'stopped', 'PING': 'status'}[pending.kind]
            if kind == 'error':
                raise BoardProtocolError(f"Plansza odrzuciła {pending.kind}: {frame.get('code')}")
            if kind != expected:
                raise BoardProtocolError('Niezgodne potwierdzenie komendy planszy.')
            if pending.kind == 'HELLO':
                validate_info(frame)
            if pending.kind in {'SET_INPUT', 'STOP'} and (not is_uint(frame.get('context'), positive=True) or frame.get('context') != pending.fields['context']):
                raise BoardProtocolError('Potwierdzenie niewłaściwego kontekstu.')
            if frame.get('ready') is not True or frame.get('state') not in {'idle', 'waiting_release', 'scanning', 'completed'}:
                raise BoardProtocolError('Plansza nie potwierdziła gotowego wejścia.')
            pending.reply = frame
            pending.done.set()
            self._pending = None
            self._last_valid = time.monotonic()
        if kind in {'status', 'input_ready'}:
            if (frame.get('state') not in {'idle', 'waiting_release', 'scanning', 'completed'}
                    or frame.get('ready') is not True):
                raise BoardProtocolError('Nieprawidłowy stan planszy.')
            context = frame.get('context')
            if context is not None and not is_uint(context, positive=True):
                raise BoardProtocolError('Nieprawidłowy identyfikator kontekstu.')
            if kind == 'status' and any(not is_uint(frame.get(name)) for name in ('seq', 'ack', 'queued', 'i2c_errors', 'scan_us', 'scan_max_us')):
                raise BoardProtocolError('Nieprawidłowy status czujników.')
            self.status = frame
            self._last_valid = time.monotonic()
        if kind != 'press':
            return
        active = self._input
        if active is None or frame.get('context') != active.number:
            return
        seq, col, row = frame.get('seq'), frame.get('col'), frame.get('row')
        if (not is_uint(seq, positive=True) or not is_uint(frame.get('context'), positive=True)
                or type(col) is not int or type(row) is not int or (col, row) not in active.positions
                or type(frame.get('final')) is not bool or not is_uint(frame.get('uptime_ms'))):
            raise BoardProtocolError('Nieprawidłowe zdarzenie naciśnięcia.')
        if frame['final'] != (active.mode == 'single' or (col, row) in active.finish):
            raise BoardProtocolError('Niezgodne zakończenie wejścia.')
        if seq > active.received + 1:
            return  # The missing event will be retransmitted; never skip to ✓.
        if seq == active.received + 1:
            if active.final_received or len(self._events) >= 64:
                raise BoardProtocolError('Nadmiarowe zdarzenia planszy; wejście zatrzymane.')
            active.received = seq
            active.final_received = frame['final']
            self._events.append((col, row))
            self._condition.notify_all()
        self._write(self._wire('ACK', context=active.number, seq=active.received))
        self._last_valid = time.monotonic()
