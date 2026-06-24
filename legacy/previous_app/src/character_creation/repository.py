from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(item) for item in value]
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if hasattr(value, "id") and hasattr(value, "label"):
        return {
            "id": str(getattr(value, "id", "") or ""),
            "label": str(getattr(value, "label", "") or ""),
            "data": _to_jsonable(getattr(value, "data", None)),
        }
    if hasattr(value, "__dict__"):
        return _to_jsonable(vars(value))
    return str(value)


@dataclass
class CharacterRepository:
    base_dir: Path

    def ensure(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, character_id: str) -> Path:
        safe = str(character_id or "").strip().lower().replace(" ", "_")
        return self.base_dir / f"{safe}.json"

    def list_characters(self) -> list[dict[str, Any]]:
        self.ensure()
        out: list[dict[str, Any]] = []
        for path in sorted(self.base_dir.glob("*.json")):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(raw, dict):
                continue
            char_id = str(raw.get("character_id") or path.stem).strip()
            if not char_id:
                continue
            out.append(
                {
                    "character_id": char_id,
                    "name": str(raw.get("name") or char_id),
                    "class_id": str(raw.get("class_id") or ""),
                    "ancestry_id": str(raw.get("ancestry_id") or ""),
                    "level": int(raw.get("level") or 1),
                    "updated_at": str(raw.get("updated_at") or ""),
                    "path": str(path),
                }
            )
        return out

    def load_character(self, character_id: str) -> dict[str, Any] | None:
        self.ensure()
        path = self._path(character_id)
        if not path.exists():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        return raw if isinstance(raw, dict) else None

    def save_character(self, snapshot: dict[str, Any]) -> str:
        self.ensure()
        character_id = str(snapshot.get("character_id") or "").strip().lower().replace(" ", "_")
        if not character_id:
            raise ValueError("Brak character_id w snapshot.")
        path = self._path(character_id)
        payload = _to_jsonable(dict(snapshot))
        if not payload.get("created_at"):
            payload["created_at"] = _now_iso()
        payload["updated_at"] = _now_iso()
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return character_id


__all__ = ["CharacterRepository"]
