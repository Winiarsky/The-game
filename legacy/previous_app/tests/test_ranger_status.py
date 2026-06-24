from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from statuses.classes.ranger.ranger import RANGER_STATUS


def test_ranger_status_identity():
    assert RANGER_STATUS.id == "ranger"
    assert RANGER_STATUS.label == "Ranger"


def test_ranger_prompt_contains_core_sections():
    prompt = str((RANGER_STATUS.data or {}).get("ui_prompt") or "")
    assert "KEY ABILITY: STRENGTH OR DEXTERITY" in prompt
    assert "HIT POINTS: 10 plus your Constitution Modifier" in prompt
    assert "Hunt Prey" in prompt
    assert "Hunter's Edge" in prompt


def test_ranger_sets_class_name_and_grants_hunt_prey():
    attrs = dict((RANGER_STATUS.data or {}).get("set_actor_attrs") or {})
    assert attrs.get("class_name") == "ranger"

    grants = list((RANGER_STATUS.data or {}).get("grants_statuses") or [])
    grant_ids = [getattr(item, "id", str(item)) for item in grants]
    assert "hunt_prey" in grant_ids
