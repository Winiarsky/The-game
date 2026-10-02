"""Natural equal-cost routes without changing charge-profile movement rules."""
from dataclasses import replace

import pytest

from dnd_board_game.actors import Actor, ActorId, Faction
from dnd_board_game.scenarios.loader import build_encounter_from_scenario, load_scenario
from dnd_board_game.world import BoardDimensions, BoardState, Coordinate
from dnd_board_game.world.charge_movement import charge_paths
from dnd_board_game.world.movement import can_traverse
from dnd_board_game.world.terrain import BLOCKING_TERRAIN, DIFFICULT_TERRAIN


def walker(position: Coordinate) -> Actor:
    return Actor(ActorId("hero"), "Bohater", 12, 20, 0, 30, position, Faction.ALLY)


@pytest.mark.parametrize("offset", [(4, 0), (-4, 0), (0, 4), (0, -4),
                                   (4, 1), (-4, 1), (1, -4), (-1, -4)])
@pytest.mark.parametrize("parkour", [False, True])
def test_open_ground_has_only_necessary_diagonals(offset: tuple[int, int], parkour: bool) -> None:
    board = BoardState()
    actor = walker(Coordinate(9, 10))
    target = Coordinate(actor.position.col + offset[0], actor.position.row + offset[1])
    path = charge_paths(board, actor, (actor,), 4, parkour=parkour)[target]
    route = (actor.position, *path.cells)
    diagonal_count = sum(a.col != b.col and a.row != b.row for a, b in zip(route, route[1:]))
    assert path.cost == 4 and len(path.cells) == 4
    assert diagonal_count == min(abs(value) for value in offset)
    assert path.cells[-1] == target


@pytest.mark.parametrize("start,target,expected", [
    ((13, 22), (16, 21), ((14, 22), (15, 22), (16, 21))),
    ((12, 19), (8, 19), ((11, 20), (10, 20), (9, 20), (8, 19))),
])
def test_mission_log_routes_drop_gratuitous_zigzags(
    start: tuple[int, int], target: tuple[int, int], expected: tuple[tuple[int, int], ...],
) -> None:
    # Erynd seq219 and Nimra seq522 in the 2026-10-02 playtest. At these
    # moments no other figurine occupied the traversed part of the board.
    encounter = build_encounter_from_scenario(load_scenario(
        "content/scenarios/misja_0_dzwon/mechanics/battle.json"))
    actor = walker(Coordinate(*start))
    budget = len(expected)
    paths = charge_paths(encounter.board, actor, (actor,), budget)
    path = paths[Coordinate(*target)]
    assert tuple(p.as_tuple() for p in path.cells) == expected
    assert path.cost == budget and path.costs == (1,) * budget
    assert Coordinate(*target) not in charge_paths(encounter.board, actor, (actor,), budget - 1)
    route = (actor.position, *path.cells)
    assert all(can_traverse(encounter.board, actor, (actor,), a, b) for a, b in zip(route, route[1:]))
    if start == (12, 19):
        assert encounter.board.terrain_at(Coordinate(11, 19)).is_difficult
        assert Coordinate(11, 19) not in path.cells


def test_cost_still_takes_precedence_over_geometrically_shorter_route() -> None:
    board = BoardState(BoardDimensions(7, 5))
    actor = walker(Coordinate(1, 2))
    board.set_terrain(Coordinate(2, 2), DIFFICULT_TERRAIN)
    board.set_terrain(Coordinate(3, 2), DIFFICULT_TERRAIN)
    path = charge_paths(board, actor, (actor,), 6)[Coordinate(5, 2)]
    assert path.cost == 4  # The straight route costs six movement points.
    assert not any(board.terrain_at(p).is_difficult for p in path.cells)


def test_diagonal_corner_and_door_rules_remain_unchanged() -> None:
    board = BoardState(BoardDimensions(4, 4))
    actor = walker(Coordinate(1, 1))
    diagonal = Coordinate(2, 2)
    board.set_terrain(Coordinate(1, 2), BLOCKING_TERRAIN)
    board.set_door(actor.position, Coordinate(2, 1), is_open=False)
    assert diagonal not in charge_paths(board, actor, (actor,), 1)
    board.set_door(actor.position, Coordinate(2, 1), is_open=True)
    # Existing corner geometry needs one open side, not both.
    assert charge_paths(board, actor, (actor,), 1)[diagonal].cost == 1


def test_allied_transit_keeps_extra_cost_and_never_becomes_a_destination() -> None:
    board = BoardState(BoardDimensions(4, 1))
    actor = walker(Coordinate(0, 0))
    ally = replace(actor, id=ActorId("ally"), position=Coordinate(1, 0))
    actors = (actor, ally)
    paths = charge_paths(board, actor, actors, 3)
    assert set(paths) == {actor.position, Coordinate(2, 0)}
    assert paths[Coordinate(2, 0)].costs == (2, 1)
    assert Coordinate(2, 0) not in charge_paths(board, actor, actors, 2)
    assert set(charge_paths(board, actor, actors, 3, parkour=True)) == {actor.position}


def test_parkour_crosses_blocked_enemy_cell_but_cannot_land_there() -> None:
    board = BoardState(BoardDimensions(4, 1))
    actor = walker(Coordinate(0, 0))
    enemy = replace(actor, id=ActorId("enemy"), faction=Faction.ENEMY, position=Coordinate(1, 0))
    board.set_terrain(enemy.position, BLOCKING_TERRAIN)
    assert set(charge_paths(board, actor, (actor, enemy), 2)) == {actor.position}
    paths = charge_paths(board, actor, (actor, enemy), 2, parkour=True)
    assert set(paths) == {actor.position, Coordinate(2, 0)}
    assert paths[Coordinate(2, 0)].costs == (1, 1)


def test_physical_panel_remains_outside_movement_range() -> None:
    board = BoardState()
    actor = walker(Coordinate(18, 10))
    for parkour in (False, True):
        assert all(p.col < 19 for p in charge_paths(board, actor, (actor,), 4, parkour=parkour))
