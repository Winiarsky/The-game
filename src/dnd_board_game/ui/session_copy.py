"""Editable presentation copy shared by the application and session-zero pack."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

DEFAULT_PACK = Path(__file__).resolve().parents[3] / "content/scenarios/misja_0_dzwon"


def load_ui_copy(root: Path | None = None) -> dict[str, Any]:
    """Read on each request so prose edits do not require rebuilding the app."""
    folder = (root or DEFAULT_PACK) / "text/ui"
    if not folder.is_dir():
        folder = DEFAULT_PACK / "text/ui"
    result: dict[str, Any] = {}
    for source in sorted(folder.glob("*.json")):
        try:
            value = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise ValueError(f"Nie można odczytać tekstów UI: {source}: {error}") from error
        if not isinstance(value, dict):
            raise ValueError(f"Teksty UI muszą być obiektem JSON: {source}")
        result[source.stem] = value
    return result


def render_ui_text(copy: Mapping[str, Any], key: str, **params: object) -> str:
    value: Any = copy
    for part in key.split("."):
        if not isinstance(value, dict) or part not in value:
            raise ValueError(f"Brak tekstu UI: {key}")
        value = value[part]
    if not isinstance(value, str):
        raise ValueError(f"Tekst UI nie jest napisem: {key}")
    for name, replacement in params.items():
        value = value.replace("{" + name + "}", str(replacement))
    return value


def ui_text(key: str, /, *, root: Path | None = None, **params: object) -> str:
    return render_ui_text(load_ui_copy(root), key, **params)
