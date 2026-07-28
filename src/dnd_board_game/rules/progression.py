"""D&D 5e 2014 experience thresholds and level-up eligibility."""

from __future__ import annotations

from dataclasses import dataclass, replace

from dnd_board_game.actors import Actor


EXPERIENCE_THRESHOLDS: tuple[int, ...] = (
    0,
    300,
    900,
    2_700,
    6_500,
    14_000,
    23_000,
    34_000,
    48_000,
    64_000,
    85_000,
    100_000,
    120_000,
    140_000,
    165_000,
    195_000,
    225_000,
    265_000,
    305_000,
    355_000,
)


@dataclass(frozen=True, slots=True)
class ExperienceProgress:
    level: int
    experience_points: int
    eligible_level: int
    next_level_experience: int | None
    experience_to_next_level: int | None

    @property
    def level_up_available(self) -> bool:
        return self.eligible_level > self.level


@dataclass(frozen=True, slots=True)
class ExperienceAwardResult:
    actor: Actor
    awarded_experience: int
    before: ExperienceProgress
    after: ExperienceProgress


@dataclass(frozen=True, slots=True)
class PartyExperienceAwardResult:
    actors: tuple[Actor, ...]
    total_experience: int
    experience_per_actor: int
    discarded_remainder: int
    actor_ids: tuple[str, ...]


def level_for_experience(experience_points: int, *, level_cap: int = 20) -> int:
    if experience_points < 0:
        raise ValueError("Punkty doświadczenia nie mogą być ujemne.")
    _validate_level_cap(level_cap)
    eligible = 1
    for level, threshold in enumerate(EXPERIENCE_THRESHOLDS, start=1):
        if level > level_cap or experience_points < threshold:
            break
        eligible = level
    return eligible


def experience_progress(actor: Actor, *, level_cap: int = 3) -> ExperienceProgress:
    _validate_level_cap(level_cap)
    eligible_level = level_for_experience(
        actor.experience_points,
        level_cap=level_cap,
    )
    next_level = actor.level + 1
    next_threshold = (
        EXPERIENCE_THRESHOLDS[next_level - 1]
        if next_level <= level_cap
        else None
    )
    remaining = (
        max(0, next_threshold - actor.experience_points)
        if next_threshold is not None
        else None
    )
    return ExperienceProgress(
        level=actor.level,
        experience_points=actor.experience_points,
        eligible_level=max(actor.level, eligible_level),
        next_level_experience=next_threshold,
        experience_to_next_level=remaining,
    )


def award_experience(
    actor: Actor,
    amount: int,
    *,
    level_cap: int = 3,
) -> ExperienceAwardResult:
    if amount < 0:
        raise ValueError("Nie można przyznać ujemnych punktów doświadczenia.")
    before = experience_progress(actor, level_cap=level_cap)
    updated = replace(
        actor,
        experience_points=actor.experience_points + amount,
    )
    return ExperienceAwardResult(
        actor=updated,
        awarded_experience=amount,
        before=before,
        after=experience_progress(updated, level_cap=level_cap),
    )


def award_party_experience(
    actors: tuple[Actor, ...],
    total_experience: int,
    *,
    level_cap: int = 3,
) -> PartyExperienceAwardResult:
    if total_experience < 0:
        raise ValueError("Nagroda XP nie może być ujemna.")
    participants = tuple(
        actor
        for actor in actors
        if actor.faction.value == "ally"
        and actor.uses_death_saves
        and not actor.is_dead()
    )
    if not participants:
        raise ValueError("Brak żywych członków drużyny, którym można przyznać XP.")
    share, remainder = divmod(total_experience, len(participants))
    participant_ids = {actor.id for actor in participants}
    updated_by_id = {
        actor.id: award_experience(actor, share, level_cap=level_cap).actor
        for actor in participants
    }
    return PartyExperienceAwardResult(
        actors=tuple(
            updated_by_id.get(actor.id, actor)
            if actor.id in participant_ids
            else actor
            for actor in actors
        ),
        total_experience=total_experience,
        experience_per_actor=share,
        discarded_remainder=remainder,
        actor_ids=tuple(str(actor.id) for actor in participants),
    )


def _validate_level_cap(level_cap: int) -> None:
    if not 1 <= level_cap <= len(EXPERIENCE_THRESHOLDS):
        raise ValueError("Limit poziomu musi mieścić się między 1 a 20.")
