from dataclasses import replace

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.combat import (
    SpellArea,
    SpellAreaShape,
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
from dnd_board_game.world import BoardDimensions, BoardState, Coordinate


def test_grid_distance_uses_5_10_diagonal_rule():
    assert grid_distance_feet(Coordinate(2, 2), Coordinate(3, 3)) == 5
    assert grid_distance_feet(Coordinate(2, 2), Coordinate(4, 4)) == 15
    assert grid_distance_feet(Coordinate(2, 2), Coordinate(5, 4)) == 20


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


def test_cone_area_expands_from_direction():
    board = BoardState(BoardDimensions(cols=8, rows=8))
    area = SpellArea(SpellAreaShape.CONE, length_feet=15)

    positions = area_positions_for_direction(board, Coordinate(2, 2), Coordinate(2, 3), area)

    assert Coordinate(2, 3) in positions
    assert Coordinate(1, 4) in positions
    assert Coordinate(3, 4) in positions


def test_direction_anchor_positions_are_adjacent_tiles():
    board = BoardState(BoardDimensions(cols=4, rows=4))

    anchors = direction_anchor_positions(board, Coordinate(0, 0))

    assert set(anchors) == {Coordinate(1, 0), Coordinate(0, 1), Coordinate(1, 1)}


def test_area_targets_only_living_enemies():
    hero = Actor(ActorId("hero"), "Hero", 15, 10, 0, 30, Coordinate(1, 1), Faction.ALLY)
    enemy = Actor(ActorId("enemy"), "Enemy", 12, 7, 0, 30, Coordinate(2, 1), Faction.ENEMY)
    defeated = replace(enemy, id=ActorId("defeated"), hp=0, position=Coordinate(3, 1))
    ally = replace(hero, id=ActorId("ally"), position=Coordinate(2, 2))

    targets = actors_in_area((hero, enemy, defeated, ally), (Coordinate(2, 1), Coordinate(3, 1), Coordinate(2, 2)), hero)

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
