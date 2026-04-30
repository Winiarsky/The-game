from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any


CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "board": {
        "rows": 30,
        "cols": 20,
    },
    "connection": {
        "backend": "hardware",
        "simulator_url": "http://127.0.0.1:5000",
    },
    "hardware": {
        "protocol": "board_scan_usb_v1",
        "serial_port": "",
        "baud_rate": 115200,
        "scan_command": "SCAN",
        "stop_command": "STOP",
        "stop_before_scan": True,
        "pre_scan_stop_s": 0.08,
        "probe_timeout_s": 6.0,
        "line_timeout_s": 0.25,
        "write_timeout_s": 0.5,
    },
    "wled": {
        "base_url": "http://wled.local",
        "segment_id": 0,
        "led_offset": 0,
        "led_count": 620,
        "brightness": 128,
        "request_timeout_s": 2.0,
    },
}


def _deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _normalize_legacy_config(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(payload)
    board_cfg = normalized.setdefault("board", {})
    connection_cfg = normalized.setdefault("connection", {})
    hardware_cfg = normalized.setdefault("hardware", {})

    if "n_rows" in normalized:
        board_cfg.setdefault("rows", int(normalized["n_rows"]))
    if "n_cols" in normalized:
        board_cfg.setdefault("cols", int(normalized["n_cols"]))
    if "serial_port" in normalized:
        hardware_cfg.setdefault("serial_port", str(normalized["serial_port"] or ""))
    if "baud_rate" in normalized:
        hardware_cfg.setdefault("baud_rate", int(normalized["baud_rate"]))
    if "simulator_url" in normalized:
        connection_cfg.setdefault("simulator_url", str(normalized["simulator_url"] or ""))
    if "backend" in normalized:
        connection_cfg.setdefault("backend", str(normalized["backend"] or "hardware"))
    return normalized


def _apply_env_overrides(config: dict[str, Any]) -> dict[str, Any]:
    board_cfg = config.setdefault("board", {})
    connection_cfg = config.setdefault("connection", {})
    hardware_cfg = config.setdefault("hardware", {})
    wled_cfg = config.setdefault("wled", {})

    if os.environ.get("BOARD_ROWS"):
        board_cfg["rows"] = int(os.environ["BOARD_ROWS"])
    if os.environ.get("BOARD_COLS"):
        board_cfg["cols"] = int(os.environ["BOARD_COLS"])
    if os.environ.get("BOARD_BACKEND"):
        connection_cfg["backend"] = str(os.environ["BOARD_BACKEND"]).strip().lower()
    if os.environ.get("BOARD_SIMULATOR_URL"):
        connection_cfg["simulator_url"] = str(os.environ["BOARD_SIMULATOR_URL"]).strip()
    if os.environ.get("BOARD_SERIAL_PORT"):
        hardware_cfg["serial_port"] = str(os.environ["BOARD_SERIAL_PORT"]).strip()
    if os.environ.get("BOARD_SERIAL_BAUD"):
        hardware_cfg["baud_rate"] = int(os.environ["BOARD_SERIAL_BAUD"])
    if os.environ.get("BOARD_SCAN_COMMAND"):
        hardware_cfg["scan_command"] = str(os.environ["BOARD_SCAN_COMMAND"]).strip()
    if os.environ.get("BOARD_STOP_COMMAND"):
        hardware_cfg["stop_command"] = str(os.environ["BOARD_STOP_COMMAND"]).strip()
    if os.environ.get("BOARD_STOP_BEFORE_SCAN"):
        raw = str(os.environ["BOARD_STOP_BEFORE_SCAN"]).strip().lower()
        hardware_cfg["stop_before_scan"] = raw not in {"0", "false", "no", "off"}
    if os.environ.get("BOARD_PRE_SCAN_STOP_S"):
        hardware_cfg["pre_scan_stop_s"] = float(os.environ["BOARD_PRE_SCAN_STOP_S"])
    if os.environ.get("WLED_URL"):
        wled_cfg["base_url"] = str(os.environ["WLED_URL"]).strip()
    if os.environ.get("WLED_SEGMENT_ID"):
        wled_cfg["segment_id"] = int(os.environ["WLED_SEGMENT_ID"])
    if os.environ.get("WLED_LED_OFFSET"):
        wled_cfg["led_offset"] = int(os.environ["WLED_LED_OFFSET"])
    if os.environ.get("WLED_LED_COUNT"):
        wled_cfg["led_count"] = int(os.environ["WLED_LED_COUNT"])
    if os.environ.get("WLED_BRIGHTNESS"):
        wled_cfg["brightness"] = int(os.environ["WLED_BRIGHTNESS"])
    return config


def load_board_config(config_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(config_path) if config_path is not None else CONFIG_PATH
    config = deepcopy(DEFAULT_CONFIG)
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            normalized = _normalize_legacy_config(raw)
            _deep_merge(config, normalized)
    return _apply_env_overrides(config)


def board_dimensions(config: dict[str, Any] | None = None) -> tuple[int, int]:
    payload = config or load_board_config()
    board_cfg = payload.get("board") or {}
    return int(board_cfg.get("rows", 30)), int(board_cfg.get("cols", 20))


def connection_backend(config: dict[str, Any] | None = None) -> str:
    payload = config or load_board_config()
    connection_cfg = payload.get("connection") or {}
    return str(connection_cfg.get("backend") or "hardware").strip().lower()


def simulator_url(config: dict[str, Any] | None = None) -> str:
    payload = config or load_board_config()
    connection_cfg = payload.get("connection") or {}
    return str(connection_cfg.get("simulator_url") or "http://127.0.0.1:5000").rstrip("/")


def hardware_scan_config(config: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = config or load_board_config()
    return dict(payload.get("hardware") or {})


def wled_config(config: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = config or load_board_config()
    return dict(payload.get("wled") or {})
