from types import SimpleNamespace

from hero import Hero
from statuses.poisoned import PoisonedStatus, process_poisoned


def test_poisoned_triggers_check_each_turn(monkeypatch):
    calls = {"count": 0}

    def _fake_resolve(*_args, **_kwargs):
        calls["count"] += 1
        return SimpleNamespace(outcome="success")

    monkeypatch.setattr("statuses.poisoned.resolve_skill_check_with_sources", _fake_resolve)

    hero = Hero()
    hero.add_status(PoisonedStatus(duration=3, damage=2, dc=15))

    for _ in range(3):
        process_poisoned(hero, game=SimpleNamespace(ui_log=lambda *_a, **_k: None, ui_event=lambda *_a, **_k: None))
        hero.tick_statuses_turn()

    assert calls["count"] == 3


def test_poisoned_damage_by_outcome(monkeypatch):
    outcomes = {
        "critical_success": 0,
        "success": 2,
        "failure": 5,
        "critical_failure": 10,
    }

    for outcome, expected in outcomes.items():
        def _fake_resolve(*_args, **_kwargs):
            return SimpleNamespace(outcome=outcome)

        monkeypatch.setattr("statuses.poisoned.resolve_skill_check_with_sources", _fake_resolve)

        hero = Hero()
        hero.add_status(PoisonedStatus(duration=1, damage=5, dc=15))
        process_poisoned(hero, game=SimpleNamespace(ui_log=lambda *_a, **_k: None, ui_event=lambda *_a, **_k: None))

        assert hero.wounds == expected


def test_poisoned_removed_after_duration(monkeypatch):
    def _fake_resolve(*_args, **_kwargs):
        return SimpleNamespace(outcome="failure")

    monkeypatch.setattr("statuses.poisoned.resolve_skill_check_with_sources", _fake_resolve)

    hero = Hero()
    hero.add_status(PoisonedStatus(duration=2, damage=1, dc=15))

    process_poisoned(hero, game=SimpleNamespace(ui_log=lambda *_a, **_k: None, ui_event=lambda *_a, **_k: None))
    hero.tick_statuses_turn()
    assert hero.get_status("poisoned") is not None

    process_poisoned(hero, game=SimpleNamespace(ui_log=lambda *_a, **_k: None, ui_event=lambda *_a, **_k: None))
    hero.tick_statuses_turn()
    assert hero.get_status("poisoned") is None
