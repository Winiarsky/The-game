from dataclasses import replace

import pytest

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.rules import (
    EXPERIENCE_THRESHOLDS,
    award_experience,
    award_party_experience,
    award_party_experience_per_actor,
    experience_progress,
    level_for_experience,
)
from dnd_board_game.world import Coordinate


def _actor(*, level: int = 1, experience_points: int = 0) -> Actor:
    return Actor(
        id=ActorId("hero"),
        name="Bohater",
        ac=14,
        hp=10,
        max_hp=10,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(0, 0),
        faction=Faction.ALLY,
        ability_scores=AbilityScores(),
        level=level,
        experience_points=experience_points,
    )


def test_srd_experience_thresholds_cover_levels_one_to_twenty() -> None:
    assert len(EXPERIENCE_THRESHOLDS) == 20
    assert EXPERIENCE_THRESHOLDS[:3] == (0, 300, 900)
    assert EXPERIENCE_THRESHOLDS[-1] == 355_000
    assert level_for_experience(299, level_cap=3) == 1
    assert level_for_experience(300, level_cap=3) == 2
    assert level_for_experience(10_000, level_cap=3) == 3


def test_award_experience_marks_level_up_without_mutating_level() -> None:
    result = award_experience(_actor(experience_points=250), 75)

    assert result.actor.experience_points == 325
    assert result.actor.level == 1
    assert result.before.level_up_available is False
    assert result.after.level_up_available is True
    assert result.after.eligible_level == 2
    assert result.after.experience_to_next_level == 0


def test_level_three_cap_has_no_next_threshold() -> None:
    progress = experience_progress(
        _actor(level=3, experience_points=1_200),
        level_cap=3,
    )

    assert progress.eligible_level == 3
    assert progress.next_level_experience is None
    assert progress.experience_to_next_level is None


def test_experience_rejects_negative_values() -> None:
    with pytest.raises(ValueError, match="ujemnych"):
        award_experience(_actor(), -1)
    with pytest.raises(ValueError, match="cannot be negative"):
        replace(_actor(), experience_points=-1)


def test_party_experience_is_split_between_living_player_characters() -> None:
    actors = (
        replace(_actor(), uses_death_saves=True),
        replace(
            _actor(),
            id=ActorId("rogue"),
            uses_death_saves=True,
            experience_points=10,
        ),
        replace(
            _actor(),
            id=ActorId("summon"),
            uses_death_saves=False,
        ),
    )

    result = award_party_experience(actors, 101)

    assert result.experience_per_actor == 50
    assert result.discarded_remainder == 1
    assert [actor.experience_points for actor in result.actors] == [50, 60, 0]


def test_fixed_party_experience_awards_every_hero_the_same_amount() -> None:
    actors = (
        replace(_actor(), uses_death_saves=True),
        replace(
            _actor(),
            id=ActorId("second"),
            experience_points=25,
            uses_death_saves=True,
        ),
        replace(
            _actor(),
            id=ActorId("enemy"),
            faction=Faction.ENEMY,
            uses_death_saves=False,
        ),
    )

    result = award_party_experience_per_actor(actors, 300)

    assert result.total_experience == 600
    assert result.experience_per_actor == 300
    assert result.discarded_remainder == 0
    assert [actor.experience_points for actor in result.actors] == [300, 325, 0]
