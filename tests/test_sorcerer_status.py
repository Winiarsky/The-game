from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from statuses.classes.sorcerer.sorcerer import SORCERER_STATUS


def test_sorcerer_status_identity():
    assert SORCERER_STATUS.id == "sorcerer"
    assert SORCERER_STATUS.label == "Sorcerer"


def test_sorcerer_prompt_contains_core_sections():
    prompt = str((SORCERER_STATUS.data or {}).get("ui_prompt") or "")
    assert "KEY ABILITY: CHARISMA" in prompt
    assert "HIT POINTS: 6 plus your Constitution Modifier" in prompt
    assert "Bloodline" in prompt
    assert "Focus Pool: 1 Focus Point." in prompt


def test_sorcerer_sets_class_name_and_focus_point():
    attrs = dict((SORCERER_STATUS.data or {}).get("set_actor_attrs") or {})
    assert attrs.get("class_name") == "sorcerer"
    assert attrs.get("focus_point") == 1


def test_sorcerer_setup_choices_include_bloodlines_and_feats():
    data = SORCERER_STATUS.data or {}
    bloodlines = list(data.get("sorcerer_bloodline_choices") or [])
    feats = list(data.get("sorcerer_feat_choices") or [])

    assert "draconic" in bloodlines
    assert "elemental" in bloodlines
    assert "counterspell" in feats
    assert "dangerous_sorcery" in feats
