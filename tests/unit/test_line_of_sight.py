from dnd_board_game.world import BLOCKING_TERRAIN, BoardState, Coordinate, bresenham_line, line_of_sight_clear


def test_bresenham_line_tracks_grid_cells():
    assert bresenham_line(Coordinate(0, 0), Coordinate(3, 1)) == (
        Coordinate(0, 0),
        Coordinate(1, 0),
        Coordinate(2, 1),
        Coordinate(3, 1),
    )


def test_line_of_sight_clear_without_obstacles():
    assert line_of_sight_clear(BoardState(), Coordinate(0, 0), Coordinate(4, 0))


def test_line_of_sight_blocked_by_blocking_terrain_between_source_and_target():
    board = BoardState()
    board.set_terrain(Coordinate(2, 0), BLOCKING_TERRAIN)

    assert not line_of_sight_clear(board, Coordinate(0, 0), Coordinate(4, 0))


def test_line_of_sight_blocked_by_closed_edge():
    board = BoardState()
    board.add_wall(Coordinate(1, 0), Coordinate(2, 0))

    assert not line_of_sight_clear(board, Coordinate(0, 0), Coordinate(4, 0))
