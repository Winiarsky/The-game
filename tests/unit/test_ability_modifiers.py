import pytest

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.rules import ability_modifier, dexterity_modifier
from dnd_board_game.world import Coordinate


def test_ability_modifier_uses_dnd_formula():
    assert ability_modifier(10) == 0
    assert ability_modifier(11) == 0
    assert ability_modifier(12) == 1
    assert ability_modifier(8) == -1
    assert ability_modifier(1) == -5


def test_ability_modifier_rejects_non_positive_score():
    with pytest.raises(ValueError):
        ability_modifier(0)


def test_dexterity_modifier_reads_actor_ability_scores():
    actor = Actor(
        id=ActorId("rogue"),
        name="Łotrzyca",
        ac=14,
        hp=10,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(1, 1),
        faction=Faction.ALLY,
        ability_scores=AbilityScores(dexterity=18),
    )

    assert dexterity_modifier(actor) == 4
