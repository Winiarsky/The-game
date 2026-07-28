import pytest

from dataclasses import replace

from dnd_board_game.actors import (
    Actor,
    ActorId,
    CreatureSize,
    Faction,
    FeatureGrant,
    FeatureSourceKind,
)
from dnd_board_game.world import (
    BLOCKING_TERRAIN,
    BoardState,
    Coordinate,
    can_traverse,
    find_path,
    movement_range,
)


def _actor(actor_id: str, position: Coordinate, faction: Faction = Faction.ALLY) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id,
        ac=12,
        hp=10,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=faction,
    )


def test_wall_blocks_orthogonal_movement():
    board = BoardState()
    board.add_wall(Coordinate(0, 0), Coordinate(0, 1))
    actor = _actor("hero", Coordinate(0, 0))

    assert not can_traverse(board, actor, [actor], Coordinate(0, 0), Coordinate(0, 1))


def test_wall_must_connect_orthogonally_adjacent_tiles():
    board = BoardState()

    with pytest.raises(ValueError):
        board.add_wall(Coordinate(0, 0), Coordinate(1, 1))


def test_closed_door_blocks_and_open_door_allows_movement():
    board = BoardState()
    actor = _actor("hero", Coordinate(0, 0))
    board.set_door(Coordinate(0, 0), Coordinate(0, 1), is_open=False)

    assert not can_traverse(board, actor, [actor], Coordinate(0, 0), Coordinate(0, 1))

    board.set_door(Coordinate(0, 0), Coordinate(0, 1), is_open=True)

    assert can_traverse(board, actor, [actor], Coordinate(0, 0), Coordinate(0, 1))


def test_blocking_terrain_blocks_entry():
    board = BoardState()
    board.set_terrain(Coordinate(0, 1), BLOCKING_TERRAIN)
    actor = _actor("hero", Coordinate(0, 0))

    assert not can_traverse(board, actor, [actor], Coordinate(0, 0), Coordinate(0, 1))


def test_enemy_blocks_traversal_and_destination():
    board = BoardState()
    actor = _actor("hero", Coordinate(0, 0), Faction.ALLY)
    enemy = _actor("enemy", Coordinate(0, 1), Faction.ENEMY)

    assert not can_traverse(board, actor, [actor, enemy], Coordinate(0, 0), Coordinate(0, 1))
    assert Coordinate(0, 1) not in movement_range(board, actor, [actor, enemy]).reachable_tiles


def test_ally_can_be_crossed_but_not_used_as_destination():
    board = BoardState()
    actor = _actor("hero", Coordinate(0, 0), Faction.ALLY)
    ally = _actor("ally", Coordinate(0, 1), Faction.ALLY)

    result = movement_range(board, actor, [actor, ally])

    assert can_traverse(board, actor, [actor, ally], Coordinate(0, 0), Coordinate(0, 1))
    assert Coordinate(0, 1) not in result.reachable_tiles
    assert Coordinate(0, 2) in result.reachable_tiles


def test_diagonal_through_fully_blocked_corner_is_rejected():
    board = BoardState()
    board.set_terrain(Coordinate(1, 0), BLOCKING_TERRAIN)
    board.set_terrain(Coordinate(0, 1), BLOCKING_TERRAIN)
    actor = _actor("hero", Coordinate(0, 0))

    assert not can_traverse(board, actor, [actor], Coordinate(0, 0), Coordinate(1, 1))
    assert not find_path(board, actor, [actor], Coordinate(1, 1)).valid


def test_halfling_nimbleness_crosses_larger_enemy_but_cannot_end_there():
    board = BoardState()
    halfling = replace(
        _actor("halfling", Coordinate(0, 0)),
        size=CreatureSize.SMALL,
        features=(
            FeatureGrant(
                "halfling_nimbleness",
                "Halfling Nimbleness",
                FeatureSourceKind.SPECIES,
                "halfling",
            ),
        ),
    )
    enemy = _actor("enemy", Coordinate(0, 1), Faction.ENEMY)

    result = movement_range(board, halfling, (halfling, enemy))

    assert can_traverse(
        board,
        halfling,
        (halfling, enemy),
        Coordinate(0, 0),
        Coordinate(0, 1),
    )
    assert Coordinate(0, 1) not in result.reachable_tiles
    assert Coordinate(0, 2) in result.reachable_tiles


def test_small_actor_without_nimbleness_cannot_cross_medium_enemy():
    board = BoardState()
    small = replace(
        _actor("small", Coordinate(0, 0)),
        size=CreatureSize.SMALL,
    )
    enemy = _actor("enemy", Coordinate(0, 1), Faction.ENEMY)

    assert not can_traverse(
        board,
        small,
        (small, enemy),
        Coordinate(0, 0),
        Coordinate(0, 1),
    )
