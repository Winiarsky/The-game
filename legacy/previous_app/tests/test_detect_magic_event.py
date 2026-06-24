from __future__ import annotations

from board_grid import BoardGrid
from hero import Hero
from GameObjects.Enemies.basic_enemy import BasicEnemy
from GameObjects.Interactables.hidden_cache import HiddenCache
from GameObjects.events.base import EventContext
from GameObjects.events.magic.cantrips.events import DetectMagicEvent


class DummyConn:
    def __init__(self):
        self.led_calls: list[list[tuple[int, int]]] = []
        self.scan_calls: int = 0
        self.leds_off_calls: int = 0

    def set_leds(self, positions, _colors):
        self.led_calls.append(list(positions or []))

    def scan_board(self, _positions):
        self.scan_calls += 1
        return None

    def leds_off(self):
        self.leds_off_calls += 1


class DummyUI:
    def __init__(self):
        self.last_prompt_long = None

    def prompt_info(self, _title, *, prompt_long=None, **_kwargs):
        self.last_prompt_long = prompt_long
        return "ok"


class DummyGame:
    def __init__(self, board: BoardGrid):
        self.board = board
        self.conn = DummyConn()
        self.ui = DummyUI()
        self.heroes: list[Hero] = []
        self.enemies: list[BasicEnemy] = []

    def ui_log(self, _msg: str) -> None:
        return None


def _make_board_with_room(room_id: str, positions: list[tuple[int, int]]) -> BoardGrid:
    board = BoardGrid(rows=5, cols=5)
    board.apply_rooms([{"id": room_id, "positions": positions}])
    return board


def _run_detect_magic(game: DummyGame, hero: Hero):
    event = DetectMagicEvent()
    ctx = EventContext(game=game, actor=hero)
    return event.run(ctx)


def test_detect_magic_no_magic_in_room():
    board = _make_board_with_room("room1", [(0, 0), (1, 0)])
    game = DummyGame(board)
    hero = Hero()
    board.place(hero, (0, 0))
    game.heroes.append(hero)

    _run_detect_magic(game, hero)

    assert game.ui.last_prompt_long is not None
    assert "Nie wyczuwasz magii" in game.ui.last_prompt_long
    assert game.conn.led_calls == []


def test_detect_magic_magic_out_of_range():
    board = _make_board_with_room("room1", [(0, 0), (2, 0)])
    game = DummyGame(board)
    hero = Hero()
    hero.level = 1  # zasięg 5 stóp
    board.place(hero, (0, 0))
    game.heroes.append(hero)

    cache = HiddenCache(hidden=False)
    board.add_interactable(cache, (2, 0))  # 10 stóp

    _run_detect_magic(game, hero)

    assert game.ui.last_prompt_long is not None
    assert "Poza zasięgiem wyczuwasz jeszcze 1" in game.ui.last_prompt_long
    assert game.conn.led_calls == []
    assert cache.revealed is True  # hidden=False oznacza odkryty


def test_detect_magic_magic_in_range_highlights_and_lists():
    board = _make_board_with_room("room1", [(0, 0), (1, 0)])
    game = DummyGame(board)
    hero = Hero()
    hero.level = 1
    board.place(hero, (0, 0))
    game.heroes.append(hero)

    cache = HiddenCache(hidden=False, magical_description="Magiczny schowek")
    board.add_interactable(cache, (1, 0))  # 5 stóp

    _run_detect_magic(game, hero)

    assert game.ui.last_prompt_long is not None
    assert "Magiczny schowek" in game.ui.last_prompt_long
    assert game.conn.led_calls
    assert set(game.conn.led_calls[-1]) == {(1, 0)}


def test_detect_magic_range_scales_with_level():
    board = _make_board_with_room("room1", [(0, 0), (2, 0)])
    game = DummyGame(board)
    hero = Hero()
    hero.level = 4  # zasięg 10 stóp
    board.place(hero, (0, 0))
    game.heroes.append(hero)

    cache = HiddenCache(hidden=False)
    board.add_interactable(cache, (2, 0))  # 10 stóp

    _run_detect_magic(game, hero)

    assert game.conn.led_calls
    assert set(game.conn.led_calls[-1]) == {(2, 0)}


def test_detect_magic_hidden_in_range_revealed_and_info():
    board = _make_board_with_room("room1", [(0, 0), (1, 0)])
    game = DummyGame(board)
    hero = Hero()
    hero.level = 1
    board.place(hero, (0, 0))
    game.heroes.append(hero)

    cache = HiddenCache(hidden=True)
    board.add_interactable(cache, (1, 0))

    _run_detect_magic(game, hero)

    assert cache.revealed is True
    assert "Odkryto ukryte magiczne obiekty" in game.ui.last_prompt_long


def test_detect_magic_hidden_out_of_range_stays_hidden():
    board = _make_board_with_room("room1", [(0, 0), (2, 0)])
    game = DummyGame(board)
    hero = Hero()
    hero.level = 1
    board.place(hero, (0, 0))
    game.heroes.append(hero)

    cache = HiddenCache(hidden=True)
    board.add_interactable(cache, (2, 0))  # 10 stóp

    _run_detect_magic(game, hero)

    assert cache.revealed is False
    assert "Poza zasięgiem wyczuwasz jeszcze 1" in game.ui.last_prompt_long


def test_detect_magic_only_magical_highlighted():
    board = _make_board_with_room("room1", [(0, 0), (1, 0), (1, 1)])
    game = DummyGame(board)
    hero = Hero()
    hero.level = 1
    board.place(hero, (0, 0))
    game.heroes.append(hero)

    magical = HiddenCache(hidden=False, magical=True)
    non_magical = HiddenCache(hidden=False, magical=False)
    board.add_interactable(magical, (1, 0))
    board.add_interactable(non_magical, (1, 1))

    _run_detect_magic(game, hero)

    assert game.conn.led_calls
    assert set(game.conn.led_calls[-1]) == {(1, 0)}


def test_detect_magic_multiple_rooms_on_hero_cell():
    board = BoardGrid(rows=5, cols=5)
    board.apply_rooms(
        [
            {"id": "room1", "positions": [(0, 0), (1, 0)]},
            {"id": "room2", "positions": [(0, 0), (0, 1)]},
        ]
    )
    game = DummyGame(board)
    hero = Hero()
    hero.level = 1
    board.place(hero, (0, 0))
    game.heroes.append(hero)

    cache1 = HiddenCache(hidden=False, magical_description="A")
    cache2 = HiddenCache(hidden=False, magical_description="B")
    board.add_interactable(cache1, (1, 0))
    board.add_interactable(cache2, (0, 1))

    _run_detect_magic(game, hero)

    text = game.ui.last_prompt_long or ""
    assert "A" in text
    assert "B" in text


def test_detect_magic_fallback_description_uses_name():
    board = _make_board_with_room("room1", [(0, 0), (1, 0)])
    game = DummyGame(board)
    hero = Hero()
    hero.level = 1
    board.place(hero, (0, 0))
    game.heroes.append(hero)

    enemy = BasicEnemy(name="Mage", magical=True, magical_description="")
    board.place(enemy, (1, 0))
    game.enemies.append(enemy)

    _run_detect_magic(game, hero)

    assert "Magiczny obiekt: Mage" in (game.ui.last_prompt_long or "")


def test_detect_magic_leds_off_after_ack():
    board = _make_board_with_room("room1", [(0, 0), (1, 0)])
    game = DummyGame(board)
    hero = Hero()
    hero.level = 1
    board.place(hero, (0, 0))
    game.heroes.append(hero)

    cache = HiddenCache(hidden=False)
    board.add_interactable(cache, (1, 0))

    _run_detect_magic(game, hero)

    assert game.conn.scan_calls >= 1
    assert game.conn.leds_off_calls >= 1
