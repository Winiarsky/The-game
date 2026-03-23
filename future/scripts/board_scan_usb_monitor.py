#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass

try:
    import serial
    from serial.tools import list_ports
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Brakuje pakietu pyserial. Zainstaluj zależności: pip install -r requirements.txt"
    ) from exc


PROTOCOL_NAME = "board_scan_usb_v1"
DEFAULT_BAUD = 115200
PORT_HINTS = ("esp32", "silabs", "cp210", "wch", "ch340", "usb", "uart")


@dataclass(slots=True)
class PortProbeResult:
    port: str
    description: str
    serial_handle: serial.Serial


def _parse_json_line(raw_line: str) -> dict | None:
    candidates = [raw_line]
    start = raw_line.find("{")
    end = raw_line.rfind("}")
    if start != -1 and end != -1 and end >= start:
        trimmed = raw_line[start : end + 1]
        if trimmed != raw_line:
            candidates.append(trimmed)

    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


def _is_protocol_line(payload: dict | None) -> bool:
    return bool(payload and payload.get("protocol") == PROTOCOL_NAME)


def _candidate_ports() -> list:
    ports = list(list_ports.comports())
    scored: list[tuple[int, object]] = []
    for port in ports:
        haystack = " ".join(
            str(part or "")
            for part in (port.device, port.description, port.manufacturer, port.product)
        ).lower()
        score = 0
        for hint in PORT_HINTS:
            if hint in haystack:
                score += 1
        scored.append((score, port))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [port for _, port in scored]


def _read_lines_until(
    ser: serial.Serial,
    *,
    timeout_s: float,
    echo_unparsed: bool = False,
) -> tuple[dict | None, list[str]]:
    deadline = time.monotonic() + timeout_s
    seen_lines: list[str] = []
    while time.monotonic() < deadline:
        raw = ser.readline().decode("utf-8", errors="replace").strip()
        if not raw:
            continue
        seen_lines.append(raw)
        payload = _parse_json_line(raw)
        if _is_protocol_line(payload):
            return payload, seen_lines
        if echo_unparsed:
            print(f"[{ser.port}] {raw}", file=sys.stderr)
    return None, seen_lines


def probe_port(
    port_name: str,
    baud_rate: int,
    *,
    debug_probe: bool = False,
) -> PortProbeResult | None:
    try:
        ser = serial.Serial(port=port_name, baudrate=baud_rate, timeout=0.25, write_timeout=0.5)
    except serial.SerialException:
        return None

    try:
        ser.setDTR(False)
        ser.setRTS(False)
        time.sleep(0.1)
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        payload, seen_lines = _read_lines_until(ser, timeout_s=6.0, echo_unparsed=debug_probe)
        if payload is None:
            ser.reset_input_buffer()
            ser.write(b"PING\n")
            ser.flush()
            payload, extra_lines = _read_lines_until(ser, timeout_s=3.0, echo_unparsed=debug_probe)
            seen_lines.extend(extra_lines)

        if payload is None:
            if debug_probe and seen_lines:
                print(
                    f"[{port_name}] Nie znaleziono odpowiedzi protokołu {PROTOCOL_NAME}. "
                    "Odczytane linie:",
                    file=sys.stderr,
                )
                for line in seen_lines:
                    print(f"[{port_name}] {line}", file=sys.stderr)
            ser.close()
            return None

        return PortProbeResult(port=port_name, description=str(payload.get("event") or "ready"), serial_handle=ser)
    except Exception as exc:
        if debug_probe:
            print(f"[{port_name}] Błąd podczas probe: {exc}", file=sys.stderr)
        ser.close()
        return None


def autodetect_port(baud_rate: int, *, debug_probe: bool = False) -> PortProbeResult:
    ports = _candidate_ports()
    if not ports:
        raise SystemExit("Nie znaleziono żadnych portów szeregowych.")

    for port in ports:
        result = probe_port(port.device, baud_rate, debug_probe=debug_probe)
        if result is not None:
            return result

    names = ", ".join(port.device for port in ports)
    raise SystemExit(
        "Nie udało się wykryć płytki z protokołem "
        f"{PROTOCOL_NAME}. Sprawdzone porty: {names}"
    )


def open_known_port(port_name: str, baud_rate: int, *, debug_probe: bool = False) -> PortProbeResult:
    result = probe_port(port_name, baud_rate, debug_probe=debug_probe)
    if result is None:
        raise SystemExit(
            f"Port {port_name} nie odpowiedział protokołem {PROTOCOL_NAME}. "
            "Sprawdź port, baud rate i wgrany szkic."
        )
    return result


def format_event(payload: dict) -> str:
    event = str(payload.get("event") or "").lower()
    if event in {"ready", "status", "pong"}:
        rows = payload.get("rows")
        cols = payload.get("cols")
        return (
            f"{event.upper()}: protocol={payload.get('protocol')} "
            f"board={cols}x{rows} rows_addr=0x20,0x21 cols_addr=0x22,0x23"
        )
    if event in {"press", "release"}:
        return (
            f"{event.upper():7} "
            f"col0={int(payload['col']):02d} col1={int(payload['col_1b']):02d} "
            f"row0={int(payload['row']):02d} row1={int(payload['row_1b']):02d} "
            f"ts={payload.get('ts_ms')}ms"
        )
    return json.dumps(payload, ensure_ascii=False)


def monitor_events(ser: serial.Serial, raw_output: bool) -> None:
    print(f"Nasłuch na porcie {ser.port} ({PROTOCOL_NAME})")
    try:
        while True:
            raw = ser.readline().decode("utf-8", errors="replace").strip()
            if not raw:
                continue
            if raw_output:
                print(raw)
                continue
            payload = _parse_json_line(raw)
            if payload is None:
                print(raw)
                continue
            print(format_event(payload))
    except KeyboardInterrupt:
        print("\nZatrzymano nasłuch.")
    finally:
        try:
            ser.close()
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Wykrywa szkic ESP32 board_scan_usb_v1 i wypisuje zdarzenia z planszy 20x30."
    )
    parser.add_argument("--port", help="Port szeregowy, np. /dev/ttyUSB0 lub COM5.")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD, help="Baud rate. Domyślnie 115200.")
    parser.add_argument("--raw", action="store_true", help="Wypisuj surowe linie JSON bez formatowania.")
    parser.add_argument("--debug-probe", action="store_true", help="Pokaż surowe linie podczas wykrywania portu.")
    args = parser.parse_args()

    result = (
        open_known_port(args.port, args.baud, debug_probe=args.debug_probe)
        if args.port
        else autodetect_port(args.baud, debug_probe=args.debug_probe)
    )
    monitor_events(result.serial_handle, raw_output=args.raw)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
