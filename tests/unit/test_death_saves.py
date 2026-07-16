from dataclasses import replace

import pytest

from dnd_board_game.actors import Actor, ActorId, DeathSaveState, Faction
from dnd_board_game.combat import DeathSaveOutcome, HealingSource, HealingSourceType, apply_healing_result, resolve_death_save, stabilize_actor
from dnd_board_game.world import Coordinate


def _dying_hero(*, successes: int = 0, failures: int = 0) -> Actor:
    hero = Actor(
        id=ActorId("hero"),
        name="Hero",
        ac=15,
        hp=10,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(0, 0),
        faction=Faction.ALLY,
        uses_death_saves=True,
    )
    return replace(hero, hp=0, death_saves=DeathSaveState(successes=successes, failures=failures))


def test_death_save_tracks_success_and_failure() -> None:
    success = resolve_death_save(_dying_hero(), 10)
    failure = resolve_death_save(success.actor_after, 9)

    assert success.outcome == DeathSaveOutcome.SUCCESS
    assert failure.outcome == DeathSaveOutcome.FAILURE
    assert failure.actor_after.death_saves.successes == 1
    assert failure.actor_after.death_saves.failures == 1


def test_natural_one_adds_two_failures_and_can_kill() -> None:
    result = resolve_death_save(_dying_hero(failures=1), 1)

    assert result.outcome == DeathSaveOutcome.DIED
    assert result.failures_added == 2
    assert result.actor_after.is_dead() is True


def test_natural_twenty_restores_one_hp_and_resets_counters() -> None:
    result = resolve_death_save(_dying_hero(successes=1, failures=2), 20)

    assert result.outcome == DeathSaveOutcome.REVIVED
    assert result.actor_after.hp == 1
    assert result.actor_after.death_saves == DeathSaveState()


def test_third_success_stabilizes_and_resets_counters() -> None:
    result = resolve_death_save(_dying_hero(successes=2, failures=2), 15)

    assert result.outcome == DeathSaveOutcome.STABILIZED
    assert result.actor_after.death_saves == DeathSaveState(stable=True)
    assert result.actor_after.needs_death_save() is False


def test_stabilization_and_positive_healing_end_death_saves() -> None:
    stable = stabilize_actor(_dying_hero(successes=1, failures=1))
    source = HealingSource("help", "Pomoc", HealingSourceType.CUSTOM, 5)
    healed = apply_healing_result(stable, source, 4).actor_after

    assert stable.death_saves == DeathSaveState(stable=True)
    assert healed.hp == 4
    assert healed.death_saves == DeathSaveState()


def test_actor_without_pending_death_save_cannot_roll() -> None:
    with pytest.raises(ValueError):
        resolve_death_save(replace(_dying_hero(), hp=1), 10)
