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


def test_strong_blooded_no_longer_adds_flat_fort_bonus(monkeypatch):
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
    assert res_yes.modifier == 0
    assert res_yes.total == res_yes.roll


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


def test_strong_blooded_reduces_stage_by_two_on_success(monkeypatch):
    monkeypatch.setattr(
        "statuses.poisoned.resolve_skill_check_with_sources",
        lambda *_args, **_kwargs: SimpleNamespace(outcome="success"),
    )

    hero = Hero()
    hero.add_status(STRONG_BLOODED_DWARF_STATUS)
    stages = [{"damage": 0}, {"damage": 0}, {"damage": 0}, {"damage": 0}]
    hero.add_status(PoisonedStatus(duration=3, damage=0, dc=15, stages=stages, stage=3))

    process_poisoned(hero, game=SimpleNamespace(ui_log=lambda *_a, **_k: None, ui_event=lambda *_a, **_k: None))
    status = hero.get_status("poisoned")
    assert status is not None
    assert int(status.data.get("stage", 0) or 0) == 1


def test_strong_blooded_virulent_stage_reduction_is_lower(monkeypatch):
    monkeypatch.setattr(
        "statuses.poisoned.resolve_skill_check_with_sources",
        lambda *_args, **_kwargs: SimpleNamespace(outcome="critical_success"),
    )

    hero = Hero()
    hero.add_status(STRONG_BLOODED_DWARF_STATUS)
    stages = [{"damage": 0, "virulent": True}, {"damage": 0}, {"damage": 0}, {"damage": 0}]
    hero.add_status(PoisonedStatus(duration=3, damage=0, dc=15, stages=stages, stage=4, virulent=True))

    process_poisoned(hero, game=SimpleNamespace(ui_log=lambda *_a, **_k: None, ui_event=lambda *_a, **_k: None))
    status = hero.get_status("poisoned")
    assert status is not None
    # virulent: critical success redukuje stage o 2
    assert int(status.data.get("stage", 0) or 0) == 2
