from dataclasses import replace

import pytest

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.combat import (
    SpellArea,
    SpellAreaShape,
    SpellAreaTargetMode,
    SpellSlotState,
    apply_save_damage_amount,
    actors_in_area,
    area_positions_for_center,
    area_positions_for_direction,
    consume_spell_resource,
    direction_anchor_positions,
    grid_distance_feet,
    resolve_spell_save,
)
from dnd_board_game.world import BLOCKING_TERRAIN, BoardDimensions, BoardState, Coordinate


def test_grid_distance_uses_5_10_diagonal_rule():
    assert grid_distance_feet(Coordinate(2, 2), Coordinate(3, 3)) == 5
    assert grid_distance_feet(Coordinate(2, 2), Coordinate(4, 4)) == 15
    assert grid_distance_feet(Coordinate(2, 2), Coordinate(5, 4)) == 20


def test_spell_area_dimensions_must_use_positive_five_foot_increments() -> None:
    with pytest.raises(ValueError, match="radius_feet"):
        SpellArea(SpellAreaShape.RADIUS)
    with pytest.raises(ValueError, match="width_feet"):
        SpellArea(SpellAreaShape.LINE, length_feet=15, width_feet=7)


def test_radius_area_returns_tiles_inside_radius():
    board = BoardState(BoardDimensions(cols=7, rows=7))
    area = SpellArea(SpellAreaShape.RADIUS, radius_feet=10)

    positions = area_positions_for_center(board, Coordinate(3, 3), area)

    assert Coordinate(3, 3) in positions
    assert Coordinate(4, 4) in positions
    assert Coordinate(5, 5) not in positions


def test_line_area_uses_adjacent_click_as_direction():
    board = BoardState(BoardDimensions(cols=8, rows=5))
    area = SpellArea(SpellAreaShape.LINE, length_feet=15)

    positions = area_positions_for_direction(board, Coordinate(2, 2), Coordinate(3, 2), area)

    assert positions == (Coordinate(3, 2), Coordinate(4, 2), Coordinate(5, 2))


def test_line_area_uses_declared_width() -> None:
    board = BoardState(BoardDimensions(cols=8, rows=6))
    area = SpellArea(SpellAreaShape.LINE, length_feet=15, width_feet=10)

    positions = area_positions_for_direction(
        board,
        Coordinate(2, 2),
        Coordinate(3, 2),
        area,
    )

    assert set(positions) == {
        Coordinate(col, row)
        for col in (3, 4, 5)
        for row in (1, 2)
    }


def test_cube_area_extends_from_caster_in_selected_direction() -> None:
    board = BoardState(BoardDimensions(cols=8, rows=8))
    area = SpellArea(SpellAreaShape.CUBE, length_feet=15)

    positions = area_positions_for_direction(
        board,
        Coordinate(2, 2),
        Coordinate(3, 2),
        area,
    )

    assert set(positions) == {
        Coordinate(col, row)
        for col in (3, 4, 5)
        for row in (1, 2, 3)
    }
    assert Coordinate(2, 2) not in positions


def test_cube_area_can_use_a_remote_board_selected_center() -> None:
    board = BoardState(BoardDimensions(cols=10, rows=10))
    area = SpellArea(SpellAreaShape.CUBE, length_feet=20, width_feet=20)

    positions = area_positions_for_center(board, Coordinate(4, 4), area)

    assert len(positions) == 16
    assert set(positions) == {
        Coordinate(col, row)
        for col in (3, 4, 5, 6)
        for row in (3, 4, 5, 6)
    }


def test_cone_area_expands_from_direction():
    board = BoardState(BoardDimensions(cols=8, rows=8))
    area = SpellArea(SpellAreaShape.CONE, length_feet=15)

    positions = area_positions_for_direction(board, Coordinate(2, 2), Coordinate(2, 3), area)

    assert Coordinate(2, 3) in positions
    assert Coordinate(3, 4) in positions
    assert Coordinate(1, 5) in positions
    assert Coordinate(3, 5) in positions


def test_directional_area_does_not_continue_through_blocking_terrain() -> None:
    board = BoardState(BoardDimensions(cols=8, rows=5))
    board.set_terrain(Coordinate(4, 2), BLOCKING_TERRAIN)
    area = SpellArea(SpellAreaShape.LINE, length_feet=25)

    positions = area_positions_for_direction(
        board,
        Coordinate(2, 2),
        Coordinate(3, 2),
        area,
    )

    assert Coordinate(3, 2) in positions
    assert Coordinate(5, 2) not in positions
    assert Coordinate(6, 2) not in positions


def test_radius_area_does_not_reach_behind_blocking_terrain() -> None:
    board = BoardState(BoardDimensions(cols=8, rows=5))
    board.set_terrain(Coordinate(4, 2), BLOCKING_TERRAIN)
    area = SpellArea(SpellAreaShape.RADIUS, radius_feet=15)

    positions = area_positions_for_center(board, Coordinate(2, 2), area)

    assert Coordinate(3, 2) in positions
    assert Coordinate(5, 2) not in positions


def test_direction_anchor_positions_are_adjacent_tiles():
    board = BoardState(BoardDimensions(cols=4, rows=4))

    anchors = direction_anchor_positions(board, Coordinate(0, 0))

    assert set(anchors) == {Coordinate(1, 0), Coordinate(0, 1), Coordinate(1, 1)}


def test_area_targets_all_living_creatures_by_default_for_friendly_fire():
    hero = Actor(ActorId("hero"), "Hero", 15, 10, 0, 30, Coordinate(1, 1), Faction.ALLY)
    enemy = Actor(ActorId("enemy"), "Enemy", 12, 7, 0, 30, Coordinate(2, 1), Faction.ENEMY)
    defeated = replace(enemy, id=ActorId("defeated"), hp=0, position=Coordinate(3, 1))
    ally = replace(hero, id=ActorId("ally"), position=Coordinate(2, 2))

    targets = actors_in_area((hero, enemy, defeated, ally), (Coordinate(2, 1), Coordinate(3, 1), Coordinate(2, 2)), hero)

    assert targets == (enemy, ally)


def test_area_target_mode_can_limit_effect_to_enemies() -> None:
    hero = Actor(ActorId("hero"), "Hero", 15, 10, 0, 30, Coordinate(1, 1), Faction.ALLY)
    enemy = Actor(ActorId("enemy"), "Enemy", 12, 7, 0, 30, Coordinate(2, 1), Faction.ENEMY)
    ally = replace(hero, id=ActorId("ally"), position=Coordinate(2, 2))

    targets = actors_in_area(
        (hero, enemy, ally),
        (Coordinate(2, 1), Coordinate(2, 2)),
        hero,
        SpellAreaTargetMode.ENEMIES,
    )

    assert targets == (enemy,)


def test_spell_slot_consumption_reduces_remaining_slots():
    actor = Actor(
        ActorId("cleric"),
        "Cleric",
        15,
        10,
        0,
        30,
        Coordinate(1, 1),
        Faction.ALLY,
        spell_slots=(SpellSlotState(level=1, remaining=2, maximum=2),),
    )

    result = consume_spell_resource(actor, 1)

    assert result.consumed is True
    assert result.actor_after.spell_slots[0].remaining == 1


def test_spell_save_result_tracks_roll_and_damage_multiplier():
    enemy = Actor(
        ActorId("goblin"),
        "Goblin",
        15,
        10,
        0,
        30,
        Coordinate(1, 1),
        Faction.ENEMY,
        ability_scores=AbilityScores(dexterity=14),
    )

    failed = resolve_spell_save(enemy, ability="dexterity", dc=13, natural_roll=8, damage_on_success="half")
    succeeded = resolve_spell_save(enemy, ability="dexterity", dc=13, natural_roll=15, damage_on_success="half")

    assert failed.total == 10
    assert failed.success is False
    assert apply_save_damage_amount(9, failed) == 9
    assert succeeded.total == 17
    assert succeeded.success is True
    assert apply_save_damage_amount(9, succeeded) == 4
