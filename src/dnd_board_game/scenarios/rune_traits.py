"""Canonical flaw descriptions for rune heroes, independent of legacy mana."""
from __future__ import annotations

import json
from pathlib import Path
from functools import lru_cache
from dnd_board_game.character_creation.boardgame_help import RuleNote


def rune_flaw(hero_id: str) -> RuleNote:
    path = Path(__file__).resolve().parents[3] / "content/print/runes_v01/flaws.json"
    return _flaw(hero_id, path, path.stat().st_mtime_ns)


@lru_cache(maxsize=28)
def _flaw(hero_id: str, path: Path, modified: int) -> RuleNote:
    row = json.loads(path.read_text(encoding="utf-8"))[hero_id]
    return RuleNote(row["name"], row["description"])
