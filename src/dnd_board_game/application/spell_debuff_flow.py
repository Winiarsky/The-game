from __future__ import annotations

from dataclasses import dataclass, replace
from random import Random
from typing import Protocol

from dnd_board_game.actions import ActionResourceResolver
from dnd_board_game.actors import Actor, Faction
from dnd_board_game.combat import (
    ActionEconomyCost,
    CombatCondition,
    CombatState,
    ConditionSaveTiming,
    actor_spell_cast_validation,
    apply_condition,
    condition_label,
    current_actor,
    grid_distance_feet,
    resolve_spell_save,
    reveal_actor,
    ActiveCombatEffect,
)
from dnd_board_game.rules import (
    EffectDuration,
    EffectSource,
    EffectSourceType,
    EffectStackingPolicy,
    RollMode,
)
from dnd_board_game.world import BoardState, line_of_sight_clear


class SpellDebuffActionSpec(Protocol):
    id: str
    action_type: str
    label: str
    range_feet: int
    spell_level: int
    action_cost: ActionEconomyCost
    duration: str
    effect_kind: str | None
    condition: CombatCondition | None
    condition_options: tuple[CombatCondition, ...]
    additional_conditions: tuple[CombatCondition, ...]
    save_ability: str | None
    save_dc: int | None
    save_timing: str | None
    concentration: bool
    cast_flag: str
    allowed_creature_types: tuple[str, ...]
    minimum_intelligence: int | None


@dataclass(frozen=True, slots=True)
class PendingSpellDebuff:
    caster_id: str
    action_id: str
    cast_level: int
    legal_target_ids: tuple[str, ...]
    selected_condition: str = ""

    def as_payload(self) -> dict[str, object]:
        return {
            "caster_id": self.caster_id,
            "action_id": self.action_id,
            "cast_level": self.cast_level,
            "legal_target_ids": list(self.legal_target_ids),
            "selected_condition": self.selected_condition,
        }


@dataclass(frozen=True, slots=True)
class SpellDebuffTransition:
    state: CombatState
    pending: PendingSpellDebuff | None
    message_title: str
    message_body: str
    event_type: str
    event_payload: tuple[tuple[str, object], ...]
    concentration_effect: ActiveCombatEffect | None = None
    scene_flag_changes: tuple[tuple[str, object], ...] = ()


class SpellDebuffFlowService:
    """Resolve a save-first condition spell with optional repeated saves."""

    def __init__(self) -> None:
        self._resources = ActionResourceResolver()

    def prepare(
        self,
        *,
        board: BoardState,
        state: CombatState,
        action: SpellDebuffActionSpec,
        cast_level: int | None = None,
        active_effects: tuple[ActiveCombatEffect, ...] = (),
    ) -> SpellDebuffTransition:
        caster = current_actor(state)
        _validate_action(action)
        validation = actor_spell_cast_validation(
            caster,
            action.id,
            cast_level=cast_level,
            condition_states=state.condition_states,
            active_effects=active_effects,
        )
        if validation is None or not validation.valid:
            raise ValueError(
                " ".join(validation.errors)
                if validation is not None
                else "Aktor nie zna tego czaru."
            )
        targets = _legal_targets(board, state, caster, action)
        if not targets:
            raise ValueError("Brak widocznego, legalnego celu debuffu.")
        pending = PendingSpellDebuff(
            caster_id=str(caster.id),
            action_id=action.id,
            cast_level=validation.cast_level,
            legal_target_ids=tuple(str(target.id) for target in targets),
        )
        return SpellDebuffTransition(
            state=state,
            pending=pending,
            message_title="Debuff",
            message_body=(
                f"{caster.name} przygotowuje {action.label}. "
                "Wybierz podświetlonego przeciwnika."
            ),
            event_type="ui_combat_spell_debuff_started",
            event_payload=(
                ("caster_id", str(caster.id)),
                ("spell_id", action.id),
                ("cast_level", validation.cast_level),
                ("target_ids", list(pending.legal_target_ids)),
            ),
        )

    def confirm(
        self,
        *,
        board: BoardState,
        state: CombatState,
        action: SpellDebuffActionSpec,
        pending: PendingSpellDebuff,
        target_id: str,
        rng: Random,
        condition: str = "",
        active_effects: tuple[ActiveCombatEffect, ...] = (),
    ) -> SpellDebuffTransition:
        caster = current_actor(state)
        _validate_action(action)
        if str(caster.id) != pending.caster_id or action.id != pending.action_id:
            raise ValueError("Oczekujący debuff nie należy do aktywnego aktora.")
        legal_ids = {
            str(target.id)
            for target in _legal_targets(board, state, caster, action)
        }
        if target_id not in pending.legal_target_ids or target_id not in legal_ids:
            raise ValueError("Wybrany aktor nie jest legalnym celem debuffu.")
        validation = actor_spell_cast_validation(
            caster,
            action.id,
            cast_level=pending.cast_level,
            condition_states=state.condition_states,
            active_effects=active_effects,
        )
        if validation is None or not validation.valid:
            raise ValueError(
                " ".join(validation.errors)
                if validation is not None
                else "Aktor nie zna tego czaru."
            )
        resource = self._resources.consume_action_and_source_resource(
            state,
            caster,
            spell_level=action.spell_level,
            spell_id=action.id,
            cast_level=pending.cast_level,
            action_cost=action.action_cost,
            resource_pool_id=getattr(action, "resource_pool_id", None),
            resource_cost=int(getattr(action, "resource_cost", 1)),
        )
        target = _actor_by_id(resource.state, target_id)
        save_dc = action.save_dc or caster.spell_save_dc
        save = resolve_spell_save(
            target,
            ability=action.save_ability or "constitution",
            dc=save_dc,
            natural_roll=rng.randint(1, 20),
            natural_roll_2=(
                rng.randint(1, 20)
                if "nimra_forced_weave" in getattr(action, "metamagic_ids", ())
                else None
            ),
            roll_mode=(
                RollMode.DISADVANTAGE
                if "nimra_forced_weave" in getattr(action, "metamagic_ids", ())
                else RollMode.NORMAL
            ),
            condition_states=resource.state.condition_states,
            combat_actors=resource.state.actors,
        )
        selected_condition = _selected_condition(action, condition)
        conditions = (selected_condition, *action.additional_conditions)
        updated = resource.state
        applied_conditions: list[CombatCondition] = []
        application_messages: list[str] = []
        if not save.success:
            for applied_condition in conditions:
                application = apply_condition(
                    updated.condition_states,
                    target,
                    applied_condition,
                    source_actor_id=str(caster.id),
                    source_label=action.label,
                    duration=(
                        EffectDuration.CONCENTRATION
                        if action.concentration
                        else _effect_duration(action.duration)
                    ),
                    save_ability=(
                        action.save_ability
                        if action.save_timing is not None
                        else None
                    ),
                    save_dc=save_dc if action.save_timing is not None else None,
                    save_timing=(
                        ConditionSaveTiming(action.save_timing)
                        if action.save_timing is not None
                        else None
                    ),
                    source_spell_id=action.id,
                    source_spell_level=pending.cast_level,
                )
                updated = replace(
                    updated,
                    condition_states=application.condition_states,
                )
                if application.applied:
                    applied_conditions.append(applied_condition)
                application_messages.append(application.message)
        updated = replace(
            updated,
            hidden_states=reveal_actor(updated.hidden_states, str(caster.id)),
        )
        condition_name = " i ".join(condition_label(value) for value in conditions)
        outcome = (
            f"{target.name} odpiera stan {condition_name}."
            if save.success
            else " ".join(application_messages)
        )
        message = (
            f"{caster.name} rzuca {action.label} na {target.name}. "
            f"Save {save.total}/{save_dc}: {outcome}"
        )
        concentration_effect = (
            ActiveCombatEffect(
                id=f"concentration_debuff:{caster.id}:{action.id}",
                actor_id=str(target.id),
                kind="concentration_debuff",
                label=action.label,
                object_id=f"spell:{action.id}",
                value=0,
                source_actor_id=str(caster.id),
                target_actor_id=str(target.id),
                source=EffectSource(
                    EffectSourceType.SPELL,
                    action.id,
                    action.label,
                ),
                duration=EffectDuration.CONCENTRATION,
                stacking=EffectStackingPolicy.STACK,
                stacking_key=f"concentration:{caster.id}",
                spell_level=pending.cast_level,
            )
            if applied_conditions and action.concentration
            else None
        )
        return SpellDebuffTransition(
            state=updated,
            pending=None,
            message_title="Debuff",
            message_body=message,
            event_type="ui_combat_spell_debuff_confirmed",
            event_payload=(
                ("caster_id", str(caster.id)),
                ("target_id", target_id),
                ("spell_id", action.id),
                ("cast_level", pending.cast_level),
                ("conditions", [value.value for value in conditions]),
                ("save", save.as_payload()),
                ("applied", bool(applied_conditions)),
            ),
            concentration_effect=concentration_effect,
            scene_flag_changes=(
                ((action.cast_flag, True),)
                if str(getattr(action, "cast_flag", "")).strip()
                else ()
            ),
        )

    def cancel(
        self,
        *,
        state: CombatState,
        pending: PendingSpellDebuff,
    ) -> SpellDebuffTransition:
        return SpellDebuffTransition(
            state=state,
            pending=None,
            message_title="Debuff",
            message_body="Anulowano czar. Akcja i slot nie zostały zużyte.",
            event_type="ui_combat_spell_debuff_cancelled",
            event_payload=(
                ("caster_id", pending.caster_id),
                ("spell_id", pending.action_id),
            ),
        )


def _validate_action(action: SpellDebuffActionSpec) -> None:
    if (
        action.action_type != "spell_debuff"
        or action.effect_kind != "apply_condition"
        or (action.condition is None and not action.condition_options)
        or action.save_ability is None
    ):
        raise ValueError("Ta akcja nie jest kompletnym czarem debuffującym.")


def _selected_condition(
    action: SpellDebuffActionSpec,
    requested: str,
) -> CombatCondition:
    if action.condition_options:
        try:
            selected = CombatCondition(requested)
        except ValueError as exc:
            raise ValueError("Wybierz jeden z dostępnych stanów czaru.") from exc
        if selected not in action.condition_options:
            raise ValueError("Wybrany stan nie jest dostępny dla tego czaru.")
        return selected
    if action.condition is None:
        raise ValueError("Czar nie określa nakładanego stanu.")
    return action.condition


def _legal_targets(
    board: BoardState,
    state: CombatState,
    caster: Actor,
    action: SpellDebuffActionSpec,
) -> tuple[Actor, ...]:
    from dnd_board_game.combat import is_hidden_from

    return tuple(
        target
        for target in state.actors
        if target.faction not in {caster.faction, Faction.NEUTRAL}
        and not target.is_defeated()
        and (
            not getattr(action, "allowed_creature_types", ())
            or target.creature_type in action.allowed_creature_types
        )
        and (
            getattr(action, "minimum_intelligence", None) is None
            or target.ability_scores.intelligence >= action.minimum_intelligence
        )
        and grid_distance_feet(caster.position, target.position)
        <= action.range_feet
        and line_of_sight_clear(board, caster.position, target.position)
        and not is_hidden_from(
            state.hidden_states,
            str(target.id),
            str(caster.id),
        )
    )


def _actor_by_id(state: CombatState, actor_id: str) -> Actor:
    return next(
        actor for actor in state.actors if str(actor.id) == actor_id
    )


def _effect_duration(value: str) -> EffectDuration:
    return {
        "next_turn_start": EffectDuration.UNTIL_TURN_START,
        "turn_end": EffectDuration.UNTIL_TURN_END,
        "encounter": EffectDuration.UNTIL_ENCOUNTER_END,
        "short_rest": EffectDuration.UNTIL_SHORT_REST,
        "long_rest": EffectDuration.UNTIL_LONG_REST,
        "scenario": EffectDuration.UNTIL_SCENARIO_END,
        "permanent": EffectDuration.PERMANENT,
    }.get(value, EffectDuration.UNTIL_ENCOUNTER_END)
