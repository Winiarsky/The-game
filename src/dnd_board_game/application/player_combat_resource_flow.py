from __future__ import annotations

from dataclasses import dataclass, replace
from random import Random
from typing import Protocol

from dnd_board_game.actions import ActionResourceResolver
from dnd_board_game.actors import (
    Actor,
    ExhaustionRollKind,
    Faction,
    apply_exhaustion_to_roll_request,
    saving_throw_roll_modifiers,
    spell_is_prepared,
)
from dnd_board_game.combat import (
    ActionEconomyCost,
    ActiveCombatEffect,
    AppliedDamageResult,
    CombatState,
    CombatStatus,
    available_cast_levels,
    can_consume_spell_resource,
    current_actor,
    grid_distance_feet,
    replace_actor,
    use_action_economy_cost,
)
from dnd_board_game.inventory import consume_item_use, has_item_use
from dnd_board_game.rules import (
    D20RollInput,
    D20RollRequest,
    EffectDuration,
    EffectEvent,
    EffectEventType,
    EffectSource,
    EffectSourceType,
    EffectStackingPolicy,
    RollModifier,
    apply_active_effect,
    expire_active_effects,
    resolve_d20_roll,
    spell_target_count,
)
from dnd_board_game.combat.auras import saving_throw_aura_modifiers


class CombatActionSpec(Protocol):
    id: str
    action_type: str
    label: str
    value: int
    target_faction: str
    target_count: int
    upcast_targets_per_level: int
    range_feet: int
    spell_level: int
    prepared: bool
    source_item_id: str | None
    action_cost: ActionEconomyCost
    charge_cost: int


@dataclass(frozen=True, slots=True)
class PendingConcentrationAction:
    caster_id: str
    action_id: str
    target_ids: tuple[str, ...]
    cast_level: int
    maximum_targets: int
    selected_target_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PendingConcentrationCheck:
    actor_id: str
    effect_ids: tuple[str, ...]
    damage: int
    dc: int


@dataclass(frozen=True, slots=True)
class CombatResourceTransition:
    state: CombatState
    active_effects: tuple[ActiveCombatEffect, ...]
    board_message: str
    message_title: str
    message_body: str
    event_type: str
    event_payload: tuple[tuple[str, object], ...]
    pending_action: PendingConcentrationAction | None = None
    pending_check: PendingConcentrationCheck | None = None
    clear_pending_action: bool = False
    clear_pending_check: bool = False
    clear_player_choices: bool = False
    clear_movement_preview: bool = False


class PlayerCombatResourceFlowService:
    """Resolve consumable combat actions and concentration lifecycle."""

    def __init__(self) -> None:
        self._resources = ActionResourceResolver()

    def use_strength_potion(
        self,
        *,
        state: CombatState,
        active_effects: tuple[ActiveCombatEffect, ...],
        action: CombatActionSpec,
    ) -> CombatResourceTransition:
        actor = _active_hero(state)
        if action.action_type != "strength_potion":
            raise ValueError("Nieznana akcja eliksiru.")
        if action.source_item_id is not None and not has_item_use(
            actor,
            action.source_item_id,
            charge_cost=getattr(action, "charge_cost", 0),
        ):
            raise ValueError("Ten przedmiot został już zużyty.")
        action_result = use_action_economy_cost(state, _action_cost(action))
        if not action_result.accepted:
            raise ValueError(action_result.message)
        updated_state = action_result.state
        actor_after = current_actor(updated_state)
        if action.source_item_id is not None:
            actor_after = consume_item_use(
                actor_after,
                action.source_item_id,
                charge_cost=getattr(action, "charge_cost", 0),
            ).actor
            updated_state = replace_actor(updated_state, actor_after)
        effect = ActiveCombatEffect(
            id=f"strength_potion:{actor_after.id}:{action.id}",
            actor_id=str(actor_after.id),
            kind="strength_potion",
            label=action.label,
            object_id=f"combat_action:{action.id}",
            value=action.value,
            source=EffectSource(
                EffectSourceType.ITEM,
                action.source_item_id or action.id,
                action.label,
            ),
            duration=EffectDuration.UNTIL_TURN_START,
        )
        updated_effects = apply_active_effect(
            active_effects,
            effect,
        ).active_effects
        message = (
            f"{actor_after.name} wypija {action.label}. Ataki i obrażenia z Siły mają "
            f"{action.value:+d} do następnej tury."
        )
        return CombatResourceTransition(
            state=updated_state,
            active_effects=updated_effects,
            board_message=message,
            message_title="Eliksir",
            message_body=message,
            event_type="ui_combat_strength_potion_used",
            event_payload=(
                ("actor_id", str(actor_after.id)),
                ("action_id", action.id),
                ("source_item_id", action.source_item_id),
                ("value", action.value),
            ),
            clear_player_choices=True,
        )

    def start_concentration(
        self,
        *,
        state: CombatState,
        active_effects: tuple[ActiveCombatEffect, ...],
        action: CombatActionSpec,
        cast_level: int | None = None,
    ) -> CombatResourceTransition:
        actor = _active_hero(state)
        if action.action_type != "concentration_attack_bonus":
            raise ValueError("Nieznana akcja koncentracji.")
        selected_cast_level = _selected_cast_level(actor, action, cast_level)
        _require_usable_action(actor, action, selected_cast_level)
        targets = _concentration_targets(state, actor, action)
        if not targets:
            raise ValueError("Brak legalnego celu czaru koncentracyjnego.")
        maximum_targets = spell_target_count(
            base_targets=int(getattr(action, "target_count", 1)),
            spell_level=action.spell_level,
            cast_level=selected_cast_level,
            targets_per_slot_level=int(
                getattr(action, "upcast_targets_per_level", 0)
            ),
        )
        pending = PendingConcentrationAction(
            caster_id=str(actor.id),
            action_id=action.id,
            target_ids=tuple(str(target.id) for target in targets),
            cast_level=selected_cast_level,
            maximum_targets=maximum_targets,
        )
        return CombatResourceTransition(
            state=state,
            active_effects=active_effects,
            pending_action=pending,
            board_message=(
                f"{action.label}: wybierz do {maximum_targets} legalnych celów."
            ),
            message_title="Koncentracja",
            message_body=(
                f"{actor.name} przygotowuje {action.label}. "
                f"Wybierz od 1 do {maximum_targets} celów."
            ),
            event_type="ui_combat_concentration_started",
            event_payload=(
                ("caster_id", str(actor.id)),
                ("action_id", action.id),
                ("cast_level", selected_cast_level),
                ("maximum_targets", maximum_targets),
                ("target_ids", [str(target.id) for target in targets]),
            ),
            clear_player_choices=True,
        )

    def confirm_concentration(
        self,
        *,
        state: CombatState,
        active_effects: tuple[ActiveCombatEffect, ...],
        action: CombatActionSpec,
        pending: PendingConcentrationAction,
        target_id: str | None = None,
        target_ids: tuple[str, ...] = (),
    ) -> CombatResourceTransition:
        caster = _active_hero(state)
        if str(caster.id) != pending.caster_id:
            raise ValueError(
                "Oczekujący czar koncentracyjny nie należy do aktywnego aktora."
            )
        selected_target_ids = target_ids
        if not selected_target_ids and target_id:
            selected_target_ids = (target_id,)
        if not selected_target_ids:
            selected_target_ids = pending.selected_target_ids
        if not selected_target_ids:
            raise ValueError("Wybierz co najmniej jeden cel czaru koncentracyjnego.")
        if len(selected_target_ids) != len(set(selected_target_ids)):
            raise ValueError("Ten sam cel czaru został wybrany więcej niż raz.")
        if len(selected_target_ids) > pending.maximum_targets:
            raise ValueError(
                f"Ten poziom czaru pozwala wybrać maksymalnie {pending.maximum_targets} celów."
            )
        if set(selected_target_ids) - set(pending.target_ids):
            raise ValueError("Wybrano nielegalny cel czaru koncentracyjnego.")
        _require_usable_action(caster, action, pending.cast_level)
        targets = tuple(
            _actor_by_id(state, selected_id)
            for selected_id in selected_target_ids
        )
        resource_use = self._resources.consume_action_and_source_resource(
            state,
            caster,
            spell_level=action.spell_level,
            spell_id=action.id,
            cast_level=pending.cast_level,
            action_cost=_action_cost(action),
        )
        removed = concentration_effects_for_actor(active_effects, str(caster.id))
        updated_effects = remove_concentration_effects(
            active_effects,
            str(caster.id),
        )
        applied_effects: list[ActiveCombatEffect] = []
        for target in targets:
            effect = ActiveCombatEffect(
                id=f"concentration_attack_bonus:{caster.id}:{target.id}:{action.id}",
                actor_id=str(target.id),
                kind="concentration_attack_bonus",
                label=action.label,
                object_id=f"combat_action:{action.id}",
                value=action.value,
                source_actor_id=str(caster.id),
                target_actor_id=str(target.id),
                source=EffectSource(EffectSourceType.SPELL, action.id, action.label),
                duration=EffectDuration.CONCENTRATION,
                stacking=EffectStackingPolicy.STACK,
                stacking_key=f"concentration:{caster.id}",
                spell_level=pending.cast_level,
            )
            updated_effects = apply_active_effect(
                updated_effects,
                effect,
            ).active_effects
            applied_effects.append(effect)
        ended = (
            " Poprzednia koncentracja zakończona: "
            f"{', '.join(effect.label for effect in removed)}."
            if removed
            else ""
        )
        message = (
            f"{caster.name} rzuca {action.label} ze slotu {pending.cast_level}. poziomu. "
            f"Cele: {', '.join(target.name for target in targets)}; "
            f"{action.value:+d} do ataku, dopóki koncentracja trwa.{ended}"
        )
        return CombatResourceTransition(
            state=resource_use.state,
            active_effects=updated_effects,
            board_message=message,
            message_title="Koncentracja",
            message_body=message,
            event_type="ui_combat_concentration_confirmed",
            event_payload=(
                ("caster_id", str(caster.id)),
                ("target_id", str(targets[0].id)),
                ("target_ids", [str(target.id) for target in targets]),
                ("action_id", action.id),
                ("cast_level", pending.cast_level),
                ("maximum_targets", pending.maximum_targets),
                ("value", action.value),
                ("effect_ids", [effect.id for effect in applied_effects]),
                ("removed_effect_ids", [effect.id for effect in removed]),
            ),
            clear_pending_action=True,
            clear_movement_preview=True,
        )

    def toggle_concentration_target(
        self,
        pending: PendingConcentrationAction,
        target_id: str,
    ) -> PendingConcentrationAction:
        if target_id not in pending.target_ids:
            raise ValueError("Wybrany cel nie jest legalnym celem czaru koncentracyjnego.")
        selected = list(pending.selected_target_ids)
        if target_id in selected:
            selected.remove(target_id)
        else:
            if len(selected) >= pending.maximum_targets:
                raise ValueError(
                    f"Można wybrać maksymalnie {pending.maximum_targets} celów."
                )
            selected.append(target_id)
        return replace(pending, selected_target_ids=tuple(selected))

    def cancel_concentration(
        self,
        *,
        state: CombatState,
        active_effects: tuple[ActiveCombatEffect, ...],
        pending: PendingConcentrationAction,
    ) -> CombatResourceTransition:
        return CombatResourceTransition(
            state=state,
            active_effects=active_effects,
            board_message=(
                "Anulowano czar koncentracyjny. "
                "Kliknij Skanuj planszę, żeby wybrać ruch, cel albo obiekt."
            ),
            message_title="Koncentracja",
            message_body="Anulowano czar koncentracyjny.",
            event_type="ui_combat_concentration_cancelled",
            event_payload=(
                ("caster_id", pending.caster_id),
                ("action_id", pending.action_id),
            ),
            clear_pending_action=True,
        )

    def handle_damage(
        self,
        *,
        state: CombatState,
        active_effects: tuple[ActiveCombatEffect, ...],
        applied_damage: AppliedDamageResult,
        rng: Random,
    ) -> CombatResourceTransition | None:
        damage = int(applied_damage.damage.total_applied or 0)
        if damage <= 0:
            return None
        actor_id = str(applied_damage.actor_after.id)
        effects = concentration_effects_for_actor(active_effects, actor_id)
        if not effects:
            return None
        actor = _actor_by_id(state, actor_id)
        if actor.is_defeated():
            return CombatResourceTransition(
                state=state,
                active_effects=remove_concentration_effects(active_effects, actor_id),
                board_message="",
                message_title="Koncentracja",
                message_body=(
                    f"{actor.name} pada. Koncentracja zakończona: "
                    f"{', '.join(effect.label for effect in effects)}."
                ),
                event_type="",
                event_payload=(),
            )
        dc = max(10, damage // 2)
        effect_ids = tuple(effect.id for effect in effects)
        if actor.faction != Faction.ALLY:
            return self.resolve_concentration_check(
                state=state,
                active_effects=active_effects,
                actor_id=actor_id,
                effect_ids=effect_ids,
                damage=damage,
                dc=dc,
                natural_roll=rng.randint(1, 20),
                natural_roll_2=rng.randint(1, 20),
            )
        return CombatResourceTransition(
            state=state,
            active_effects=active_effects,
            pending_check=PendingConcentrationCheck(actor_id, effect_ids, damage, dc),
            board_message=f"{actor.name}: rzut na utrzymanie koncentracji, ST {dc}.",
            message_title="Koncentracja",
            message_body=(
                f"{actor.name} otrzymuje {damage} obrażeń. "
                f"Rzuć CON save przeciw ST {dc}."
            ),
            event_type="",
            event_payload=(),
        )

    def resolve_concentration_check(
        self,
        *,
        state: CombatState,
        active_effects: tuple[ActiveCombatEffect, ...],
        actor_id: str,
        effect_ids: tuple[str, ...],
        damage: int,
        dc: int,
        natural_roll: int,
        natural_roll_2: int | None = None,
    ) -> CombatResourceTransition:
        actor = _actor_by_id(state, actor_id)
        request = apply_exhaustion_to_roll_request(
            actor,
            D20RollRequest(
                modifiers=(
                    *saving_throw_roll_modifiers(actor, "constitution"),
                    *saving_throw_aura_modifiers(state.actors, actor),
                )
            ),
            ExhaustionRollKind.SAVING_THROW,
        )
        if request.mode.value != "normal" and natural_roll_2 is None:
            raise ValueError("Ten rzut obronny wymaga dwóch wyników d20.")
        roll = resolve_d20_roll(
            D20RollInput(request, int(natural_roll), natural_roll_2)
        )
        success = roll.total >= int(dc)
        effect_labels = tuple(
            effect.label for effect in active_effects if effect.id in effect_ids
        )
        updated_effects = active_effects
        removed_effect_ids: list[str] = []
        if not success:
            removed = concentration_effects_for_actor(active_effects, actor_id)
            updated_effects = remove_concentration_effects(active_effects, actor_id)
            removed_effect_ids = [
                effect.id for effect in removed if effect.id in effect_ids
            ]
        result_text = (
            "koncentracja utrzymana"
            if success
            else f"koncentracja przerwana: {', '.join(effect_labels) or 'efekt'}"
        )
        message = (
            f"{actor.name}: CON save {roll.natural_roll} "
            f"{_modifier_breakdown_text(roll.breakdown.active_modifiers)} = {roll.total} / "
            f"ST {dc}; {result_text}."
        )
        return CombatResourceTransition(
            state=state,
            active_effects=updated_effects,
            board_message=message,
            message_title="Koncentracja",
            message_body=message,
            event_type="ui_combat_concentration_check",
            event_payload=(
                ("actor_id", actor_id),
                ("effect_ids", list(effect_ids)),
                ("removed_effect_ids", removed_effect_ids),
                ("damage", damage),
                ("dc", dc),
                ("natural_roll", roll.natural_roll),
                ("modifier", roll.breakdown.modifier_total),
                ("total", roll.total),
                ("success", success),
            ),
            clear_pending_check=True,
        )


def _modifier_breakdown_text(modifiers: tuple[RollModifier, ...]) -> str:
    if not modifiers:
        return "+ 0"
    return " ".join(
        f"{'+' if modifier.value >= 0 else '-'} {abs(modifier.value)} {modifier.label}"
        for modifier in modifiers
    )


def concentration_effects_for_actor(
    active_effects: tuple[ActiveCombatEffect, ...],
    actor_id: str,
) -> tuple[ActiveCombatEffect, ...]:
    return tuple(
        effect
        for effect in active_effects
        if effect.kind.startswith("concentration_")
        and effect.source_actor_id == actor_id
    )


def remove_concentration_effects(
    active_effects: tuple[ActiveCombatEffect, ...],
    actor_id: str,
) -> tuple[ActiveCombatEffect, ...]:
    return expire_active_effects(
        active_effects,
        EffectEvent(EffectEventType.CONCENTRATION_ENDED, actor_id=actor_id),
    ).active_effects


def _active_hero(state: CombatState) -> Actor:
    if state.status != CombatStatus.ACTIVE:
        raise ValueError("Walka nie jest aktywna.")
    actor = current_actor(state)
    if actor.faction != Faction.ALLY:
        raise ValueError("To nie jest tura bohatera.")
    return actor


def _action_cost(action: CombatActionSpec) -> ActionEconomyCost:
    return ActionEconomyCost(getattr(action, "action_cost", ActionEconomyCost.ACTION))


def _require_usable_action(
    actor: Actor,
    action: CombatActionSpec,
    cast_level: int | None = None,
) -> None:
    casting_kind = getattr(action, "casting_kind", None)
    casting_value = getattr(casting_kind, "value", None)
    if casting_value is None:
        casting_value = "leveled" if action.spell_level > 0 else "none"
    if not spell_is_prepared(
        actor.spell_preparation,
        action.id,
        casting_kind=casting_value,
        legacy_prepared=action.prepared,
    ):
        raise ValueError(f"Czar {action.label} nie został przygotowany.")
    if not can_consume_spell_resource(
        actor,
        action.spell_level,
        cast_level,
    ):
        raise ValueError(f"Brak slotów czaru dla {action.label}.")


def _selected_cast_level(
    actor: Actor,
    action: CombatActionSpec,
    cast_level: int | None,
) -> int:
    if action.spell_level <= 0:
        if cast_level not in {None, 0}:
            raise ValueError("Cantrip nie korzysta ze slotu czaru.")
        return 0
    levels = available_cast_levels(actor, action.spell_level)
    selected = levels[0] if cast_level is None and levels else cast_level
    if selected is None or selected not in levels:
        raise ValueError(f"Brak slotu {cast_level}. poziomu dla {action.label}.")
    return selected


def _concentration_targets(
    state: CombatState,
    actor: Actor,
    action: CombatActionSpec,
) -> tuple[Actor, ...]:
    if action.target_faction == "ally":
        range_feet = int(getattr(action, "range_feet", 0))
        return tuple(
            candidate
            for candidate in state.actors
            if candidate.faction == actor.faction and not candidate.is_defeated()
            and (
                candidate.id == actor.id
                or (
                    range_feet > 0
                    and grid_distance_feet(actor.position, candidate.position)
                    <= range_feet
                )
            )
        )
    return (actor,)


def _actor_by_id(state: CombatState, actor_id: str) -> Actor:
    actor = next((candidate for candidate in state.actors if str(candidate.id) == actor_id), None)
    if actor is None:
        raise ValueError(f"Nieznany aktor walki: {actor_id}.")
    return actor
