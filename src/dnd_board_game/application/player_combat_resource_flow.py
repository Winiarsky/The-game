from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Protocol

from dnd_board_game.actions import ActionResourceResolver
from dnd_board_game.actors import Actor, Faction, spell_is_prepared
from dnd_board_game.combat import (
    ActiveCombatEffect,
    AppliedDamageResult,
    CombatState,
    CombatStatus,
    can_consume_spell_resource,
    current_actor,
    replace_actor,
    use_turn_action,
)
from dnd_board_game.inventory import consume_inventory_item, has_inventory_quantity
from dnd_board_game.rules import (
    D20RollInput,
    D20RollRequest,
    EffectDuration,
    EffectEvent,
    EffectEventType,
    EffectSource,
    EffectSourceType,
    RollModifier,
    RollModifierType,
    apply_active_effect,
    ability_modifier,
    expire_active_effects,
    resolve_d20_roll,
)


class CombatActionSpec(Protocol):
    id: str
    action_type: str
    label: str
    value: int
    target_faction: str
    spell_level: int
    prepared: bool
    source_item_id: str | None


@dataclass(frozen=True, slots=True)
class PendingConcentrationAction:
    caster_id: str
    action_id: str
    target_ids: tuple[str, ...]


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
        if action.source_item_id is not None and not has_inventory_quantity(
            actor,
            action.source_item_id,
        ):
            raise ValueError("Ten przedmiot został już zużyty.")
        action_result = use_turn_action(state)
        if not action_result.accepted:
            raise ValueError(action_result.message)
        updated_state = action_result.state
        actor_after = current_actor(updated_state)
        if action.source_item_id is not None:
            actor_after = consume_inventory_item(actor_after, action.source_item_id)
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
    ) -> CombatResourceTransition:
        actor = _active_hero(state)
        if action.action_type != "concentration_attack_bonus":
            raise ValueError("Nieznana akcja koncentracji.")
        _require_usable_action(actor, action)
        targets = _concentration_targets(state, actor, action)
        if not targets:
            raise ValueError("Brak legalnego celu czaru koncentracyjnego.")
        pending = PendingConcentrationAction(
            caster_id=str(actor.id),
            action_id=action.id,
            target_ids=tuple(str(target.id) for target in targets),
        )
        return CombatResourceTransition(
            state=state,
            active_effects=active_effects,
            pending_action=pending,
            board_message=f"{action.label}: wybierz sojusznika dla efektu koncentracji.",
            message_title="Koncentracja",
            message_body=(
                f"{actor.name} przygotowuje {action.label}. Wybierz sojusznika."
            ),
            event_type="ui_combat_concentration_started",
            event_payload=(
                ("caster_id", str(actor.id)),
                ("action_id", action.id),
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
        target_id: str,
    ) -> CombatResourceTransition:
        caster = _active_hero(state)
        if str(caster.id) != pending.caster_id:
            raise ValueError(
                "Oczekujący czar koncentracyjny nie należy do aktywnego aktora."
            )
        if target_id not in pending.target_ids:
            raise ValueError("Wybrany cel nie jest legalnym celem czaru koncentracyjnego.")
        _require_usable_action(caster, action)
        target = _actor_by_id(state, target_id)
        resource_use = self._resources.consume_action_and_source_resource(
            state,
            caster,
            spell_level=action.spell_level,
        )
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
            stacking_key=f"concentration:{caster.id}",
        )
        application = apply_active_effect(active_effects, effect)
        removed = application.replaced_effects
        updated_effects = application.active_effects
        ended = (
            " Poprzednia koncentracja zakończona: "
            f"{', '.join(effect.label for effect in removed)}."
            if removed
            else ""
        )
        message = (
            f"{caster.name} rzuca {action.label}. {target.name} ma {action.value:+d} "
            f"do ataku, dopóki koncentracja trwa.{ended}"
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
                ("target_id", str(target.id)),
                ("action_id", action.id),
                ("value", action.value),
                ("removed_effect_ids", [effect.id for effect in removed]),
            ),
            clear_pending_action=True,
            clear_movement_preview=True,
        )

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
    ) -> CombatResourceTransition:
        actor = _actor_by_id(state, actor_id)
        modifier = ability_modifier(actor.ability_scores.constitution)
        request = D20RollRequest(
            modifiers=(
                RollModifier(
                    "Modyfikator Kondycji",
                    modifier,
                    RollModifierType.ABILITY,
                    stacking_key="ability:constitution",
                ),
            )
        )
        roll = resolve_d20_roll(D20RollInput(request, int(natural_roll)))
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
            f"{actor.name}: CON save {roll.natural_roll} + {modifier} = {roll.total} / "
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
                ("modifier", modifier),
                ("total", roll.total),
                ("success", success),
            ),
            clear_pending_check=True,
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


def _require_usable_action(actor: Actor, action: CombatActionSpec) -> None:
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
    ):
        raise ValueError(f"Brak slotów czaru dla {action.label}.")


def _concentration_targets(
    state: CombatState,
    actor: Actor,
    action: CombatActionSpec,
) -> tuple[Actor, ...]:
    if action.target_faction == "ally":
        return tuple(
            candidate
            for candidate in state.actors
            if candidate.faction == actor.faction and not candidate.is_defeated()
        )
    return (actor,)


def _actor_by_id(state: CombatState, actor_id: str) -> Actor:
    actor = next((candidate for candidate in state.actors if str(candidate.id) == actor_id), None)
    if actor is None:
        raise ValueError(f"Nieznany aktor walki: {actor_id}.")
    return actor
