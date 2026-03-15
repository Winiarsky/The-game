from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from hero import Hero
from character_creation.pipeline import _sync_creation_preview_from_selected


def _selected(**overrides):
    base = {
        "portrait_image": "/static/placeholder.png",
        "name": "Preview",
        "concept": "",
        "ancestry_id": "",
        "heritage_id": "",
        "ancestry_feat_id": "",
        "background_id": "",
        "class_id": "",
        "barbarian_instinct_id": "",
        "manual_class_feat_id": "",
    }
    base.update(dict(overrides or {}))
    return base


def test_preview_starts_from_tens_before_heritage_choice():
    hero = Hero()
    _sync_creation_preview_from_selected(hero, _selected(ancestry_id="elf"))

    scores = dict(getattr(hero, "ability_scores", {}) or {})
    assert scores
    assert all(int(scores.get(key, -999)) == 10 for key in ("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"))


def test_preview_applies_ancestry_boosts_and_flaw_after_heritage_choice():
    hero = Hero()
    _sync_creation_preview_from_selected(
        hero,
        _selected(
            ancestry_id="elf",
            heritage_id="arctic_elf",
        ),
    )

    scores = dict(getattr(hero, "ability_scores", {}) or {})
    # Elf ancestry: DEX +2, INT +2, free (pomijany na etapie preview), CON -2.
    assert int(scores.get("dexterity", 0)) == 12
    assert int(scores.get("intelligence", 0)) == 12
    assert int(scores.get("constitution", 0)) == 8
    assert int(scores.get("strength", 0)) == 10
    assert int(scores.get("wisdom", 0)) == 10
    assert int(scores.get("charisma", 0)) == 10


def test_preview_includes_background_feat_status_when_background_selected():
    hero = Hero()
    _sync_creation_preview_from_selected(
        hero,
        _selected(background_id="background_acolyte"),
    )

    status_ids = {str(getattr(item, "id", "") or "").strip().lower() for item in list(getattr(hero, "statuses", []) or [])}
    assert "background_acolyte" in status_ids
    # Acolyte daje skill feat z tła.
    assert "student_of_the_canon" in status_ids

