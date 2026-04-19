#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from typing import Any

import requests

try:
    import serial
    from serial.tools import list_ports
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Brakuje pakietu pyserial. Uruchom: ./.venv/bin/pip install pyserial"
    ) from exc

from board20x30_mapping import (
    BOARD_COLS,
    BOARD_ROWS,
    TOTAL_LED_COUNT,
    board_cell_to_led_index,
    turnaround_led_index_after_column,
)

PROTOCOL_NAME = "board_scan_usb_v1"
DEFAULT_BAUD = 115200
DEFAULT_COLOR = "00FF00"
PORT_HINTS = ("esp32", "silabs", "cp210", "wch", "ch340", "usb", "uart")


@dataclass(slots=True)
class PortProbeResult:
    port: str
    description: str
    serial_handle: serial.Serial


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Test synchronizacji planszy 20x30: nasluchuje zdarzen `press` z ESP po USB "
            "i zapala odpowiadajacy LED przez WLED."
        )
    )
    parser.add_argument("--port", help="Port szeregowy, np. /dev/ttyUSB0.")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD, help="Baud rate. Domyslnie 115200.")
    parser.add_argument("--wled", required=True, help="Adres WLED, np. http://192.168.0.50")
    parser.add_argument("--color", default=DEFAULT_COLOR, help="Kolor LED w formacie RRGGBB. Domyslnie 00FF00.")
    parser.add_argument("--brightness", type=int, default=128, help="Jasnosc WLED 1..255. Domyslnie 128.")
    parser.add_argument("--segment-id", type=int, default=0, help="Segment WLED. Domyslnie 0.")
    parser.add_argument("--led-offset", type=int, default=0, help="Offset LED na segmencie. Domyslnie 0.")
    parser.add_argument("--request-timeout", type=float, default=2.0, help="Timeout HTTP do WLED w sekundach.")
    parser.add_argument(
        "--scan-command",
        default="SCAN",
        help="Komenda wysylana do ESP, aby uzbroic pojedynczy skan. Domyslnie SCAN.",
    )
    parser.add_argument("--debug-probe", action="store_true", help="Pokaz surowe linie podczas wykrywania portu.")
    parser.add_argument("--raw-serial", action="store_true", help="Pokaz wszystkie linie z seriala.")
    parser.add_argument("--dry-run", action="store_true", help="Nie wysylaj nic do WLED, tylko loguj mapowanie.")
    parser.add_argument(
        "--keep-running-on-release",
        action="store_true",
        help="Loguj rowniez eventy release. Domyslnie sa ignorowane.",
    )
    return parser.parse_args()


def normalize_color(color: str) -> str:
    cleaned = color.strip().lstrip("#").upper()
    if len(cleaned) != 6 or any(ch not in "0123456789ABCDEF" for ch in cleaned):
        raise ValueError(f"Nieprawidlowy kolor `{color}`. Uzyj formatu RRGGBB.")
    return cleaned


def normalize_wled_url(url: str) -> str:
    return url.rstrip("/")


def parse_json_line(raw_line: str) -> dict[str, Any] | None:
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


def is_protocol_line(payload: dict[str, Any] | None) -> bool:
    return bool(payload and payload.get("protocol") == PROTOCOL_NAME)


def candidate_ports() -> list[Any]:
    ports = list(list_ports.comports())
    scored: list[tuple[int, Any]] = []
    for port in ports:
        haystack = " ".join(
            str(part or "")
            for part in (port.device, port.description, port.manufacturer, port.product)
        ).lower()
        score = sum(1 for hint in PORT_HINTS if hint in haystack)
        scored.append((score, port))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [port for _, port in scored]


def read_lines_until(
    ser: serial.Serial,
    *,
    timeout_s: float,
    echo_unparsed: bool = False,
) -> tuple[dict[str, Any] | None, list[str]]:
    deadline = time.monotonic() + timeout_s
    seen_lines: list[str] = []
    while time.monotonic() < deadline:
        raw = ser.readline().decode("utf-8", errors="replace").strip()
        if not raw:
            continue
        seen_lines.append(raw)
        payload = parse_json_line(raw)
        if is_protocol_line(payload):
            return payload, seen_lines
        if echo_unparsed:
            print(f"[{ser.port}] {raw}", file=sys.stderr)
    return None, seen_lines


def probe_port(port_name: str, baud_rate: int, *, debug_probe: bool = False) -> PortProbeResult | None:
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

        payload, seen_lines = read_lines_until(ser, timeout_s=6.0, echo_unparsed=debug_probe)
        if payload is None:
            ser.reset_input_buffer()
            ser.write(b"PING\n")
            ser.flush()
            payload, extra_lines = read_lines_until(ser, timeout_s=3.0, echo_unparsed=debug_probe)
            seen_lines.extend(extra_lines)

        if payload is None:
            if debug_probe and seen_lines:
                print(
                    f"[{port_name}] Nie znaleziono odpowiedzi protokolu {PROTOCOL_NAME}.",
                    file=sys.stderr,
                )
                for line in seen_lines:
                    print(f"[{port_name}] {line}", file=sys.stderr)
            ser.close()
            return None

        return PortProbeResult(
            port=port_name,
            description=str(payload.get("event") or "ready"),
            serial_handle=ser,
        )
    except Exception:
        ser.close()
        return None


def autodetect_port(baud_rate: int, *, debug_probe: bool = False) -> PortProbeResult:
    ports = candidate_ports()
    if not ports:
        raise SystemExit("Nie znaleziono zadnych portow szeregowych.")

    for port in ports:
        result = probe_port(port.device, baud_rate, debug_probe=debug_probe)
        if result is not None:
            return result

    checked = ", ".join(port.device for port in ports)
    raise SystemExit(
        f"Nie udalo sie wykryc plytki z protokolem {PROTOCOL_NAME}. Sprawdzone porty: {checked}"
    )


def open_known_port(port_name: str, baud_rate: int, *, debug_probe: bool = False) -> PortProbeResult:
    result = probe_port(port_name, baud_rate, debug_probe=debug_probe)
    if result is None:
        raise SystemExit(
            f"Port {port_name} nie odpowiedzial protokolem {PROTOCOL_NAME}. "
            "Sprawdz port, baud rate i wgrany szkic."
        )
    return result


class WledClient:
    def __init__(
        self,
        base_url: str,
        *,
        segment_id: int,
        brightness: int,
        total_leds: int,
        led_offset: int,
        timeout_s: float,
    ) -> None:
        self.base_url = normalize_wled_url(base_url)
        self.segment_id = segment_id
        self.brightness = max(1, min(255, brightness))
        self.total_leds = total_leds
        self.led_offset = led_offset
        self.timeout_s = timeout_s

    def _post_state(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = requests.post(
            f"{self.base_url}/json/state",
            json=payload,
            timeout=self.timeout_s,
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError(f"Nieoczekiwana odpowiedz WLED: {data!r}")
        return data

    def _get_info(self) -> dict[str, Any]:
        response = requests.get(f"{self.base_url}/json/info", timeout=self.timeout_s)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError(f"Nieoczekiwana odpowiedz WLED info: {data!r}")
        return data

    def validate(self) -> None:
        info = self._get_info()
        leds_info = info.get("leds") or {}
        led_count = int(leds_info.get("count") or 0)
        if led_count < self.total_leds + self.led_offset:
            raise RuntimeError(
                f"WLED raportuje tylko {led_count} LED, a skrypt potrzebuje co najmniej "
                f"{self.total_leds + self.led_offset}."
            )

    def prepare(self) -> None:
        self._post_state({"on": True, "bri": self.brightness})
        self.clear()

    def clear(self) -> None:
        start = self.led_offset
        stop = self.led_offset + self.total_leds
        self._post_state({"seg": [{"id": self.segment_id, "i": [start, stop, "000000"]}]})

    def light_led(self, led_index: int, color_hex: str) -> None:
        led = self.led_offset + led_index
        start = self.led_offset
        stop = self.led_offset + self.total_leds
        self._post_state({"on": True, "bri": self.brightness})
        self._post_state(
            {
                "seg": [
                    {
                        "id": self.segment_id,
                        "i": [start, stop, "000000", led, color_hex],
                    }
                ]
            }
        )


def format_press_message(col: int, row: int, led_index: int, turn_led_index: int) -> str:
    return (
        f"PRESS col={col:02d} row={row:02d} -> led={led_index:03d} "
        f"(turn_after_col={turn_led_index:03d})"
    )


def send_serial_command(ser: serial.Serial, command: str) -> None:
    cleaned = command.strip()
    if not cleaned:
        return
    ser.write(f"{cleaned}\n".encode("ascii", errors="ignore"))
    ser.flush()


def run() -> int:
    args = parse_args()
    color_hex = normalize_color(args.color)

    port_result = (
        open_known_port(args.port, args.baud, debug_probe=args.debug_probe)
        if args.port
        else autodetect_port(args.baud, debug_probe=args.debug_probe)
    )

    print(
        f"Podlaczono ESP na {port_result.port} ({port_result.description}), "
        f"nasluch protokolu {PROTOCOL_NAME}."
    )
    print(
        f"Mapowanie planszy: {BOARD_COLS}x{BOARD_ROWS}, LED calosc={TOTAL_LED_COUNT}, "
        f"WLED={normalize_wled_url(args.wled)}, kolor=#{color_hex}."
    )

    wled: WledClient | None = None
    if not args.dry_run:
        wled = WledClient(
            args.wled,
            segment_id=args.segment_id,
            brightness=args.brightness,
            total_leds=TOTAL_LED_COUNT,
            led_offset=args.led_offset,
            timeout_s=args.request_timeout,
        )
        wled.validate()
        wled.prepare()
        print("WLED gotowy. Wcisnij pole na planszy, aby zapalic odpowiadajacy LED.")
    else:
        print("Dry-run aktywny. Skrypt tylko wypisuje mapowanie bez wysylki do WLED.")

    ser = port_result.serial_handle
    try:
        if args.scan_command.strip():
            send_serial_command(ser, args.scan_command)
            print(f"Wyslano do ESP komende uzbrojenia skanu: {args.scan_command.strip()}")
        while True:
            raw = ser.readline().decode("utf-8", errors="replace").strip()
            if not raw:
                continue

            if args.raw_serial:
                print(f"SERIAL {raw}")

            payload = parse_json_line(raw)
            if payload is None:
                continue

            event = str(payload.get("event") or "").lower()
            if event == "press":
                row = int(payload["row"])
                col = int(payload["col"])
                led_index = board_cell_to_led_index(col, row)
                turn_led_index = turnaround_led_index_after_column(col)
                print(format_press_message(col, row, led_index, turn_led_index))
                if wled is not None:
                    wled.light_led(led_index, color_hex)
                if args.scan_command.strip():
                    send_serial_command(ser, args.scan_command)
                continue

            if event == "release":
                if args.keep_running_on_release:
                    print(f"RELEASE col={int(payload['col']):02d} row={int(payload['row']):02d}")
                continue

            if event in {"ready", "status", "pong", "boot", "armed", "scan_stopped"}:
                print(json.dumps(payload, ensure_ascii=False))
                continue
    except KeyboardInterrupt:
        print("\nZatrzymano test.")
    finally:
        if wled is not None:
            try:
                wled.clear()
            except Exception as exc:  # pragma: no cover
                print(f"Nie udalo sie zgasic LED przez WLED: {exc}", file=sys.stderr)
        try:
            ser.close()
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(run())
