from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from statuses.classes.rogue.rogue import ROGUE_STATUS


def test_rogue_status_identity():
    assert ROGUE_STATUS.id == "rogue"
    assert ROGUE_STATUS.label == "Rogue"


def test_rogue_prompt_contains_core_sections():
    prompt = str((ROGUE_STATUS.data or {}).get("ui_prompt") or "")
    assert "KEY ABILITY" in prompt
    assert "Sneak Attack" in prompt
    assert "Surprise Attack" in prompt


def test_rogue_grants_core_features():
    grants = list((ROGUE_STATUS.data or {}).get("grants_statuses") or [])
    grant_ids = [getattr(item, "id", str(item)) for item in grants]
    assert "sneak_attack" in grant_ids
    assert "surprise_attack" in grant_ids

