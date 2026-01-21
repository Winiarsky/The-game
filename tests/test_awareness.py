import sys
from pathlib import Path
import types

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from board_grid import BoardGrid  # noqa: E402
from awareness import iter_watchers_in_rooms, summarize_watchers  # noqa: E402
from interactable import Interactable  # noqa: E402
from interactions.common import WatchfulMixin  # noqa: E402


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
