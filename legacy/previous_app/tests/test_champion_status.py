from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from statuses.classes.champion.champion import CHAMPION_STATUS


def test_champion_status_has_expected_identity():
    assert CHAMPION_STATUS.id == "champion"
    assert CHAMPION_STATUS.label == "Champion"


def test_champion_prompt_contains_core_sections():
    prompt = str((CHAMPION_STATUS.data or {}).get("ui_prompt") or "")
    assert "KEY ABILITY: STRENGTH OR DEXTERITY" in prompt
    assert "HIT POINTS: 10 plus your Constitution Modifier" in prompt
    assert "Expert in Fortitude" in prompt
    assert "Trained in Reflex" in prompt
    assert "Expert in Will" in prompt
    assert "Trained in Religion" in prompt
    assert "Trained in all armor" in prompt
