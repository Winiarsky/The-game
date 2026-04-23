from __future__ import annotations

import itertools
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from queue import Empty, Queue
from threading import Lock
from typing import Any

from flask import Flask, Response, abort, jsonify, render_template, request, send_from_directory

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from board.settings import connection_backend, hardware_scan_config, load_board_config, simulator_url
from character_creation.repository import CharacterRepository
from communication import normalize_communication

APP_ROOT = Path(__file__).resolve().parent
CONTENT_ROOT = APP_ROOT / "content"
V2_STATIC_ROOT = APP_ROOT / "static"
LEGACY_STATIC_ROOT = PROJECT_ROOT / "player_ui" / "static"

app = Flask(__name__, static_folder=None, template_folder="templates")

subscribers: set[Queue] = set()
subscribers_lock = Lock()
events_history: list[dict[str, Any]] = []
history_limit = 250
prompts: dict[str, dict[str, Any]] = {}
prompts_lock = Lock()
prompt_limit = 300
SESSION_RESET_COMMAND = "__session_reset__"

event_ids = itertools.count(1)
prompt_ids = itertools.count(1)
session_ids = itertools.count(1)
current_session_id = f"ui-session-{next(session_ids)}"

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


def _answer_session_prompts_unlocked(session_id: str, answer: Any) -> int:
    changed = 0
    for entry in prompts.values():
        if str(entry.get("session_id") or "") != session_id:
            continue
        if entry.get("status") == "answered":
            continue
        entry["status"] = "answered"
        entry["answer"] = answer
        changed += 1
    return changed


def _prune_prompts_unlocked() -> None:
    if len(prompts) <= prompt_limit:
        return
    ordered = sorted(
        prompts.values(),
        key=lambda item: (item.get("session_id") == current_session_id, float(item.get("created_at", 0.0))),
    )
    for entry in ordered:
        if len(prompts) <= prompt_limit:
            break
        if entry.get("status") == "answered":
            prompts.pop(str(entry.get("id")), None)
    while len(prompts) > prompt_limit and ordered:
        oldest = ordered.pop(0)
        prompts.pop(str(oldest.get("id")), None)


def _session_info() -> dict[str, Any]:
    with prompts_lock:
        current_prompts = [
            entry for entry in prompts.values() if str(entry.get("session_id") or "") == current_session_id
        ]
    return {
        "id": current_session_id,
        "history_size": len(events_history),
        "prompt_count": len(current_prompts),
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


def _serialize_prompt(entry: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "ok": True,
        "id": entry["id"],
        "prompt": entry["prompt"],
        "status": entry["status"],
        "answer": entry["answer"],
        "kind": entry.get("kind"),
        "source": entry.get("source"),
        "session_id": entry.get("session_id"),
        "choices": entry.get("choices"),
        "choice_meta": entry.get("choice_meta"),
        "title": entry.get("title"),
        "subtitle": entry.get("subtitle"),
        "prompt_long": entry.get("prompt_long"),
        "image": entry.get("image"),
        "layout": entry.get("layout"),
        "action_desc": entry.get("action_desc"),
        "desc": entry.get("desc"),
        "answer_placeholder": entry.get("answer_placeholder"),
        "modifiers": entry.get("modifiers"),
        "roll_stack": entry.get("roll_stack"),
        "communication": entry.get("communication"),
    }
    payload["communication"] = normalize_communication(event_type="prompt", payload=payload, prompt=True)
    return payload


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


def build_catalog() -> dict[str, Any]:
    repo = CharacterRepository(PROJECT_ROOT / "data" / "heroes")
    heroes: list[dict[str, Any]] = []
    for item in repo.list_characters():
        snapshot = repo.load_character(str(item.get("character_id") or ""))
        if not snapshot:
            continue
        heroes.append(_hero_catalog_entry(snapshot))
    heroes.sort(key=lambda item: str(item.get("name") or "").lower())

    scenario = _load_content_manifest("bandit_cave")
    scenario_card = {
        "id": str(scenario.get("scenario_id") or "bandit_cave"),
        "title": str(scenario.get("title") or "Bandit Cave"),
        "tagline": str(scenario.get("tagline") or ""),
        "briefing_title": str(scenario.get("briefing_title") or ""),
        "briefing_intro": str(scenario.get("briefing_intro") or ""),
        "stakes": str(scenario.get("stakes") or ""),
        "briefing_points": list(scenario.get("briefing_points") or []),
        "chapters": list(scenario.get("chapters") or []),
        "primary_objectives": list(scenario.get("primary_objectives") or []),
        "optional_objectives": list(scenario.get("optional_objectives") or []),
        "transitions": dict(scenario.get("transitions") or {}),
        "result_title": str(scenario.get("result_title") or ""),
        "result_summary": str(scenario.get("result_summary") or ""),
    }
    return {"heroes": heroes, "scenarios": [scenario_card]}


def _public_base_url() -> str:
    env_url = str(os.environ.get("PLAYER_UI_V2_PUBLIC_URL") or "").strip()
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
    with prompts_lock:
        retired_prompts = _answer_session_prompts_unlocked(previous_session_id, SESSION_RESET_COMMAND)
        _prune_prompts_unlocked()
    current_session_id = f"ui-session-{next(session_ids)}"
    events_history.clear()
    event = _make_event(
        "session_reset",
        {
            "reason": reason,
            "previous_session_id": previous_session_id,
            "retired_prompts": retired_prompts,
        },
    )
    _record_event(event)
    _broadcast(event)
    with runtime_lock:
        runtime_state["session_id"] = current_session_id
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
    explicit_backend = str(os.environ.get("PLAYER_UI_V2_BOARD_BACKEND") or "").strip().lower()
    explicit_board_url = str(os.environ.get("PLAYER_UI_V2_BOARD_URL") or "").strip()
    explicit_serial_port = str(os.environ.get("PLAYER_UI_V2_BOARD_SERIAL_PORT") or "").strip()
    explicit_wled_url = str(os.environ.get("PLAYER_UI_V2_WLED_URL") or "").strip()

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
    if scenario_id != "bandit_cave":
        raise ValueError("Only 'bandit_cave' is supported in v1.")
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


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/static/<path:filename>")
def static_files(filename: str):
    normalized = str(filename).strip().lstrip("/")
    for root in (V2_STATIC_ROOT, LEGACY_STATIC_ROOT):
        candidate = root / normalized
        if candidate.exists() and candidate.is_file():
            return send_from_directory(root, normalized)
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
        normalized_body["communication"] = normalize_communication(
            event_type=str(event_type),
            payload=normalized_body,
            prompt=False,
        )
        body = normalized_body
    event = _make_event(event_type, body)
    _record_event(event)
    _broadcast(event)
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
    kind = data.get("kind") or "info"
    source = data.get("source")
    choices = data.get("choices")
    if choices is not None and not isinstance(choices, list):
        choices = None
    choice_meta = data.get("choice_meta") if isinstance(data.get("choice_meta"), list) else None
    modifiers = data.get("modifiers") if isinstance(data.get("modifiers"), dict) else None
    layout = data.get("layout")

    prompt_id = str(next(prompt_ids))
    entry = {
        "id": prompt_id,
        "prompt": prompt_text,
        "kind": kind,
        "source": source,
        "session_id": current_session_id,
        "status": "pending",
        "answer": None,
        "created_at": time.time(),
        "choices": choices,
        "choice_meta": choice_meta,
        "title": data.get("title"),
        "subtitle": data.get("subtitle"),
        "prompt_long": data.get("prompt_long"),
        "image": data.get("image"),
        "layout": layout,
        "action_desc": data.get("action_desc"),
        "desc": data.get("desc"),
        "answer_placeholder": data.get("answer_placeholder"),
        "modifiers": modifiers,
        "roll_stack": data.get("roll_stack") if isinstance(data.get("roll_stack"), dict) else None,
        "communication": data.get("communication") if isinstance(data.get("communication"), dict) else None,
    }
    entry["communication"] = normalize_communication(event_type="prompt", payload=entry, prompt=True)
    with prompts_lock:
        prompts[prompt_id] = entry
        _prune_prompts_unlocked()

    event = _make_event("prompt", entry)
    _record_event(event)
    _broadcast(event)
    return jsonify(
        {
            "ok": True,
            "id": prompt_id,
            "prompt": prompt_text,
            "session_id": current_session_id,
            "communication": entry.get("communication"),
        }
    )


@app.get("/api/prompts")
def list_prompts():
    with prompts_lock:
        values = [
            value
            for value in prompts.values()
            if str(value.get("session_id") or "") == current_session_id
        ]
    session = {
        "id": current_session_id,
        "history_size": len(events_history),
        "prompt_count": len(values),
    }
    return jsonify({"ok": True, "session": session, "prompts": [_serialize_prompt(value) for value in values]})


@app.get("/api/prompts/<prompt_id>")
def get_prompt(prompt_id: str):
    with prompts_lock:
        entry = prompts.get(prompt_id)
    if not entry:
        return jsonify({"ok": False, "error": "prompt not found"}), 404
    return jsonify(_serialize_prompt(entry))


@app.post("/api/prompts/<prompt_id>/response")
def set_prompt_response(prompt_id: str):
    data = request.get_json(force=True, silent=True) or {}
    answer = data.get("answer")
    entry_session_id = None
    stored_answer = None
    already_answered = False
    with prompts_lock:
        entry = prompts.get(prompt_id)
        if not entry:
            return jsonify({"ok": False, "error": "prompt not found"}), 404
        entry_session_id = str(entry.get("session_id") or "")
        if entry.get("status") == "answered":
            already_answered = True
            stored_answer = entry.get("answer")
        else:
            entry["status"] = "answered"
            entry["answer"] = answer
            stored_answer = answer
        _prune_prompts_unlocked()
    if already_answered:
        return jsonify(
            {
                "ok": True,
                "id": prompt_id,
                "answer": stored_answer,
                "session_id": entry_session_id,
                "ignored": True,
            }
        )
    if entry_session_id != current_session_id:
        return jsonify(
            {
                "ok": True,
                "id": prompt_id,
                "answer": stored_answer,
                "session_id": entry_session_id,
            }
        )
    event = _make_event("prompt_answered", {"id": prompt_id, "answer": stored_answer, "prompt": entry["prompt"]})
    _record_event(event)
    _broadcast(event)
    return jsonify(
        {
            "ok": True,
            "id": prompt_id,
            "answer": stored_answer,
            "session_id": entry.get("session_id"),
        }
    )


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
        return jsonify({"ok": False, "error": "At most 4 hero_ids are supported in v1."}), 400
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


if __name__ == "__main__":
    host = os.environ.get("PLAYER_UI_HOST", "127.0.0.1")
    port = int(os.environ.get("PLAYER_UI_PORT", "5200"))
    debug_flag = str(os.environ.get("FLASK_DEBUG", "1")).lower() not in ("0", "false", "no")
    app.run(host=host, port=port, debug=debug_flag, threaded=True)
