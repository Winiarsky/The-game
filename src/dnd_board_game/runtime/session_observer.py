from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


def _utc_timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


@dataclass(slots=True)
class SessionObserver:
    session_id: str
    output_dir: Path = Path("data/session_observations")
    _seq: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("session_id cannot be empty.")
        if not SESSION_ID_PATTERN.fullmatch(self.session_id):
            raise ValueError("session_id can only contain letters, numbers, '_', '-' and '.'.")
        self.output_dir = Path(self.output_dir)

    @property
    def path(self) -> Path:
        return self.output_dir / f"{self.session_id}.jsonl"

    def record(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        if not event_type:
            raise ValueError("event_type cannot be empty.")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._seq += 1
        event = {
            "ts": _utc_timestamp(),
            "session_id": self.session_id,
            "seq": self._seq,
            "event_type": event_type,
            "payload": payload or {},
        }
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True))
            stream.write("\n")


class NullSessionObserver:
    session_id = "none"
    path: Path | None = None

    def record(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        return None

