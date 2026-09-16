"""Editable narrative packs. Reads are fresh; state contains IDs, never prose."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

MISSION_ID = 'misja_0_dzwon'


def local_path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Plik musi należeć do paczki scenariusza.')
    return path


def read_json(root: Path, relative: str) -> Any:
    return json.loads(local_path(root, relative).read_text(encoding='utf-8'))


def text_entry(root: Path, key: str, **values: object) -> dict[str, str]:
    entry = read_json(root, 'text/index.json')[key]
    body = local_path(root, entry['path']).read_text(encoding='utf-8').strip()
    for name, value in values.items():
        body = body.replace('{' + name + '}', str(value))
    return dict(id=key, title=entry['title'], speaker=entry['speaker'], body=body)


def asset_url(root: Path, relative: str) -> str:
    path = local_path(root, relative)
    return '/scenario-assets/' + relative + '?v=' + sha256(path.read_bytes()).hexdigest()[:12]
