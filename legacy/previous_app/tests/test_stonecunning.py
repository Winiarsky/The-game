import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources
from hero import Hero
from skills import Skill
from statuses.race.dwarf.feats.stonecunning import STONECUNNING_STATUS


class DummyUI:
    def __init__(self):
        self.last_prompt_long = None
        self.last_prompt = None

    def prompt_roll(self, prompt, *args, **kwargs):
        self.last_prompt = prompt
        self.last_prompt_long = kwargs.get("prompt_long")
        return 10


def _set_dummy_ui(monkeypatch):
    dummy = DummyUI()

    def _get_ui_client():
        return dummy

    monkeypatch.setattr(
        "GameObjects.interactions_mixin.skill_check_resolver.get_ui_client",
        _get_ui_client,
    )
    return dummy


def test_stonecunning_bonus_applies_with_stone_tag(monkeypatch):
    _set_dummy_ui(monkeypatch)
    actor = Hero()
    actor.add_status(STONECUNNING_STATUS)

    result = resolve_skill_check_with_sources(
        skill_id=Skill.PERCEPTION.value,
        dc=15,
        actor=actor,
        target=None,
        tags=[Skill.PERCEPTION.value, "stone"],
        apply_modifiers=True,
    )

    assert result.modifier == 2
    assert result.total == result.roll + 2


def test_stonecunning_no_bonus_without_tag(monkeypatch):
    _set_dummy_ui(monkeypatch)
    actor = Hero()
    actor.add_status(STONECUNNING_STATUS)

    result = resolve_skill_check_with_sources(
        skill_id=Skill.PERCEPTION.value,
        dc=15,
        actor=actor,
        target=None,
        tags=[Skill.PERCEPTION.value, "seek"],
        apply_modifiers=True,
    )

    assert result.modifier == 0
    assert result.total == result.roll
