"""Exploration ritual casting without spell-slot consumption."""

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
    ScenarioClockEvent,
    TimedMagicEffect,
    advance_exploration_time,
    apply_timed_magic_effect,
)
from dnd_board_game.rules import (
    SpellCastingTime,
    SpellExplorationEffectKind,
    spell_duration_minutes,
)


@dataclass(frozen=True, slots=True)
class RitualCastingResult:
    actors: tuple[Actor, ...]
    state: ExplorationState
    actor_before: Actor
    actor_after: Actor
    spell_id: str
    spell_name: str
    target_id: str
    elapsed_minutes: int
    expired_effects: tuple[TimedMagicEffect, ...] = ()
    triggered_clock_events: tuple[ScenarioClockEvent, ...] = ()


class RitualCastingFlowService:
    def cast(
        self,
        *,
        actors: tuple[Actor, ...],
        state: ExplorationState,
        actor_id: str,
        spell_id: str,
        target_id: str = "",
    ) -> RitualCastingResult:
        actor = next(
            (candidate for candidate in actors if str(candidate.id) == actor_id),
            None,
        )
        if actor is None:
            raise ValueError(f"Nieznany aktor rytuału: {actor_id}.")
        spell = next(
            (candidate for candidate in actor.spells if candidate.id == spell_id),
            None,
        )
        if spell is None:
            raise ValueError(f"Aktor {actor.name} nie zna czaru {spell_id}.")
        validation = actor_spell_cast_validation(actor, spell_id, ritual=True)
        if validation is None or not validation.valid:
            errors = validation.errors if validation is not None else ()
            raise ValueError(" ".join(errors) or f"Nie można rzucić {spell.name} jako rytuału.")
        resource_use = consume_spell_resource(
            actor,
            spell.level,
            spell_id=spell.id,
            ritual=True,
        )
        actor_after = resource_use.actor_after
        updated_actors = tuple(
            actor_after if candidate.id == actor.id else candidate
            for candidate in actors
        )
        elapsed = ritual_casting_minutes(spell.casting_time)
        time_advance = advance_exploration_time(state, elapsed)
        updated_state = time_advance.state
        effect = spell.exploration_effect
        if effect is not None:
            if effect.kind != SpellExplorationEffectKind.SET_FLAG:
                raise ValueError(f"Nieobsługiwany efekt rytuału: {effect.kind.value}.")
            duration_minutes = spell_duration_minutes(spell.duration)
            if duration_minutes == 0:
                updated_state = replace(
                    updated_state,
                    flags=set_scene_flag(
                        updated_state.flags,
                        effect.flag_key,
                        target_id or effect.flag_value,
                    ),
                )
            else:
                timed_effect = TimedMagicEffect(
                    id=f"spell:{actor.id}:{spell.id}:{target_id or 'scene'}",
                    actor_id=str(actor.id),
                    spell_id=spell.id,
                    label=spell.name,
                    flag_key=effect.flag_key,
                    flag_value=target_id or effect.flag_value,
                    started_at_minute=updated_state.elapsed_minutes,
                    expires_at_minute=(
                        None
                        if duration_minutes is None
                        else updated_state.elapsed_minutes + duration_minutes
                    ),
                )
                updated_state = apply_timed_magic_effect(updated_state, timed_effect)
        return RitualCastingResult(
            actors=updated_actors,
            state=updated_state,
            actor_before=actor,
            actor_after=actor_after,
            spell_id=spell.id,
            spell_name=spell.name,
            target_id=target_id,
            elapsed_minutes=elapsed,
            expired_effects=time_advance.expired_effects,
            triggered_clock_events=time_advance.triggered_clock_events,
        )


def ritual_casting_minutes(casting_time: SpellCastingTime) -> int:
    base_minutes = {
        SpellCastingTime.ACTION: 0,
        SpellCastingTime.BONUS_ACTION: 0,
        SpellCastingTime.REACTION: 0,
        SpellCastingTime.MINUTE: 1,
        SpellCastingTime.TEN_MINUTES: 10,
        SpellCastingTime.HOUR: 60,
    }[casting_time]
    return base_minutes + 10
