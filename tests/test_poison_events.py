from types import SimpleNamespace

from board_grid import BoardGrid
from hero import Hero
from GameObjects.Enemies.basic_enemy import BasicEnemy
from GameObjects.events.base import EventContext
from GameObjects.events.poisons.arsenic_event import ArsenicEvent
from GameObjects.events.poisons.giant_centipede_venom_event import GiantCentipedeVenomEvent


class DummyConn:
    def __init__(self, choice):
        self.choice = choice

    def set_leds(self, *_args, **_kwargs):
        return None

    def scan_board(self, *_args, **_kwargs):
        return self.choice

    def leds_off(self):
        return None


def _make_game(actor_pos=(1, 1), target_pos=(1, 2)):
    board = BoardGrid(rows=3, cols=3)
    hero = Hero()
    enemy = BasicEnemy()
    board.place(hero, actor_pos)
    board.place(enemy, target_pos)
    conn = DummyConn(choice=target_pos)
    game = SimpleNamespace(
        board=board,
        heroes=[hero],
        enemies=[enemy],
        conn=conn,
        ui_log=lambda *_a, **_k: None,
    )
    return game, hero, enemy


def test_arsenic_event_applies_stage(monkeypatch):
    def _fake_resolve(*_args, **_kwargs):
        return SimpleNamespace(outcome="failure")

    monkeypatch.setattr(
        "GameObjects.events.poisons.base_poison_event.resolve_skill_check_with_sources",
        _fake_resolve,
    )

    game, hero, enemy = _make_game()
    ctx = EventContext(game=game, actor=hero)
    event = ArsenicEvent()

    result = event.execute(ctx)
    assert result.success is True
    status = enemy.get_status("poisoned")
    assert status is not None
    assert status.data.get("stage") == 1
    assert status.data.get("onset") == 100


def test_giant_centipede_venom_stage2(monkeypatch):
    def _fake_resolve(*_args, **_kwargs):
        return SimpleNamespace(outcome="critical_failure")

    monkeypatch.setattr(
        "GameObjects.events.poisons.base_poison_event.resolve_skill_check_with_sources",
        _fake_resolve,
    )

    game, hero, enemy = _make_game()
    ctx = EventContext(game=game, actor=hero)
    event = GiantCentipedeVenomEvent()

    result = event.execute(ctx)
    assert result.success is True
    status = enemy.get_status("poisoned")
    assert status is not None
    assert status.data.get("stage") == 2
