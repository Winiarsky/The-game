import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from GameObjects.Interactables.locked_chest import LockedChest  # noqa: E402
from GameObjects.Interactables.guard_npc import GuardNPC  # noqa: E402
from actions.stealth import StealthAction  # noqa: E402
from board_grid import BoardGrid  # noqa: E402
from hero import Hero  # noqa: E402
from GameObjects.Interactables.utils.awareness import iter_watchers_in_rooms, summarize_watchers  # noqa: E402


class DummyConn:
    def __init__(self):
        self.led_calls = []

    def set_leds(self, positions, rgb_color):
        self.led_calls.append((tuple(positions), tuple(rgb_color)))

    def scan_board(self, _positions):
        return _positions[0]

    def leds_off(self):
        pass


class DummyGame:
    def __init__(self):
        self.board = BoardGrid(2, 2)
        self.conn = DummyConn()
        self.heroes = []


def test_hide_allows_stealth_despite_watchful():
    game = DummyGame()
    chest = LockedChest(
        loot=[],
        locked=False,
        allow_same_cell_interact=True,
        blocks_movement=True,
        thievery_dc=10,
        force_open_dc=10,
        push_dc=10,
        ac=10,
        hp=10,
        hardness=0,
        working_keys=[],
        inspection_msg=None,
        max_crit_failures=1,
        max_failures=1,
    )
    guard = GuardNPC(watch_disturbed=0)
    hero = Hero(position=(0, 0))
    game.board.add_interactable(chest, (0, 0))
    game.board.add_interactable(guard, (0, 1))
    game.board.place(hero, (0, 0))
    chest.is_open = True
    game.board.apply_rooms([{"id": "room", "positions": [(0, 0), (0, 1)]}])
    ctx = type("Ctx", (), {"game": game})

    # wskocz -> dostajesz hide
    msg = chest.action_jump_in(hero, game)
    assert "hide" in hero.statuses
    assert hero.hide_stealth_bonus == chest.hide_stealth_bonus
    assert "Wskakujesz" in msg

    # stealth powinien być dozwolony mimo strażnika
    sa = StealthAction()
    # podmieniamy prompt na stały wynik >= STEALTH_FAIL, by nie wejść w gałąź porażki
    import interactions_mixin.prompt_utils as prompt_utils

    prompt_utils.prompt_for_roll = lambda *_: 15
    # wymuszamy brak podświetleń (DummyConn) i sprawdzamy, że nie ma blockerów
    board = game.board
    rooms_here = board.rooms_at(hero.position)
    watchers = iter_watchers_in_rooms(board, rooms_here, ignore_obj=hero)
    # hide powinno wyłączyć strażników z rozważań
    has_hide = "hide" in hero.statuses
    assert has_hide
    penalty, blockers = (0, []) if has_hide else summarize_watchers(watchers)
    assert penalty == 0
    assert not blockers

    # wyjście z pola (remove) powinno zdjąć hide
    game.board.remove(hero.position)
    assert "hide" not in hero.statuses
