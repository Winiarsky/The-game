from __future__ import annotations

import json
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any


def _safe_actor_id(actor: Any) -> str | None:
    if actor is None:
        return None
    try:
        return str(getattr(actor, "object_id", None) or getattr(actor, "name", None) or id(actor))
    except Exception:
        return None


class DebugTrace:
    """Prosty trace runtime gry zapisywany do JSONL."""

    def __init__(self, root_dir: Path | str, *, session_id: str | None = None) -> None:
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = self.root_dir / f"{self.session_id}.jsonl"
        self._lock = threading.Lock()
        self._fh = self.path.open("a", encoding="utf-8")

    def close(self) -> None:
        with self._lock:
            try:
                self._fh.flush()
            except Exception:
                pass
            try:
                self._fh.close()
            except Exception:
                pass

    def write(self, event_type: str, **payload: Any) -> None:
        entry = {
            "ts_unix": round(time.time(), 6),
            "ts_iso": datetime.now().isoformat(timespec="milliseconds"),
            "session_id": self.session_id,
            "event_type": event_type,
            "payload": self._to_json_safe(payload),
        }
        line = json.dumps(entry, ensure_ascii=False)
        with self._lock:
            self._fh.write(line + "\n")
            self._fh.flush()

    def write_exception(self, where: str, exc: BaseException, **extra: Any) -> None:
        self.write(
            "exception",
            where=where,
            error_type=exc.__class__.__name__,
            error=str(exc),
            traceback=traceback.format_exc(),
            **extra,
        )

    def snapshot_game(self, game: Any) -> dict[str, Any]:
        state = getattr(game, "state", None)
        state_name = getattr(getattr(state, "__class__", None), "__name__", None)
        active_actor = None
        try:
            getter = getattr(state, "_current_actor", None)
            if callable(getter):
                active_actor = getter()
        except Exception:
            active_actor = None

        out: dict[str, Any] = {
            "state": state_name,
            "active_actor_id": _safe_actor_id(active_actor),
            "round_index": getattr(state, "round_index", None),
            "turn_index": getattr(state, "turn_index", None),
            "heroes": [self._actor_snapshot(a) for a in list(getattr(game, "heroes", []) or [])],
            "enemies": [self._actor_snapshot(a) for a in list(getattr(game, "enemies", []) or [])],
        }
        return self._to_json_safe(out)

    def _actor_snapshot(self, actor: Any) -> dict[str, Any]:
        statuses: list[str] = []
        try:
            labels = getattr(actor, "status_labels", None)
            if callable(labels):
                statuses = [str(x) for x in list(labels() or [])]
            else:
                statuses = [
                    str(getattr(s, "id", getattr(s, "label", s)))
                    for s in list(getattr(actor, "statuses", []) or [])
                ]
        except Exception:
            statuses = []
        return {
            "id": _safe_actor_id(actor),
            "name": getattr(actor, "name", None),
            "pos": getattr(actor, "position", None),
            "hp": getattr(actor, "hp", None),
            "max_hp": getattr(actor, "max_hp", None),
            "ac": getattr(actor, "ac", None),
            "statuses": statuses,
        }

    def _to_json_safe(self, value: Any, *, _depth: int = 0) -> Any:
        if _depth > 8:
            return str(value)
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, dict):
            out: dict[str, Any] = {}
            for k, v in value.items():
                out[str(k)] = self._to_json_safe(v, _depth=_depth + 1)
            return out
        if isinstance(value, (list, tuple, set)):
            return [self._to_json_safe(v, _depth=_depth + 1) for v in value]

        if hasattr(value, "value") and not isinstance(value, type):
            try:
                return self._to_json_safe(value.value, _depth=_depth + 1)
            except Exception:
                pass

        if hasattr(value, "__dict__"):
            try:
                raw = dict(vars(value))
                return {"__type__": value.__class__.__name__, **self._to_json_safe(raw, _depth=_depth + 1)}
            except Exception:
                pass

        return str(value)
