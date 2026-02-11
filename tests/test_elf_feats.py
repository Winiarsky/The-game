import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.Enemies.enemy_types import EnemyType  # noqa: F401,E402  # preload to uniknąć pętli importów
from GameObjects.interactions_mixin import resolve_skill_check_with_sources  # noqa: E402
from skills import Skill  # noqa: E402
from statuses.race.elf import (  # noqa: E402
    ANCESTRAL_LONGEVITY_STATUS,
    ELVEN_LORE_STATUS,
    ELVEN_WEAPON_MILITARY_STATUS,
    FORLORN_STATUS,
    NIMBLE_ELF_STATUS,
    OTHERWORLDLY_MAGIC_STATUS,
    UNWAVERING_MIEN_STATUS,
)


class DummyActor:
    def __init__(self, statuses=None, bonuses=None):
        self.statuses = statuses or []
        self.bonuses = bonuses or []


def test_forlorn_bonus_and_promote(monkeypatch):
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_: 10)
    target = DummyActor(statuses=[FORLORN_STATUS])
    res = resolve_skill_check_with_sources(
        skill_id=Skill.WILL.value,
        dc=10,
        actor=DummyActor(),
        target=target,
        tags=["saving_throw", "emotions"],
        apply_modifiers=False,
    )
    assert res.modifier == 1
    assert res.outcome == "critical_success"


def test_unwavering_mien_bonus_and_promote(monkeypatch):
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_: 10)
    target = DummyActor(statuses=[UNWAVERING_MIEN_STATUS])
    res = resolve_skill_check_with_sources(
        skill_id=Skill.FORTITUDE.value,
        dc=10,
        actor=DummyActor(),
        target=target,
        tags=["sleep"],
        apply_modifiers=False,
    )
    assert res.modifier == 1
    assert res.outcome == "critical_success"


def test_info_statuses_present():
    # tylko upewniamy się, że statusy istnieją i mają notki
    assert ANCESTRAL_LONGEVITY_STATUS.data.get("prompt_notes")
    assert ELVEN_LORE_STATUS.data.get("prompt_notes")
    assert ELVEN_WEAPON_MILITARY_STATUS.data.get("prompt_notes")
    assert NIMBLE_ELF_STATUS.data.get("speed_bonus") == 5
    assert OTHERWORLDLY_MAGIC_STATUS.data.get("prompt_notes")
