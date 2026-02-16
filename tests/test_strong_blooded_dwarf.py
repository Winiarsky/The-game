from types import SimpleNamespace

from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources
from hero import Hero
from skills import Skill
from statuses.poisoned import PoisonedStatus, process_poisoned
from statuses.race.dwarf.heritages.strong_blooded import STRONG_BLOODED_DWARF_STATUS


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


def test_strong_blooded_poison_save_bonus(monkeypatch):
    _set_dummy_ui(monkeypatch)
    hero_no = Hero()
    hero_yes = Hero()
    hero_yes.add_status(STRONG_BLOODED_DWARF_STATUS)

    res_no = resolve_skill_check_with_sources(
        skill_id=Skill.FORTITUDE.value,
        dc=15,
        actor=hero_no,
        tags=["poison", Skill.FORTITUDE.value],
        apply_modifiers=True,
    )
    res_yes = resolve_skill_check_with_sources(
        skill_id=Skill.FORTITUDE.value,
        dc=15,
        actor=hero_yes,
        tags=["poison", Skill.FORTITUDE.value],
        apply_modifiers=True,
    )

    assert res_no.modifier == 0
    assert res_yes.modifier == 1
    assert res_yes.total == res_yes.roll + 1


def test_strong_blooded_poison_damage_reduction(monkeypatch):
    def _fake_resolve(*_args, **_kwargs):
        return SimpleNamespace(outcome="failure")

    monkeypatch.setattr("statuses.poisoned.resolve_skill_check_with_sources", _fake_resolve)

    hero_no = Hero()
    hero_yes = Hero()
    hero_yes.level = 3
    hero_yes.add_status(STRONG_BLOODED_DWARF_STATUS)

    hero_no.add_status(PoisonedStatus(duration=1, damage=5, dc=15))
    hero_yes.add_status(PoisonedStatus(duration=1, damage=5, dc=15))

    game_stub = SimpleNamespace(ui_log=lambda *_a, **_k: None, ui_event=lambda *_a, **_k: None)

    process_poisoned(hero_no, game_stub)
    process_poisoned(hero_yes, game_stub)

    assert hero_no.wounds == 5
    assert hero_yes.wounds == 3
