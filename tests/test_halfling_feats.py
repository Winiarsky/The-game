from skills import Skill
from GameObjects.interactions_mixin import skill_check_resolver
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources_from_roll

from statuses.race.halfling.feats.halfling_luck import HalflingLuckStatus
from statuses.race.halfling.feats.sure_feet import SureFeetStatus
from statuses.race.halfling.feats.watchful_halfling import WatchfulHalflingStatus


class Dummy:
    def __init__(self):
        self.statuses = []

    def add_status(self, status):
        self.statuses.append(status)

    def has_status(self, status_id):
        return any(getattr(s, "id", s) == status_id for s in self.statuses)

    def remove_status(self, status_id):
        for idx, st in enumerate(list(self.statuses)):
            if getattr(st, "id", st) == status_id:
                del self.statuses[idx]
                return True
        return False


def test_watchful_halfling_sense_motive_bonus():
    actor = Dummy()
    actor.add_status(WatchfulHalflingStatus())
    res = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.PERCEPTION.value,
        dc=15,
        actor=actor,
        tags=["sense_motive", Skill.PERCEPTION.value],
        roll=13,
        apply_modifiers=True,
    )
    assert res.modifier == 2
    assert res.total == 15


def test_sure_feet_promotes_balance_success():
    actor = Dummy()
    actor.add_status(SureFeetStatus())
    res = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.ACROBATICS.value,
        dc=15,
        actor=actor,
        tags=["balance", Skill.ACROBATICS.value],
        roll=15,
        apply_modifiers=True,
    )
    assert res.outcome == "critical_success"


def test_halfling_luck_reroll_consumes_status(monkeypatch):
    actor = Dummy()
    actor.add_status(HalflingLuckStatus())

    class DummyUI:
        enabled = True

        def prompt_choice(self, *a, **k):
            return "tak"

    monkeypatch.setattr(skill_check_resolver, "get_ui_client", lambda: DummyUI())
    monkeypatch.setattr(skill_check_resolver, "prompt_for_roll", lambda *a, **k: 18)

    res = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.WILL.value,
        dc=15,
        actor=actor,
        tags=[Skill.WILL.value],
        roll=5,
        apply_modifiers=True,
    )
    assert res.outcome in ("success", "critical_success")
    assert actor.has_status("halfling_luck") is False


def test_halfling_luck_not_used_on_no(monkeypatch):
    actor = Dummy()
    actor.add_status(HalflingLuckStatus())

    class DummyUI:
        enabled = True

        def prompt_choice(self, *a, **k):
            return "nie"

    monkeypatch.setattr(skill_check_resolver, "get_ui_client", lambda: DummyUI())
    monkeypatch.setattr(skill_check_resolver, "prompt_for_roll", lambda *a, **k: 20)

    res = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.WILL.value,
        dc=15,
        actor=actor,
        tags=[Skill.WILL.value],
        roll=5,
        apply_modifiers=True,
    )
    assert res.outcome in ("failure", "critical_failure")
    assert actor.has_status("halfling_luck") is True
