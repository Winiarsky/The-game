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
from GameObjects.events.magic.focus_spells.bard.loremaster_etude_event import LoremasterEtudeEvent
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources
from GameObjects.interactions_mixin.status_mixin import StatusMixin
from states.combat import Combat
from statuses.classes.bard.bard import BARD_STATUS


class DummyHero(StatusMixin):
    pass


def _hero(name: str):
    actor = DummyHero()
    actor.name = name
    actor.object_id = name
    actor.position = (0, 0)
    return actor


def _game(heroes):
    logs: list[str] = []
    ui_calls: list[tuple[str, str]] = []
    return SimpleNamespace(
        heroes=list(heroes),
        enemies=[],
        ui=SimpleNamespace(
            prompt_info=lambda title, **kwargs: ui_calls.append((title, str(kwargs.get("prompt_long", ""))))
        ),
        ui_log=lambda msg: logs.append(str(msg)),
        _logs=logs,
        _ui_calls=ui_calls,
    )


def test_loremaster_etude_requires_bard():
    caster = _hero("caster")
    game = _game([caster])
    game.state = Combat(game)

    result = LoremasterEtudeEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is False
    assert "tylko bard" in (result.message or "").lower()


def test_loremaster_etude_action_cost_and_ui_info():
    caster = _hero("bard")
    caster.add_status(BARD_STATUS)
    game = _game([caster])

    class Exploration:
        pass

    game.state = Exploration()
    res_exploration = LoremasterEtudeEvent().execute(EventContext(game=game, actor=caster))
    assert res_exploration.success is True
    assert res_exploration.consumed_action is False
    assert getattr(caster, "focus_point", None) == 0
    assert caster.has_status("loremaster_etude_ready")
    assert "recall knowledge" in (res_exploration.message or "").lower()
    assert game._ui_calls

    game.state = Combat(game)
    res_combat = LoremasterEtudeEvent().execute(EventContext(game=game, actor=caster))
    assert res_combat.success is False
    assert "focus point" in (res_combat.message or "").lower()


def test_loremaster_etude_spends_focus_point_in_combat():
    caster = _hero("bard")
    caster.add_status(BARD_STATUS)
    game = _game([caster])
    game.state = Combat(game)

    result = LoremasterEtudeEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert result.consumed_action is True
    assert result.actions_spent == 1
    assert getattr(caster, "focus_point", None) == 0
    assert caster.has_status("loremaster_etude_ready")


def test_loremaster_etude_rolls_twice_and_consumes_ready_status(monkeypatch):
    rolls = iter([5, 17])
    monkeypatch.setattr(
        "GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll",
        lambda *_a, **_k: next(rolls),
    )

    caster = _hero("bard")
    caster.add_status(BARD_STATUS)
    game = _game([caster])
    game.state = Combat(game)

    setup = LoremasterEtudeEvent().execute(EventContext(game=game, actor=caster))
    assert setup.success is True
    assert caster.has_status("loremaster_etude_ready")

    result = resolve_skill_check_with_sources(
        skill_id="arcana",
        dc=18,
        actor=caster,
        tags=["knowledge", "recall_knowledge"],
        game=game,
        apply_modifiers=True,
    )

    assert result.roll == 17
    assert result.total == 17
    assert result.outcome == "failure"
    assert any("loremaster's etude" in note.lower() or "loremaster" in note.lower() for note in result.notes)
    assert not caster.has_status("loremaster_etude_ready")
