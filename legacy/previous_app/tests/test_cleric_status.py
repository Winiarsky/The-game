from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from statuses.classes.cleric.cleric import CLERIC_STATUS


def test_cleric_status_identity():
    assert CLERIC_STATUS.id == "cleric"
    assert CLERIC_STATUS.label == "Cleric"


def test_cleric_prompt_contains_core_sections():
    prompt = str((CLERIC_STATUS.data or {}).get("ui_prompt") or "")
    assert "KEY ABILITY: WISDOM" in prompt
    assert "DIVINE FONT:" in prompt
    assert "DOCTRINE:" in prompt
    assert "Cloistered Cleric" in prompt
    assert "Warpriest" in prompt


def test_cleric_grants_shield_block():
    grants = list((CLERIC_STATUS.data or {}).get("grants_statuses") or [])
    grant_ids = [getattr(item, "id", str(item)) for item in grants]
    assert "shield_block" in grant_ids
