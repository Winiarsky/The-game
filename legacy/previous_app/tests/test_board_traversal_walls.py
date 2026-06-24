from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import actions.move_utils as move_utils
from board_grid import BoardGrid


def test_board_can_traverse_blocks_diagonal_through_walled_corner():
    board = BoardGrid(rows=5, cols=5)
    start = (1, 1)
    target = (2, 2)
    board.add_wall(start, (2, 1))
    board.add_wall(start, (1, 2))

    assert board.can_traverse(start, target, allow_occupied=False) is False


def test_find_path_does_not_use_diagonal_shortcut_through_walls():
    board = BoardGrid(rows=5, cols=5)
    start = (1, 1)
    target = (2, 2)
    board.add_wall(start, (2, 1))
    board.add_wall(start, (1, 2))

    path = move_utils.find_path(board, start, target, allow_diagonal=True, allow_occupied=False)

    assert path == []
