from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROMPT_TEXTS_DIR = PROJECT_ROOT / "prompt_texts" / "pl"


class _SafeFormatDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + str(key) + "}"


def _normalize_text(value: Any) -> str | None:
    raw = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in raw.splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return None
    compact: list[str] = []
    blank_run = 0
    for line in lines:
        if not line.strip():
            blank_run += 1
            if blank_run > 1:
                continue
            compact.append("")
            continue
        blank_run = 0
        compact.append(line)
    text = "\n".join(compact).strip()
    return text or None


def load_prompt_catalog() -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    if not PROMPT_TEXTS_DIR.exists():
        return catalog
    for path in sorted(PROMPT_TEXTS_DIR.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        for prompt_id, entry in payload.items():
            if isinstance(prompt_id, str) and isinstance(entry, dict):
                catalog[prompt_id] = dict(entry)
    return catalog


def _render_value(value: Any, values: _SafeFormatDict) -> Any:
    if isinstance(value, str):
        try:
            text = value.format_map(values)
        except Exception:
            text = value
        return _normalize_text(text)
    if isinstance(value, dict):
        rendered_dict: dict[str, Any] = {}
        for key, nested in value.items():
            rendered_dict[str(key)] = _render_value(nested, values)
        return rendered_dict
    if isinstance(value, list):
        return [_render_value(item, values) for item in value]
    return value


def render_prompt_text(prompt_id: str, **context: Any) -> dict[str, Any]:
    entry = load_prompt_catalog().get(str(prompt_id or "").strip(), {})
    if not isinstance(entry, dict):
        return {}
    values = _SafeFormatDict({key: "" if value is None else value for key, value in context.items()})
    rendered: dict[str, Any] = {}
    for key, value in entry.items():
        rendered[key] = _render_value(value, values)
    return rendered
