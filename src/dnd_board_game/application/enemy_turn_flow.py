from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from random import Random
from typing import Mapping

from dnd_board_game.actors import Actor, ActorId, Faction, actor_has_feature
from dnd_board_game.combat import (
    ActiveCombatEffect,
    AttackSource,
    AttackSourceType,
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
    actor_as_combat_target,
    attack_source_with_target_combat_effects,
    current_actor,
    opportunity_attackers_for_movement,
    open_reaction_window,
    plan_enemy_turn,
    plan_coordinated_pack_turn,
    plan_utility_enemy_turn,
    resolve_planned_enemy_turn,
    resolve_actor_saving_throw,
    resolve_damage,
    replace_actor,
    redirect_guarded_single_target,
    reaction_available_for,
    start_attack_action,
    grid_distance_feet,
    is_hidden_from,
    legal_attack_targets,
    movement_remaining,
    path_with_condition_cost,
    reveal_to_observer,
    use_movement,
    use_turn_action,
)
from dnd_board_game.rules import (
    RollModifier,
    RollModifierType,
    SavingThrowRequest,
    SavingThrowResult,
)
from dnd_board_game.world import BoardState, Coordinate, PathResult, movement_range

from dnd_board_game.combat.stealth import actors_visible_for_pathfinding

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
    active_effects: tuple[ActiveCombatEffect, ...] | None = None


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
        attack_source_options_by_actor: Mapping[ActorId, tuple[AttackSource, ...]] | None = None,
        multiattack_sources_by_actor: Mapping[ActorId, tuple[AttackSource, ...]] | None = None,
        scene_objects: tuple[SceneObject, ...] = (),
        ai_profile: EnemyAiProfile | None = None,
        ai_roles: Mapping[str, str] | None = None,
        ai_zone_positions: Mapping[str, tuple[Coordinate, ...]] | None = None,
        active_effects: tuple[ActiveCombatEffect, ...] = (),
    ) -> EnemyTurnIntentTransition:
        enemy = _active_enemy(state)
        role_by_actor = dict(ai_roles or {})
        zones = dict(ai_zone_positions or {})
        hazard_positions = (
            zones.get(ai_profile.hazard_zone_tag, ())
            if ai_profile is not None
            else ()
        )
        state, enemy, command_path, command_message = _apply_stage_command_movement(
            board,
            state,
            enemy,
            active_effects,
            hazard_positions=hazard_positions,
        )
        source = _enemy_attack_source(
            state,
            enemy,
            attack_sources_by_actor,
            multiattack_sources_by_actor,
        )
        role_id = role_by_actor.get(str(enemy.id), "")
        source_options = (
            tuple(attack_source_options_by_actor.get(enemy.id, ()))
            if attack_source_options_by_actor is not None
            else ()
        ) or (source,)
        if _stage_command_variant(active_effects, str(enemy.id)) == "silence":
            source_options = tuple(
                option
                for option in source_options
                if option is not None
                and option.source_type != AttackSourceType.SPELL
            )
            if source is not None and source.source_type == AttackSourceType.SPELL:
                source = source_options[0] if source_options else None
        if source is None:
            action = use_turn_action(state)
            message = (
                f"{command_message}{enemy.name} jest objęty rozkazem Milcz i nie ma "
                "dostępnego ataku niewymagającego mowy."
            )
            intent = EnemyTurnPlan(
                action.state,
                enemy,
                None,
                message,
                action_used=action.accepted,
                intent="stage_command_silence",
            )
            return _intent_transition(intent, enemy)
        intent = (
            plan_coordinated_pack_turn(
                board,
                state,
                enemy,
                source_options,
                role_id=role_id,
                actor_roles=role_by_actor,
                escape_positions=zones.get(ai_profile.escape_zone_tag, ()),
            )
            if ai_profile is not None
            and ai_profile.model == "coordinated_pack_v1"
            and role_id
            and "leader" in role_by_actor.values()
            else
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
        if not intent.source_id and source.id:
            intent = replace(intent, source_id=source.id)
        if command_message:
            intent = replace(
                intent,
                movement_path=(
                    _combined_movement_path(command_path, intent.movement_path)
                    if command_path is not None
                    else intent.movement_path
                ),
                moved_enemy=(intent.enemy if command_path is not None else intent.moved_enemy),
                message=f"{command_message}{intent.message}",
            )
        intent = _prefer_provoked_lorian_target(
            board,
            intent,
            source,
            active_effects,
        )
        return _intent_transition(intent, enemy)

    def resolve(
        self,
        *,
        state: CombatState,
        intent: EnemyTurnPlan,
        board: BoardState,
        attack_sources_by_actor: Mapping[ActorId, AttackSource],
        attack_source_options_by_actor: Mapping[ActorId, tuple[AttackSource, ...]] | None = None,
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
        if intent.source_id and attack_source_options_by_actor is not None:
            source = next(
                (
                    option
                    for option in attack_source_options_by_actor.get(enemy.id, ())
                    if option.id == intent.source_id
                ),
                source,
            )
        if intent.pack_attack_bonus > 0:
            bonus = intent.pack_attack_bonus
            source = replace(
                source,
                attack_roll_request=replace(
                    source.attack_roll_request,
                    modifiers=(
                        *source.attack_roll_request.modifiers,
                        RollModifier(
                            "Premia stada",
                            bonus,
                            RollModifierType.FEATURE,
                            stacking_key="hungry_shadow_pack_bonus",
                        ),
                    ),
                ),
                damage_components=tuple(
                    replace(component, modifier=component.modifier + bonus)
                    for component in source.damage_components
                ),
                damage_modifier=source.damage_modifier + bonus,
            )
        target_actor = None
        intercepted_target = None
        interception_message = ''
        if intent.target is not None:
            target_actor = next(
                (actor for actor in state.actors if str(actor.id) == intent.target.id),
                None,
            )
        if target_actor is not None:
            if source.area is None and source.save_ability is None:
                guard = redirect_guarded_single_target(
                    state,
                    active_effects,
                    str(target_actor.id),
                )
                active_effects = guard.active_effects
                if guard.redirected:
                    protected_name = target_actor.name
                    target_actor = guard.target
                    intent = replace(
                        intent,
                        target=actor_as_combat_target(
                            target_actor,
                            active_effects,
                            attacker=enemy,
                            actors=state.actors,
                        ),
                        message=(
                            f"Osłona towarzysza przekierowuje efekt na "
                            f"{target_actor.name}."
                        ),
                    )
                    intercepted_target = intent.target
                    interception_message = f'{enemy.name} atakował {protected_name}. {target_actor.name} przejmuje ten atak; używamy KP obrońcy. '
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
        result = _accidental_hidden_collision(
            state,
            intent,
            enemy,
            board,
            active_effects,
        )
        if result is None:
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
                intercepted_target=intercepted_target,
            )
        if interception_message:
            result = replace(result, message=interception_message + result.message)
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
                active_effects=active_effects,
            )
        if result.accidentally_detected_actor_id is not None:
            detected = next(
                actor
                for actor in state.actors
                if str(actor.id) == result.accidentally_detected_actor_id
            )
            stealth_continues = any(
                hidden.actor_id == str(detected.id)
                for hidden in result.state.hidden_states
            )
            detection_consequence = (
                "Dopóki trwa ta sesja skradania, ma przewagę w atakach przeciw niej."
                if stealth_continues
                else "Był ostatnim niewidzącym jej wrogiem, więc skradanie automatycznie się kończy."
            )
            return EnemyTurnResolutionTransition(
                result=result,
                kind=EnemyTurnTransitionKind.MOVEMENT,
                board_message=(
                    f"{enemy.name} wpada na ślad {detected.name}. Przestaw figurkę "
                    f"na {result.movement_path.destination.as_tuple()} i potwierdź pole."
                ),
                message_title="Przypadkowe wykrycie",
                message_body=(
                    f"{enemy.name} zatrzymuje się przed zajętym polem i wykrywa {detected.name}. "
                    f"{detection_consequence} "
                    "Po Enterze ponownie zaplanuje pozostałą część tury."
                ),
                event_type="ui_combat_hidden_actor_path_collision",
                event_payload=(
                    ("enemy_id", str(enemy.id)),
                    ("detected_actor_id", str(detected.id)),
                ),
                active_effects=active_effects,
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
                active_effects=active_effects,
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
                    active_effects=active_effects,
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
                active_effects=active_effects,
            )
        return EnemyTurnResolutionTransition(
            result=result,
            kind=EnemyTurnTransitionKind.FINISHED,
            board_message="",
            message_title="",
            message_body="",
            active_effects=active_effects,
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


def _accidental_hidden_collision(
    state: CombatState,
    intent: EnemyTurnPlan,
    enemy: Actor,
    board: BoardState,
    active_effects: tuple[ActiveCombatEffect, ...],
) -> EnemyAutoTurnResult | None:
    path = intent.movement_path
    if path is None or not path.valid or len(path.path) < 2:
        return None
    hidden_by_position = {
        actor.position: actor
        for actor in state.actors
        if is_hidden_from(state.hidden_states, str(actor.id), str(enemy.id))
        and not actor.is_defeated()
    }
    collision_index = next(
        (index for index, tile in enumerate(path.path[1:], 1) if tile in hidden_by_position),
        None,
    )
    if collision_index is None:
        return None
    hidden_actor = hidden_by_position[path.path[collision_index]]
    prefix = path.path[:collision_index]
    destination = prefix[-1]
    base_cost = sum(
        10 if board.terrain_at(tile).is_difficult else 5
        for tile in prefix[1:]
    )
    stopped_path = path_with_condition_cost(
        PathResult(enemy.position, destination, prefix, base_cost, True),
        state.condition_states,
        str(enemy.id),
        movement_budget_feet=movement_remaining(state, enemy, active_effects),
    )
    moved_state = state
    moved_enemy = enemy
    if stopped_path.cost_feet > 0:
        movement = use_movement(state, enemy, stopped_path, active_effects)
        if not movement.accepted:
            return None
        moved_state = movement.state
        moved_enemy = next(actor for actor in moved_state.actors if actor.id == enemy.id)
    moved_state = replace(
        moved_state,
        hidden_states=reveal_to_observer(
            moved_state.hidden_states,
            str(hidden_actor.id),
            str(enemy.id),
        ),
    )
    return EnemyAutoTurnResult(
        state=moved_state,
        enemy=enemy,
        target=None,
        message=f"{enemy.name} przypadkiem wykrywa {hidden_actor.name}.",
        movement_path=stopped_path,
        moved_enemy=moved_enemy,
        source=None,
        intent="accidental_detection",
        accidentally_detected_actor_id=str(hidden_actor.id),
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


def _stage_command_variant(
    active_effects: tuple[ActiveCombatEffect, ...],
    actor_id: str,
) -> str:
    prefix = "stage_command:"
    effect = next(
        (
            effect
            for effect in active_effects
            if effect.actor_id == actor_id and effect.kind.startswith(prefix)
        ),
        None,
    )
    return effect.kind.removeprefix(prefix) if effect is not None else ""


def _apply_stage_command_movement(
    board: BoardState,
    state: CombatState,
    enemy: Actor,
    active_effects: tuple[ActiveCombatEffect, ...],
    *,
    hazard_positions: tuple[Coordinate, ...],
) -> tuple[CombatState, Actor, PathResult | None, str]:
    """Apply the bounded movement part of Lorian's command before normal AI."""

    variant = _stage_command_variant(active_effects, str(enemy.id))
    if variant not in {"approach", "retreat"}:
        return state, enemy, None, ""
    effect = next(
        effect
        for effect in active_effects
        if effect.actor_id == str(enemy.id)
        and effect.kind == f"stage_command:{variant}"
    )
    commander = next(
        (
            actor
            for actor in state.actors
            if str(actor.id) == effect.source_actor_id and not actor.is_defeated()
        ),
        None,
    )
    if commander is None:
        return (
            state,
            enemy,
            None,
            f"Rozkaz sceniczny ({variant}) nie może poruszyć {enemy.name}: brak źródła rozkazu. ",
        )
    budget = min(15, movement_remaining(state, enemy, active_effects))
    if budget < 5:
        return (
            state,
            enemy,
            None,
            f"Rozkaz sceniczny nie może poruszyć {enemy.name}: brak dostępnego ruchu. ",
        )
    movement_actor = replace(enemy, speed_feet=budget)
    movement = movement_range(
        board,
        movement_actor,
        actors_visible_for_pathfinding(
            state.actors,
            state.hidden_states,
            str(enemy.id),
        ),
    )
    hazards = set(hazard_positions)
    candidates = tuple(
        position
        for position in movement.reachable_tiles
        if position != enemy.position
        and position not in hazards
        and not any(tile in hazards for tile in movement.paths_by_tile[position])
    )
    if not candidates:
        return (
            state,
            enemy,
            None,
            f"Rozkaz sceniczny nie znajduje bezpiecznego pola dla {enemy.name}. ",
        )
    distance = lambda position: max(  # noqa: E731 - compact deterministic key
        abs(position.col - commander.position.col),
        abs(position.row - commander.position.row),
    )
    current_distance = distance(enemy.position)
    directional = tuple(
        position
        for position in candidates
        if (
            distance(position) < current_distance
            if variant == "approach"
            else distance(position) > current_distance
        )
    )
    if not directional:
        return (
            state,
            enemy,
            None,
            f"{enemy.name} nie może bezpiecznie wykonać rozkazu scenicznego. ",
        )
    destination = (
        min(
            directional,
            key=lambda position: (
                distance(position),
                -movement.costs_by_tile[position],
                position.col,
                position.row,
            ),
        )
        if variant == "approach"
        else max(
            directional,
            key=lambda position: (
                distance(position),
                movement.costs_by_tile[position],
                -position.col,
                -position.row,
            ),
        )
    )
    path = PathResult(
        enemy.position,
        destination,
        movement.paths_by_tile[destination],
        movement.costs_by_tile[destination],
        True,
    )
    path = path_with_condition_cost(
        path,
        state.condition_states,
        str(enemy.id),
        movement_budget_feet=budget,
    )
    moved = use_movement(state, enemy, path, active_effects)
    if not moved.accepted:
        return (
            state,
            enemy,
            None,
            f"{enemy.name} nie może wykonać wymuszonego ruchu: {moved.message} ",
        )
    moved_enemy = next(actor for actor in moved.state.actors if actor.id == enemy.id)
    label = "podchodzi" if variant == "approach" else "oddala się"
    return (
        moved.state,
        moved_enemy,
        path,
        f"Rozkaz sceniczny: {enemy.name} {label} o {path.cost_feet} stóp. ",
    )


def _combined_movement_path(
    first: PathResult,
    second: PathResult | None,
) -> PathResult:
    if second is None:
        return first
    suffix = second.path[1:] if second.path and second.path[0] == first.destination else second.path
    return PathResult(
        first.origin,
        second.destination,
        (*first.path, *suffix),
        first.cost_feet + second.cost_feet,
        first.valid and second.valid,
    )


def _prefer_provoked_lorian_target(
    board: BoardState,
    intent: EnemyTurnPlan,
    source: AttackSource,
    active_effects: tuple[ActiveCombatEffect, ...],
) -> EnemyTurnPlan:
    provoked = any(
        effect.actor_id == str(intent.enemy.id)
        and effect.kind == "lorian_provoked"
        for effect in active_effects
    )
    if not provoked:
        return intent
    legal = legal_attack_targets(
        board,
        intent.enemy,
        intent.state.actors,
        source,
        intent.state.hidden_states,
        active_effects,
    )
    lorian = next((target for target in legal if target.id == "lorian"), None)
    if lorian is None or (intent.target is not None and intent.target.id == "lorian"):
        return intent
    return replace(
        intent,
        target=lorian,
        message=f"{intent.message} Prowokujący ostrzał kieruje atak na Loriena.",
    )


def _intent_transition(intent: EnemyTurnPlan, enemy: Actor) -> EnemyTurnIntentTransition:
    return EnemyTurnIntentTransition(
        intent=intent,
        enemy_id=str(enemy.id),
        board_message=intent.message,
        message_title="Zamiar przeciwnika",
        message_body=intent.message,
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
