"""Deterministic casting boundary for exploration and narrative spells."""

from __future__ import annotations

from dataclasses import dataclass, replace

from dnd_board_game.actors import Actor
from dnd_board_game.combat import (
    actor_spell_cast_validation,
    consume_spell_resource,
    set_scene_flag,
)
from dnd_board_game.exploration import (
    ExplorationState,
    TimedMagicEffect,
    apply_timed_magic_effect,
)
from dnd_board_game.rules import spell_duration_minutes


@dataclass(frozen=True, slots=True)
class ExplorationSpellCastResult:
    actors: tuple[Actor, ...]
    state: ExplorationState
    actor_before: Actor
    actor_after: Actor
    spell_id: str
    spell_name: str
    cast_level: int
    cast_flag: str
    target_id: str
    timed_effect: TimedMagicEffect | None


class ExplorationSpellCastingFlowService:
    def cast(
        self,
        *,
        actors: tuple[Actor, ...],
        state: ExplorationState,
        actor_id: str,
        spell_id: str,
        cast_level: int | None = None,
        target_id: str = "",
    ) -> ExplorationSpellCastResult:
        actor = next(
            (candidate for candidate in actors if str(candidate.id) == actor_id),
            None,
        )
        if actor is None:
            raise ValueError(f"Nieznany aktor czaru: {actor_id}.")
        spell = next(
            (candidate for candidate in actor.spells if candidate.id == spell_id),
            None,
        )
        if spell is None:
            raise ValueError(f"Aktor {actor.name} nie zna czaru {spell_id}.")
        validation = actor_spell_cast_validation(actor, spell_id)
        if validation is None or not validation.valid:
            errors = validation.errors if validation is not None else ()
            raise ValueError(" ".join(errors) or f"Nie można rzucić {spell.name}.")
        selected_level = int(cast_level or spell.level)
        if selected_level not in validation.available_cast_levels:
            raise ValueError(
                f"{spell.name} nie może zostać rzucony ze slotu {selected_level}."
            )
        resource = consume_spell_resource(
            actor,
            spell.level,
            spell_id=spell.id,
            cast_level=selected_level,
        )
        actor_after = resource.actor_after
        updated_actors = tuple(
            actor_after if candidate.id == actor.id else candidate
            for candidate in actors
        )
        cast_flag = f"cast_{spell.id}"
        flag_value: bool | str = target_id or True
        updated_state = replace(
            state,
            flags=set_scene_flag(state.flags, cast_flag, flag_value),
        )
        duration_minutes = spell_duration_minutes(spell.duration)
        timed_effect = None
        if duration_minutes != 0:
            timed_effect = TimedMagicEffect(
                id=f"spell:{actor.id}:{spell.id}:{target_id or 'scene'}",
                actor_id=str(actor.id),
                spell_id=spell.id,
                label=spell.name,
                flag_key=cast_flag,
                flag_value=flag_value,
                started_at_minute=state.elapsed_minutes,
                expires_at_minute=(
                    None
                    if duration_minutes is None
                    else state.elapsed_minutes + duration_minutes
                ),
            )
            updated_state = apply_timed_magic_effect(
                updated_state,
                timed_effect,
            )
        return ExplorationSpellCastResult(
            actors=updated_actors,
            state=updated_state,
            actor_before=actor,
            actor_after=actor_after,
            spell_id=spell.id,
            spell_name=spell.name,
            cast_level=selected_level,
            cast_flag=cast_flag,
            target_id=target_id,
            timed_effect=timed_effect,
        )


__all__ = [
    "ExplorationSpellCastResult",
    "ExplorationSpellCastingFlowService",
]
