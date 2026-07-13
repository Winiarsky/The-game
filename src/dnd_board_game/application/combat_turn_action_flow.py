from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from dnd_board_game.actors import Actor, ActorId, Faction
from dnd_board_game.combat import (
    ActionUse,
    ActiveCombatEffect,
    AttackSource,
    CombatState,
    CombatStatus,
    current_actor,
    use_dash,
    use_turn_action,
)


@dataclass(frozen=True, slots=True)
class CombatTurnActionTransition:
    state: CombatState
    active_effects: tuple[ActiveCombatEffect, ...]
    actor_id: str
    message_title: str
    message_body: str
    event_type: str
    event_payload: tuple[tuple[str, object], ...]


@dataclass(frozen=True, slots=True)
class HelpPreparation:
    helper_id: str
    ally_ids: tuple[str, ...]
    target_ids: tuple[str, ...]
    board_message: str
    message_title: str
    message_body: str
    event_type: str
    event_payload: tuple[tuple[str, object], ...]


@dataclass(frozen=True, slots=True)
class ReadyPreparation:
    actor_id: str
    triggers: tuple[str, ...]
    board_message: str
    message_title: str
    message_body: str
    event_type: str
    event_payload: tuple[tuple[str, object], ...]


class CombatTurnActionFlowService:
    """Resolve common player turn actions without UI or hardware concerns."""

    def use_dash(
        self,
        *,
        state: CombatState,
        active_effects: tuple[ActiveCombatEffect, ...],
    ) -> CombatTurnActionTransition:
        actor = _active_hero(state)
        result = use_dash(state, actor)
        if not result.accepted:
            raise ValueError(result.message)
        return CombatTurnActionTransition(
            state=result.state,
            active_effects=active_effects,
            actor_id=str(actor.id),
            message_title="Dash",
            message_body=result.message,
            event_type="ui_combat_dash",
            event_payload=(("actor_id", str(actor.id)), ("extra_movement_feet", actor.speed_feet)),
        )

    def use_dodge(
        self,
        *,
        state: CombatState,
        active_effects: tuple[ActiveCombatEffect, ...],
    ) -> CombatTurnActionTransition:
        actor = _active_hero(state)
        effect = ActiveCombatEffect(
            id=f"dodge_until_next_turn:{actor.id}",
            actor_id=str(actor.id),
            kind="dodge_until_next_turn",
            label="Unik",
            object_id="combat_action:dodge",
            value=0,
        )
        return CombatTurnActionTransition(
            state=_consume_action(state),
            active_effects=_replace_actor_effect(active_effects, actor, effect),
            actor_id=str(actor.id),
            message_title="Unik",
            message_body=(
                f"Unik: ataki przeciwko {actor.name} mają utrudnienie do początku "
                "następnej tury tego aktora."
            ),
            event_type="ui_combat_dodge",
            event_payload=(("actor_id", str(actor.id)), ("attack_mode", "disadvantage")),
        )

    def use_disengage(
        self,
        *,
        state: CombatState,
        active_effects: tuple[ActiveCombatEffect, ...],
    ) -> CombatTurnActionTransition:
        actor = _active_hero(state)
        effect = ActiveCombatEffect(
            id=f"disengage_until_turn_end:{actor.id}",
            actor_id=str(actor.id),
            kind="disengage_until_turn_end",
            label="Odwrót",
            object_id="combat_action:disengage",
            value=0,
        )
        return CombatTurnActionTransition(
            state=_consume_action(state),
            active_effects=_replace_actor_effect(active_effects, actor, effect),
            actor_id=str(actor.id),
            message_title="Odwrót",
            message_body=f"Odwrót: {actor.name} może bezpiecznie odejść do końca tej tury.",
            event_type="ui_combat_disengage",
            event_payload=(("actor_id", str(actor.id)),),
        )

    def prepare_help(self, *, state: CombatState) -> HelpPreparation:
        actor = _active_hero(state)
        if state.turn_action.action_use != ActionUse.ACTION_AVAILABLE:
            raise ValueError("Akcja w tej turze została już zużyta.")
        allies = tuple(
            candidate
            for candidate in state.actors
            if candidate.faction == actor.faction
            and candidate.id != actor.id
            and not candidate.is_defeated()
        )
        targets = tuple(
            candidate
            for candidate in state.actors
            if candidate.faction not in {actor.faction, Faction.NEUTRAL}
            and not candidate.is_defeated()
            and _coordinates_in_reach(actor, candidate, 5)
        )
        if not allies:
            raise ValueError("Brak żywego sojusznika, któremu można pomóc.")
        if not targets:
            raise ValueError("Brak przeciwnika w zasięgu 5 ft pomagającego.")
        ally_ids = tuple(str(ally.id) for ally in allies)
        target_ids = tuple(str(target.id) for target in targets)
        return HelpPreparation(
            helper_id=str(actor.id),
            ally_ids=ally_ids,
            target_ids=target_ids,
            board_message="Wybierz sojusznika i cel pomocy w panelu walki.",
            message_title="Pomoc",
            message_body=f"{actor.name} przygotowuje akcję Help.",
            event_type="ui_combat_help_started",
            event_payload=(
                ("helper_id", str(actor.id)),
                ("ally_ids", list(ally_ids)),
                ("target_ids", list(target_ids)),
            ),
        )

    def confirm_help(
        self,
        *,
        state: CombatState,
        active_effects: tuple[ActiveCombatEffect, ...],
        helper_id: str,
        ally_ids: tuple[str, ...],
        target_ids: tuple[str, ...],
        ally_id: str,
        target_id: str,
    ) -> CombatTurnActionTransition:
        helper = _active_hero(state)
        if str(helper.id) != helper_id:
            raise ValueError("Oczekująca akcja Help nie należy do aktywnego aktora.")
        if ally_id not in ally_ids:
            raise ValueError("Wybrany sojusznik nie jest legalnym celem Help.")
        if target_id not in target_ids:
            raise ValueError("Wybrany przeciwnik nie jest legalnym celem Help.")
        ally = _actor_by_string_id(state, ally_id)
        target = _actor_by_string_id(state, target_id)
        remaining_effects = tuple(
            effect
            for effect in active_effects
            if not (
                effect.kind == "help_attack_advantage"
                and effect.source_actor_id == str(helper.id)
            )
        )
        effect = ActiveCombatEffect(
            id=f"help_attack_advantage:{helper.id}:{ally.id}:{target.id}",
            actor_id=str(ally.id),
            kind="help_attack_advantage",
            label=f"Pomoc: {helper.name}",
            object_id="combat_action:help",
            value=0,
            source_actor_id=str(helper.id),
            target_actor_id=str(target.id),
        )
        return CombatTurnActionTransition(
            state=_consume_action(state),
            active_effects=remaining_effects + (effect,),
            actor_id=str(helper.id),
            message_title="Pomoc",
            message_body=(
                f"Help: {helper.name} pomaga {ally.name}. Następny atak {ally.name} "
                f"przeciwko {target.name} ma przewagę."
            ),
            event_type="ui_combat_help_confirmed",
            event_payload=(
                ("helper_id", str(helper.id)),
                ("ally_id", str(ally.id)),
                ("target_id", str(target.id)),
            ),
        )

    def prepare_ready(
        self,
        *,
        state: CombatState,
        attack_sources_by_actor: Mapping[ActorId, AttackSource],
        triggers: tuple[str, ...] = ("enemy_moves", "enemy_attacks"),
    ) -> ReadyPreparation:
        actor = _active_hero(state)
        if state.turn_action.action_use != ActionUse.ACTION_AVAILABLE:
            raise ValueError("Akcja w tej turze została już zużyta.")
        if attack_sources_by_actor.get(actor.id) is None:
            raise ValueError(f"Aktor {actor.name} nie ma zdefiniowanego ataku do przygotowania.")
        return ReadyPreparation(
            actor_id=str(actor.id),
            triggers=triggers,
            board_message="Wybierz warunek przygotowanej akcji w panelu walki.",
            message_title="Ready",
            message_body=f"{actor.name} przygotowuje akcję.",
            event_type="ui_combat_ready_started",
            event_payload=(("actor_id", str(actor.id)),),
        )

    def confirm_ready(
        self,
        *,
        state: CombatState,
        active_effects: tuple[ActiveCombatEffect, ...],
        actor_id: str,
        triggers: tuple[str, ...],
        trigger: str,
    ) -> CombatTurnActionTransition:
        if trigger not in triggers:
            raise ValueError("Nieznany warunek przygotowanej akcji.")
        actor = _active_hero(state)
        if str(actor.id) != actor_id:
            raise ValueError("Oczekująca akcja Ready nie należy do aktywnego aktora.")
        remaining_effects = tuple(
            effect
            for effect in active_effects
            if not (effect.actor_id == str(actor.id) and effect.kind == "ready_attack")
        )
        effect = ActiveCombatEffect(
            id=f"ready_attack:{actor.id}:{trigger}",
            actor_id=str(actor.id),
            kind="ready_attack",
            label="Ready",
            object_id=f"combat_action:ready:{trigger}",
            value=0,
        )
        return CombatTurnActionTransition(
            state=_consume_action(state),
            active_effects=remaining_effects + (effect,),
            actor_id=str(actor.id),
            message_title="Ready",
            message_body=f"Ready: {actor.name} przygotowuje atak, {_ready_trigger_label(trigger)}.",
            event_type="ui_combat_ready_confirmed",
            event_payload=(("actor_id", str(actor.id)), ("trigger", trigger)),
        )


def _active_hero(state: CombatState) -> Actor:
    if state.status != CombatStatus.ACTIVE:
        raise ValueError("Walka nie jest aktywna.")
    actor = current_actor(state)
    if actor.faction != Faction.ALLY:
        raise ValueError("To nie jest tura bohatera.")
    return actor


def _consume_action(state: CombatState) -> CombatState:
    result = use_turn_action(state)
    if not result.accepted:
        raise ValueError(result.message)
    return result.state


def _replace_actor_effect(
    active_effects: tuple[ActiveCombatEffect, ...],
    actor: Actor,
    replacement: ActiveCombatEffect,
) -> tuple[ActiveCombatEffect, ...]:
    return tuple(
        effect
        for effect in active_effects
        if not (effect.actor_id == str(actor.id) and effect.kind == replacement.kind)
    ) + (replacement,)


def _actor_by_string_id(state: CombatState, actor_id: str) -> Actor:
    actor = next((candidate for candidate in state.actors if str(candidate.id) == actor_id), None)
    if actor is None:
        raise ValueError(f"Nieznany aktor walki: {actor_id}.")
    return actor


def _coordinates_in_reach(a: Actor, b: Actor, reach_feet: int) -> bool:
    distance_feet = max(
        abs(a.position.col - b.position.col),
        abs(a.position.row - b.position.row),
    ) * 5
    return reach_feet > 0 and 0 < distance_feet <= reach_feet


def _ready_trigger_label(trigger: str) -> str:
    labels = {
        "enemy_moves": "gdy przeciwnik się poruszy",
        "enemy_attacks": "gdy przeciwnik zaatakuje",
    }
    return labels.get(trigger, trigger)
