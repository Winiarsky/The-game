from __future__ import annotations

import itertools
import json
import time
from queue import Empty, Queue
from threading import Lock
from typing import Any

from flask import Flask, Response, jsonify, render_template, request

app = Flask(__name__, static_folder="static", template_folder="templates")

subscribers: set[Queue] = set()
subscribers_lock = Lock()
events_history: list[dict[str, Any]] = []
history_limit = 200
prompts: dict[str, dict[str, Any]] = {}
prompts_lock = Lock()

event_ids = itertools.count(1)
prompt_ids = itertools.count(1)


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
    }


# --- Routes ---


@app.get("/")
def index():
    return render_template("index.html")


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
    event_type = payload.get("type") or "log"
    body = payload.get("payload") or {}
    event = _make_event(event_type, body)
    _record_event(event)
    _broadcast(event)
    return jsonify({"ok": True, "event": event})


@app.post("/api/prompts")
def create_prompt():
    data = request.get_json(force=True, silent=True) or {}
    prompt_text = (data.get("prompt") or "").strip()
    if not prompt_text:
        return jsonify({"ok": False, "error": "prompt is required"}), 400
    kind = data.get("kind") or "info"
    source = data.get("source")
    choices = data.get("choices")
    if choices is not None and not isinstance(choices, list):
        choices = None

    prompt_id = str(next(prompt_ids))
    entry = {
        "id": prompt_id,
        "prompt": prompt_text,
        "kind": kind,
        "source": source,
        "status": "pending",
        "answer": None,
        "created_at": time.time(),
        "choices": choices,
    }
    with prompts_lock:
        prompts[prompt_id] = entry

    event = _make_event("prompt", entry)
    _record_event(event)
    _broadcast(event)

    return jsonify({"ok": True, "id": prompt_id, "prompt": prompt_text})


@app.get("/api/prompts")
def list_prompts():
    with prompts_lock:
        values = list(prompts.values())
    return jsonify({"ok": True, "prompts": values})


@app.get("/api/prompts/<prompt_id>")
def get_prompt(prompt_id: str):
    with prompts_lock:
        entry = prompts.get(prompt_id)
    if not entry:
        return jsonify({"ok": False, "error": "prompt not found"}), 404
    return jsonify(
        {
            "ok": True,
            "id": entry["id"],
            "prompt": entry["prompt"],
            "status": entry["status"],
            "answer": entry["answer"],
            "kind": entry.get("kind"),
            "source": entry.get("source"),
            "choices": entry.get("choices"),
        }
    )


@app.post("/api/prompts/<prompt_id>/response")
def set_prompt_response(prompt_id: str):
    data = request.get_json(force=True, silent=True) or {}
    answer = data.get("answer")
    with prompts_lock:
        entry = prompts.get(prompt_id)
        if not entry:
            return jsonify({"ok": False, "error": "prompt not found"}), 404
        entry["status"] = "answered"
        entry["answer"] = answer

    event = _make_event(
        "prompt_answered", {"id": prompt_id, "answer": answer, "prompt": entry["prompt"]}
    )
    _record_event(event)
    _broadcast(event)

    return jsonify({"ok": True, "id": prompt_id, "answer": answer})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5100, debug=True, threaded=True)
