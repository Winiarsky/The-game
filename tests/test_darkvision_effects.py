import sys
from pathlib import Path
import types
import importlib.util

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

# podmień stub z conftest na realny move_utils
MOVE_UTILS_PATH = SRC_ROOT / "actions" / "move_utils.py"
spec = importlib.util.spec_from_file_location("actions.move_utils", MOVE_UTILS_PATH)
move_utils = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(move_utils)  # type: ignore[arg-type]
sys.modules["actions.move_utils"] = move_utils

from board_grid import BoardGrid  # noqa: E402
from GameObjects.Terrains.darknes_terrain import DarknesTerrain  # noqa: E402
from GameObjects.interactions_mixin.status_mixin import StatusMixin  # noqa: E402
from GameObjects.interactions_mixin.skill_check_resolver import (  # noqa: E402
    resolve_skill_check_with_sources_from_roll,
)
from GameObjects.events.attack import attack_base  # noqa: E402
from skills import Skill  # noqa: E402
from statuses import (  # noqa: E402
    BLINDED_STATUS,
    CONCEALED_STATUS,
    DARKVISION_STATUS,
    IN_DARK_STATUS,
)


class DummyHero(StatusMixin):
    def __init__(self, position=None):
        self.position = position
        self.statuses = []

    def set_position(self, position):
        self.position = position


def test_darkvision_allows_in_dark_and_concealed_but_blocks_blinded():
    board = BoardGrid(rows=1, cols=2)
    board.set_field((1, 0), DarknesTerrain())

    hero = DummyHero((0, 0))
    hero.add_status(DARKVISION_STATUS)
    board.place(hero, (0, 0))

    ctx = types.SimpleNamespace(game=types.SimpleNamespace(board=board))
    path = [(0, 0), (1, 0)]
    completed, stop_pos, reason = move_utils.follow_path(
        ctx,
        hero,
        path,
        on_enter=move_utils.default_on_enter,
        allow_occupied=True,
    )
    assert completed and reason is None
    assert hero.has_status(IN_DARK_STATUS)
    assert not hero.has_status(BLINDED_STATUS)
    assert hero.has_status(CONCEALED_STATUS)


def test_no_darkvision_gets_all_darkness_statuses_on_entry():
    board = BoardGrid(rows=1, cols=2)
    board.set_field((1, 0), DarknesTerrain())

    hero = DummyHero((0, 0))
    board.place(hero, (0, 0))

    ctx = types.SimpleNamespace(game=types.SimpleNamespace(board=board))
    path = [(0, 0), (1, 0)]
    completed, stop_pos, reason = move_utils.follow_path(
        ctx,
        hero,
        path,
        on_enter=move_utils.default_on_enter,
        allow_occupied=True,
    )
    assert completed and reason is None
    assert hero.has_status(IN_DARK_STATUS)
    assert hero.has_status(CONCEALED_STATUS)
    assert hero.has_status(BLINDED_STATUS)


def test_darkvision_perception_bonus_vs_in_dark_target():
    actor = DummyHero()
    actor.add_status(DARKVISION_STATUS)
    target = DummyHero()
    target.add_status(IN_DARK_STATUS)

    res = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.PERCEPTION.value,
        dc=10,
        actor=actor,
        target=target,
        tags=[Skill.PERCEPTION.value, "seek"],
        roll=10,
        apply_modifiers=True,
    )
    assert res.modifier == 10
    assert res.total == 20
    assert any("Ignorujesz efekty naturalnej ciemnosci" in note for note in res.notes)


def test_no_darkvision_no_perception_bonus_vs_in_dark_target():
    actor = DummyHero()
    target = DummyHero()
    target.add_status(IN_DARK_STATUS)

    res = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.PERCEPTION.value,
        dc=10,
        actor=actor,
        target=target,
        tags=[Skill.PERCEPTION.value, "seek"],
        roll=10,
        apply_modifiers=True,
    )
    assert res.modifier == 0


def test_darkvision_ignores_concealed_target(monkeypatch):
    actor = DummyHero()
    actor.add_status(DARKVISION_STATUS)
    target = DummyHero()
    target.add_status(CONCEALED_STATUS)

    def _fail(*_args, **_kwargs):
        raise AssertionError("prompt_for_roll should not be called for darkvision")

    monkeypatch.setattr(attack_base, "prompt_for_roll", _fail)
    ctx = types.SimpleNamespace(actor=actor, game=types.SimpleNamespace(ui_log=lambda *_a, **_k: None, ui=None))
    assert attack_base.check_concealed(ctx, target) is True


def test_no_darkvision_requires_concealed_flat_check(monkeypatch):
    actor = DummyHero()
    target = DummyHero()
    target.add_status(CONCEALED_STATUS)

    monkeypatch.setattr(attack_base, "prompt_for_roll", lambda *_a, **_k: 4)
    ctx = types.SimpleNamespace(actor=actor, game=types.SimpleNamespace(ui_log=lambda *_a, **_k: None, ui=None))
    assert attack_base.check_concealed(ctx, target) is False
