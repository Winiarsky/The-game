from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from statuses.classes.wizard.wizard import WIZARD_STATUS


def test_wizard_status_identity():
    assert WIZARD_STATUS.id == "wizard"
    assert WIZARD_STATUS.label == "Wizard"


def test_wizard_prompt_contains_core_sections():
    prompt = str((WIZARD_STATUS.data or {}).get("ui_prompt") or "")
    assert "KEY ABILITY: INTELLIGENCE" in prompt
    assert "HIT POINTS: 6 plus your Constitution Modifier" in prompt
    assert "Arcane Spellcasting" in prompt
    assert "Arcane Thesis" in prompt


def test_wizard_sets_class_name():
    attrs = dict((WIZARD_STATUS.data or {}).get("set_actor_attrs") or {})
    assert attrs.get("class_name") == "wizard"


def test_wizard_setup_choices_include_schools_theses_and_feats():
    data = WIZARD_STATUS.data or {}
    studies = list(data.get("wizard_arcane_study_choices") or [])
    theses = list(data.get("wizard_arcane_thesis_choices") or [])
    feats = list(data.get("wizard_feat_choices") or [])

    assert "evocation" in studies
    assert "universalist" in studies
    assert "metamagical_experimentation" in theses
    assert "staff_nexus" in theses
    assert "eschew_materials" in feats
    assert "hand_of_the_apprentice" not in feats
