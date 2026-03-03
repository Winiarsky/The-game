from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from statuses.classes.monk.monk import MONK_STATUS


def test_monk_status_identity():
    assert MONK_STATUS.id == "monk"
    assert MONK_STATUS.label == "Monk"


def test_monk_prompt_contains_core_sections():
    prompt = str((MONK_STATUS.data or {}).get("ui_prompt") or "")
    assert "KEY ABILITY: STRENGTH OR DEXTERITY" in prompt
    assert "HIT POINTS: 10 plus your Constitution Modifier" in prompt
    assert "Flurry of Blows" in prompt
    assert "Powerful Fist" in prompt


def test_monk_grants_core_features():
    grants = list((MONK_STATUS.data or {}).get("grants_statuses") or [])
    grant_ids = [getattr(item, "id", str(item)) for item in grants]
    assert "flurry_of_blows" in grant_ids
    assert "powerful_fist" in grant_ids
