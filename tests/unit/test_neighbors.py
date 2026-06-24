import pytest

from dnd_board_game.world import BoardState, Coordinate, neighbors


def test_neighbors_include_orthogonal_and_diagonal_by_default():
    board = BoardState()

    assert neighbors(board, Coordinate(5, 5)) == [
        Coordinate(4, 4),
        Coordinate(4, 5),
        Coordinate(4, 6),
        Coordinate(5, 4),
        Coordinate(5, 6),
        Coordinate(6, 4),
        Coordinate(6, 5),
        Coordinate(6, 6),
    ]


def test_neighbors_can_be_orthogonal_only():
    board = BoardState()

    assert neighbors(board, Coordinate(5, 5), diagonal=False) == [
        Coordinate(4, 5),
        Coordinate(5, 4),
        Coordinate(5, 6),
        Coordinate(6, 5),
    ]


def test_neighbors_at_corner_stay_in_bounds():
    board = BoardState()

    assert neighbors(board, Coordinate(0, 0)) == [
        Coordinate(0, 1),
        Coordinate(1, 0),
        Coordinate(1, 1),
    ]


def test_neighbors_reject_out_of_bounds_origin():
    board = BoardState()

    with pytest.raises(ValueError):
        neighbors(board, Coordinate(-1, 0))
