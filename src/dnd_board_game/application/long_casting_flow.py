from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol

from dnd_board_game.actors import Actor
from dnd_board_game.combat import (
    ActiveCombatEffect,
    CombatState,
    LongCastState,
    add_long_cast,
    actor_spell_cast_validation,
    advance_long_cast,
    casting_time_actions,
    consume_spell_resource,
    current_actor,
    long_cast_for_actor,
    remove_long_cast,
    replace_actor,
    use_turn_action,
)
from dnd_board_game.rules import (
    EffectDuration,
    EffectSource,
    EffectSourceType,
    SpellCastingTime,
    apply_active_effect,
)

from .player_combat_resource_flow import (
    concentration_effects_for_actor,
    remove_concentration_effects,
)


class LongCastActionSpec(Protocol):
    id: str
    label: str
    action_type: str
    effect_kind: str | None
    value: int
    spell_level: int
    casting_time: SpellCastingTime


@dataclass(frozen=True, slots=True)
class LongCastingTransition:
    state: CombatState
    active_effects: tuple[ActiveCombatEffect, ...]
    cast: LongCastState | None
    completed: bool
    interrupted: bool
    message_title: str
    message_body: str
    event_type: str
    event_payload: tuple[tuple[str, object], ...]


class LongCastingFlowService:
    """Resolve action-by-action casting times longer than one action."""

    def start(
        self,
        *,
        state: CombatState,
        active_effects: tuple[ActiveCombatEffect, ...],
        action: LongCastActionSpec,
        cast_level: int | None = None,
    ) -> LongCastingTransition:
        caster = current_actor(state)
        if action.action_type != "long_cast_effect":
            raise ValueError("Ta akcja nie jest długotrwałym czarem.")
        required_actions = casting_time_actions(action.casting_time)
        if required_actions <= 1:
            raise ValueError("Ten czar nie ma długiego czasu rzucania.")
        if long_cast_for_actor(state.long_casts, caster.id) is not None:
            raise ValueError("Aktor już rzuca długotrwały czar.")
        validation = actor_spell_cast_validation(
            caster,
            action.id,
            cast_level=cast_level,
        )
        if validation is None or not validation.valid:
            raise ValueError(
                " ".join(validation.errors)
                if validation is not None
                else "Aktor nie zna tego czaru."
            )
        selected_level = validation.cast_level
        action_use = use_turn_action(state)
        if not action_use.accepted:
            raise ValueError(action_use.message)

        cast = LongCastState(
            caster_id=caster.id,
            spell_id=action.id,
            label=action.label,
            cast_level=selected_level,
            required_actions=required_actions,
            completed_actions=1,
            started_round=state.round_number,
            last_progress_round=state.round_number,
        )
        updated_state = replace(
            action_use.state,
            long_casts=add_long_cast(action_use.state.long_casts, cast),
        )
        ended = concentration_effects_for_actor(active_effects, str(caster.id))
        updated_effects = remove_concentration_effects(
            active_effects,
            str(caster.id),
        )
        casting_effect = ActiveCombatEffect(
            id=_long_cast_effect_id(caster, action.id),
            actor_id=str(caster.id),
            kind="concentration_long_cast",
            label=f"Rzucanie: {action.label}",
            object_id=f"spell:{action.id}",
            value=0,
            source_actor_id=str(caster.id),
            source=EffectSource(
                EffectSourceType.SPELL,
                action.id,
                action.label,
            ),
            duration=EffectDuration.CONCENTRATION,
            stacking_key=f"concentration:{caster.id}",
        )
        updated_effects = apply_active_effect(
            updated_effects,
            casting_effect,
        ).active_effects
        ended_text = (
            f" Poprzednia koncentracja zakończona: "
            f"{', '.join(effect.label for effect in ended)}."
            if ended
            else ""
        )
        message = (
            f"{caster.name} rozpoczyna {action.label}: postęp 1/{required_actions} "
            f"akcji. Slot zostanie zużyty dopiero po ukończeniu.{ended_text}"
        )
        return LongCastingTransition(
            state=updated_state,
            active_effects=updated_effects,
            cast=cast,
            completed=False,
            interrupted=False,
            message_title="Długie rzucanie",
            message_body=message,
            event_type="ui_combat_long_cast_started",
            event_payload=(
                ("caster_id", str(caster.id)),
                ("spell_id", action.id),
                ("cast_level", selected_level),
                ("required_actions", required_actions),
            ),
        )

    def continue_cast(
        self,
        *,
        state: CombatState,
        active_effects: tuple[ActiveCombatEffect, ...],
        action: LongCastActionSpec,
    ) -> LongCastingTransition:
        caster = current_actor(state)
        cast = long_cast_for_actor(state.long_casts, caster.id)
        if cast is None or cast.spell_id != action.id:
            raise ValueError("Aktywny aktor nie rzuca tego czaru.")
        action_use = use_turn_action(state)
        if not action_use.accepted:
            raise ValueError(action_use.message)
        casts, advanced = advance_long_cast(
            action_use.state.long_casts,
            caster.id,
            round_number=state.round_number,
        )
        progressed_state = replace(action_use.state, long_casts=casts)
        if not advanced.completed:
            message = (
                f"{caster.name} kontynuuje {action.label}: postęp "
                f"{advanced.completed_actions}/{advanced.required_actions} akcji."
            )
            return LongCastingTransition(
                state=progressed_state,
                active_effects=active_effects,
                cast=advanced,
                completed=False,
                interrupted=False,
                message_title="Długie rzucanie",
                message_body=message,
                event_type="ui_combat_long_cast_progressed",
                event_payload=(
                    ("caster_id", str(caster.id)),
                    ("spell_id", action.id),
                    ("completed_actions", advanced.completed_actions),
                    ("required_actions", advanced.required_actions),
                ),
            )
        return self._complete(
            state=progressed_state,
            active_effects=active_effects,
            action=action,
            cast=advanced,
        )

    def interrupt(
        self,
        *,
        state: CombatState,
        active_effects: tuple[ActiveCombatEffect, ...],
        caster_id: str,
        reason: str,
    ) -> LongCastingTransition:
        cast = long_cast_for_actor(state.long_casts, caster_id)
        if cast is None:
            raise ValueError("Aktor nie rzuca długotrwałego czaru.")
        caster = next(
            actor for actor in state.actors if str(actor.id) == caster_id
        )
        updated_state = replace(
            state,
            long_casts=remove_long_cast(state.long_casts, caster_id),
        )
        updated_effects = tuple(
            effect
            for effect in active_effects
            if effect.id != _long_cast_effect_id(caster, cast.spell_id)
        )
        message = (
            f"{caster.name} przerywa rzucanie {cast.label}: {reason}. "
            "Slot czaru nie został zużyty."
        )
        return LongCastingTransition(
            state=updated_state,
            active_effects=updated_effects,
            cast=None,
            completed=False,
            interrupted=True,
            message_title="Przerwane rzucanie",
            message_body=message,
            event_type="ui_combat_long_cast_interrupted",
            event_payload=(
                ("caster_id", caster_id),
                ("spell_id", cast.spell_id),
                ("reason", reason),
                ("completed_actions", cast.completed_actions),
                ("required_actions", cast.required_actions),
            ),
        )

    def _complete(
        self,
        *,
        state: CombatState,
        active_effects: tuple[ActiveCombatEffect, ...],
        action: LongCastActionSpec,
        cast: LongCastState,
    ) -> LongCastingTransition:
        caster = current_actor(state)
        resource_use = consume_spell_resource(
            caster,
            action.spell_level,
            cast.cast_level,
            spell_id=action.id,
        )
        caster_after = resource_use.actor_after
        if action.effect_kind == "grant_temp_hp":
            caster_after = replace(
                caster_after,
                temp_hp=max(caster_after.temp_hp, int(action.value)),
            )
        else:
            raise ValueError(
                f"Nieobsługiwany efekt ukończonego długiego czaru: {action.effect_kind}."
            )
        updated_state = replace_actor(state, caster_after)
        updated_state = replace(
            updated_state,
            long_casts=remove_long_cast(updated_state.long_casts, caster.id),
        )
        updated_effects = tuple(
            effect
            for effect in active_effects
            if effect.id != _long_cast_effect_id(caster, action.id)
        )
        message = (
            f"{caster.name} kończy {action.label} po {cast.required_actions} akcjach "
            f"i zyskuje {action.value} tymczasowych HP. Zużyto slot "
            f"{cast.cast_level}. poziomu."
        )
        return LongCastingTransition(
            state=updated_state,
            active_effects=updated_effects,
            cast=None,
            completed=True,
            interrupted=False,
            message_title="Czar ukończony",
            message_body=message,
            event_type="ui_combat_long_cast_completed",
            event_payload=(
                ("caster_id", str(caster.id)),
                ("spell_id", action.id),
                ("cast_level", cast.cast_level),
                ("required_actions", cast.required_actions),
                ("effect_kind", action.effect_kind),
                ("value", action.value),
            ),
        )


def _long_cast_effect_id(caster: Actor, spell_id: str) -> str:
    return f"long-cast:{caster.id}:{spell_id}"
