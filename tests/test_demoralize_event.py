from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.events.base import EventContext
from GameObjects.events.demoralize_utils import perform_demoralize
from states.combat import Combat


@dataclass
class DummyActor:
    object_id: str
    name: str
    position: tuple[int, int] | None
    will_bonus: int = 0
    intimidation_bonus: int = 0
    statuses: list = field(default_factory=list)
    bonuses: list = field(default_factory=list)
    hp: int = 20

    def has_status(self, status_id: str) -> bool:
        return any(getattr(item, "id", item) == status_id for item in self.statuses)

    def add_bonus(self, effect) -> None:
        self.bonuses.append(effect)

    def remove_bonuses_with_prefix(self, prefix: str) -> int:
        before = len(self.bonuses)
        self.bonuses = [item for item in self.bonuses if not str(getattr(item, "source", "") or "").startswith(prefix)]
        return before - len(self.bonuses)


class DummyConn:
    def set_leds(self, *_args, **_kwargs):
        return None

    def scan_board(self, _positions):
        return None

    def leds_off(self):
        return None


def _build_game():
    game = SimpleNamespace(
        heroes=[],
        enemies=[],
        conn=DummyConn(),
        ui_log=lambda *_a, **_k: None,
        ui_event=lambda *_a, **_k: None,
        ui_hero=lambda *_a, **_k: None,
        ui_active_actor=lambda *_a, **_k: None,
        board=SimpleNamespace(),
    )
    game.events = SimpleNamespace(safe_emit_action=lambda **_kwargs: None)
    game.state = Combat(game)
    return game


def test_demoralize_immunity_blocks_same_target_for_rest_of_combat(monkeypatch):
    game = _build_game()
    hero = DummyActor(object_id="hero-1", name="Hero", position=(0, 0), intimidation_bonus=6)
    enemy = DummyActor(object_id="enemy-1", name="Enemy", position=(1, 0), will_bonus=2)
    game.heroes = [hero]
    game.enemies = [enemy]

    calls = {"count": 0}

    def _fake_resolve(**_kwargs):
        calls["count"] += 1
        return SimpleNamespace(outcome="failure", roll=8, modifier=6, total=14)

    monkeypatch.setattr("GameObjects.events.demoralize_utils.resolve_skill_check_with_sources", _fake_resolve)

    ctx = EventContext(game=game, actor=hero)
    first = perform_demoralize(ctx, hero, forced_target=enemy, source_action="demoralize")
    second = perform_demoralize(ctx, hero, forced_target=enemy, source_action="demoralize")

    assert first.get("success") is True
    assert second.get("success") is False
    assert second.get("immunity_blocked") is True
    assert calls["count"] == 1

