import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.Enemies.enemy_types import EnemyType  # noqa: F401,E402  # preload to uniknąć pętli importów
from skills import Skill  # noqa: E402
from GameObjects.interactions_mixin.skill_check_resolver import (  # noqa: E402
    resolve_skill_check_with_sources,
)
from statuses.race.gnome import (  # noqa: E402
    CHAMELEON_GNOME_STATUS,
    FEY_TOUCHED_GNOME_STATUS,
    SENSATE_GNOME_STATUS,
    UMBRAL_GNOME_STATUS,
    WELLSPRING_GNOME_STATUS,
)
from statuses import IN_DARK_STATUS  # noqa: E402


class DummyActor:
    def __init__(self, statuses=None, bonuses=None):
        self.statuses = statuses or []
        self.bonuses = bonuses or []

    def has_status(self, status_id):
        return any(status_id == s or getattr(s, "id", None) == status_id for s in self.statuses)


def test_chameleon_gnome_bonus_try_stealth(monkeypatch):
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_: 10)
    actor = DummyActor(statuses=[CHAMELEON_GNOME_STATUS])
    res = resolve_skill_check_with_sources(
        skill_id=Skill.STEALTH.value,
        dc=10,
        actor=actor,
        target=None,
        tags=["try_stealth", Skill.STEALTH.value],
        apply_modifiers=False,
    )
    assert res.modifier == 2


def test_sensate_gnome_seek_bonus(monkeypatch):
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_: 12)
    actor = DummyActor(statuses=[SENSATE_GNOME_STATUS])
    res = resolve_skill_check_with_sources(
        skill_id=Skill.PERCEPTION.value,
        dc=12,
        actor=actor,
        target=None,
        tags=["seek", Skill.PERCEPTION.value],
        apply_modifiers=False,
    )
    assert res.modifier == 2


def test_umbral_gnome_blocks_in_dark_status():
    actor = DummyActor(statuses=[UMBRAL_GNOME_STATUS])
    from GameObjects.interactions_mixin.status_mixin import StatusMixin

    sm = StatusMixin(statuses=list(actor.statuses))
    sm.statuses = list(actor.statuses)

    result = sm.add_status(IN_DARK_STATUS)
    assert result is False
    assert not any(s == IN_DARK_STATUS for s in sm.statuses)


def test_info_prompt_notes_present():
    # tylko upewniamy się, że statusy informacyjne mają notki
    notes_fey = " ".join(FEY_TOUCHED_GNOME_STATUS.data.get("prompt_notes", []))
    notes_well = " ".join(WELLSPRING_GNOME_STATUS.data.get("prompt_notes", []))
    assert "primal" in notes_fey.lower()
    assert all(word in notes_well.lower() for word in ["arcane", "divine", "occult"])
