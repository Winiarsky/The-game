from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from statuses.classes.fighter.fighter import FIGHTER_STATUS


def test_fighter_status_identity():
    assert FIGHTER_STATUS.id == "fighter"
    assert FIGHTER_STATUS.label == "Fighter"


def test_fighter_prompt_contains_core_sections():
    prompt = str((FIGHTER_STATUS.data or {}).get("ui_prompt") or "")
    assert "KEY ABILITY: STRENGTH or DEXTERITY" in prompt
    assert "HIT POINTS: 10 plus your Constitution Modifier" in prompt
    assert "Atak okazyjny" in prompt
    assert "Shield Block" in prompt


def test_fighter_grants_guaranteed_features():
    grants = list((FIGHTER_STATUS.data or {}).get("grants_statuses") or [])
    grant_ids = [getattr(item, "id", str(item)) for item in grants]
    assert "opportunity_attack" in grant_ids
    assert "shield_block" in grant_ids
