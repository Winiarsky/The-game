from dataclasses import replace

import pytest

from dnd_board_game.actors import (
    AbilityScores,
    Actor,
    ActorId,
    ActorResourcePool,
    Faction,
    HitDicePool,
    PreparableSpell,
    RecoveryPeriod,
    SpellPreparationProfile,
)
from dnd_board_game.combat import SpellSlotState
from dnd_board_game.rules import complete_long_rest, complete_short_rest, spend_hit_die
from dnd_board_game.world import Coordinate


def _actor() -> Actor:
    return Actor(
        ActorId("hero"),
        "Bohater",
        14,
        7,
        3,
        30,
        Coordinate(0, 0),
        Faction.ALLY,
        max_hp=20,
        ability_scores=AbilityScores(constitution=14),
        spell_slots=(SpellSlotState(1, 0, 2),),
        spell_preparation=SpellPreparationProfile(
            source_label="lista próbna",
            preparation_limit=1,
            available_spells=(PreparableSpell("bless", "Błogosławieństwo", 1),),
            prepared_spell_ids=("bless",),
            confirmed=True,
        ),
        hit_dice=(HitDicePool(8, 1, 3),),
        resource_pools=(
            ActorResourcePool("focus", "Skupienie", 0, 2, RecoveryPeriod.SHORT_REST),
            ActorResourcePool("ward", "Osłona", 0, 1, RecoveryPeriod.LONG_REST),
            ActorResourcePool("charges", "Ładunki", 0, 3, RecoveryPeriod.NEVER),
        ),
    )


def test_short_rest_recovers_only_short_rest_resources() -> None:
    result = complete_short_rest(_actor())

    assert result.recovered_resource_ids == ("focus",)
    assert [pool.current for pool in result.actor_after.resource_pools] == [2, 0, 0]
    assert result.actor_after.hp == 7
    assert result.actor_after.spell_slots[0].remaining == 0


def test_hit_die_is_spent_after_short_rest_and_heals_with_constitution() -> None:
    result = spend_hit_die(_actor(), die_sides=8, natural_roll=6)

    assert result.constitution_modifier == 2
    assert result.healing_total == 8
    assert result.effective_healing == 8
    assert result.actor_after.hp == 15
    assert result.actor_after.hit_dice[0].remaining == 0


def test_hit_die_validates_roll_and_available_pool() -> None:
    with pytest.raises(ValueError, match="zakresie 1-8"):
        spend_hit_die(_actor(), die_sides=8, natural_roll=9)
    with pytest.raises(ValueError, match="nie ma dostępnej"):
        spend_hit_die(replace(_actor(), hit_dice=(HitDicePool(8, 0, 3),)), die_sides=8, natural_roll=4)


def test_long_rest_restores_hp_slots_resources_hit_dice_and_reopens_preparation() -> None:
    result = complete_long_rest(_actor())

    assert result.actor_after.hp == 20
    assert result.actor_after.temp_hp == 0
    assert result.actor_after.spell_slots[0].remaining == 2
    assert result.actor_after.hit_dice[0].remaining == 2
    assert [pool.current for pool in result.actor_after.resource_pools] == [2, 1, 0]
    assert result.actor_after.spell_preparation is not None
    assert result.actor_after.spell_preparation.confirmed is False
    assert result.hp_recovered == 13
    assert result.hit_dice_recovered == 1


def test_long_rest_requires_positive_hp() -> None:
    with pytest.raises(ValueError, match="co najmniej 1 HP"):
        complete_long_rest(replace(_actor(), hp=0))
