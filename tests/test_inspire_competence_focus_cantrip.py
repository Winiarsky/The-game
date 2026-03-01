from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.events.base import EventContext
from GameObjects.events.magic.focus_spells.bard.inspire_competence_event import InspireCompetenceEvent
from GameObjects.interactions_mixin.status_mixin import StatusMixin
from GameObjects.interactions_mixin.bonus_mixin import BonusMixin
from statuses.classes.bard.bard import BARD_STATUS
from statuses.race.human.feats.cooperative_nature import COOPERATIVE_NATURE_STATUS
from states.combat import Combat


class DummyHero(StatusMixin, BonusMixin):
    def __init__(self, name: str, position: tuple[int, int]):
        super().__init__()
        self.name = name
        self.object_id = name
        self.position = position
        self.bonuses = []


def _game(heroes):
    logs: list[str] = []

    class DummyConn:
        def set_leds(self, *_a, **_k):
            return None

        def scan_board(self, _positions):
            return None

        def leds_off(self):
            return None

    return SimpleNamespace(
        heroes=list(heroes),
        enemies=[],
        conn=DummyConn(),
        ui=SimpleNamespace(prompt_info=lambda *_a, **_k: None),
        ui_log=lambda msg: logs.append(str(msg)),
        _logs=logs,
    )


def test_inspire_competence_uses_performance_not_selected_skill(monkeypatch):
    caster = DummyHero("bard", (0, 0))
    caster.add_status(BARD_STATUS)
    ally = DummyHero("ally", (1, 0))
    game = _game([caster, ally])
    game.state = Combat(game)

    captured = {}

    def _resolver(**kwargs):
        captured["skill_id"] = kwargs.get("skill_id")
        captured["tags"] = list(kwargs.get("tags", []))
        return SimpleNamespace(outcome="success")

    event = InspireCompetenceEvent()
    monkeypatch.setattr(event, "_pick_target", lambda *_a, **_k: (ally, ally.position))
    monkeypatch.setattr(event, "_pick_skill", lambda *_a, **_k: "athletics")
    monkeypatch.setattr(
        "GameObjects.events.magic.focus_spells.bard.inspire_competence_event.resolve_skill_check_with_sources",
        _resolver,
    )

    result = event.execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert captured["skill_id"] == "performance"
    assert "inspire_competence" in captured["tags"]
    status = ally.get_status("aided")
    assert status is not None
    assert status.data.get("skill_id") == "athletics"
    assert status.data.get("bonus") == 1


def test_inspire_competence_consumes_action_only_in_combat(monkeypatch):
    caster = DummyHero("bard", (0, 0))
    caster.add_status(BARD_STATUS)
    caster.focus_point = 1
    ally = DummyHero("ally", (1, 0))
    game = _game([caster, ally])

    event = InspireCompetenceEvent()
    monkeypatch.setattr(event, "_pick_target", lambda *_a, **_k: (ally, ally.position))
    monkeypatch.setattr(event, "_pick_skill", lambda *_a, **_k: "athletics")
    monkeypatch.setattr(
        "GameObjects.events.magic.focus_spells.bard.inspire_competence_event.resolve_skill_check_with_sources",
        lambda **_k: SimpleNamespace(outcome="success"),
    )

    class Exploration:
        pass

    game.state = Exploration()
    result_exploration = event.execute(EventContext(game=game, actor=caster))
    assert result_exploration.success is True
    assert result_exploration.consumed_action is False
    assert caster.focus_point == 1

    game.state = Combat(game)
    result_combat = event.execute(EventContext(game=game, actor=caster))
    assert result_combat.success is True
    assert result_combat.consumed_action is True
    assert result_combat.actions_spent == 1
    assert caster.focus_point == 1


def test_inspire_competence_respects_cooperative_nature(monkeypatch):
    caster = DummyHero("bard", (0, 0))
    caster.add_status(BARD_STATUS)
    caster.add_status(COOPERATIVE_NATURE_STATUS)
    ally = DummyHero("ally", (1, 0))
    game = _game([caster, ally])
    game.state = Combat(game)

    event = InspireCompetenceEvent()
    monkeypatch.setattr(event, "_pick_target", lambda *_a, **_k: (ally, ally.position))
    monkeypatch.setattr(event, "_pick_skill", lambda *_a, **_k: "arcana")
    monkeypatch.setattr(
        "GameObjects.events.magic.focus_spells.bard.inspire_competence_event.resolve_skill_check_with_sources",
        lambda **_k: SimpleNamespace(outcome="critical_success"),
    )

    result = event.execute(EventContext(game=game, actor=caster))

    assert result.success is True
    status = ally.get_status("aided")
    assert status is not None
    assert status.data.get("bonus") == 4
    assert status.data.get("skill_id") == "arcana"

