#!/usr/bin/env python3
"""Manual v2 input check; opens only the explicitly supplied serial port."""

from __future__ import annotations

import argparse
import json
import secrets
import time
from typing import Any, Protocol


MAPPING = 'mcp20_21_rows_mcp22_23_cols_20x30_v1'


class SerialLink(Protocol):
    in_waiting: int

    def read(self, size: int = 1) -> bytes: ...
    def write(self, data: bytes) -> int: ...


class Probe:
    def __init__(self, port: SerialLink, *, full: bool) -> None:
        self.port = port
        self.full = full
        self.boot = ''
        self.session = secrets.token_hex(8)
        self.id = 0
        self.seq = 0
        self.finished = False
        self.buffer = bytearray()
        self.discard = False
        self.value = 10

    def read_frames(self) -> list[dict[str, Any]]:
        frames: list[dict[str, Any]] = []
        for byte in self.port.read(min(512, max(1, self.port.in_waiting))):
            if byte == 10:
                if not self.discard:
                    try:
                        frame = json.loads(self.buffer)
                    except (ValueError, UnicodeDecodeError):
                        frame = None
                    if isinstance(frame, dict):
                        frames.append(frame)
                self.buffer.clear()
                self.discard = False
            elif not self.discard:
                if len(self.buffer) == 2048:
                    self.discard = True
                else:
                    self.buffer.append(byte)
        return frames

    def send(self, payload: dict[str, Any]) -> bytes:
        wire = (json.dumps(payload, separators=(',', ':')) + '\n').encode('ascii')
        self.port.write(wire)
        return wire

    def envelope(self, kind: str, **fields: Any) -> dict[str, Any]:
        return dict(v=2, type=kind, boot=self.boot, session=self.session, **fields)

    def current(self, frame: dict[str, Any]) -> bool:
        return frame.get('v') == 2 and frame.get('boot') == self.boot and frame.get('session') == self.session

    def event(self, frame: dict[str, Any]) -> None:
        if frame.get('type') == 'info' and frame.get('boot') != self.boot:
            raise RuntimeError('ESP uruchomiło się ponownie. Uruchom test jeszcze raz.')
        if not self.current(frame):
            return
        if frame.get('type') == 'fault' or frame.get('fault'):
            raise RuntimeError(f"Awaria skanera: {frame.get('code', frame.get('fault'))}")
        if frame.get('type') != 'press' or frame.get('context') != 1:
            return
        seq, col, row = frame.get('seq'), frame.get('col'), frame.get('row')
        if any(type(value) is not int for value in (seq, col, row)):
            raise RuntimeError('Nieprawidłowy typ danych press.')
        if not (0 <= col < 20 and 0 <= row < 30) or (not self.full and (col != 19 or row not in (1, 2, 3))):
            raise RuntimeError('Naciśnięcie spoza aktywnej maski.')
        expected_final = self.full or row == 1
        if type(frame.get('final')) is not bool or frame['final'] != expected_final:
            raise RuntimeError('Nieprawidłowe zakończenie kontekstu.')
        if seq > self.seq + 1:
            return  # Wait for retransmission of the missing event.
        if seq == self.seq + 1:
            if self.finished:
                raise RuntimeError('ESP wysłało nowe naciśnięcie po zakończeniu wyboru.')
            self.seq = seq
            if not self.full and row in (2, 3):
                self.value = max(1, min(20, self.value + (1 if row == 2 else -1)))
            self.finished = frame['final']
            print(f'Naciśnięcie #{seq}: ({col}, {row}), wynik próbny: {self.value}'
                  + (' — KONIEC' if self.finished else ''), flush=True)
        if self.seq:
            self.send(self.envelope('ACK', context=1, seq=self.seq))

    def command(self, kind: str, **fields: Any) -> dict[str, Any]:
        self.id += 1
        wire = self.send(self.envelope(kind, id=self.id, **fields))
        for attempt in range(3):
            deadline = time.monotonic() + 0.5
            while time.monotonic() < deadline:
                reply = None
                for frame in self.read_frames():
                    self.event(frame)
                    if self.current(frame) and frame.get('id') == self.id:
                        if frame.get('type') == 'error':
                            raise RuntimeError(f"ESP odrzuciło {kind}: {frame.get('code')}")
                        expected = {'HELLO': 'hello', 'SET_INPUT': 'input_set', 'PING': 'status', 'STOP': 'stopped'}[kind]
                        if frame.get('type') != expected:
                            raise RuntimeError(f'Nieprawidłowe potwierdzenie {kind}.')
                        reply = frame
                # A serial chunk may contain the reply followed by press.
                # Consume the entire chunk before returning the command result.
                if reply is not None:
                    return reply
            if attempt < 2:
                self.port.write(wire)
        raise RuntimeError(f'Brak potwierdzenia {kind}.')

    def discover(self) -> None:
        deadline = time.monotonic() + 8
        next_ping = 0.0
        while time.monotonic() < deadline:
            if time.monotonic() >= next_ping:
                self.port.write(b'PING\n')
                next_ping = time.monotonic() + 1
            for frame in self.read_frames():
                if frame.get('protocol') != 'board_scan_usb_v2' or frame.get('type') != 'info':
                    continue
                if frame.get('mapping_id') != MAPPING or (frame.get('cols'), frame.get('rows')) != (20, 30):
                    raise RuntimeError('Firmware ma inne mapowanie planszy.')
                if frame.get('ready') is not True:
                    raise RuntimeError('ESP odpowiada, ale czujniki MCP nie są gotowe.')
                boot = frame.get('boot')
                if not isinstance(boot, str) or len(boot) != 16 or any(c not in '0123456789abcdef' for c in boot):
                    raise RuntimeError('Nieprawidłowy identyfikator ESP.')
                self.boot = boot
                print(f"Firmware: {frame.get('firmware')}, boot: {self.boot}", flush=True)
                return
        raise RuntimeError('Brak gotowego firmware v2 na wskazanym porcie.')

    def run(self, duration: float) -> None:
        self.discover()
        hello = self.command('HELLO')
        if hello.get('ready') is not True or hello.get('mapping_id') != MAPPING:
            raise RuntimeError('Sesja nie potwierdziła gotowości właściwej planszy.')
        mask = [[col, '3fffffff'] for col in range(20)] if self.full else [[19, '0000000e']]
        armed = self.command('SET_INPUT', context=1, mode='single' if self.full else 'stream',
                             mask=mask, finish=[] if self.full else [[19, '00000002']])
        if armed.get('context') != 1:
            raise RuntimeError('Potwierdzono niewłaściwy kontekst.')
        print('Zwolnij przyciski. Test pełnej planszy: naciśnij jedno pole.' if self.full else
              'Zwolnij przyciski. Testuj − / +; ✓ kończy test. Wynik początkowy: 10.', flush=True)
        deadline = time.monotonic() + duration
        next_ping = time.monotonic() + 1
        try:
            while not self.finished and time.monotonic() < deadline:
                for frame in self.read_frames():
                    self.event(frame)
                if time.monotonic() >= next_ping:
                    status = self.command('PING')
                    if status.get('state') == 'waiting_release' and status.get('held'):
                        print(f"Przytrzymane pola: {status['held']}", flush=True)
                    next_ping = time.monotonic() + 1
        finally:
            self.command('STOP', context=1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', required=True, help='Np. /dev/ttyUSB0 albo COM3; zamknij grę i monitor portu.')
    parser.add_argument('--full', action='store_true', help='Jednorazowy skan wszystkich 600 pól zamiast panelu.')
    parser.add_argument('--duration', type=float, default=60, help='Maksymalny czas testu w sekundach.')
    args = parser.parse_args()
    if args.duration <= 0:
        parser.error('--duration musi być dodatnie')
    import serial  # Existing project dependency; no connection on import or --help.

    try:
        with serial.Serial(args.port, 115200, timeout=0.05, write_timeout=0.5) as port:
            Probe(port, full=args.full).run(args.duration)
    except (RuntimeError, serial.SerialException, KeyboardInterrupt) as exc:
        print(f'Test zakończony: {exc}')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
