from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from dnd_board_game.actors import Actor, Faction, skill_modifier, skill_roll_modifiers
from dnd_board_game.combat import HiddenState, resolve_hide
from dnd_board_game.exploration import (
    EncounterOpeningOutcome,
    EncounterOpeningResolution,
    PrecombatStealthAttempt,
)
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll


@dataclass(frozen=True, slots=True)
class PrecombatStealthResolution:
    attempt: PrecombatStealthAttempt
    hidden_state: HiddenState | None


def precombat_stealth_is_available(
    opening: EncounterOpeningResolution | None,
) -> bool:
    """Return whether the authored opening leaves the enemy unaware of the party."""

    return bool(
        opening is not None
        and opening.outcome
        in {
            EncounterOpeningOutcome.PARTY_CAN_HIDE,
            EncounterOpeningOutcome.PARTY_INITIATIVE_ADVANTAGE_AND_CAN_HIDE,
        }
    )


def resolve_precombat_stealth(
    actors: Sequence[Actor],
    attempts: Sequence[PrecombatStealthAttempt],
    *,
    actor_id: str,
    natural_roll: int,
) -> PrecombatStealthResolution:
    actor = next((candidate for candidate in actors if str(candidate.id) == actor_id), None)
    if actor is None:
        raise ValueError(f"Nieznany bohater próby skradania: {actor_id}.")
    if actor.faction != Faction.ALLY or actor.is_defeated():
        raise ValueError("Przed starciem może skradać się tylko przytomny bohater drużyny.")
    if any(attempt.actor_id == actor_id for attempt in attempts):
        raise ValueError(f"{actor.name} wykorzystał już próbę skradania przed tym starciem.")

    roll = resolve_d20_roll(
        D20RollInput(
            D20RollRequest(modifiers=skill_roll_modifiers(actor, "stealth")),
            natural_roll,
        )
    )
    hiding = resolve_hide((), actor, actors, roll.total)
    hidden_from = hiding.hidden_state.hidden_from_actor_ids if hiding.hidden_state else ()
    attempt = PrecombatStealthAttempt(
        actor_id=actor_id,
        natural_roll=roll.natural_roll,
        total=roll.total,
        hidden_from_actor_ids=hidden_from,
        detected_by_actor_ids=hiding.detected_by_actor_ids,
    )
    return PrecombatStealthResolution(attempt, hiding.hidden_state)


def hidden_states_from_precombat_attempts(
    attempts: Sequence[PrecombatStealthAttempt],
    actors: Sequence[Actor],
) -> tuple[HiddenState, ...]:
    living_ids = {str(actor.id) for actor in actors if not actor.is_defeated()}
    return tuple(
        HiddenState(
            actor_id=attempt.actor_id,
            stealth_total=attempt.total,
            hidden_from_actor_ids=tuple(
                observer_id
                for observer_id in attempt.hidden_from_actor_ids
                if observer_id in living_ids
            ),
        )
        for attempt in attempts
        if attempt.actor_id in living_ids
        and any(observer_id in living_ids for observer_id in attempt.hidden_from_actor_ids)
    )


def precombat_stealth_modifier(actor: Actor) -> int:
    return skill_modifier(actor, "stealth")
