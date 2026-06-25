from dnd_board_game.actors import Actor, ActorId, Faction
from dnd_board_game.combat import AttackSource, AttackSourceType, legal_melee_targets
from dnd_board_game.rules import D20RollRequest
from dnd_board_game.world import BoardState, Coordinate


def _actor(actor_id: str, faction: Faction, position: Coordinate, hp: int = 10) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id,
        ac=12,
        hp=hp,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=faction,
    )


def test_adjacent_enemy_is_legal_melee_target():
    board = BoardState()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))

    targets = legal_melee_targets(board, hero, (hero, goblin))

    assert [target.id for target in targets] == ["goblin"]


def test_ally_defeated_and_out_of_range_targets_are_not_legal():
    board = BoardState()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    ally = _actor("ally", Faction.ALLY, Coordinate(1, 0))
    defeated = _actor("dead", Faction.ENEMY, Coordinate(0, 1), hp=0)
    far = _actor("far", Faction.ENEMY, Coordinate(3, 0))

    targets = legal_melee_targets(board, hero, (hero, ally, defeated, far))

    assert targets == ()


def test_wall_blocks_orthogonal_melee_target():
    board = BoardState()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    board.add_wall(hero.position, goblin.position)

    targets = legal_melee_targets(board, hero, (hero, goblin))

    assert targets == ()
