from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

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


class _BoardScanIdleTimeout(TimeoutError):
    pass


class _BoardScanResponseTimeout(TimeoutError):
    pass


class _BoardSerialError(RuntimeError):
    pass


@dataclass(slots=True)
class PortProbeResult:
    port: str
    description: str
    serial_handle: serial.Serial  # type: ignore[name-defined]


def _parse_json_line(raw_line: str) -> dict[str, Any] | None:
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


def _read_lines_until(
    ser: serial.Serial,  # type: ignore[name-defined]
    *,
    protocol_name: str,
    timeout_s: float,
) -> tuple[dict[str, Any] | None, list[str]]:
    deadline = time.monotonic() + timeout_s
    seen_lines: list[str] = []
    while time.monotonic() < deadline:
        raw = ser.readline().decode("utf-8", errors="replace").strip()
        if not raw:
            continue
        seen_lines.append(raw)
        payload = _parse_json_line(raw)
        if payload and payload.get("protocol") == protocol_name:
            return payload, seen_lines
    return None, seen_lines


def _probe_port(
    port_name: str,
    *,
    protocol_name: str,
    baud_rate: int,
    probe_timeout_s: float,
    line_timeout_s: float,
    write_timeout_s: float,
) -> PortProbeResult | None:
    if serial is None:
        raise RuntimeError("Brakuje pakietu pyserial. Zainstaluj zależności z requirements.txt.")
    try:
        ser = serial.Serial(
            port=port_name,
            baudrate=baud_rate,
            timeout=line_timeout_s,
            write_timeout=write_timeout_s,
        )
    except serial.SerialException:
        return None

    try:
        ser.setDTR(False)
        ser.setRTS(False)
        time.sleep(0.1)
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        payload, _seen = _read_lines_until(ser, protocol_name=protocol_name, timeout_s=probe_timeout_s)
        if payload is None:
            ser.reset_input_buffer()
            ser.write(b"PING\n")
            ser.flush()
            payload, _seen = _read_lines_until(ser, protocol_name=protocol_name, timeout_s=3.0)
        if payload is None:
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


def _open_serial_probe(scan_cfg: dict[str, Any]) -> PortProbeResult:
    protocol_name = str(scan_cfg.get("protocol") or "board_scan_usb_v1")
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

    def scan_board(
        self,
        acceptable_responses: list[tuple[int, int]] | None = None,
        *,
        timeout_s: float | None = None,
    ) -> tuple[int, int] | None:
        while True:
            request_timeout = None if timeout_s is None else max(0.1, float(timeout_s))
            response = requests.get(f"{self.base_url}/scan_board", timeout=request_timeout)
            response.raise_for_status()
            data = response.json()
            event = str(data.get("event") or data.get("type") or "").strip().lower()
            if event in {"cancel", "cancelled", "stop", "abort"} or bool(data.get("cancelled")):
                return None
            result = (int(data["col"] - 1), int(data["row"] - 1))
            if acceptable_responses and result not in acceptable_responses:
                logger.warning("Nieakceptowalna odpowiedź z symulatora: %s", result)
                continue
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
        self.protocol_name = str(self.scan_cfg.get("protocol") or "board_scan_usb_v1")
        self.scan_command = str(self.scan_cfg.get("scan_command") or "SCAN").strip() or "SCAN"
        self.stop_command = str(self.scan_cfg.get("stop_command") or "STOP").strip() or "STOP"
        self.stop_before_scan = bool(self.scan_cfg.get("stop_before_scan", True))
        self.pre_scan_stop_s = max(0.0, float(self.scan_cfg.get("pre_scan_stop_s", 0.08)))
        self.pre_scan_delay_s = max(0.0, float(self.scan_cfg.get("pre_scan_delay_s") or 0.12))
        self.scan_recovery_timeout_s = max(0.0, float(self.scan_cfg.get("scan_recovery_timeout_s") or 0.0))
        self.port_result = _open_serial_probe(self.scan_cfg)
        self.ser = self.port_result.serial_handle
        self.wled = _WledClient(wled_cfg)
        if self.wled.validate(raise_on_failure=False):
            self.wled.clear()
        else:
            logger.warning("Start hardware bez aktywnego WLED. Skan planszy dziala, ale LED-y beda ponawiane automatycznie.")
        self.serial_port = self.port_result.port

    def _reset_input_buffer(self) -> None:
        try:
            self.ser.reset_input_buffer()
        except Exception:
            pass

    def _send_stop_command(self) -> None:
        self.ser.write(f"{self.stop_command}\n".encode("ascii", errors="ignore"))
        self.ser.flush()

    def _send_scan_command(self) -> None:
        if self.stop_before_scan:
            try:
                self._send_stop_command()
                if self.pre_scan_stop_s > 0:
                    time.sleep(self.pre_scan_stop_s)
            except Exception:
                logger.debug("Nie udało się asekuracyjnie zatrzymać poprzedniego skanu.", exc_info=True)
        self._reset_input_buffer()
        self.ser.write(f"{self.scan_command}\n".encode("ascii", errors="ignore"))
        self.ser.flush()
        if self.pre_scan_delay_s > 0:
            time.sleep(self.pre_scan_delay_s)

    def cancel_scan(self) -> None:
        try:
            self._send_stop_command()
        except Exception:
            logger.debug("Nie udało się wysłać komendy zatrzymania skanu.", exc_info=True)

    def rearm_scan(self) -> None:
        try:
            self._send_scan_command()
        except Exception:
            logger.debug("Nie udało się ponownie uzbroić skanu planszy.", exc_info=True)

    def reset_connection(self, *, reopen: bool = False) -> None:
        try:
            self.cancel_scan()
            self._reset_input_buffer()
            try:
                self.ser.reset_output_buffer()
            except Exception:
                pass
            if not reopen:
                return
        except Exception:
            logger.debug("Miękki reset połączenia planszy nie powiódł się.", exc_info=True)
        try:
            self.ser.close()
        except Exception:
            pass
        self.port_result = _open_serial_probe(self.scan_cfg)
        self.ser = self.port_result.serial_handle
        self.serial_port = self.port_result.port

    def _read_protocol_payload(self, *, timeout_s: float | None = None) -> dict[str, Any]:
        deadline = None if timeout_s is None else (time.monotonic() + timeout_s)
        idle_deadline = None
        if timeout_s is None and self.scan_recovery_timeout_s > 0:
            idle_deadline = time.monotonic() + self.scan_recovery_timeout_s
        while deadline is None or time.monotonic() < deadline:
            now = time.monotonic()
            if idle_deadline is not None and now >= idle_deadline:
                raise _BoardScanIdleTimeout("Brak odpowiedzi z planszy podczas aktywnego skanu.")
            try:
                raw = self.ser.readline().decode("utf-8", errors="replace").strip()
            except Exception as exc:
                raise _BoardSerialError(f"Błąd odczytu z portu planszy: {exc}") from exc
            if not raw:
                continue
            if idle_deadline is not None:
                idle_deadline = time.monotonic() + self.scan_recovery_timeout_s
            payload = _parse_json_line(raw)
            if payload and payload.get("protocol") == self.protocol_name:
                return payload
        raise _BoardScanResponseTimeout(f"Timeout oczekiwania na odpowiedź protokołu {self.protocol_name}.")

    def scan_board(
        self,
        acceptable_responses: list[tuple[int, int]] | None = None,
        *,
        timeout_s: float | None = None,
    ) -> tuple[int, int] | None:
        deadline = None if timeout_s is None else (time.monotonic() + max(0.0, float(timeout_s)))
        while True:
            remaining = None if deadline is None else max(0.0, deadline - time.monotonic())
            if remaining is not None and remaining <= 0:
                raise TimeoutError("Timeout oczekiwania na wybór pola na planszy.")
            try:
                self._send_scan_command()
            except Exception as exc:
                logger.warning("Błąd wysłania komendy skanu planszy, ponawiam po reconnect: %s", exc)
                self.reset_connection(reopen=True)
                continue
            while True:
                remaining = None if deadline is None else max(0.0, deadline - time.monotonic())
                if remaining is not None and remaining <= 0:
                    raise TimeoutError("Timeout oczekiwania na wybór pola na planszy.")
                try:
                    payload = self._read_protocol_payload(timeout_s=remaining)
                except _BoardScanIdleTimeout:
                    logger.warning(
                        "Skan planszy nie zwrócił żadnych danych przez %.1fs; resetuję skan i ponawiam.",
                        self.scan_recovery_timeout_s,
                    )
                    self.reset_connection()
                    break
                except _BoardSerialError as exc:
                    logger.warning("Połączenie z planszą przerwane podczas skanu, próbuję reconnect: %s", exc)
                    self.reset_connection(reopen=True)
                    break
                except _BoardScanResponseTimeout as exc:
                    if remaining is not None:
                        raise TimeoutError("Timeout oczekiwania na wybór pola na planszy.") from exc
                    raise
                event = str(payload.get("event") or "").lower()
                if event in {"cancel", "cancelled", "stop", "abort"} or bool(payload.get("cancelled")):
                    return None
                if event != "press":
                    continue
                result = (int(payload["col"]), int(payload["row"]))
                if acceptable_responses and result not in acceptable_responses:
                    logger.warning("Nieakceptowalna odpowiedź z planszy: %s", result)
                    self.cancel_scan()
                    break
                return result

    def set_leds(
        self,
        led_updates: list[tuple[int, list[int]]],
        *,
        brightness: int | None = None,
        replace: bool = False,
        transition_ms: int | None = None,
    ) -> None:
        self.wled.set_leds(
            led_updates,
            brightness=brightness,
            replace=replace,
            transition_ms=transition_ms,
        )

    def leds_off(self) -> None:
        self.wled.clear()

    def close(self) -> None:
        try:
            self.ser.close()
        except Exception:
            pass


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

    def scan_board(
        self,
        acceptable_responses: list[tuple[int, int]] | None = None,
        *,
        timeout_s: float | None = None,
    ) -> tuple[int, int] | None:
        try:
            return self._backend.scan_board(acceptable_responses, timeout_s=timeout_s)
        except TypeError:
            return self._backend.scan_board(acceptable_responses)

    def set_leds(
        self,
        positions: list[tuple[int, int]],
        rgb_color,
        *,
        brightness: int | None = None,
        replace: bool = False,
        transition_ms: int | None = None,
    ) -> None:
        led_updates = self._resolve_led_updates(positions, rgb_color)
        if not led_updates:
            return
        try:
            self._backend.set_leds(
                led_updates,
                brightness=brightness,
                replace=replace,
                transition_ms=transition_ms,
            )
        except TypeError:
            if brightness is None:
                self._backend.set_leds(led_updates)
            else:
                try:
                    self._backend.set_leds(led_updates, brightness=brightness)
                except TypeError:
                    self._backend.set_leds(led_updates)

    def leds_off(self) -> None:
        self._backend.leds_off()

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
