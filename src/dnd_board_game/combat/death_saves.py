from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from dnd_board_game.actors import Actor, DeathSaveState


class DeathSaveOutcome(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    STABILIZED = "stabilized"
    DIED = "died"
    REVIVED = "revived"


@dataclass(frozen=True, slots=True)
class DeathSaveResolution:
    actor_before: Actor
    actor_after: Actor
    natural_roll: int
    outcome: DeathSaveOutcome
    successes_added: int = 0
    failures_added: int = 0


def resolve_death_save(actor: Actor, natural_roll: int) -> DeathSaveResolution:
    if not actor.needs_death_save():
        raise ValueError(f"{actor.name} nie wykonuje teraz rzutu śmierci.")
    if not 1 <= natural_roll <= 20:
        raise ValueError("Wynik rzutu śmierci musi być w zakresie 1-20.")

    if natural_roll == 20:
        revived = replace(actor, hp=1, death_saves=DeathSaveState())
        return DeathSaveResolution(actor, revived, natural_roll, DeathSaveOutcome.REVIVED)

    failures_added = 2 if natural_roll == 1 else (1 if natural_roll < 10 else 0)
    successes_added = 1 if natural_roll >= 10 else 0
    failures = min(3, actor.death_saves.failures + failures_added)
    successes = min(3, actor.death_saves.successes + successes_added)
    if failures >= 3:
        state = DeathSaveState(successes=successes, failures=3, dead=True)
        outcome = DeathSaveOutcome.DIED
    elif successes >= 3:
        state = DeathSaveState(stable=True)
        outcome = DeathSaveOutcome.STABILIZED
    else:
        state = DeathSaveState(successes=successes, failures=failures)
        outcome = DeathSaveOutcome.SUCCESS if successes_added else DeathSaveOutcome.FAILURE
    return DeathSaveResolution(
        actor,
        replace(actor, death_saves=state),
        natural_roll,
        outcome,
        successes_added=successes_added,
        failures_added=failures_added,
    )


def stabilize_actor(actor: Actor) -> Actor:
    if not actor.needs_death_save():
        raise ValueError(f"{actor.name} nie może być teraz stabilizowany.")
    return replace(
        actor,
        death_saves=DeathSaveState(stable=True),
    )
