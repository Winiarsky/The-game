from __future__ import annotations

import atexit
import itertools
import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from queue import Empty, Queue
from threading import Lock
from typing import Any

import requests
from flask import Flask, Response, abort, jsonify, render_template, request, send_from_directory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from board.settings import connection_backend, hardware_scan_config, load_board_config, simulator_url
from character_creation.repository import CharacterRepository
from communication import normalize_communication
from player_prompting import PromptDirector, SESSION_RESET_COMMAND
from scenario_flow import scenario_flow_path

APP_ROOT = Path(__file__).resolve().parent
CONTENT_ROOT = APP_ROOT / "content"
STATIC_ROOT = APP_ROOT / "static"
SHARED_STATIC_ROOT = PROJECT_ROOT / "player_ui" / "static"
ASSETS_ROOT = PROJECT_ROOT / "assets"

app = Flask(__name__, static_folder=None, template_folder="templates")

subscribers: set[Queue] = set()
subscribers_lock = Lock()
events_history: list[dict[str, Any]] = []
history_limit = 250

event_ids = itertools.count(1)
session_ids = itertools.count(1)
current_session_id = f"ui-session-{next(session_ids)}"
prompt_director = PromptDirector(session_id=current_session_id)

runtime_lock = Lock()
runtime_state: dict[str, Any] = {
    "process": None,
    "state": "idle",
    "scenario_id": None,
    "hero_ids": [],
    "session_id": current_session_id,
    "started_at": None,
    "stopped_at": None,
    "returncode": None,
    "command": [],
    "base_url": None,
    "error": None,
    "board_backend": None,
    "board_url": None,
}


def _format_sse(event: dict[str, Any]) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


def _broadcast(event: dict[str, Any]) -> None:
    with subscribers_lock:
        for queue in list(subscribers):
            try:
                queue.put_nowait(event)
            except Exception:
                subscribers.discard(queue)


def _record_event(event: dict[str, Any]) -> None:
    events_history.append(event)
    if len(events_history) > history_limit:
        del events_history[: len(events_history) - history_limit]


def _make_event(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": next(event_ids),
        "type": event_type,
        "payload": payload,
        "ts": time.time(),
        "session_id": current_session_id,
    }


def _publish(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    event = _make_event(event_type, payload)
    _record_event(event)
    _broadcast(event)
    return event


prompt_director.set_publisher(_publish)


def _configured_wled_state() -> tuple[str, int, int, int]:
    env_url = str(os.environ.get("WLED_URL") or "").strip()
    segment_id = int(os.environ.get("WLED_SEGMENT_ID") or 0)
    led_offset = int(os.environ.get("WLED_LED_OFFSET") or 0)
    led_count = int(os.environ.get("WLED_LED_COUNT") or 620)
    if env_url:
        return env_url.rstrip("/"), segment_id, led_offset, led_count
    try:
        cfg = load_board_config()
    except Exception:
        return "", segment_id, led_offset, led_count
    wled_cfg = cfg.get("wled") or {}
    return (
        str(wled_cfg.get("base_url") or "").strip().rstrip("/"),
        int(wled_cfg.get("segment_id") or segment_id),
        int(wled_cfg.get("led_offset") or led_offset),
        int(wled_cfg.get("led_count") or led_count),
    )


def _power_off_wled(*, reason: str, log_failure: bool = True) -> None:
    base_url, segment_id, led_offset, led_count = _configured_wled_state()
    if not base_url:
        return
    stop = led_offset + led_count
    payload = {
        "on": False,
        "seg": [
            {
                "id": segment_id,
                "on": False,
                "fx": 0,
                "col": [[0, 0, 0], [0, 0, 0], [0, 0, 0]],
                "i": [led_offset, stop, "000000"],
            }
        ],
    }
    try:
        requests.post(f"{base_url}/json/state", json=payload, timeout=2.0).raise_for_status()
    except Exception as exc:
        if log_failure:
            app.logger.warning("Nie udało się wyłączyć WLED podczas %s: %s", reason, exc)


def _shutdown_hardware_outputs() -> None:
    _power_off_wled(reason="shutdown", log_failure=False)


atexit.register(_shutdown_hardware_outputs)


def _session_info() -> dict[str, Any]:
    current_prompts = prompt_director.list_prompts(session_id=current_session_id)
    return {
        "id": current_session_id,
        "history_size": len(events_history),
        "prompt_count": len(current_prompts),
        "revision": prompt_director.revision,
    }


def _validate_request_session_id(data: dict[str, Any]) -> tuple[bool, Response | None]:
    request_session_id = str(data.get("session_id") or "").strip()
    if request_session_id and request_session_id != current_session_id:
        return False, jsonify(
            {
                "ok": False,
                "error": "session mismatch",
                "current_session_id": current_session_id,
            }
        )
    return True, None


def _board_scan_status_payload(event_type: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    kind = str(payload.get("kind") or "board").strip().replace("_", " ")
    attempt = payload.get("attempt")
    attempt_text = ""
    try:
        attempt_num = int(attempt)
        if attempt_num > 0:
            attempt_text = f" Próba {attempt_num}."
    except Exception:
        attempt_text = ""
    hero_name = str(payload.get("hero_name") or "").strip()
    subject = f" dla {hero_name}" if hero_name else ""
    if event_type == "board_scan_wait":
        return {
            "title": "Czekam na planszę",
            "message": f"Skan planszy: {kind}{subject}.{attempt_text}",
            "source": "board_scan",
            "level": "info",
        }
    if event_type == "board_scan_result":
        position = payload.get("position")
        if position is None:
            return {
                "title": "Skan planszy bez wyboru",
                "message": f"Plansza nie zwróciła pola: {kind}{subject}.{attempt_text}",
                "source": "board_scan",
                "level": "warning",
            }
        return {
            "title": "Skan planszy",
            "message": f"Plansza zwróciła pole {position}: {kind}{subject}.{attempt_text}",
            "source": "board_scan",
            "level": "info",
        }
    return None



def _normalize_skill_ranks(snapshot: dict[str, Any]) -> list[str]:
    ranks = dict(snapshot.get("skill_ranks") or {})
    trained = set(str(item or "").strip().lower() for item in list(snapshot.get("trained_skills") or []))
    ordered = [
        "acrobatics",
        "arcana",
        "athletics",
        "crafting",
        "deception",
        "diplomacy",
        "intimidation",
        "medicine",
        "nature",
        "occultism",
        "performance",
        "religion",
        "society",
        "stealth",
        "survival",
        "thievery",
    ]
    out: list[str] = []
    for skill_id in ordered:
        rank = str(ranks.get(skill_id) or ("trained" if skill_id in trained else "")).strip().lower()
        if not rank or rank == "untrained":
            continue
        out.append(f"{skill_id.replace('_', ' ').title()} ({rank})")
    return out


def _hero_catalog_entry(snapshot: dict[str, Any]) -> dict[str, Any]:
    name = str(snapshot.get("name") or snapshot.get("character_id") or "Hero")
    class_id = str(snapshot.get("class_id") or "").strip()
    ancestry_id = str(snapshot.get("ancestry_id") or "").strip()
    hp = int(snapshot.get("max_hp") or 0) or None
    ac = int(snapshot.get("ac") or 0) or None
    speed = int(snapshot.get("speed_feet") or snapshot.get("base_speed_feet") or 0) or None
    key_statuses = [str(item).replace("_", " ").title() for item in list(snapshot.get("status_ids") or [])[:6]]
    trained_skills = _normalize_skill_ranks(snapshot)[:4]
    summary_parts = []
    if class_id:
        summary_parts.append(class_id.replace("_", " ").title())
    if ancestry_id:
        summary_parts.append(ancestry_id.replace("_", " ").title())
    if trained_skills:
        summary_parts.append("Skills: " + ", ".join(trained_skills[:3]))
    return {
        "id": str(snapshot.get("character_id") or "").strip().lower(),
        "name": name,
        "portrait": str(snapshot.get("portrait_image") or snapshot.get("image") or "/static/placeholder.png"),
        "class_id": class_id,
        "ancestry_id": ancestry_id,
        "hp": hp,
        "ac": ac,
        "speed": speed,
        "summary": " · ".join(part for part in summary_parts if part),
        "trained_skills": trained_skills,
        "key_traits": key_statuses,
        "level": int(snapshot.get("level") or 1),
        "background_id": str(snapshot.get("background_id") or "").strip(),
    }


def _load_content_manifest(name: str) -> dict[str, Any]:
    path = CONTENT_ROOT / f"{name}.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _scenario_catalog_entry(scenario: dict[str, Any], *, fallback_id: str) -> dict[str, Any]:
    scenario_id = str(scenario.get("scenario_id") or fallback_id).strip().lower()
    title = str(scenario.get("title") or scenario_id.replace("_", " ").title())
    return {
        "id": scenario_id,
        "title": title,
        "tagline": str(scenario.get("tagline") or ""),
        "briefing_title": str(scenario.get("briefing_title") or ""),
        "briefing_intro": str(scenario.get("briefing_intro") or ""),
        "stakes": str(scenario.get("stakes") or ""),
        "briefing_points": list(scenario.get("briefing_points") or []),
        "chapters": list(scenario.get("chapters") or []),
        "primary_objectives": list(scenario.get("primary_objectives") or []),
        "optional_objectives": list(scenario.get("optional_objectives") or []),
        "transitions": dict(scenario.get("transitions") or {}),
        "asset_manifest": str(scenario.get("asset_manifest") or ""),
        "audio_cues": dict(scenario.get("audio_cues") or {}),
        "result_title": str(scenario.get("result_title") or ""),
        "result_summary": str(scenario.get("result_summary") or ""),
    }


def build_catalog() -> dict[str, Any]:
    repo = CharacterRepository(PROJECT_ROOT / "data" / "heroes")
    heroes: list[dict[str, Any]] = []
    for item in repo.list_characters():
        snapshot = repo.load_character(str(item.get("character_id") or ""))
        if not snapshot:
            continue
        heroes.append(_hero_catalog_entry(snapshot))
    heroes.sort(key=lambda item: str(item.get("name") or "").lower())

    scenarios: list[dict[str, Any]] = []
    for path in sorted(CONTENT_ROOT.glob("*.json")):
        scenario = _load_content_manifest(path.stem)
        if not scenario:
            continue
        scenarios.append(_scenario_catalog_entry(scenario, fallback_id=path.stem))
    scenarios.sort(key=lambda item: (item["id"] != "bandit_cave", str(item.get("title") or "").lower()))
    return {"heroes": heroes, "scenarios": scenarios}


def _public_base_url() -> str:
    env_url = str(os.environ.get("PLAYER_UI_PUBLIC_URL") or "").strip()
    if env_url:
        return env_url.rstrip("/")
    if request:
        return request.url_root.rstrip("/")
    host = os.environ.get("PLAYER_UI_HOST", "127.0.0.1")
    port = int(os.environ.get("PLAYER_UI_PORT", "5200"))
    return f"http://{host}:{port}"


def _refresh_runtime_state_unlocked() -> None:
    process = runtime_state.get("process")
    if process is None:
        return
    try:
        code = process.poll()
    except Exception as exc:
        runtime_state["state"] = "error"
        runtime_state["error"] = str(exc)
        runtime_state["stopped_at"] = time.time()
        runtime_state["process"] = None
        return
    if code is None:
        if runtime_state.get("state") == "starting":
            runtime_state["state"] = "running"
        return
    runtime_state["returncode"] = int(code)
    runtime_state["process"] = None
    runtime_state["stopped_at"] = time.time()
    runtime_state["state"] = "stopped" if int(code) == 0 else "error"
    if int(code) != 0 and not runtime_state.get("error"):
        runtime_state["error"] = f"Runtime finished with code {code}."
    _power_off_wled(reason="runtime_exit")


def _runtime_status_payload() -> dict[str, Any]:
    with runtime_lock:
        _refresh_runtime_state_unlocked()
        return {
            "state": runtime_state.get("state"),
            "scenario_id": runtime_state.get("scenario_id"),
            "hero_ids": list(runtime_state.get("hero_ids") or []),
            "session_id": runtime_state.get("session_id"),
            "started_at": runtime_state.get("started_at"),
            "stopped_at": runtime_state.get("stopped_at"),
            "returncode": runtime_state.get("returncode"),
            "error": runtime_state.get("error"),
            "command": list(runtime_state.get("command") or []),
            "board_backend": runtime_state.get("board_backend"),
            "board_url": runtime_state.get("board_url"),
        }


def reset_session_state(*, reason: str = "manual") -> dict[str, Any]:
    global current_session_id
    previous_session_id = current_session_id
    current_session_id = f"ui-session-{next(session_ids)}"
    events_history.clear()
    with runtime_lock:
        runtime_state["session_id"] = current_session_id
    retired_prompts = prompt_director.rotate_session(
        current_session_id,
        retired_answer=SESSION_RESET_COMMAND,
        runtime_status=_runtime_status_payload(),
    )
    _publish(
        "session_reset",
        {
            "reason": reason,
            "previous_session_id": previous_session_id,
            "retired_prompts": retired_prompts,
        },
    )
    return {
        "ok": True,
        "session": _session_info(),
        "previous_session_id": previous_session_id,
        "retired_prompts": retired_prompts,
    }


def _build_runtime_command(*, scenario_id: str, hero_ids: list[str]) -> list[str]:
    cmd = [sys.executable, "main.py", "--scenario", scenario_id]
    for hero_id in hero_ids:
        cmd.extend(["--hero-id", hero_id])
    return cmd


def _resolve_runtime_board_settings() -> dict[str, str | None]:
    explicit_backend = str(os.environ.get("PLAYER_UI_BOARD_BACKEND") or "").strip().lower()
    explicit_board_url = str(os.environ.get("PLAYER_UI_BOARD_URL") or "").strip()
    explicit_serial_port = str(os.environ.get("PLAYER_UI_BOARD_SERIAL_PORT") or "").strip()
    explicit_wled_url = str(os.environ.get("PLAYER_UI_WLED_URL") or "").strip()

    if explicit_backend:
        return {
            "backend": explicit_backend,
            "board_url": explicit_board_url or None,
            "serial_port": explicit_serial_port or None,
            "wled_url": explicit_wled_url or None,
        }

    config = load_board_config()
    configured_backend = connection_backend(config)
    configured_simulator_url = simulator_url(config)
    configured_serial_port = str((hardware_scan_config(config) or {}).get("serial_port") or "").strip()

    if configured_backend == "hardware" and not configured_serial_port and configured_simulator_url:
        return {
            "backend": "simulator",
            "board_url": configured_simulator_url or None,
            "serial_port": None,
            "wled_url": explicit_wled_url or None,
        }

    return {
        "backend": configured_backend or "hardware",
        "board_url": configured_simulator_url or None,
        "serial_port": configured_serial_port or None,
        "wled_url": explicit_wled_url or None,
    }


def stop_runtime_process(*, reason: str = "manual") -> dict[str, Any]:
    with runtime_lock:
        _refresh_runtime_state_unlocked()
        process = runtime_state.get("process")
        if process is None:
            runtime_state["state"] = "stopped"
            runtime_state["stopped_at"] = time.time()
            _power_off_wled(reason=reason)
            return {
                "state": runtime_state.get("state"),
                "scenario_id": runtime_state.get("scenario_id"),
                "hero_ids": list(runtime_state.get("hero_ids") or []),
                "session_id": runtime_state.get("session_id"),
                "started_at": runtime_state.get("started_at"),
                "stopped_at": runtime_state.get("stopped_at"),
                "returncode": runtime_state.get("returncode"),
                "error": runtime_state.get("error"),
                "command": list(runtime_state.get("command") or []),
                "board_backend": runtime_state.get("board_backend"),
                "board_url": runtime_state.get("board_url"),
            }
        try:
            process.terminate()
            process.wait(timeout=2)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass
        _power_off_wled(reason=reason)
        runtime_state["process"] = None
        runtime_state["stopped_at"] = time.time()
        runtime_state["state"] = "stopped"
        runtime_state["error"] = None if reason == "manual" else runtime_state.get("error")
        try:
            runtime_state["returncode"] = process.poll()
        except Exception:
            runtime_state["returncode"] = None
        return {
            "state": runtime_state.get("state"),
            "scenario_id": runtime_state.get("scenario_id"),
            "hero_ids": list(runtime_state.get("hero_ids") or []),
            "session_id": runtime_state.get("session_id"),
            "started_at": runtime_state.get("started_at"),
            "stopped_at": runtime_state.get("stopped_at"),
            "returncode": runtime_state.get("returncode"),
            "error": runtime_state.get("error"),
            "command": list(runtime_state.get("command") or []),
            "board_backend": runtime_state.get("board_backend"),
            "board_url": runtime_state.get("board_url"),
        }


def start_runtime_process(*, scenario_id: str, hero_ids: list[str], base_url: str) -> dict[str, Any]:
    scenario_id = str(scenario_id or "").strip().lower()
    if not scenario_id or not scenario_flow_path(scenario_id).exists():
        raise ValueError(f"Unknown scenario_id '{scenario_id}'.")
    stop_runtime_process(reason="restart")
    reset_session_state(reason="runtime_start")
    board_settings = _resolve_runtime_board_settings()
    cmd = _build_runtime_command(scenario_id=scenario_id, hero_ids=hero_ids)
    board_backend = str(board_settings.get("backend") or "").strip().lower()
    board_url = str(board_settings.get("board_url") or "").strip()
    serial_port = str(board_settings.get("serial_port") or "").strip()
    wled_url = str(board_settings.get("wled_url") or "").strip()
    if board_backend:
        cmd.extend(["--board-backend", board_backend])
    if board_url:
        cmd.extend(["--board-url", board_url])
    if serial_port:
        cmd.extend(["--board-serial-port", serial_port])
    if wled_url:
        cmd.extend(["--wled-url", wled_url])
    env = os.environ.copy()
    env["PLAYER_UI_URL"] = base_url
    env["PLAYER_UI_BASE_URL"] = base_url
    env["ALLOW_CLI_FALLBACK"] = "0"
    env["PYTHONUNBUFFERED"] = "1"
    process = subprocess.Popen(cmd, cwd=str(PROJECT_ROOT), env=env)
    with runtime_lock:
        runtime_state.update(
            {
                "process": process,
                "state": "starting",
                "scenario_id": scenario_id,
                "hero_ids": list(hero_ids),
                "session_id": current_session_id,
                "started_at": time.time(),
                "stopped_at": None,
                "returncode": None,
                "command": list(cmd),
                "base_url": base_url,
                "error": None,
                "board_backend": board_backend or None,
                "board_url": board_url or None,
            }
        )
        return {
            "state": runtime_state.get("state"),
            "scenario_id": runtime_state.get("scenario_id"),
            "hero_ids": list(runtime_state.get("hero_ids") or []),
            "session_id": runtime_state.get("session_id"),
            "started_at": runtime_state.get("started_at"),
            "stopped_at": runtime_state.get("stopped_at"),
            "returncode": runtime_state.get("returncode"),
            "error": runtime_state.get("error"),
            "command": list(runtime_state.get("command") or []),
            "board_backend": runtime_state.get("board_backend"),
            "board_url": runtime_state.get("board_url"),
        }


def retry_runtime_process(*, base_url: str) -> dict[str, Any]:
    with runtime_lock:
        _refresh_runtime_state_unlocked()
        scenario_id = str(runtime_state.get("scenario_id") or "").strip()
        hero_ids = list(runtime_state.get("hero_ids") or [])
    if not scenario_id or not hero_ids:
        raise ValueError("No previous runtime configuration to retry.")
    return start_runtime_process(scenario_id=scenario_id, hero_ids=hero_ids, base_url=base_url)


def _signal_runtime_board_control(signal_name: str, unavailable_message: str, failure_prefix: str) -> dict[str, Any]:
    with runtime_lock:
        _refresh_runtime_state_unlocked()
        process = runtime_state.get("process")
        if process is None:
            raise ValueError("No running runtime process.")
        pid = int(getattr(process, "pid", 0) or 0)
        if pid <= 0:
            raise RuntimeError("Running runtime process has no PID.")
        control_signal = getattr(signal, signal_name, None)
        if control_signal is None:
            raise RuntimeError(unavailable_message)
        try:
            os.kill(pid, control_signal)
        except Exception as exc:
            raise RuntimeError(f"{failure_prefix}: {exc}") from exc
        return {
            "state": runtime_state.get("state"),
            "scenario_id": runtime_state.get("scenario_id"),
            "hero_ids": list(runtime_state.get("hero_ids") or []),
            "session_id": runtime_state.get("session_id"),
            "started_at": runtime_state.get("started_at"),
            "stopped_at": runtime_state.get("stopped_at"),
            "returncode": runtime_state.get("returncode"),
            "error": runtime_state.get("error"),
            "command": list(runtime_state.get("command") or []),
            "board_backend": runtime_state.get("board_backend"),
            "board_url": runtime_state.get("board_url"),
        }


def reset_board_runtime_process() -> dict[str, Any]:
    return _signal_runtime_board_control(
        "SIGUSR1",
        "Runtime board rearm signal is not available on this platform.",
        "Could not signal runtime board rearm",
    )


def cancel_runtime_board_scan() -> tuple[dict[str, Any] | None, bool, str | None]:
    board_url = ""
    with runtime_lock:
        board_url = str(runtime_state.get("board_url") or "").strip().rstrip("/")
    if board_url:
        try:
            requests.post(f"{board_url}/simulate/cancel_scan", timeout=2.0).raise_for_status()
            return _runtime_status_payload(), True, None
        except Exception as exc:
            direct_error = str(exc)
            try:
                status = _signal_runtime_board_control(
                    "SIGUSR2",
                    "Runtime board cancel signal is not available on this platform.",
                    "Could not signal runtime board scan cancel",
                )
                return status, True, direct_error
            except Exception:
                return None, False, direct_error
    try:
        status = _signal_runtime_board_control(
            "SIGUSR2",
            "Runtime board cancel signal is not available on this platform.",
            "Could not signal runtime board scan cancel",
        )
        return status, True, None
    except Exception as exc:
        return None, False, str(exc)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/static/<path:filename>")
def static_files(filename: str):
    normalized = str(filename).strip().lstrip("/")
    for root in (STATIC_ROOT, SHARED_STATIC_ROOT):
        candidate = root / normalized
        if candidate.exists() and candidate.is_file():
            return send_from_directory(root, normalized)
    abort(404)


@app.get("/assets/<path:filename>")
def asset_files(filename: str):
    normalized = str(filename).strip().lstrip("/")
    if not normalized or normalized.startswith("../") or "/../" in f"/{normalized}/":
        abort(404)
    candidate = ASSETS_ROOT / normalized
    if candidate.exists() and candidate.is_file():
        return send_from_directory(ASSETS_ROOT, normalized)
    abort(404)


@app.get("/api/session")
def get_session():
    return jsonify({"ok": True, "session": _session_info()})


@app.post("/api/session/reset")
def reset_session():
    data = request.get_json(force=True, silent=True) or {}
    reason = str(data.get("reason") or "manual").strip() or "manual"
    return jsonify(reset_session_state(reason=reason))


@app.get("/stream")
def stream():
    queue: Queue = Queue()
    with subscribers_lock:
        subscribers.add(queue)

    def _generator():
        for event in events_history[-75:]:
            yield _format_sse(event)
        try:
            while True:
                try:
                    event = queue.get(timeout=15)
                except Empty:
                    yield ": keepalive\n\n"
                    continue
                yield _format_sse(event)
        except GeneratorExit:
            pass
        finally:
            with subscribers_lock:
                subscribers.discard(queue)

    return Response(_generator(), mimetype="text/event-stream")


@app.post("/api/events")
def api_events():
    payload = request.get_json(force=True, silent=True) or {}
    is_valid, error_response = _validate_request_session_id(payload)
    if not is_valid:
        return error_response, 409
    event_type = payload.get("type") or "log"
    body = payload.get("payload") or {}
    if isinstance(body, dict):
        normalized_body = dict(body)
        normalized_body["_communication_explicit"] = isinstance(body.get("communication"), dict)
        normalized_body["communication"] = normalize_communication(
            event_type=str(event_type),
            payload=normalized_body,
            prompt=False,
        )
        body = normalized_body
    event = _publish(str(event_type), body)
    if str(event_type) in {"board_scan_wait", "board_scan_result"}:
        scan_status = _board_scan_status_payload(str(event_type), body if isinstance(body, dict) else {})
        if scan_status:
            prompt_director.ingest_event("idle_hint", scan_status, runtime_status=_runtime_status_payload())
    elif str(event_type) in {"log", "info", "narration", "idle_hint", "player_card"}:
        prompt_director.ingest_event(str(event_type), body, runtime_status=_runtime_status_payload())
    elif str(event_type) == "prompt_scope_cancel":
        prompt_director.cancel_scope(str(body.get("scope_key") or ""), runtime_status=_runtime_status_payload())
    elif str(event_type) == "prompt_answer":
        prompt_director.answer_prompt(
            str(body.get("prompt_id") or ""),
            body.get("answer"),
            current_session_id=current_session_id,
            runtime_status=_runtime_status_payload(),
        )
    return jsonify({"ok": True, "event": event})


@app.post("/api/prompts")
def create_prompt():
    data = request.get_json(force=True, silent=True) or {}
    is_valid, error_response = _validate_request_session_id(data)
    if not is_valid:
        return error_response, 409
    prompt_text = str(data.get("prompt") or "").strip()
    if not prompt_text:
        return jsonify({"ok": False, "error": "prompt is required"}), 400
    payload = dict(data)
    payload["prompt"] = prompt_text
    prompt = prompt_director.create_prompt_from_api(
        payload,
        session_id=current_session_id,
        runtime_status=_runtime_status_payload(),
    )
    return jsonify(
        {
            "ok": True,
            "id": prompt["id"],
            "prompt_key": prompt.get("prompt_key"),
            "prompt": prompt_text,
            "session_id": current_session_id,
            "communication": prompt.get("communication"),
            "confirm_enabled": prompt.get("confirm_enabled"),
            "input_mode": prompt.get("input_mode"),
            "cancel_enabled": prompt.get("cancel_enabled"),
            "cancel_answer": prompt.get("cancel_answer"),
        }
    )


@app.get("/api/prompts")
def list_prompts():
    session = {
        "id": current_session_id,
        "history_size": len(events_history),
        "prompt_count": len(prompt_director.list_prompts(session_id=current_session_id)),
        "revision": prompt_director.revision,
    }
    return jsonify({"ok": True, "session": session, "prompts": prompt_director.list_prompts(session_id=current_session_id)})


@app.get("/api/prompts/<prompt_id>")
def get_prompt(prompt_id: str):
    entry = prompt_director.get_prompt(prompt_id)
    if not entry:
        return jsonify({"ok": False, "error": "prompt not found"}), 404
    return jsonify({"ok": True, **entry})


@app.patch("/api/prompts/<prompt_id>")
def update_prompt(prompt_id: str):
    data = request.get_json(force=True, silent=True) or {}
    is_valid, error_response = _validate_request_session_id(data)
    if not is_valid:
        return error_response, 409
    entry = prompt_director.update_prompt(
        prompt_id,
        dict(data),
        current_session_id=current_session_id,
        runtime_status=_runtime_status_payload(),
    )
    if not entry:
        return jsonify({"ok": False, "error": "prompt not found"}), 404
    return jsonify({"ok": True, **entry})


@app.post("/api/prompts/<prompt_id>/response")
def set_prompt_response(prompt_id: str):
    data = request.get_json(force=True, silent=True) or {}
    answer = data.get("answer")
    entry = prompt_director.get_prompt(prompt_id)
    if not entry:
        return jsonify({"ok": False, "error": "prompt not found"}), 404
    result = prompt_director.answer_prompt(
        prompt_id,
        answer,
        current_session_id=current_session_id,
        runtime_status=_runtime_status_payload(),
    )
    assert result is not None
    return jsonify({"ok": True, **result})


@app.post("/api/prompts/<prompt_id>/answer")
def set_prompt_answer(prompt_id: str):
    return set_prompt_response(prompt_id)


@app.get("/api/view-state")
def api_view_state():
    return jsonify(
        {
            "ok": True,
            "session": _session_info(),
            "view_state": prompt_director.snapshot(runtime_status=_runtime_status_payload()),
        }
    )


@app.get("/api/journal")
def api_journal():
    try:
        after = max(0, int(request.args.get("after", "0") or 0))
    except Exception:
        after = 0
    payload = prompt_director.journal_after(after)
    return jsonify({"ok": True, "session": _session_info(), **payload})


@app.get("/api/catalog")
def api_catalog():
    return jsonify({"ok": True, "catalog": build_catalog()})


@app.get("/api/runtime/status")
def api_runtime_status():
    return jsonify({"ok": True, "runtime_status": _runtime_status_payload()})


@app.post("/api/runtime/start")
def api_runtime_start():
    data = request.get_json(force=True, silent=True) or {}
    scenario_id = str(data.get("scenario_id") or "").strip().lower() or "bandit_cave"
    hero_ids = [
        str(item or "").strip().lower()
        for item in list(data.get("hero_ids") or [])
        if str(item or "").strip()
    ]
    if not hero_ids:
        return jsonify({"ok": False, "error": "At least one hero_id is required."}), 400
    if len(hero_ids) > 4:
        return jsonify({"ok": False, "error": "At most 4 hero_ids are supported."}), 400
    base_url = _public_base_url()
    try:
        status = start_runtime_process(scenario_id=scenario_id, hero_ids=hero_ids, base_url=base_url)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({"ok": True, "session_id": current_session_id, "runtime_status": status})


@app.post("/api/runtime/stop")
def api_runtime_stop():
    status = stop_runtime_process()
    return jsonify({"ok": True, "runtime_status": status})


@app.post("/api/runtime/retry")
def api_runtime_retry():
    try:
        status = retry_runtime_process(base_url=_public_base_url())
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({"ok": True, "session_id": current_session_id, "runtime_status": status})


@app.post("/api/runtime/board-reset")
def api_runtime_board_reset():
    try:
        status = reset_board_runtime_process()
    except (ValueError, RuntimeError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    _publish("info", {"message": "Wysłano anulowanie i ponowne uzbrojenie skanu planszy.", "source": "runtime"})
    return jsonify({"ok": True, "session_id": current_session_id, "runtime_status": status})


@app.post("/api/runtime/cancel-scan")
def api_runtime_cancel_scan():
    data = request.get_json(force=True, silent=True) or {}
    reason = str(data.get("reason") or "prompt_cancel").strip()
    status, cancelled, error = cancel_runtime_board_scan()
    _publish(
        "prompt_scope_cancel",
        {
            "scope_key": "hero_turn:targeting",
            "reason": reason,
            "scan_cancelled": cancelled,
            "error": error,
        },
    )
    return jsonify({"ok": True, "scan_cancelled": cancelled, "error": error, "runtime_status": status})


if __name__ == "__main__":
    host = os.environ.get("PLAYER_UI_HOST", "127.0.0.1")
    port = int(os.environ.get("PLAYER_UI_PORT", "5200"))
    debug_flag = str(os.environ.get("FLASK_DEBUG", "1")).lower() not in ("0", "false", "no")
    app.run(host=host, port=port, debug=debug_flag, threaded=True)
