from __future__ import annotations

from dataclasses import dataclass, replace

from dnd_board_game.actors import ActorId
from dnd_board_game.rules import SpellCastingTime


@dataclass(frozen=True, slots=True)
class LongCastState:
    """A spell requiring the caster's action on several consecutive turns."""

    caster_id: ActorId
    spell_id: str
    label: str
    cast_level: int
    required_actions: int
    completed_actions: int
    started_round: int
    last_progress_round: int

    def __post_init__(self) -> None:
        if not self.spell_id.strip() or not self.label.strip():
            raise ValueError("Long casting requires a spell id and label.")
        if self.cast_level < 0:
            raise ValueError("Long casting slot level cannot be negative.")
        if self.required_actions < 2:
            raise ValueError("Long casting must require at least two actions.")
        if not 1 <= self.completed_actions <= self.required_actions:
            raise ValueError("Long casting progress is out of range.")
        if self.started_round < 1 or self.last_progress_round < self.started_round:
            raise ValueError("Long casting round metadata is invalid.")

    @property
    def completed(self) -> bool:
        return self.completed_actions >= self.required_actions


def casting_time_actions(casting_time: SpellCastingTime) -> int:
    """Convert 2014 combat rounds (6 seconds) into required Cast actions."""

    return {
        SpellCastingTime.MINUTE: 10,
        SpellCastingTime.TEN_MINUTES: 100,
        SpellCastingTime.HOUR: 600,
    }.get(casting_time, 1)


def long_cast_for_actor(
    casts: tuple[LongCastState, ...],
    actor_id: ActorId | str,
) -> LongCastState | None:
    actor_key = str(actor_id)
    return next(
        (cast for cast in casts if str(cast.caster_id) == actor_key),
        None,
    )


def add_long_cast(
    casts: tuple[LongCastState, ...],
    cast: LongCastState,
) -> tuple[LongCastState, ...]:
    if long_cast_for_actor(casts, cast.caster_id) is not None:
        raise ValueError("Aktor już rzuca długotrwały czar.")
    return (*casts, cast)


def advance_long_cast(
    casts: tuple[LongCastState, ...],
    actor_id: ActorId | str,
    *,
    round_number: int,
) -> tuple[tuple[LongCastState, ...], LongCastState]:
    current = long_cast_for_actor(casts, actor_id)
    if current is None:
        raise ValueError("Aktor nie rzuca długotrwałego czaru.")
    if current.last_progress_round == round_number:
        raise ValueError("Postęp długiego czaru został już wykonany w tej rundzie.")
    advanced = replace(
        current,
        completed_actions=current.completed_actions + 1,
        last_progress_round=round_number,
    )
    return (
        tuple(
            advanced if cast.caster_id == current.caster_id else cast
            for cast in casts
        ),
        advanced,
    )


def remove_long_cast(
    casts: tuple[LongCastState, ...],
    actor_id: ActorId | str,
) -> tuple[LongCastState, ...]:
    actor_key = str(actor_id)
    return tuple(
        cast for cast in casts if str(cast.caster_id) != actor_key
    )
