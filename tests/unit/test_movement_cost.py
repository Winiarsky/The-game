from dataclasses import replace

from dnd_board_game.actors import (
    AbilityScores,
    Actor,
    ActorId,
    ActorSenseProfile,
    CreatureSize,
    DamageAffinityProfile,
    Faction,
    WildShapeState,
)
from dnd_board_game.world import (
    DIFFICULT_MOVE_COST_FEET,
    NORMAL_MOVE_COST_FEET,
    BoardState,
    Coordinate,
    DIFFICULT_TERRAIN,
    movement_cost,
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


def test_normal_terrain_costs_five_feet():
    board = BoardState()
    actor = _actor("hero", Coordinate(0, 0))

    assert movement_cost(board, actor, [actor], Coordinate(0, 1)) == NORMAL_MOVE_COST_FEET


def test_difficult_terrain_costs_ten_feet():
    board = BoardState()
    board.set_terrain(Coordinate(0, 1), DIFFICULT_TERRAIN)
    actor = _actor("hero", Coordinate(0, 0))

    assert movement_cost(board, actor, [actor], Coordinate(0, 1)) == DIFFICULT_MOVE_COST_FEET


def test_giant_eagle_wild_shape_ignores_difficult_terrain_cost():
    board = BoardState()
    board.set_terrain(Coordinate(0, 1), DIFFICULT_TERRAIN)
    actor = _actor("druid", Coordinate(0, 0))
    actor = replace(
        actor,
        wild_shape=WildShapeState(
            form_id="giant_eagle",
            form_name="Olbrzymi orzeł",
            original_ac=actor.ac,
            original_hp=actor.hp,
            original_max_hp=actor.max_hp,
            original_speed_feet=actor.speed_feet,
            original_ability_scores=AbilityScores(),
            original_size=CreatureSize.MEDIUM,
            original_senses=ActorSenseProfile(),
            original_damage_affinities=DamageAffinityProfile(),
            original_creature_type="humanoid",
            remaining_minutes=60,
        ),
    )

    assert movement_cost(board, actor, [actor], Coordinate(0, 1)) == NORMAL_MOVE_COST_FEET


def test_ally_occupied_tile_costs_like_difficult_terrain():
    board = BoardState()
    actor = _actor("hero", Coordinate(0, 0), Faction.ALLY)
    ally = _actor("ally", Coordinate(0, 1), Faction.ALLY)

    assert movement_cost(board, actor, [actor, ally], Coordinate(0, 1)) == DIFFICULT_MOVE_COST_FEET


def test_enemy_occupied_tile_is_not_enterable():
    board = BoardState()
    actor = _actor("hero", Coordinate(0, 0), Faction.ALLY)
    enemy = _actor("enemy", Coordinate(0, 1), Faction.ENEMY)

    assert movement_cost(board, actor, [actor, enemy], Coordinate(0, 1)) is None


def test_multiple_difficult_sources_do_not_stack():
    board = BoardState()
    board.set_terrain(Coordinate(0, 1), DIFFICULT_TERRAIN)
    actor = _actor("hero", Coordinate(0, 0), Faction.ALLY)
    ally = _actor("ally", Coordinate(0, 1), Faction.ALLY)

    assert movement_cost(board, actor, [actor, ally], Coordinate(0, 1)) == DIFFICULT_MOVE_COST_FEET
