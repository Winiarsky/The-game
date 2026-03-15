from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from character_creation.catalog import ANCESTRY_FEAT_IDS_BY_ANCESTRY
from character_creation.pipeline import _filter_ancestry_feat_ids_for_selection, _status_mechanics_short
from statuses.race.human.feats.haughty_obstinacy import HAUGHTY_OBSTINACY_STATUS
from statuses.race.human.feats.natural_skill import NATURAL_SKILL_STATUS
from statuses.race.human.feats.orc_ferocity import ORC_FEROCITY_STATUS
from statuses.race.goblin.feats.city_scavenger import CITY_SCAVENGER_STATUS


def test_half_orc_filters_out_elf_specific_feats():
    all_human_feats = list(ANCESTRY_FEAT_IDS_BY_ANCESTRY.get("human", []) or [])
    filtered = _filter_ancestry_feat_ids_for_selection("human", "half_orc", all_human_feats)
    assert "elf_atavism" not in filtered
    assert "haughty_obstinacy" not in filtered
    assert "orc_ferocity" in filtered
    assert "orc_weapon_familiarity" in filtered


def test_half_elf_filters_out_orc_specific_feats():
    all_human_feats = list(ANCESTRY_FEAT_IDS_BY_ANCESTRY.get("human", []) or [])
    filtered = _filter_ancestry_feat_ids_for_selection("human", "half_elf", all_human_feats)
    assert "elf_atavism" in filtered
    assert "haughty_obstinacy" in filtered
    assert "orc_ferocity" not in filtered
    assert "orc_weapon_familiarity" not in filtered


def test_regular_human_heritage_uses_generic_human_feats_only():
    all_human_feats = list(ANCESTRY_FEAT_IDS_BY_ANCESTRY.get("human", []) or [])
    filtered = _filter_ancestry_feat_ids_for_selection("human", "skilled_heritage", all_human_feats)
    assert "natural_skill" in filtered
    assert "general_training" in filtered
    assert "elf_atavism" not in filtered
    assert "orc_ferocity" not in filtered


def test_status_mechanics_short_prefers_mechanical_line():
    text = _status_mechanics_short(NATURAL_SKILL_STATUS)
    assert "Mechanika" in text or "zyskujesz" in text.lower()

    text2 = _status_mechanics_short(ORC_FEROCITY_STATUS)
    assert "Mechanika" in text2 or "1 HP" in text2

    text3 = _status_mechanics_short(HAUGHTY_OBSTINACY_STATUS)
    assert "save" in text3.lower() or "coerce" in text3.lower() or "Mechanika" in text3


def test_status_mechanics_short_does_not_duplicate_same_bonus_without_target():
    text = _status_mechanics_short(CITY_SCAVENGER_STATUS)
    assert "+1 circumstance, +1 circumstance" not in text
    assert "Spoleczenstwo" in text
    assert "Przetrwanie" in text
