import pytest

from dnd_board_game.world import BoardDimensions, BoardState, Coordinate


def test_coordinate_as_tuple_and_iteration():
    coord = Coordinate(3, 7)

    assert coord.as_tuple() == (3, 7)
    assert tuple(coord) == (3, 7)


def test_default_board_dimensions_match_physical_board():
    dimensions = BoardDimensions()

    assert dimensions.cols == 20
    assert dimensions.rows == 30
    assert dimensions.in_bounds(Coordinate(0, 0))
    assert dimensions.in_bounds(Coordinate(19, 29))
    assert not dimensions.in_bounds(Coordinate(20, 29))
    assert not dimensions.in_bounds(Coordinate(19, 30))


def test_board_rejects_out_of_bounds_terrain_lookup():
    board = BoardState()

    with pytest.raises(ValueError):
        board.terrain_at(Coordinate(-1, 0))


def test_board_dimensions_must_be_positive():
    with pytest.raises(ValueError):
        BoardDimensions(cols=0, rows=30)
