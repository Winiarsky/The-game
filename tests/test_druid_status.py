from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from statuses.classes.druid.druid import DRUID_STATUS


def test_druid_status_identity():
    assert DRUID_STATUS.id == "druid"
    assert DRUID_STATUS.label == "Druid"


def test_druid_prompt_contains_core_sections():
    prompt = str((DRUID_STATUS.data or {}).get("ui_prompt") or "")
    assert "KEY ABILITY: WISDOM" in prompt
    assert "HIT POINTS: 8 plus your Constitution Modifier" in prompt
    assert "Trained in Nature" in prompt
    assert "Primal spellcasting" in prompt


def test_druid_sets_class_name_and_focus_point():
    attrs = dict((DRUID_STATUS.data or {}).get("set_actor_attrs") or {})
    assert attrs.get("class_name") == "druid"
    assert attrs.get("focus_point") == 1
