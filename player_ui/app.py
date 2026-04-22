from __future__ import annotations

import itertools
import json
import time
import os
from pathlib import Path
import sys
import threading
import webbrowser
from queue import Empty, Queue
from threading import Lock
from typing import Any

from flask import Flask, Response, jsonify, render_template, request

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from communication import normalize_communication

app = Flask(__name__, static_folder="static", template_folder="templates")

subscribers: set[Queue] = set()
subscribers_lock = Lock()
events_history: list[dict[str, Any]] = []
history_limit = 200
prompts: dict[str, dict[str, Any]] = {}
prompts_lock = Lock()
prompt_limit = 300
SESSION_RESET_COMMAND = "__session_reset__"

event_ids = itertools.count(1)
prompt_ids = itertools.count(1)
session_ids = itertools.count(1)
current_session_id = f"ui-session-{next(session_ids)}"


# --- Helpers ---

def _format_sse(event: dict[str, Any]) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


def _broadcast(event: dict[str, Any]) -> None:
    with subscribers_lock:
        for queue in list(subscribers):
            try:
                queue.put_nowait(event)
            except Exception:
                # klient rozłączony lub jego kolejka jest pełna
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


# --- Routes ---


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/session")
def get_session():
    return jsonify({"ok": True, "session": _session_info()})


@app.post("/api/session/reset")
def reset_session():
    global current_session_id
    data = request.get_json(force=True, silent=True) or {}
    reason = str(data.get("reason") or "manual").strip() or "manual"
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
    return jsonify(
        {
            "ok": True,
            "session": _session_info(),
            "previous_session_id": previous_session_id,
            "retired_prompts": retired_prompts,
        }
    )


@app.get("/stream")
def stream():
    """Strumień SSE dla frontu."""
    queue: Queue = Queue()
    with subscribers_lock:
        subscribers.add(queue)

    def _generator():
        # wyślij historię, żeby nowi klienci dostali kontekst
        for event in events_history[-50:]:
            yield _format_sse(event)
        try:
            while True:
                event = queue.get()
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
    prompt_text = (data.get("prompt") or "").strip()
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

    event = _make_event(
        "prompt_answered", {"id": prompt_id, "answer": stored_answer, "prompt": entry["prompt"]}
    )
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


if __name__ == "__main__":
    host = os.environ.get("PLAYER_UI_HOST", "127.0.0.1")
    port = int(os.environ.get("PLAYER_UI_PORT", "5100"))
    debug_flag = str(os.environ.get("FLASK_DEBUG", "1")).lower() not in ("0", "false", "no")

    # Opcjonalne auto-otwarcie przeglądarki – domyślnie wyłączone.
    # Włącz tylko przez PLAYER_UI_AUTO_BROWSER=1.
    def _open_browser() -> None:
        try:
            webbrowser.open(f"http://{host}:{port}/")
        except Exception:
            pass

    if os.environ.get("PLAYER_UI_AUTO_BROWSER") in ("1", "true", "yes"):
        # W debug mode reloader odpala kod 2x; otwieramy tylko w głównym procesie.
        if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
            threading.Timer(0.8, _open_browser).start()

    app.run(host=host, port=port, debug=debug_flag, threaded=True)
