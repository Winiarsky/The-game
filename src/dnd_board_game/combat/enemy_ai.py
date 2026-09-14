from __future__ import annotations

import random
from dataclasses import dataclass, replace

from dnd_board_game.actors import (
    Actor,
    Faction,
    can_spend_actor_resource,
    skill_roll_modifiers,
    spend_actor_resource,
)
from dnd_board_game.rules import (
    ActiveEffect,
    D20RollInput,
    D20RollRequest,
    D20RollResult,
    RollMode,
    SaveDamageOnSuccess,
    SavingThrowRequest,
    SavingThrowResult,
    resolve_d20_roll,
)
from dnd_board_game.world import BoardState, PathResult, movement_range
from dnd_board_game.inventory import consume_ammunition, has_ammunition

from .action_economy import ActionUse
from .archetype_flaws import attack_source_with_exposed_mira_bonus
from .targets import mira_ranged_armor_class_bonus
from .attack_flow import (
    AttackDeclaration,
    AttackResolution,
    AttackSource,
    AttackSourceType,
    legal_attack_targets,
    legal_melee_targets,
    resolve_attack,
)
from .attack_positioning import AttackPositioning, attack_source_with_positioning, evaluate_attack_positioning
from .conditions import (
    CombatCondition,
    apply_condition,
    attack_source_with_prone,
    condition_roll_request,
    condition_hit_is_automatic_critical,
    has_condition,
    path_with_condition_cost,
)
from .scene import SceneObject
from .scene_interactions import MirrorImageOutcome, resolve_mirror_image_redirect
from .spells import resolve_actor_saving_throw
from .stealth import (
    actors_visible_for_pathfinding,
    is_hidden_from,
    resolve_search,
    reveal_actor,
)
from .damage import (
    AppliedDamageResult,
    DamageComponentInput,
    DamageResult,
    DamageType,
    apply_damage_result,
    resolve_damage,
    roll_damage_components,
)
from .session import (
    CombatState,
    expend_thrown_weapon,
    movement_remaining,
    record_ammunition_expenditure,
    replace_actor,
    stand_up,
    use_attack_action,
    use_dash,
    use_movement,
    use_turn_action,
)
from .targets import CombatTarget


@dataclass(frozen=True, slots=True)
class EnemyAutoAttackResult:
    state: CombatState
    enemy: Actor
    target: CombatTarget | None
    message: str
    attack_roll: D20RollResult | None = None
    attack_resolution: AttackResolution | None = None
    damage: DamageResult | None = None
    applied_damage: AppliedDamageResult | None = None
    updated_target: Actor | None = None
    action_used: bool = False
    positioning: AttackPositioning = AttackPositioning()
    source: AttackSource | None = None
    saving_throw_request: SavingThrowRequest | None = None
    saving_throw_result: SavingThrowResult | None = None
    base_damage: int | None = None
    base_damage_components: tuple[DamageComponentInput, ...] = ()
    mirror_image_outcome: MirrorImageOutcome | None = None
    sanctuary_saves: tuple[SavingThrowResult, ...] = ()


@dataclass(frozen=True, slots=True)
class EnemyAutoTurnResult:
    state: CombatState
    enemy: Actor
    target: CombatTarget | None
    message: str
    movement_path: PathResult | None = None
    moved_enemy: Actor | None = None
    attack_roll: D20RollResult | None = None
    attack_resolution: AttackResolution | None = None
    damage: DamageResult | None = None
    applied_damage: AppliedDamageResult | None = None
    updated_target: Actor | None = None
    action_used: bool = False
    positioning: AttackPositioning = AttackPositioning()
    source: AttackSource | None = None
    saving_throw_request: SavingThrowRequest | None = None
    saving_throw_result: SavingThrowResult | None = None
    base_damage: int | None = None
    base_damage_components: tuple[DamageComponentInput, ...] = ()
    spell_countered: bool = False
    counterspell_actor_id: str | None = None
    mirror_image_outcome: MirrorImageOutcome | None = None
    sanctuary_saves: tuple[SavingThrowResult, ...] = ()
    intent: str = "fallback"
    utility_score: float | None = None
    utility_breakdown: tuple[tuple[str, float], ...] = ()
    escaped: bool = False
    pack_heal_target_id: str | None = None
    pack_heal_amount: int = 0
    life_drain: bool = False
    accidentally_detected_actor_id: str | None = None


@dataclass(frozen=True, slots=True)
class EnemyTurnPlan:
    state: CombatState
    enemy: Actor
    target: CombatTarget | None
    message: str
    movement_path: PathResult | None = None
    moved_enemy: Actor | None = None
    action_used: bool = False
    intent: str = "fallback"
    utility_score: float | None = None
    utility_breakdown: tuple[tuple[str, float], ...] = ()
    escaped: bool = False
    source_id: str = ""
    pack_attack_bonus: int = 0
    pack_heal_target_id: str | None = None
    escape_target: Coordinate | None = None
    life_drain: bool = False


def resolve_enemy_auto_attack(
    board: BoardState,
    state: CombatState,
    enemy: Actor,
    source: AttackSource,
    rng: random.Random,
    scene_objects: tuple[SceneObject, ...] = (),
    active_effects: tuple[ActiveEffect, ...] = (),
    *,
    maximum_attacks: int | None = None,
    preferred_target_id: str | None = None,
    intercepted_target: CombatTarget | None = None,
) -> EnemyAutoAttackResult:
    enemy = _actor_for_id(state, enemy.id)
    if source.resource_pool_id is not None and not can_spend_actor_resource(
        enemy,
        source.resource_pool_id,
        source.resource_cost,
    ):
        return EnemyAutoAttackResult(
            state,
            enemy,
            None,
            f"{source.name} nie jest jeszcze dostępne — oczekuje na recharge.",
            action_used=False,
            source=source,
        )
    if source.ammunition_type is not None and not has_ammunition(
        enemy,
        source.ammunition_type,
    ):
        return EnemyAutoAttackResult(
            state,
            enemy,
            None,
            f"{enemy.name} nie ma amunicji typu {source.ammunition_type} dla {source.name}.",
            action_used=False,
            source=source,
        )
    if source.thrown and source.source_item_id is not None and not any(
        item.available
        and (
            item.id == source.source_item_id
            or item.source_ref == source.source_item_id
        )
        for item in enemy.inventory
    ):
        return EnemyAutoAttackResult(
            state,
            enemy,
            None,
            f"{enemy.name} nie ma już dostępnej broni {source.name} do rzutu.",
            action_used=False,
            source=source,
        )
    action_result = use_attack_action(
        state,
        enemy,
        maximum_attacks=1
        if source.loading or source.limited_attacks
        else maximum_attacks,
    )
    if not action_result.accepted:
        return EnemyAutoAttackResult(action_result.state, enemy, None, action_result.message, action_used=False)
    if source.resource_pool_id is not None:
        usage = spend_actor_resource(
            _actor_for_id(action_result.state, enemy.id),
            source.resource_pool_id,
            source.resource_cost,
        )
        action_result = replace(
            action_result,
            state=replace_actor(action_result.state, usage.actor_after),
        )
        enemy = usage.actor_after

    targets = legal_attack_targets(
        board,
        enemy,
        action_result.state.actors,
        source,
        action_result.state.hidden_states,
        active_effects,
    )
    # A validated interception replaces this one declared attack even when
    # the protector stands beyond the attacker's normal reach.
    if intercepted_target is not None:
        targets = (intercepted_target,)
    if not targets:
        return EnemyAutoAttackResult(
            action_result.state,
            enemy,
            None,
            f"{enemy.name} nie ma legalnego celu ataku i kończy akcję.",
            action_used=True,
        )

    target = next(
        (candidate for candidate in targets if candidate.id == preferred_target_id),
        None,
    ) or _select_enemy_target(enemy, targets)
    sanctuary_saves: list[SavingThrowResult] = []
    remaining_targets = tuple(targets)
    while True:
        sanctuary = next(
            (
                effect
                for effect in active_effects
                if effect.actor_id == target.id
                and effect.kind == "sanctuary"
            ),
            None,
        )
        if sanctuary is None:
            break
        caster = next(
            (
                actor
                for actor in action_result.state.actors
                if str(actor.id) == sanctuary.source_actor_id
            ),
            _actor_for_target(action_result.state, target),
        )
        save = resolve_actor_saving_throw(
            enemy,
            SavingThrowRequest(
                "wisdom",
                caster.spell_save_dc,
                "Sanktuarium",
                SaveDamageOnSuccess.NONE,
                dc_source_label=f"ST czarów: {caster.name}",
            ),
            natural_roll=rng.randint(1, 20),
            condition_states=action_result.state.condition_states,
            combat_actors=action_result.state.actors,
        )
        sanctuary_saves.append(save)
        if save.success:
            break
        remaining_targets = tuple(
            candidate
            for candidate in remaining_targets
            if candidate.id != target.id
        )
        if not remaining_targets:
            return EnemyAutoAttackResult(
                state=action_result.state,
                enemy=enemy,
                target=target,
                message=(
                    f"{enemy.name} nie przełamuje Sanktuarium {target.name} "
                    f"(Wis {save.total} przeciw ST {save.dc}) i traci atak, "
                    "bo nie ma innego legalnego celu."
                ),
                action_used=True,
                source=source,
                sanctuary_saves=tuple(sanctuary_saves),
            )
        target = _select_enemy_target(enemy, remaining_targets)
    if source.ammunition_type is not None:
        usage = consume_ammunition(
            _actor_for_id(action_result.state, enemy.id),
            source.ammunition_type,
        )
        recorded_state = record_ammunition_expenditure(
            action_result.state,
            enemy,
            usage,
        )
        action_result = replace(
            action_result,
            state=replace_actor(recorded_state, usage.actor_after),
        )
        enemy = usage.actor_after
    target_actor = _actor_for_target(action_result.state, target)
    if source.thrown and source.source_item_id is not None:
        thrown_state = expend_thrown_weapon(
            action_result.state,
            str(enemy.id),
            source.source_item_id,
            target.position,
        )
        action_result = replace(action_result, state=thrown_state)
        enemy = _actor_for_id(thrown_state, enemy.id)
    positioning = evaluate_attack_positioning(
        board,
        enemy,
        target_actor,
        source,
        action_result.state.actors,
        scene_objects,
        action_result.state.condition_states,
    )
    source = attack_source_with_positioning(source, positioning)
    source = attack_source_with_prone(
        source,
        action_result.state.condition_states,
        enemy,
        target_actor,
    )
    source = attack_source_with_exposed_mira_bonus(
        action_result.state.hidden_states,
        enemy,
        target_actor,
        source,
    )
    target = replace(
        target,
        ac=(
            target.ac
            + positioning.cover_bonus
            + mira_ranged_armor_class_bonus(target_actor, source)
        ),
    )
    if source.save_ability is not None:
        dc = int(source.save_dc or enemy.spell_save_dc)
        if dc <= 0:
            raise ValueError(f"Atak {source.name} wymaga dodatniego ST rzutu obronnego.")
        base_damage_components = roll_damage_components(
            source.damage_components,
            lambda sides: rng.randint(1, sides),
        )
        base_damage = sum(component.amount for component in base_damage_components)
        saving_throw_request = SavingThrowRequest(
            ability=source.save_ability,
            dc=dc,
            source_label=source.name,
            dc_source_label=f"ST efektu: {source.name}",
            damage_on_success=SaveDamageOnSuccess(source.save_damage_on_success),
            effect_tags=(
                (DamageType.POISON.value,)
                if source.damage_type == DamageType.POISON.value
                else ()
            ),
        )
        updated_state = replace(
            action_result.state,
            hidden_states=reveal_actor(action_result.state.hidden_states, str(enemy.id)),
        )
        return EnemyAutoAttackResult(
            state=updated_state,
            enemy=enemy,
            target=target,
            message=(
                f"{enemy.name} używa {source.name} przeciwko {target.name}. "
                f"Cel wykonuje {source.save_ability} save przeciw ST {dc}."
            ),
            action_used=True,
            positioning=positioning,
            source=source,
            saving_throw_request=saving_throw_request,
            base_damage=base_damage,
            base_damage_components=base_damage_components,
        )
    attack_roll = resolve_d20_roll(_roll_input_for_request(source.attack_roll_request, rng))
    has_mirror_image = any(
        effect.actor_id == str(target_actor.id)
        and effect.kind == "mirror_image"
        and effect.value > 0
        for effect in active_effects
    )
    mirror_outcome = (
        resolve_mirror_image_redirect(
            target_actor,
            attack_total=attack_roll.total,
            active_effects=active_effects,
            redirect_roll=rng.randint(1, 20),
        )
        if has_mirror_image
        else None
    )
    attack_target = (
        replace(target, ac=mirror_outcome.duplicate_ac)
        if mirror_outcome is not None and mirror_outcome.redirected
        else target
    )
    declaration = AttackDeclaration(attacker=enemy, target=attack_target, source=source)
    resolution = resolve_attack(declaration, attack_roll, ActionUse.ACTION_AVAILABLE)
    duplicate_was_hit = bool(
        mirror_outcome is not None
        and mirror_outcome.redirected
        and resolution.hit
    )
    if mirror_outcome is not None and mirror_outcome.redirected:
        mirror_outcome = replace(
            mirror_outcome,
            duplicate_hit=duplicate_was_hit,
            duplicates_after=(
                mirror_outcome.duplicates_before - 1
                if duplicate_was_hit
                else mirror_outcome.duplicates_before
            ),
        )
        resolution = replace(resolution, hit=False, critical=False)
    if resolution.hit and condition_hit_is_automatic_critical(
        action_result.state.condition_states,
        str(target_actor.id),
        within_five_feet=(
            max(
                abs(enemy.position.col - target_actor.position.col),
                abs(enemy.position.row - target_actor.position.row),
            )
            <= 1
        ),
    ):
        resolution = replace(resolution, critical=True)
    updated_state = action_result.state
    damage: DamageResult | None = None
    applied_damage: AppliedDamageResult | None = None
    updated_target: Actor | None = None

    if resolution.hit:
        if source.on_hit_condition is not None:
            if (
                source.weapon_special_rule is not None
                and source.weapon_special_rule.value == "net"
                and target_actor.size.value in {"large", "huge", "gargantuan"}
            ):
                message = (
                    f"{enemy.name} trafia {target.name}, ale cel jest zbyt duży dla sieci."
                )
            else:
                application = apply_condition(
                    action_result.state.condition_states,
                    target_actor,
                    CombatCondition(source.on_hit_condition),
                    source_actor_id=str(enemy.id),
                    source_label=source.name,
                    duration=source.on_hit_condition_duration,
                    expiration_actor_id=(
                        str(enemy.id)
                        if source.on_hit_condition_expiration == "source"
                        else str(target_actor.id)
                    ),
                    source_spell_id=(
                        source.id if source.source_type == AttackSourceType.SPELL else None
                    ),
                    source_spell_level=(
                        source.spell_level
                        if source.source_type == AttackSourceType.SPELL
                        else None
                    ),
                )
                updated_state = replace(
                    action_result.state,
                    condition_states=application.condition_states,
                )
                message = (
                    f"{enemy.name} trafia {target.name}. Wynik ataku: {attack_roll.total}. "
                    f"{application.message}"
                )
        if source.on_hit_condition is None or any(
            component.dice is not None
            or int(component.fixed or 0) + component.modifier > 0
            for component in source.damage_components
        ):
            rolled_components = roll_damage_components(
                    source.damage_components,
                    lambda sides: rng.randint(1, sides),
                    critical=resolution.critical,
                )
            if source.damage_divisor > 1:
                rolled_components = tuple(
                    replace(
                        component,
                        amount=component.amount // source.damage_divisor,
                    )
                    for component in rolled_components
                )
            damage = resolve_damage(
                rolled_components
            )
            applied_damage = apply_damage_result(
                target_actor,
                damage,
                critical=resolution.critical,
                active_effects=active_effects,
                combat_actors=updated_state.actors,
            )
            damage = applied_damage.damage
            updated_target = applied_damage.actor_after
            updated_state = replace_actor(updated_state, updated_target)
            from .warding_bond import transfer_warding_bond_damage

            transfer = transfer_warding_bond_damage(
                updated_state,
                protected_actor=target_actor,
                damage_amount=applied_damage.damage.total_applied,
                active_effects=active_effects,
            )
            updated_state = transfer.state
            defeated_text = " Cel zostaje pokonany." if applied_damage.defeated_by_damage else ""
            damage_message = (
                f"Obrażenia: {_damage_result_text(damage)}. "
                f"{target_actor.name}: HP {applied_damage.hp_before} -> {applied_damage.hp_after}.{defeated_text}"
            )
            message = (
                f"{message} {damage_message}"
                if source.on_hit_condition is not None
                else (
                    f"{enemy.name} trafia {target.name}. Wynik ataku: {attack_roll.total}. "
                    f"{damage_message}"
                )
            )
            if transfer.source_damage is not None:
                message += (
                    " Więź ochronna przekazuje rzucającemu "
                    f"{transfer.source_damage.damage.total_applied} obrażeń."
                )
    else:
        message = f"{enemy.name} pudłuje przeciwko {target.name}. Wynik ataku: {attack_roll.total}."
    if mirror_outcome is not None:
        if mirror_outcome.redirected and duplicate_was_hit:
            message = (
                f"{enemy.name} atakuje {target.name}. Lustrzane odbicia: "
                f"k20 {mirror_outcome.redirect_roll}; atak trafia KP "
                f"{mirror_outcome.duplicate_ac} i niszczy duplikat "
                f"({mirror_outcome.duplicates_after} pozostało)."
            )
        elif mirror_outcome.redirected:
            message = (
                f"{enemy.name} atakuje {target.name}. Lustrzane odbicia: "
                f"k20 {mirror_outcome.redirect_roll}; atak zostaje "
                f"przekierowany, ale nie trafia KP {mirror_outcome.duplicate_ac}."
            )
        else:
            message += (
                f" Lustrzane odbicia: k20 {mirror_outcome.redirect_roll}; "
                "atak nie został przekierowany."
            )
    if sanctuary_saves:
        successful = sanctuary_saves[-1]
        message = (
            f"Sanktuarium: {enemy.name} uzyskuje Wis {successful.total} "
            f"przeciw ST {successful.dc}. {message}"
        )

    updated_state = replace(
        updated_state,
        hidden_states=reveal_actor(updated_state.hidden_states, str(enemy.id)),
    )
    return EnemyAutoAttackResult(
        state=updated_state,
        enemy=enemy,
        target=target,
        message=message,
        attack_roll=attack_roll,
        attack_resolution=resolution,
        damage=damage,
        applied_damage=applied_damage,
        updated_target=updated_target,
        action_used=True,
        positioning=positioning,
        source=source,
        mirror_image_outcome=mirror_outcome,
        sanctuary_saves=tuple(sanctuary_saves),
    )


def _roll_input_for_request(request, rng: random.Random) -> D20RollInput:
    first = rng.randint(1, 20)
    second = rng.randint(1, 20) if request.mode != RollMode.NORMAL else None
    original = (first,) if second is None else (first, second)
    rerolls = (
        tuple(rng.randint(1, 20) for value in original if value == 1)
        if request.reroll_natural_ones
        else ()
    )
    return D20RollInput(request, first, second, rerolls)


def resolve_enemy_auto_turn(
    board: BoardState,
    state: CombatState,
    enemy: Actor,
    source: AttackSource,
    rng: random.Random,
    scene_objects: tuple[SceneObject, ...] = (),
    active_effects: tuple[ActiveEffect, ...] = (),
    *,
    maximum_attacks: int | None = None,
) -> EnemyAutoTurnResult:
    plan = plan_enemy_turn(board, state, enemy, source)
    return resolve_planned_enemy_turn(
        board,
        plan,
        source,
        rng,
        scene_objects,
        active_effects,
        maximum_attacks=maximum_attacks,
        original_state=state,
    )


def resolve_planned_enemy_turn(
    board: BoardState,
    plan: EnemyTurnPlan,
    source: AttackSource,
    rng: random.Random,
    scene_objects: tuple[SceneObject, ...] = (),
    active_effects: tuple[ActiveEffect, ...] = (),
    *,
    maximum_attacks: int | None = None,
    original_state: CombatState | None = None,
    intercepted_target: CombatTarget | None = None,
) -> EnemyAutoTurnResult:
    enemy = plan.enemy
    state = plan.state
    original_state = original_state or state
    original_enemy = next(
        (actor for actor in original_state.actors if actor.id == enemy.id),
        enemy,
    )
    stood_up = (
        has_condition(
            original_state.condition_states,
            str(original_enemy.id),
            CombatCondition.PRONE,
        )
        and not has_condition(plan.state.condition_states, str(enemy.id), CombatCondition.PRONE)
    )
    movement_message = (
        f"{enemy.name} wstaje, wydając połowę szybkości. "
        if stood_up
        else ""
    )
    if plan.target is None:
        if plan.intent in {"flee", "regroup", "guard", "cornered"}:
            return EnemyAutoTurnResult(
                plan.state,
                plan.enemy,
                None,
                plan.message,
                movement_path=plan.movement_path,
                moved_enemy=plan.moved_enemy,
                action_used=plan.action_used,
                intent=plan.intent,
                utility_score=plan.utility_score,
                utility_breakdown=plan.utility_breakdown,
                escaped=plan.escaped,
            )
        if plan.movement_path is not None:
            follow_up = resolve_enemy_auto_attack(
                board,
                plan.state,
                plan.enemy,
                source,
                rng,
                scene_objects,
                active_effects,
                maximum_attacks=maximum_attacks,
            )
            return EnemyAutoTurnResult(
                follow_up.state,
                plan.enemy,
                None,
                plan.message,
                movement_path=plan.movement_path,
                moved_enemy=plan.moved_enemy,
                action_used=follow_up.action_used,
                positioning=follow_up.positioning,
            )
        hidden_opponents = tuple(
            actor
            for actor in plan.state.actors
            if actor.faction not in {enemy.faction, Faction.NEUTRAL}
            and not actor.is_defeated()
            and is_hidden_from(plan.state.hidden_states, str(actor.id), str(enemy.id))
        )
        if hidden_opponents and not plan.action_used:
            action = use_turn_action(plan.state)
            perception = resolve_d20_roll(
                D20RollInput(
                    condition_roll_request(
                        D20RollRequest(modifiers=skill_roll_modifiers(enemy, "perception")),
                        action.state.condition_states,
                        enemy,
                        ability_check=True,
                    ),
                    rng.randint(1, 20),
                )
            )
            search = resolve_search(action.state.hidden_states, enemy, perception.total)
            found_names = ", ".join(
                actor.name
                for actor in hidden_opponents
                if str(actor.id) in search.found_actor_ids
            )
            message = (
                f"{enemy.name} używa Search ({perception.total}) i odnajduje: {found_names}."
                if found_names
                else f"{enemy.name} używa Search ({perception.total}), ale nikogo nie odnajduje."
            )
            return EnemyAutoTurnResult(
                replace(action.state, hidden_states=search.hidden_states),
                enemy,
                None,
                message,
                action_used=action.accepted,
            )
        return EnemyAutoTurnResult(
            plan.state,
            plan.enemy,
            None,
            plan.message,
            movement_path=plan.movement_path,
            moved_enemy=plan.moved_enemy,
            action_used=plan.action_used,
        )
    attack = resolve_enemy_auto_attack(
        board,
        plan.state,
        plan.enemy,
        source,
        rng,
        scene_objects,
        active_effects,
        maximum_attacks=maximum_attacks,
        preferred_target_id=plan.target.id,
        intercepted_target=intercepted_target,
    )
    if plan.movement_path is None:
        return replace(
            _turn_result_from_attack(attack),
            intent=plan.intent,
            utility_score=plan.utility_score,
            utility_breakdown=plan.utility_breakdown,
            pack_heal_target_id=plan.pack_heal_target_id,
            pack_heal_amount=(rng.randint(1, 6) + 2 if plan.pack_heal_target_id else 0),
            life_drain=plan.life_drain,
        )
    if attack.target is None:
        return EnemyAutoTurnResult(
            attack.state,
            plan.enemy,
            None,
            f"{movement_message}{_enemy_movement_message(enemy, plan.movement_path)} Po ruchu nadal nie ma legalnego celu ataku.",
            movement_path=plan.movement_path,
            moved_enemy=plan.moved_enemy,
            action_used=attack.action_used,
        )
    result = EnemyAutoTurnResult(
        state=attack.state,
        enemy=plan.enemy,
        target=attack.target,
        message=f"{movement_message}{_enemy_movement_message(enemy, plan.movement_path)} {attack.message}",
        movement_path=plan.movement_path,
        moved_enemy=plan.moved_enemy,
        attack_roll=attack.attack_roll,
        attack_resolution=attack.attack_resolution,
        damage=attack.damage,
        applied_damage=attack.applied_damage,
        updated_target=attack.updated_target,
        action_used=attack.action_used,
        positioning=attack.positioning,
        source=attack.source,
        saving_throw_request=attack.saving_throw_request,
        saving_throw_result=attack.saving_throw_result,
        base_damage=attack.base_damage,
        base_damage_components=attack.base_damage_components,
        mirror_image_outcome=attack.mirror_image_outcome,
        sanctuary_saves=attack.sanctuary_saves,
        intent=plan.intent,
        utility_score=plan.utility_score,
        utility_breakdown=plan.utility_breakdown,
        pack_heal_target_id=plan.pack_heal_target_id,
        pack_heal_amount=(rng.randint(1, 6) + 2 if plan.pack_heal_target_id else 0),
        life_drain=plan.life_drain,
    )
    return _with_conditional_on_hit_save(result, plan, source)


def _with_conditional_on_hit_save(
    result: EnemyAutoTurnResult,
    plan: EnemyTurnPlan,
    source: AttackSource,
) -> EnemyAutoTurnResult:
    ability = source.conditional_on_hit_save_ability
    condition = source.conditional_on_hit_save_condition
    if (
        ability is None
        or condition is None
        or result.attack_resolution is None
        or not result.attack_resolution.hit
        or result.target is None
        or plan.movement_path is None
        or plan.movement_path.cost_feet
        < source.conditional_on_hit_minimum_movement_feet
    ):
        return result
    if source.conditional_on_hit_requires_adjacent_ally:
        target_position = result.target.position
        has_pack_ally = any(
            actor.id != plan.enemy.id
            and actor.faction == plan.enemy.faction
            and not actor.is_defeated()
            and max(
                abs(actor.position.col - target_position.col),
                abs(actor.position.row - target_position.row),
            ) <= 1
            for actor in result.state.actors
        )
        if not has_pack_ally:
            return result
    request = SavingThrowRequest(
        ability=ability,
        dc=source.conditional_on_hit_save_dc,
        source_label=source.name,
        dc_source_label=f"ST efektu: {source.name}",
        damage_on_success=SaveDamageOnSuccess.NONE,
    )
    return replace(
        result,
        saving_throw_request=request,
        base_damage=0,
        base_damage_components=(),
        message=(
            f"{result.message} Skok stada: cel wykonuje {ability} save "
            f"przeciw ST {request.dc}."
        ),
    )


def plan_enemy_turn(
    board: BoardState,
    state: CombatState,
    enemy: Actor,
    source: AttackSource | None = None,
) -> EnemyTurnPlan:
    turned = next(
        (
            condition
            for condition in state.condition_states
            if condition.actor_id == str(enemy.id)
            and condition.condition == CombatCondition.TURNED
        ),
        None,
    )
    if turned is not None:
        return _plan_turned_enemy_turn(board, state, enemy, turned.source_actor_id)
    opening_message = ""
    if has_condition(state.condition_states, str(enemy.id), CombatCondition.PRONE):
        standing = stand_up(state, enemy)
        if standing.accepted:
            state = standing.state
            enemy = _actor_for_id(state, enemy.id)
            opening_message = f"{standing.message} "
    targets = (
        legal_attack_targets(board, enemy, state.actors, source, state.hidden_states)
        if source is not None
        else legal_melee_targets(board, enemy, state.actors, state.hidden_states)
    )
    if targets:
        target = _select_enemy_target(enemy, targets)
        return EnemyTurnPlan(state, enemy, target, f"{opening_message}{enemy.name} atakuje {target.name}.")

    movement_path = _best_enemy_movement_path(board, state, enemy, source)
    if movement_path is not None and movement_path.valid and movement_path.destination != enemy.position:
        movement = use_movement(state, enemy, movement_path)
        moved_state = movement.state
        moved_enemy = _actor_for_id(moved_state, enemy.id)
        moved_targets = (
            legal_attack_targets(
                board, moved_enemy, moved_state.actors, source, moved_state.hidden_states
            )
            if source is not None
            else legal_melee_targets(
                board, moved_enemy, moved_state.actors, moved_state.hidden_states
            )
        )
        target = _select_enemy_target(moved_enemy, moved_targets) if moved_targets else None
        message = f"{opening_message}{_enemy_movement_message(enemy, movement_path)}"
        if target is not None:
            message = f"{message} Po ruchu atakuje {target.name}."
        else:
            message = f"{message} Po ruchu nadal nie ma legalnego celu ataku."
        return EnemyTurnPlan(
            moved_state,
            moved_enemy,
            target,
            message,
            movement_path=movement_path,
            moved_enemy=moved_enemy,
        )

    has_hidden_opponent = any(
        actor.faction not in {enemy.faction, Faction.NEUTRAL}
        and not actor.is_defeated()
        and is_hidden_from(state.hidden_states, str(actor.id), str(enemy.id))
        for actor in state.actors
    )
    if has_hidden_opponent:
        return EnemyTurnPlan(
            state,
            enemy,
            None,
            f"{opening_message}{enemy.name} nie widzi celu i zamierza użyć Search.",
            action_used=False,
        )
    action_result = use_turn_action(state)
    return EnemyTurnPlan(
        action_result.state,
        enemy,
        None,
        f"{opening_message}{enemy.name} nie ma legalnego celu ani dostępnego ruchu i kończy akcję.",
        action_used=action_result.accepted,
    )


def _plan_turned_enemy_turn(
    board: BoardState,
    state: CombatState,
    enemy: Actor,
    source_actor_id: str | None,
) -> EnemyTurnPlan:
    source = next(
        (actor for actor in state.actors if str(actor.id) == source_actor_id),
        None,
    )
    if source is None:
        action = use_turn_action(state)
        return EnemyTurnPlan(
            action.state,
            enemy,
            None,
            f"{enemy.name} jest odpędzony i używa Dodge.",
            action_used=action.accepted,
        )
    dash = use_dash(state, enemy)
    if not dash.accepted:
        return EnemyTurnPlan(
            dash.state,
            enemy,
            None,
            f"{enemy.name} jest odpędzony, ale nie może użyć Dash.",
        )
    budget = movement_remaining(dash.state, enemy)
    movement_actor = replace(enemy, speed_feet=budget)
    movement = movement_range(
        board,
        movement_actor,
        actors_visible_for_pathfinding(
            dash.state.actors,
            dash.state.hidden_states,
            str(enemy.id),
        ),
    )
    destinations = tuple(
        destination
        for destination in movement.reachable_tiles
        if destination != enemy.position
    )
    if not destinations:
        return EnemyTurnPlan(
            dash.state,
            enemy,
            None,
            f"{enemy.name} jest odpędzony, nie może się oddalić i używa Dodge.",
            action_used=True,
        )
    destination = max(
        destinations,
        key=lambda position: (
            max(
                abs(position.col - source.position.col),
                abs(position.row - source.position.row),
            ),
            movement.costs_by_tile.get(position, 0),
            position.col,
            position.row,
        ),
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
        dash.state.condition_states,
        str(enemy.id),
        movement_budget_feet=budget,
    )
    moved = use_movement(dash.state, enemy, path)
    moved_enemy = _actor_for_id(moved.state, enemy.id)
    return EnemyTurnPlan(
        moved.state,
        moved_enemy,
        None,
        f"{enemy.name} jest odpędzony, używa Dash i oddala się od {source.name}.",
        movement_path=path,
        moved_enemy=moved_enemy,
        action_used=True,
    )


def _actor_for_target(state: CombatState, target: CombatTarget) -> Actor:
    for actor in state.actors:
        if str(actor.id) == target.id:
            return actor
    raise ValueError(f"Unknown target actor: {target.id}.")


def _actor_for_id(state: CombatState, actor_id) -> Actor:
    for actor in state.actors:
        if actor.id == actor_id:
            return actor
    raise ValueError(f"Unknown actor: {actor_id}.")


def _select_enemy_target(enemy: Actor, targets: tuple[CombatTarget, ...]) -> CombatTarget:
    return min(
        targets,
        key=lambda target: (
            max(abs(enemy.position.col - target.position.col), abs(enemy.position.row - target.position.row)),
            target.position.col,
            target.position.row,
            target.id,
        ),
    )


def _best_enemy_movement_path(
    board: BoardState,
    state: CombatState,
    enemy: Actor,
    source: AttackSource | None = None,
) -> PathResult | None:
    budget = movement_remaining(state, enemy)
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
    opponents = tuple(
        actor
        for actor in state.actors
        if actor.faction not in {enemy.faction, Faction.NEUTRAL}
        and not actor.is_defeated()
        and not is_hidden_from(state.hidden_states, str(actor.id), str(enemy.id))
    )
    if not opponents:
        return None
    best_path: PathResult | None = None
    best_key: tuple[int, int, int, int, str] | None = None
    for destination in movement.reachable_tiles:
        if destination == enemy.position:
            continue
        candidate_enemy = replace(enemy, position=destination)
        candidate_actors = tuple(candidate_enemy if actor.id == enemy.id else actor for actor in state.actors)
        candidate_targets = (
            legal_attack_targets(
                board,
                candidate_enemy,
                candidate_actors,
                source,
                state.hidden_states,
            )
            if source is not None
            else legal_melee_targets(
                board,
                candidate_enemy,
                candidate_actors,
                state.hidden_states,
            )
        )
        can_attack_after_move = 0 if candidate_targets else 1
        distance_to_opponent = min(
            (
                max(abs(destination.col - opponent.position.col), abs(destination.row - opponent.position.row))
                for opponent in opponents
            ),
            default=999,
        )
        # ``movement_range`` has already solved every reachable path.  Calling
        # ``find_path`` here used to recompute the complete range once per
        # candidate tile, making a single AI turn take several seconds.
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
        if not path.valid:
            continue
        key = (can_attack_after_move, path.cost_feet, distance_to_opponent, destination.col, destination.row)
        if best_key is None or key < best_key:
            best_key = key
            best_path = path
    return best_path


def _enemy_movement_message(enemy: Actor, movement_path: PathResult) -> str:
    return f"{enemy.name} rusza się na {movement_path.destination.as_tuple()}."


def _turn_result_from_attack(result: EnemyAutoAttackResult) -> EnemyAutoTurnResult:
    return EnemyAutoTurnResult(
        state=result.state,
        enemy=result.enemy,
        target=result.target,
        message=result.message,
        attack_roll=result.attack_roll,
        attack_resolution=result.attack_resolution,
        damage=result.damage,
        applied_damage=result.applied_damage,
        updated_target=result.updated_target,
        action_used=result.action_used,
        positioning=result.positioning,
        source=result.source,
        saving_throw_request=result.saving_throw_request,
        saving_throw_result=result.saving_throw_result,
        base_damage=result.base_damage,
        base_damage_components=result.base_damage_components,
        mirror_image_outcome=result.mirror_image_outcome,
        sanctuary_saves=result.sanctuary_saves,
    )


def _damage_result_text(damage: DamageResult) -> str:
    parts = []
    for component in damage.resolved_components:
        amount = (
            f"{component.amount_before} -> {component.amount_applied}"
            if component.changed
            else str(component.amount_applied)
        )
        parts.append(f"{amount} {component.damage_type.value}")
    return ", ".join(parts) + f"; razem {damage.total_applied}"
