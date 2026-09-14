from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import requests

from .led_output import LedFrame, LedOutput, LedOutputError
from .serial_v2 import PROTOCOL, BoardProtocolError, FrameReader, SerialV2, coordinates, validate_info
from .led_mapping import load_led_mapping
from .settings import (
    board_dimensions,
    connection_backend,
    hardware_scan_config,
    load_board_config,
    simulator_url as config_simulator_url,
    wled_config,
)

try:
    import serial
    from serial.tools import list_ports
except Exception:  # pragma: no cover
    serial = None  # type: ignore[assignment]
    list_ports = None  # type: ignore[assignment]


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PORT_HINTS = ("esp32", "silabs", "cp210", "wch", "ch340", "usb", "uart")


@dataclass(slots=True)
class PortProbeResult:
    port: str
    description: str
    serial_handle: serial.Serial  # type: ignore[name-defined]
    info: dict[str, Any]


def _normalize_wled_url(url: str) -> str:
    return str(url or "").strip().rstrip("/")


def _ordered_color(color: list[int], color_order: str = "rgb") -> list[int]:
    clipped = [max(0, min(255, int(component))) for component in color[:3]]
    while len(clipped) < 3:
        clipped.append(0)
    channels = {"r": clipped[0], "g": clipped[1], "b": clipped[2]}
    order = str(color_order or "rgb").strip().lower()
    if sorted(order) != ["b", "g", "r"]:
        order = "rgb"
    return [channels[channel] for channel in order]


def _color_to_hex(color: list[int], color_order: str = "rgb") -> str:
    return "".join(f"{component:02X}" for component in _ordered_color(color, color_order))


def _candidate_ports() -> list[Any]:
    if list_ports is None:
        return []
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


def _probe_port(
    port_name: str, *, protocol_name: str, baud_rate: int,
    probe_timeout_s: float, line_timeout_s: float, write_timeout_s: float,
) -> PortProbeResult | None:
    if serial is None:
        raise RuntimeError("Brakuje pakietu pyserial.")
    if protocol_name != PROTOCOL:
        raise BoardProtocolError("Aplikacja obsługuje wyłącznie protokół planszy v2.")
    try:
        ser = serial.Serial(port=None, baudrate=baud_rate, timeout=min(.05, line_timeout_s),
                            write_timeout=write_timeout_s)
        ser.dtr = ser.rts = False
        ser.port = port_name
        ser.open()
    except serial.SerialException:
        return None
    try:
        reader = FrameReader()
        deadline, next_ping = time.monotonic() + probe_timeout_s, 0.0
        while time.monotonic() < deadline:
            if time.monotonic() >= next_ping:
                ser.write(b"PING\n")
                next_ping = time.monotonic() + 1
            for payload in reader.feed(ser.read(min(512, max(1, ser.in_waiting)))):
                if payload.get("protocol") == "board_scan_usb_v1":
                    raise BoardProtocolError("Na ESP jest stary protokół. Wgraj firmware v2.")
                if payload.get("protocol") == PROTOCOL and payload.get("type") == "info":
                    validate_info(payload)
                    return PortProbeResult(port_name, str(payload.get("firmware")), ser, payload)
        ser.close()
        return None
    except Exception:
        ser.close()
        raise


def _open_serial_probe(scan_cfg: dict[str, Any]) -> PortProbeResult:
    protocol_name = str(scan_cfg.get("protocol") or PROTOCOL)
    baud_rate = int(scan_cfg.get("baud_rate") or 115200)
    probe_timeout_s = float(scan_cfg.get("probe_timeout_s") or 6.0)
    line_timeout_s = float(scan_cfg.get("line_timeout_s") or 0.25)
    write_timeout_s = float(scan_cfg.get("write_timeout_s") or 0.5)
    port_name = str(scan_cfg.get("serial_port") or "").strip()
    if port_name:
        result = _probe_port(
            port_name,
            protocol_name=protocol_name,
            baud_rate=baud_rate,
            probe_timeout_s=probe_timeout_s,
            line_timeout_s=line_timeout_s,
            write_timeout_s=write_timeout_s,
        )
        if result is None:
            raise RuntimeError(
                f"Port {port_name} nie odpowiedział protokołem {protocol_name}. "
                "Sprawdź port, baud rate i wgrany szkic."
            )
        return result

    ports = _candidate_ports()
    if not ports:
        raise RuntimeError("Nie znaleziono żadnych portów szeregowych.")
    for port in ports:
        result = _probe_port(
            port.device,
            protocol_name=protocol_name,
            baud_rate=baud_rate,
            probe_timeout_s=probe_timeout_s,
            line_timeout_s=line_timeout_s,
            write_timeout_s=write_timeout_s,
        )
        if result is not None:
            return result
    checked = ", ".join(port.device for port in ports)
    raise RuntimeError(f"Nie udało się wykryć płytki z protokołem {protocol_name}. Sprawdzone porty: {checked}")


class _SimulatorBackend:
    def __init__(self, base_url: str) -> None:
        self.base_url = str(base_url).rstrip("/")
        self._generation = 0

    def scan_board(
        self, acceptable_responses: list[tuple[int, int]] | None = None, *,
        timeout_s: float | None = None, context_key: str = "", mode: str = "single",
        finish_positions: tuple[tuple[int, int], ...] = (),
    ) -> tuple[int, int] | None:
        allowed = coordinates(acceptable_responses)
        if not allowed:
            return None
        generation = self._generation
        deadline = None if timeout_s is None else time.monotonic() + max(0, timeout_s)
        while True:
            remaining = None if deadline is None else deadline - time.monotonic()
            if remaining is not None and remaining <= 0:
                raise TimeoutError("Upłynął czas wyboru pola w symulatorze.")
            response = requests.get(f"{self.base_url}/scan_board", timeout=remaining)
            response.raise_for_status()
            if generation != self._generation:
                return None
            data = response.json()
            if str(data.get("event") or data.get("type") or "").lower() in {"cancel", "cancelled", "stop", "abort"} or data.get("cancelled") is True:
                return None
            col, row = data.get("col"), data.get("row")
            if type(col) is not int or type(row) is not int or not (1 <= col <= 20 and 1 <= row <= 30):
                raise BoardProtocolError("Nieprawidłowe pole z symulatora.")
            result = (col - 1, row - 1)
            if result in allowed:
                return result

    def set_leds(
        self,
        led_updates: list[tuple[int, list[int]]],
        *,
        brightness: int | None = None,
        replace: bool = False,
        transition_ms: int | None = None,
    ) -> None:
        payload = {
            "leds": [{"i": idx + 1, "rgb": rgb} for idx, rgb in led_updates],
            "replace": replace,
        }
        if brightness is not None:
            payload["brightness"] = max(1, min(255, int(brightness)))
        if transition_ms is not None:
            payload["transition_ms"] = max(0, int(transition_ms))
        requests.post(f"{self.base_url}/set", json=payload, timeout=5.0).raise_for_status()

    def leds_off(self) -> None:
        requests.get(f"{self.base_url}/off", timeout=5.0).raise_for_status()

    def cancel_scan(self) -> None:
        self._generation += 1
        requests.post(f"{self.base_url}/simulate/cancel_scan", timeout=5.0).raise_for_status()

    def rearm_scan(self) -> None:
        self.cancel_scan()

    def reset_connection(self) -> None:
        self.cancel_scan()


class _WledClient:
    def __init__(self, cfg: dict[str, Any]) -> None:
        self.base_url = _normalize_wled_url(str(cfg.get("base_url") or ""))
        self.segment_id = int(cfg.get("segment_id") or 0)
        self.led_offset = int(cfg.get("led_offset") or 0)
        self.led_count = int(cfg.get("led_count") or 620)
        self.brightness = max(1, min(255, int(cfg.get("brightness") or 128)))
        self.scan_brightness = max(1, min(255, int(cfg.get("scan_brightness") or 255)))
        self.color_order = str(cfg.get("color_order") or "rgb").strip().lower()
        self.request_timeout_s = float(cfg.get("request_timeout_s") or 2.0)
        retry_cooldown_raw = cfg.get("retry_cooldown_s")
        self.retry_cooldown_s = max(0.0, float(3.0 if retry_cooldown_raw is None else retry_cooldown_raw))
        self.available = False
        self.last_error: str | None = None
        self.last_error_at: float | None = None
        self._last_warning_at = 0.0
        if not self.base_url:
            raise RuntimeError("Brak konfiguracji WLED base_url.")

    def _mark_available(self) -> None:
        self.available = True
        self.last_error = None
        self.last_error_at = None

    def _mark_unavailable(self, exc: Exception, *, action: str) -> None:
        self.available = False
        self.last_error = f"{action}: {exc}"
        self.last_error_at = time.monotonic()
        now = time.monotonic()
        if now - self._last_warning_at >= 5.0:
            logger.warning(
                "WLED offline podczas %s: %s. LED-y zostaja tymczasowo wylaczone i beda ponawiane automatycznie.",
                action,
                exc,
            )
            self._last_warning_at = now

    def _post_state(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = requests.post(f"{self.base_url}/json/state", json=payload, timeout=self.request_timeout_s)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError(f"Nieoczekiwana odpowiedź WLED: {data!r}")
        if data.get("success") is False or data.get("error"):
            raise RuntimeError(f"WLED odrzucił ramkę: {data!r}")
        return data

    def _get_info(self) -> dict[str, Any]:
        response = requests.get(f"{self.base_url}/json/info", timeout=self.request_timeout_s)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError(f"Nieoczekiwana odpowiedź WLED info: {data!r}")
        return data

    def validate(self, *, raise_on_failure: bool = True) -> bool:
        try:
            info = self._get_info()
            leds = info.get("leds") or {}
            count = int(leds.get("count") or 0)
            expected = self.led_offset + self.led_count
            if count < expected:
                raise RuntimeError(f"WLED raportuje tylko {count} LED, a konfiguracja wymaga co najmniej {expected}.")
        except Exception as exc:
            self._mark_unavailable(exc, action="validate")
            if raise_on_failure:
                raise
            return False
        self._mark_available()
        return True

    def ensure_available(self, *, force: bool = False) -> bool:
        if self.available:
            return True
        if not force and self.last_error_at is not None:
            if (time.monotonic() - self.last_error_at) < self.retry_cooldown_s:
                return False
        return self.validate(raise_on_failure=False)

    def clear(self) -> bool:
        if not self.ensure_available():
            return False
        start = self.led_offset
        stop = self.led_offset + self.led_count
        try:
            self._post_state({"on": True, "seg": [{"id": self.segment_id, "on": True, "i": [start, stop, "000000"]}]})
        except Exception as exc:
            self._mark_unavailable(exc, action="clear")
            return False
        self._mark_available()
        return True

    def set_leds(
        self,
        led_updates: list[tuple[int, list[int]]],
        *,
        brightness: int | None = None,
        replace: bool = False,
        transition_ms: int | None = None,
    ) -> bool:
        if not led_updates:
            return True
        if not self.ensure_available():
            return False
        start = self.led_offset
        stop = self.led_offset + self.led_count
        instructions: list[Any] = [start, stop, "000000"]
        for led_index, color in led_updates:
            instructions.extend([self.led_offset + int(led_index), _color_to_hex(color, self.color_order)])
        effective_brightness = (
            self.brightness
            if brightness is None
            else max(1, min(255, int(brightness)))
        )
        try:
            payload: dict[str, Any] = {
                "on": True,
                "bri": effective_brightness,
                "seg": [{"id": self.segment_id, "on": True, "i": instructions}],
            }
            if transition_ms is not None:
                payload["transition"] = max(0, int(round(transition_ms / 100)))
            self._post_state(payload)
        except Exception as exc:
            self._mark_unavailable(exc, action="set_leds")
            return False
        self._mark_available()
        return True


class _HardwareBackend:
    def __init__(self, scan_cfg: dict[str, Any], wled_cfg: dict[str, Any]) -> None:
        self.scan_cfg = dict(scan_cfg)
        self.port_result = _open_serial_probe(self.scan_cfg)
        self.serial_port = self.port_result.port
        self.ser = self.port_result.serial_handle
        self.input = SerialV2(self.ser, self.port_result.info)
        self.wled = _WledClient(wled_cfg)
        self._scan_lock = threading.RLock()
        self._scan_cancelled = threading.Event()
        self.output = LedOutput(self._send_led_frame)
        self.output.submit(LedFrame(()))

    def _send_led_frame(self, frame: LedFrame) -> bool:
        if not frame.updates:
            confirmed = self.wled.clear()
        else:
            confirmed = self.wled.set_leds([(index, list(color)) for index, color in frame.updates],
                                           brightness=frame.brightness, replace=True,
                                           transition_ms=frame.transition_ms)
        if not confirmed:
            # Preserve the HTTP/validation failure during retry cooldown too.
            # The output worker records it; USB input remains independent.
            raise LedOutputError(self.wled.last_error or 'WLED nie potwierdził ramki.')
        return True

    def prepare_scan(self, positions: list[tuple[int, int]] | None, *, context_key: str,
                     mode: str, finish_positions: tuple[tuple[int, int], ...]) -> Callable[..., tuple[int, int] | None]:
        with self._scan_lock:
            cancelled = self._scan_cancelled

        def wait(timeout_s: float | None = None) -> tuple[int, int] | None:
            # USB input is governed by the game's current mask and context.
            # A missing WLED HTTP acknowledgement must not disable buttons:
            # the LEDs may already be lit while their response was lost.
            with self._scan_lock:
                if cancelled.is_set():
                    return None
                read = self.input.prepare_input(positions, context_key=context_key,
                                               mode=mode, finish_positions=finish_positions)
            return read(timeout_s)
        return wait

    @property
    def connected(self) -> bool:
        return self.input.connected

    def scan_board(self, acceptable_responses: list[tuple[int, int]] | None = None, *, timeout_s: float | None = None,
                   context_key: str = "", mode: str = "single", finish_positions: tuple[tuple[int, int], ...] = ()) -> tuple[int, int] | None:
        return self.prepare_scan(acceptable_responses, context_key=context_key,
                                 mode=mode, finish_positions=finish_positions)(timeout_s)

    def cancel_scan(self) -> None:
        with self._scan_lock:
            self._scan_cancelled.set()
            self._scan_cancelled = threading.Event()
            self.output.wake()
            self.input.cancel()

    def rearm_scan(self) -> None:
        self.cancel_scan()

    def reset_connection(self, *, reopen: bool = False) -> None:
        self.cancel_scan()
        if reopen or not self.input.connected:
            self.input.close()
            self.port_result = _open_serial_probe(self.scan_cfg)
            self.ser = self.port_result.serial_handle
            self.serial_port = self.port_result.port
            self.input = SerialV2(self.ser, self.port_result.info)

    def set_leds(
        self,
        led_updates: list[tuple[int, list[int]]],
        *,
        brightness: int | None = None,
        replace: bool = False,
        transition_ms: int | None = None,
    ) -> bool:
        self.output.submit(LedFrame(tuple((i, tuple(color)) for i, color in led_updates),
                                    brightness, transition_ms))
        return True  # Queue owns delivery/retries; this is not a device ACK.

    def leds_off(self) -> bool:
        self.output.submit(LedFrame(()))
        return True

    def close(self) -> None:
        try:
            self.cancel_scan()
        finally:
            try:
                self.input.close()
            finally:
                self.output.close()


class Connection:
    def __init__(
        self,
        target: str | None = None,
        *,
        backend: str | None = None,
        simulator_url: str | None = None,
        serial_port: str | None = None,
        wled_url: str | None = None,
        config_path: str | Path | None = None,
    ) -> None:
        self.config_path = Path(config_path) if config_path is not None else Path(__file__).resolve().parent / "config.json"
        self.config = load_board_config(self.config_path)
        self.rows, self.cols = board_dimensions(self.config)
        self.led_config = load_led_mapping(rows=self.rows, cols=self.cols)
        configured_wled = wled_config(self.config)
        self.scan_brightness = max(
            1,
            min(255, int(configured_wled.get("scan_brightness") or 255)),
        )
        transition_ms = configured_wled.get("transition_ms")
        scan_transition_ms = configured_wled.get("scan_transition_ms")
        self.led_transition_ms = max(
            0,
            int(180 if transition_ms is None else transition_ms),
        )
        self.scan_led_transition_ms = max(
            0,
            int(80 if scan_transition_ms is None else scan_transition_ms),
        )

        resolved_backend = backend
        resolved_simulator_url = simulator_url
        if resolved_backend is None:
            if target in {"hardware", "simulator"}:
                resolved_backend = target
            elif isinstance(target, str) and target.startswith("http"):
                resolved_backend = "simulator"
                resolved_simulator_url = target
            else:
                resolved_backend = connection_backend(self.config)
        resolved_backend = str(resolved_backend or "hardware").strip().lower()
        self.backend = resolved_backend

        if resolved_backend == "simulator":
            self.simulator_url = str(resolved_simulator_url or config_simulator_url(self.config)).rstrip("/")
            self._backend: Any = _SimulatorBackend(self.simulator_url)
            return

        scan_cfg = hardware_scan_config(self.config)
        if serial_port is not None:
            scan_cfg["serial_port"] = serial_port
        wled_cfg = wled_config(self.config)
        if wled_url is not None:
            wled_cfg["base_url"] = wled_url
        self._backend = _HardwareBackend(scan_cfg, wled_cfg)
        self.serial_port = getattr(self._backend, "serial_port", None)
        self.wled_url = _normalize_wled_url(str(wled_cfg.get("base_url") or ""))

    def _resolve_led_updates(self, positions: list[tuple[int, int]], rgb_color) -> list[tuple[int, list[int]]]:
        if not positions:
            return []
        if isinstance(rgb_color, list) and rgb_color and isinstance(rgb_color[0], list):
            if len(rgb_color) != len(positions):
                raise ValueError("rgb_color length must match positions length when passing per-position colors.")
            colors = [list(map(int, color)) for color in rgb_color]
        else:
            colors = [list(map(int, rgb_color)) for _ in positions]  # type: ignore[arg-type]
        updates: list[tuple[int, list[int]]] = []
        for (col, row), color in zip(positions, colors):
            led_index = int(self.led_config[str(col)][str(row)])
            updates.append((led_index, color))
        return updates

    def prepare_scan(self, positions: list[tuple[int, int]], *, context_key: str,
                     mode: str, finish_positions: tuple[tuple[int, int], ...]) -> Callable[..., tuple[int, int] | None]:
        if isinstance(self._backend, _HardwareBackend):
            return self._backend.prepare_scan(positions, context_key=context_key,
                                              mode=mode, finish_positions=finish_positions)
        generation = getattr(self._backend, "_generation", 0)
        def wait(timeout_s: float | None = None) -> tuple[int, int] | None:
            if generation != getattr(self._backend, "_generation", 0):
                return None
            return self.scan_board(positions, timeout_s=timeout_s, context_key=context_key,
                                   mode=mode, finish_positions=finish_positions)
        return wait

    @property
    def connected(self) -> bool:
        return bool(getattr(self._backend, "connected", True))

    @property
    def led_status(self) -> dict[str, object]:
        output = getattr(self._backend, "output", None)
        return output.status if output is not None else {}

    def scan_board(
        self, acceptable_responses: list[tuple[int, int]] | None = None, *,
        timeout_s: float | None = None, context_key: str = "", mode: str = "single",
        finish_positions: tuple[tuple[int, int], ...] = (),
    ) -> tuple[int, int] | None:
        return self._backend.scan_board(acceptable_responses, timeout_s=timeout_s,
                                       context_key=context_key, mode=mode, finish_positions=finish_positions)

    def set_leds(
        self,
        positions: list[tuple[int, int]],
        rgb_color,
        *,
        brightness: int | None = None,
        replace: bool = False,
        transition_ms: int | None = None,
    ) -> bool | None:
        led_updates = self._resolve_led_updates(positions, rgb_color)
        if not led_updates:
            return
        try:
            return self._backend.set_leds(
                led_updates,
                brightness=brightness,
                replace=replace,
                transition_ms=transition_ms,
            )
        except TypeError:
            if brightness is None:
                return self._backend.set_leds(led_updates)
            else:
                try:
                    return self._backend.set_leds(led_updates, brightness=brightness)
                except TypeError:
                    return self._backend.set_leds(led_updates)

    def leds_off(self) -> bool | None:
        return self._backend.leds_off()

    def cancel_scan(self) -> None:
        canceller = getattr(self._backend, "cancel_scan", None)
        if callable(canceller):
            canceller()

    def rearm_scan(self) -> None:
        rearmer = getattr(self._backend, "rearm_scan", None)
        if callable(rearmer):
            rearmer()
            return
        self.cancel_scan()

    def reset_connection(self) -> None:
        resetter = getattr(self._backend, "reset_connection", None)
        if callable(resetter):
            resetter()
            return
        self.cancel_scan()

    def close(self) -> None:
        closer = getattr(self._backend, "close", None)
        if callable(closer):
            closer()

    def __del__(self) -> None:  # pragma: no cover
        try:
            self.close()
        except Exception:
            pass
