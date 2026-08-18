from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from random import Random
from typing import Mapping

from dnd_board_game.actors import Actor, ActorId, Faction, actor_has_feature
from dnd_board_game.combat import (
    ActiveCombatEffect,
    AttackSource,
    CombatState,
    CombatStatus,
    CombatCondition,
    EnemyAutoTurnResult,
    EnemyAiProfile,
    EnemyTurnPlan,
    OpportunityAttackThreat,
    ReactionKind,
    ReactionOption,
    ReactionWindow,
    SceneObject,
    DamageComponentInput,
    DamageType,
    apply_damage_result,
    apply_condition,
    apply_save_damage_amount,
    attack_source_with_target_combat_effects,
    current_actor,
    opportunity_attackers_for_movement,
    open_reaction_window,
    plan_enemy_turn,
    plan_utility_enemy_turn,
    resolve_planned_enemy_turn,
    resolve_actor_saving_throw,
    resolve_damage,
    replace_actor,
    reaction_available_for,
    start_attack_action,
    grid_distance_feet,
)
from dnd_board_game.rules import (
    RollModifier,
    RollModifierType,
    SavingThrowRequest,
    SavingThrowResult,
)
from dnd_board_game.world import BoardState, Coordinate

from .combat_reaction_flow import PlayerReactionFlowService, ReadyAttackTrigger
from .damage_presentation import applied_damage_message, applied_damage_payload


class EnemyTurnTransitionKind(StrEnum):
    REACTION = "reaction"
    READY = "ready"
    OPPORTUNITY = "opportunity"
    MOVEMENT = "movement"
    ATTACK = "attack"
    FINISHED = "finished"


@dataclass(frozen=True, slots=True)
class EnemyTurnIntentTransition:
    intent: EnemyTurnPlan
    enemy_id: str
    board_message: str
    message_title: str
    message_body: str
    event_type: str
    event_payload: tuple[tuple[str, object], ...]


@dataclass(frozen=True, slots=True)
class EnemyTurnResolutionTransition:
    result: EnemyAutoTurnResult
    kind: EnemyTurnTransitionKind
    board_message: str
    message_title: str
    message_body: str
    reaction_window: ReactionWindow | None = None
    ready_trigger: ReadyAttackTrigger | None = None
    threat_actor_ids: tuple[str, ...] = ()
    event_type: str = ""
    event_payload: tuple[tuple[str, object], ...] = ()


@dataclass(frozen=True, slots=True)
class PendingEnemySavingThrow:
    target_id: str
    source_id: str
    request: SavingThrowRequest


@dataclass(frozen=True, slots=True)
class EnemySavingThrowTransition:
    result: EnemyAutoTurnResult
    saving_throw: SavingThrowResult
    board_message: str
    message_title: str
    message_body: str
    event_type: str
    event_payload: tuple[tuple[str, object], ...]


class EnemyTurnFlowService:
    """Plan and classify enemy turns before UI and board confirmation."""

    def __init__(self) -> None:
        self._player_reactions = PlayerReactionFlowService()

    def plan(
        self,
        *,
        state: CombatState,
        board: BoardState,
        attack_sources_by_actor: Mapping[ActorId, AttackSource],
        multiattack_sources_by_actor: Mapping[ActorId, tuple[AttackSource, ...]] | None = None,
        scene_objects: tuple[SceneObject, ...] = (),
        ai_profile: EnemyAiProfile | None = None,
        ai_roles: Mapping[str, str] | None = None,
        ai_zone_positions: Mapping[str, tuple[Coordinate, ...]] | None = None,
    ) -> EnemyTurnIntentTransition:
        enemy = _active_enemy(state)
        source = _enemy_attack_source(
            state,
            enemy,
            attack_sources_by_actor,
            multiattack_sources_by_actor,
        )
        if source is None:
            raise ValueError(f"Aktor {enemy.name} nie ma zdefiniowanego ataku.")
        role_by_actor = dict(ai_roles or {})
        zones = dict(ai_zone_positions or {})
        role_id = role_by_actor.get(str(enemy.id), "")
        intent = (
            plan_utility_enemy_turn(
                board,
                state,
                enemy,
                source,
                profile=ai_profile,
                role_id=role_id,
                actor_roles=role_by_actor,
                escape_positions=zones.get(ai_profile.escape_zone_tag, ()),
                guard_positions=zones.get(ai_profile.guard_zone_tag, ()),
                hazard_positions=zones.get(ai_profile.hazard_zone_tag, ()),
                scene_objects=scene_objects,
            )
            if ai_profile is not None and role_id
            else plan_enemy_turn(board, state, enemy, source)
        )
        return EnemyTurnIntentTransition(
            intent=intent,
            enemy_id=str(enemy.id),
            board_message=intent.message,
            message_title="Zamiar przeciwnika",
            message_body=f"{intent.message} Potwierdź Enterem albo przyciskiem.",
            event_type="ui_combat_enemy_turn_intent",
            event_payload=(
                ("enemy_id", str(enemy.id)),
                ("target_id", intent.target.id if intent.target is not None else None),
                ("message", intent.message),
                ("intent", intent.intent),
                ("utility_score", intent.utility_score),
                ("utility_breakdown", list(intent.utility_breakdown)),
            ),
        )

    def resolve(
        self,
        *,
        state: CombatState,
        intent: EnemyTurnPlan,
        board: BoardState,
        attack_sources_by_actor: Mapping[ActorId, AttackSource],
        multiattack_sources_by_actor: Mapping[ActorId, tuple[AttackSource, ...]] | None = None,
        active_effects: tuple[ActiveCombatEffect, ...],
        rng: Random,
        scene_objects: tuple[SceneObject, ...] = (),
    ) -> EnemyTurnResolutionTransition:
        enemy = _active_enemy(state)
        source = _enemy_attack_source(
            state,
            enemy,
            attack_sources_by_actor,
            multiattack_sources_by_actor,
        )
        if source is None:
            raise ValueError(f"Aktor {enemy.name} nie ma zdefiniowanego ataku.")
        target_actor = None
        if intent.target is not None:
            target_actor = next(
                (actor for actor in state.actors if str(actor.id) == intent.target.id),
                None,
            )
        if target_actor is not None:
            source = attack_source_with_target_combat_effects(
                enemy,
                target_actor,
                source,
                active_effects,
            )
        bane = next(
            (
                effect
                for effect in active_effects
                if effect.actor_id == str(enemy.id)
                and effect.kind == "bane_roll_penalty"
            ),
            None,
        )
        if bane is not None:
            bane_roll = rng.randint(1, bane.value)
            source = replace(
                source,
                attack_roll_request=replace(
                    source.attack_roll_request,
                    modifiers=(
                        *source.attack_roll_request.modifiers,
                        RollModifier(
                            bane.label,
                            -bane_roll,
                            RollModifierType.SPELL,
                            stacking_key=bane.id,
                        ),
                    ),
                ),
            )
        result = resolve_planned_enemy_turn(
            board,
            intent,
            source,
            rng,
            scene_objects,
            active_effects,
            maximum_attacks=(
                len(multiattack_sources_by_actor.get(enemy.id, ()))
                if multiattack_sources_by_actor
                and multiattack_sources_by_actor.get(enemy.id)
                else None
            ),
            original_state=state,
        )
        ready_attacks = (
            *self._player_reactions.detect_ready_attacks(
                state=state,
                enemy_result=result,
                board=board,
                attack_sources_by_actor=attack_sources_by_actor,
                active_effects=active_effects,
            ),
            *_giant_killer_reactions(
                state=state,
                enemy_result=result,
                board=board,
                attack_sources_by_actor=attack_sources_by_actor,
            ),
        )
        movement_threats = (
            tuple(
                threat
                for threat in opportunity_attackers_for_movement(
                    state,
                    enemy,
                    enemy.position,
                    result.movement_path.destination,
                    attack_sources_by_actor,
                    active_effects,
                )
                if threat.attacker.faction == Faction.ALLY
            )
            if _result_has_movement(result, enemy.position)
            else ()
        )
        reaction_options = (
            *(
                ReactionOption(
                    id=f"ready:{ready.effect_id}:{ready.target_id}",
                    kind=ReactionKind.READY_ATTACK,
                    reactor_actor_id=ready.readied_actor_id,
                    target_actor_id=ready.target_id,
                    trigger_event=ready.trigger,
                    effect_id=ready.effect_id,
                    label=(
                        "Giant Killer"
                        if ready.trigger == "giant_killer"
                        else "Ready"
                    ),
                )
                for ready in ready_attacks
            ),
            *(
                ReactionOption(
                    id=f"opportunity:{threat.attacker.id}:{enemy.id}",
                    kind=ReactionKind.OPPORTUNITY_ATTACK,
                    reactor_actor_id=str(threat.attacker.id),
                    target_actor_id=str(enemy.id),
                    trigger_event="enemy_leaves_reach",
                    label="Atak okazyjny",
                )
                for threat in movement_threats
            ),
        )
        reaction_window = open_reaction_window(
            interrupted_actor_id=str(enemy.id),
            trigger_event=_reaction_window_trigger(ready_attacks, movement_threats),
            options=reaction_options,
        )
        if reaction_window is not None:
            ready = ready_attacks[0] if ready_attacks else None
            threat_actor_ids = tuple(
                str(threat.attacker.id) for threat in movement_threats
            )
            if ready is not None:
                readied_actor = next(
                    actor for actor in state.actors if str(actor.id) == ready.readied_actor_id
                )
                board_message = (
                    f"Wyzwolono Ready: {readied_actor.name} może użyć przygotowanego ataku."
                )
                message_title = "Ready"
                message_body = (
                    f"{readied_actor.name}: warunek przygotowanej akcji został spełniony "
                    f"({_ready_trigger_label(ready.trigger)})."
                )
                event_type = "ui_combat_ready_triggered"
                event_payload = (
                    ("readied_actor_id", ready.readied_actor_id),
                    ("target_id", ready.target_id),
                    ("trigger", ready.trigger),
                    ("reaction_count", len(reaction_options)),
                )
            else:
                threat_names = ", ".join(
                    threat.attacker.name for threat in movement_threats
                )
                board_message = (
                    f"{enemy.name} opuszcza zasięg: {threat_names}. "
                    "Wybierz atak okazyjny albo pomiń reakcję."
                )
                message_title = "Atak okazyjny"
                message_body = (
                    f"{enemy.name} prowokuje atak okazyjny. "
                    f"Reakcję może wykonać: {threat_names}."
                )
                event_type = "ui_combat_enemy_opportunity_pending"
                event_payload = (
                    ("enemy_id", str(enemy.id)),
                    (
                        "destination",
                        [
                            result.movement_path.destination.col,
                            result.movement_path.destination.row,
                        ],
                    ),
                    ("threat_actor_ids", list(threat_actor_ids)),
                    ("reaction_count", len(reaction_options)),
                )
            return EnemyTurnResolutionTransition(
                result=result,
                kind=EnemyTurnTransitionKind.REACTION,
                reaction_window=reaction_window,
                ready_trigger=ready,
                threat_actor_ids=threat_actor_ids,
                board_message=board_message,
                message_title=message_title,
                message_body=message_body,
                event_type=event_type,
                event_payload=event_payload,
            )
        if _result_has_movement(result, enemy.position):
            destination = result.movement_path.destination
            return EnemyTurnResolutionTransition(
                result=result,
                kind=EnemyTurnTransitionKind.MOVEMENT,
                board_message=(
                    f"{enemy.name} rusza na {destination.as_tuple()}. "
                    "Przestaw figurkę po podświetlonej ścieżce i kliknij pole docelowe."
                ),
                message_title="Ruch przeciwnika",
                message_body=(
                    f"{enemy.name} planuje ruch na {destination.as_tuple()}. "
                    "Potwierdź pole docelowe na planszy."
                ),
            )
        if result.target is not None:
            if result.saving_throw_request is not None:
                request = result.saving_throw_request
                ability_label = request.as_payload()["ability_label"]
                return EnemyTurnResolutionTransition(
                    result=result,
                    kind=EnemyTurnTransitionKind.ATTACK,
                    board_message=(
                        f"{enemy.name} używa {source.name} przeciw {result.target.name}. "
                        "Kliknij podświetlone pole celu, żeby potwierdzić efekt."
                    ),
                    message_title="Efekt przeciwnika",
                    message_body=(
                        f"{enemy.name} używa {source.name} przeciw {result.target.name}. "
                        f"Po potwierdzeniu celu {result.target.name} wykona "
                        f"{ability_label} save przeciw ST {request.dc}."
                    ),
                )
            return EnemyTurnResolutionTransition(
                result=result,
                kind=EnemyTurnTransitionKind.ATTACK,
                board_message=(
                    f"{enemy.name} atakuje {result.target.name}. "
                    "Kliknij podświetlone pole celu, żeby potwierdzić atak."
                ),
                message_title="Atak przeciwnika",
                message_body=(
                    f"{enemy.name} atakuje {result.target.name}. {_enemy_roll_summary(result)} "
                    "Potwierdź atak klikając pole celu."
                ),
            )
        return EnemyTurnResolutionTransition(
            result=result,
            kind=EnemyTurnTransitionKind.FINISHED,
            board_message="",
            message_title="",
            message_body="",
        )

    def resolve_player_saving_throw(
        self,
        *,
        result: EnemyAutoTurnResult,
        natural_roll: int,
        natural_roll_2: int | None = None,
        natural_rerolls: tuple[int, ...] = (),
        additional_modifiers: tuple[RollModifier, ...] = (),
        active_effects: tuple[ActiveCombatEffect, ...] = (),
    ) -> EnemySavingThrowTransition:
        request = result.saving_throw_request
        source = result.source
        if request is None or source is None or result.target is None:
            raise ValueError("Tura przeciwnika nie oczekuje rzutu obronnego gracza.")
        target = next(
            (actor for actor in result.state.actors if str(actor.id) == result.target.id),
            None,
        )
        if target is None:
            raise ValueError("Nie znaleziono celu oczekującego rzutu obronnego.")
        saving_throw = resolve_actor_saving_throw(
            target,
            request,
            natural_roll=int(natural_roll),
            natural_roll_2=natural_roll_2,
            natural_rerolls=natural_rerolls,
            condition_states=result.state.condition_states,
            combat_actors=result.state.actors,
            situational_modifiers=additional_modifiers,
            active_effects=active_effects,
        )
        base_components = result.base_damage_components or (
            DamageComponentInput(
                max(0, int(result.base_damage or 0)),
                DamageType(source.damage_type),
                source.name,
            ),
        )
        base_damage = sum(component.amount for component in base_components)
        damage = resolve_damage(
            tuple(
                DamageComponentInput(
                    apply_save_damage_amount(component.amount, saving_throw),
                    component.damage_type,
                    component.label,
                )
                for component in base_components
            )
        )
        applied = apply_damage_result(
            target,
            damage,
            active_effects=active_effects,
        )
        updated_state = replace_actor(result.state, applied.actor_after)
        condition_message = ""
        if (
            not saving_throw.success
            and source.conditional_on_hit_save_condition is not None
        ):
            condition = apply_condition(
                updated_state.condition_states,
                applied.actor_after,
                CombatCondition(source.conditional_on_hit_save_condition),
                source_actor_id=str(result.enemy.id),
                source_label=source.name,
            )
            updated_state = replace(
                updated_state,
                condition_states=condition.condition_states,
            )
            condition_message = f" {condition.message}"
        outcome = "sukces" if saving_throw.success else "porażka"
        message = (
            f"{target.name}: {request.ability} save d20 {saving_throw.natural_roll}, "
            f"modyfikator {saving_throw.modifier:+d}, razem {saving_throw.total} przeciw "
            f"ST {request.dc}: {outcome}. {applied_damage_message(applied)}"
            f"{condition_message}"
        )
        updated_result = replace(
            result,
            state=updated_state,
            message=f"{result.message} {message}",
            damage=applied.damage,
            applied_damage=applied,
            updated_target=applied.actor_after,
            saving_throw_result=saving_throw,
        )
        return EnemySavingThrowTransition(
            result=updated_result,
            saving_throw=saving_throw,
            board_message="Rzut obronny rozstrzygnięty. Potwierdź wynik tury przeciwnika.",
            message_title="Rzut obronny",
            message_body=message,
            event_type="ui_combat_enemy_saving_throw",
            event_payload=(
                ("enemy_id", str(result.enemy.id)),
                ("target_id", str(target.id)),
                ("source_id", source.id),
                ("saving_throw", saving_throw.as_payload()),
                ("base_damage", base_damage),
                ("damage_result", applied_damage_payload(applied)),
            ),
        )


def _enemy_attack_source(
    state: CombatState,
    enemy: Actor,
    attack_sources_by_actor: Mapping[ActorId, AttackSource],
    multiattack_sources_by_actor: Mapping[ActorId, tuple[AttackSource, ...]] | None,
) -> AttackSource | None:
    sequence = (
        multiattack_sources_by_actor.get(enemy.id, ())
        if multiattack_sources_by_actor is not None
        else ()
    )
    if not sequence:
        return attack_sources_by_actor.get(enemy.id)
    used = state.turn_action.attacks_used if state.turn_action.attack_action_active else 0
    return sequence[min(used, len(sequence) - 1)]


def _reaction_window_trigger(
    ready_attacks: tuple[ReadyAttackTrigger, ...],
    movement_threats: tuple[OpportunityAttackThreat, ...],
) -> str:
    if ready_attacks and movement_threats:
        return "enemy_action"
    if ready_attacks:
        return ready_attacks[0].trigger
    return "enemy_leaves_reach"


def _active_enemy(state: CombatState) -> Actor:
    if state.status != CombatStatus.ACTIVE:
        raise ValueError("Walka nie jest aktywna.")
    enemy = current_actor(state)
    if enemy.faction != Faction.ENEMY:
        raise ValueError("To nie jest tura przeciwnika.")
    return enemy


def _result_has_movement(result: EnemyAutoTurnResult, origin: Coordinate) -> bool:
    return bool(
        result.movement_path is not None
        and result.movement_path.valid
        and result.movement_path.destination != origin
    )


def _ready_trigger_label(trigger: str) -> str:
    return {
        "enemy_moves": "gdy przeciwnik się poruszy",
        "enemy_attacks": "gdy przeciwnik zaatakuje",
        "giant_killer": "po ataku Dużej lub większej istoty",
    }.get(trigger, trigger)


def _giant_killer_reactions(
    *,
    state: CombatState,
    enemy_result: EnemyAutoTurnResult,
    board: BoardState,
    attack_sources_by_actor: Mapping[ActorId, AttackSource],
) -> tuple[ReadyAttackTrigger, ...]:
    if (
        enemy_result.attack_resolution is None
        or enemy_result.target is None
        or enemy_result.enemy.size.value
        not in {"large", "huge", "gargantuan"}
    ):
        return ()
    ranger = next(
        (
            actor
            for actor in state.actors
            if str(actor.id) == enemy_result.target.id
        ),
        None,
    )
    if (
        ranger is None
        or not actor_has_feature(ranger, "giant_killer")
        or not reaction_available_for(state, ranger)
        or grid_distance_feet(ranger.position, enemy_result.enemy.position) > 5
    ):
        return ()
    source = attack_sources_by_actor.get(ranger.id)
    if source is None:
        return ()
    legal = start_attack_action(
        board,
        ranger,
        enemy_result.state.actors,
        source,
        enemy_result.state.hidden_states,
    ).legal_targets
    if not any(target.id == str(enemy_result.enemy.id) for target in legal):
        return ()
    return (
        ReadyAttackTrigger(
            readied_actor_id=str(ranger.id),
            target_id=str(enemy_result.enemy.id),
            effect_id="giant_killer",
            trigger="giant_killer",
        ),
    )


def _enemy_roll_summary(result: EnemyAutoTurnResult) -> str:
    if result.saving_throw_result is not None:
        save = result.saving_throw_result
        outcome = "sukces" if save.success else "porażka"
        parts = [
            f"Rzut obronny d20: {save.natural_roll}",
            f"modyfikator: {save.modifier:+d}",
            f"wynik końcowy: {save.total} przeciw ST {save.dc}: {outcome}",
        ]
        if result.damage is not None:
            parts.append(f"obrażenia: {result.damage.total_applied}")
        return ". ".join(parts) + "."
    if result.attack_roll is None or result.target is None:
        return ""
    natural_rolls = result.attack_roll.natural_rolls
    roll_text = (
        f"{' / '.join(str(value) for value in natural_rolls)} -> {result.attack_roll.natural_roll}"
        if len(natural_rolls) > 1
        else str(result.attack_roll.natural_roll)
    )
    parts = [f"Rzut d20: {roll_text}", f"wynik końcowy: {result.attack_roll.total}"]
    if result.attack_resolution is not None:
        parts.append("trafienie" if result.attack_resolution.hit else "pudło")
        if result.attack_resolution.critical:
            parts.append("krytyk")
    if result.damage is not None:
        parts.append(f"obrażenia: {result.damage.total_applied}")
    if result.applied_damage is not None:
        parts.append(
            f"HP celu: {result.applied_damage.hp_before} -> {result.applied_damage.hp_after}"
        )
        if result.applied_damage.defeated_by_damage:
            parts.append("cel pokonany")
    return ". ".join(parts) + "."


def enemy_turn_message(result: EnemyAutoTurnResult) -> str:
    summary = _enemy_roll_summary(result)
    if not summary:
        return result.message
    return f"{result.message} {summary}"
