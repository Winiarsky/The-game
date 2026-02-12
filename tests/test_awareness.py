import sys
from pathlib import Path
import types

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from board_grid import BoardGrid  # noqa: E402
from GameObjects.Interactables.utils.awareness import iter_watchers_in_rooms, summarize_watchers  # noqa: E402
from GameObjects.interactions_mixin.base_interaction import InteractableMixin as Interactable  # noqa: E402
from GameObjects.interactions_mixin import StatusMixin, WatchfulMixin  # noqa: E402
from actions.stealth import StealthAction  # noqa: E402
from hero import Hero  # noqa: E402
from GameObjects.Enemies.simple_enemy import Enemy  # noqa: E402
from statuses import StealthStatus  # noqa: E402


class DummyWatchful(WatchfulMixin, Interactable):
    def __init__(self, watch_disturbed=0, watch_disabled=False):
        Interactable.__init__(self, position=None)
        self.watch_disturbed = watch_disturbed
        self.watch_disabled = watch_disabled


def test_iter_watchers_collects_from_rooms():
    board = BoardGrid(3, 3)
    board.apply_rooms([{"id": "room1", "positions": [(0, 0), (1, 0)]}])

    watcher = DummyWatchful(watch_disturbed=0)
    board.add_interactable(watcher, (0, 0))

    watchers = iter_watchers_in_rooms(board, {"room1"})
    assert len(watchers) == 1
    assert watchers[0][0] is watcher
    assert watchers[0][1] == (0, 0)


def test_summarize_watchers_blocks_and_penalizes():
    board = BoardGrid(3, 3)
    board.apply_rooms([{"id": "room1", "positions": [(0, 0), (1, 0)]}])
    blocker = DummyWatchful(watch_disturbed=0)
    penalizer = DummyWatchful(watch_disturbed=5)
    board.add_interactable(blocker, (0, 0))
    board.add_interactable(penalizer, (1, 0))

    watchers = iter_watchers_in_rooms(board, {"room1"})
    penalty, blockers = summarize_watchers(watchers)
    assert penalty == 5
    assert (blocker, (0, 0)) in blockers
    assert all(w[0] is not penalizer for w in blockers)


def test_attempt_spot_applies_hero_perception_penalty(monkeypatch):
    class DummyHero(StatusMixin):
        def __init__(self):
            super().__init__()
            self.add_status(StealthStatus(detection_dc=12, stealth_bonus=2))

    hero = DummyHero()

    watcher = DummyWatchful(watch_disturbed=0)
    monkeypatch.setattr("GameObjects.interactions_mixin.watchful_mixin.random.randint", lambda *_args, **_kwargs: 10)

    spotted, msg = watcher.attempt_spot(hero, None)
    assert not spotted
    assert "r=10" in msg
    assert hero.has_status("stealth")
    assert hero.get_status_data("stealth", "stealth_detection_dc") == 12


def test_stealth_reactivation_triggers_watchers_once(monkeypatch):
    board = BoardGrid(2, 2)
    board.apply_rooms([{"id": "room", "positions": [(0, 0), (0, 1)]}])

    class CountingWatchful(DummyWatchful):
        def __init__(self):
            super().__init__(watch_disturbed=0)
            self.spot_calls = 0

        def attempt_spot(self, hero, game):
            self.spot_calls += 1
            return False, "czujny strażnik"

    guard = CountingWatchful()
    hero = Hero(position=(0, 0))
    hero.add_status(StealthStatus(detection_dc=30))

    board.place(hero, (0, 0))
    board.add_interactable(guard, (0, 1))

    conn = types.SimpleNamespace(
        set_leds=lambda *_args, **_kwargs: None,
        scan_board=lambda positions: positions[0],
        leds_off=lambda: None,
    )
    game = types.SimpleNamespace(board=board, conn=conn, heroes=[hero])

    monkeypatch.setattr("actions.stealth.perform_movement", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("GameObjects.interactions_mixin.watchful_mixin.random.randint", lambda *_args, **_kwargs: 5)

    sa = StealthAction()
    sa.execute(types.SimpleNamespace(game=game))

    assert guard.spot_calls == 1


def test_enemy_watchful_spots_hero_and_triggers_combat(monkeypatch):
    board = BoardGrid(1, 1)
    board.apply_rooms([{"id": "room", "positions": [(0, 0)]}])

    enemy = Enemy(position=(0, 0), watch_disturbed=0, watch_disabled=False, perception_bonus=10)
    board.place(enemy, (0, 0))

    hero = Hero(position=(0, 0))
    hero.add_status(StealthStatus(detection_dc=5))

    class DummyGame:
        def __init__(self):
            self.board = board
            self.start_combat_calls = 0

        def start_combat(self, trigger=None):
            self.start_combat_calls += 1

    game = DummyGame()
    monkeypatch.setattr("GameObjects.interactions_mixin.watchful_mixin.random.randint", lambda *_args, **_kwargs: 20)

    spotted, msg = enemy.attempt_spot(hero, game)

    assert spotted
    assert "zauważa" in msg
    assert game.start_combat_calls == 1
    assert hero.has_status("observable")
    assert not hero.has_status("stealth")
