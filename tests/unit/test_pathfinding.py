from dnd_board_game.actors import Actor, ActorId, Faction
from dnd_board_game.world import (
    BLOCKING_TERRAIN,
    BoardState,
    Coordinate,
    DIFFICULT_TERRAIN,
    find_path,
    movement_range,
)


def _actor(actor_id: str, position: Coordinate, speed_feet: int = 30) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id,
        ac=12,
        hp=10,
        temp_hp=0,
        speed_feet=speed_feet,
        position=position,
        faction=Faction.ALLY,
    )


def test_speed_30_reaches_six_orthogonal_tiles_on_clear_board():
    board = BoardState()
    actor = _actor("hero", Coordinate(10, 10), speed_feet=30)
    result = movement_range(board, actor, [actor])

    assert Coordinate(10, 4) in result.reachable_tiles
    assert Coordinate(10, 16) in result.reachable_tiles
    assert Coordinate(4, 10) in result.reachable_tiles
    assert Coordinate(16, 10) in result.reachable_tiles
    assert Coordinate(10, 3) not in result.reachable_tiles


def test_path_uses_diagonal_steps_costing_five_feet():
    board = BoardState()
    actor = _actor("hero", Coordinate(0, 0), speed_feet=30)
    path = find_path(board, actor, [actor], Coordinate(3, 3))

    assert path.valid
    assert path.cost_feet == 15
    assert path.path == (Coordinate(0, 0), Coordinate(1, 1), Coordinate(2, 2), Coordinate(3, 3))


def test_path_omits_blocking_terrain():
    board = BoardState()
    board.set_terrain(Coordinate(1, 0), BLOCKING_TERRAIN)
    actor = _actor("hero", Coordinate(0, 0), speed_feet=30)
    path = find_path(board, actor, [actor], Coordinate(2, 0))

    assert path.valid
    assert Coordinate(1, 0) not in path.path


def test_difficult_terrain_consumes_extra_budget():
    board = BoardState()
    board.set_terrain(Coordinate(1, 0), DIFFICULT_TERRAIN)
    board.set_terrain(Coordinate(0, 1), BLOCKING_TERRAIN)
    board.set_terrain(Coordinate(1, 1), BLOCKING_TERRAIN)
    actor = _actor("hero", Coordinate(0, 0), speed_feet=10)
    result = movement_range(board, actor, [actor])

    assert Coordinate(1, 0) in result.reachable_tiles
    assert result.costs_by_tile[Coordinate(1, 0)] == 10
    assert Coordinate(2, 0) not in result.reachable_tiles


def test_movement_range_is_deterministic():
    board = BoardState()
    actor = _actor("hero", Coordinate(5, 5), speed_feet=20)

    first = movement_range(board, actor, [actor])
    second = movement_range(board, actor, [actor])

    assert first.reachable_tiles == second.reachable_tiles
    assert first.costs_by_tile == second.costs_by_tile
    assert first.paths_by_tile == second.paths_by_tile
