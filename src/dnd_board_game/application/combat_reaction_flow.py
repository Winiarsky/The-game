from __future__ import annotations

from dataclasses import dataclass, replace
from dnd_board_game.actors.resources import uses_physical_mana, uses_shared_mana
from typing import Callable, Mapping, Protocol, Sequence

from dnd_board_game.actors import (
    Actor,
    ActorId,
    ability_roll_modifier,
    actor_has_feature,
    can_spend_actor_resource,
    spend_actor_resource,
)
from dnd_board_game.combat import (
    ActionUse,
    ActiveCombatEffect,
    AppliedDamageResult,
    AttackKind,
    AttackDeclaration,
    AttackSource,
    AttackSourceType,
    CombatState,
    CombatStatus,
    ConditionState,
    CombatResolutionStage,
    DamageComponentInput,
    DamageResult,
    DamageType,
    EnemyAutoTurnResult,
    ReactionKind,
    ReactionOption,
    apply_damage_result,
    attack_source_with_exposed_mira_bonus,
    advance_reaction_window,
    attack_source_with_target_combat_effects,
    attack_source_with_hidden_advantage,
    attack_source_with_prone,
    actor_as_combat_target,
    actor_spell_cast_validation,
    consume_spell_resource,
    consume_next_attack_effects,
    damage_components_from_totals,
    expend_thrown_weapon,
    grid_distance_feet,
    replace_actor,
    record_ammunition_expenditure,
    reveal_actor,
    is_hidden_from,
    open_reaction_window,
    resolve_attack,
    resolve_damage,
    roll_damage_components,
    reaction_available_for,
    start_attack_action,
    use_actor_reaction,
    use_movement,
    bardic_inspiration_die_sides,
    deflect_missiles,
    deflected_missile_attack_source,
)
from dnd_board_game.rules import (
    EffectDuration,
    D20RollInput,
    D20RollRequest,
    D20RollResult,
    EffectEvent,
    EffectEventType,
    EffectSource,
    EffectSourceType,
    RollMode,
    RollModifier,
    RollModifierType,
    expire_active_effects,
    apply_active_effect,
    resolve_d20_roll,
)
from dnd_board_game.inventory import (
    consume_ammunition,
    free_hand_count,
    has_ammunition,
)
from dnd_board_game.world import BoardState, PathResult, line_of_sight_clear
from dnd_board_game.combat.lorian_features import require_lorian_audience

from .damage_presentation import applied_damage_message


@dataclass(frozen=True, slots=True)
class CombatReactionResolution:
    state: CombatState
    active_effects: tuple[ActiveCombatEffect, ...]
    applied_damages: tuple[AppliedDamageResult, ...]
    movement_performed: bool
    message_title: str
    message_body: str


@dataclass(frozen=True, slots=True)
class PlayerReactionAttackResolution:
    state: CombatState
    active_effects: tuple[ActiveCombatEffect, ...]
    source: AttackSource
    attack_roll: D20RollResult
    hit: bool
    critical: bool
    message: str


@dataclass(frozen=True, slots=True)
class PlayerReactionDamageResolution:
    state: CombatState
    applied_damage: AppliedDamageResult
    target_id: str


@dataclass(frozen=True, slots=True)
class ReadyAttackTrigger:
    readied_actor_id: str
    target_id: str
    effect_id: str
    trigger: str


class DefensiveSpellActionSpec(Protocol):
    id: str
    label: str
    action_type: str
    value: int
    spell_level: int


@dataclass(frozen=True, slots=True)
class DefensiveSpellReactionResolution:
    state: CombatState
    active_effects: tuple[ActiveCombatEffect, ...]
    result: EnemyAutoTurnResult
    effect: ActiveCombatEffect
    prevented_hit: bool
    message: str


class DefensiveSpellReactionFlowService:
    """Offer and resolve a self-only AC reaction after a known attack roll."""

    def option(
        self,
        *,
        state: CombatState,
        enemy_result: EnemyAutoTurnResult,
        actions_by_actor: Mapping[ActorId, tuple[DefensiveSpellActionSpec, ...]],
    ) -> ReactionOption | None:
        resolution = enemy_result.attack_resolution
        target = enemy_result.target
        if (
            resolution is None
            or target is None
            or not resolution.hit
            or resolution.critical
        ):
            return None
        actor = next(
            (candidate for candidate in state.actors if str(candidate.id) == target.id),
            None,
        )
        if (
            actor is None
            or actor.is_defeated()
            or not reaction_available_for(state, actor)
        ):
            return None
        action = next(
            (
                candidate
                for candidate in actions_by_actor.get(actor.id, ())
                if candidate.action_type == "reaction_ac_bonus"
                and candidate.value > 0
                and _spell_action_is_available(
                    actor,
                    candidate,
                    condition_states=state.condition_states,
                )
            ),
            None,
        )
        if action is None:
            return None
        return ReactionOption(
            id=f"defensive-spell:{actor.id}:{action.id}",
            kind=ReactionKind.DEFENSIVE_SPELL,
            reactor_actor_id=str(actor.id),
            target_actor_id=str(enemy_result.enemy.id),
            trigger_event="actor_hit_by_attack",
            effect_id=action.id,
            label=action.label,
            value=action.value,
            spell_level=action.spell_level,
        )

    def cast(
        self,
        *,
        state: CombatState,
        enemy_result: EnemyAutoTurnResult,
        active_effects: tuple[ActiveCombatEffect, ...],
        option: ReactionOption,
        actions_by_actor: Mapping[ActorId, tuple[DefensiveSpellActionSpec, ...]],
    ) -> DefensiveSpellReactionResolution:
        if option.kind != ReactionKind.DEFENSIVE_SPELL or option.effect_id is None:
            raise ValueError("Aktualna reakcja nie jest czarem obronnym.")
        target = _actor_by_string_id(state, option.reactor_actor_id)
        action = next(
            (
                candidate
                for candidate in actions_by_actor.get(target.id, ())
                if candidate.id == option.effect_id
                and candidate.action_type == "reaction_ac_bonus"
            ),
            None,
        )
        if action is None:
            raise ValueError("Czar obronny nie jest dostępny dla tego aktora.")
        if enemy_result.attack_resolution is None or enemy_result.attack_roll is None:
            raise ValueError("Brak oczekującego rzutu ataku dla reakcji obronnej.")
        if enemy_result.target is None or enemy_result.target.id != str(target.id):
            raise ValueError("Oczekujący atak nie jest wymierzony w tego aktora.")

        if uses_physical_mana(target) and action.id == "shield":
            action = replace(action, value=3)
        reaction = use_actor_reaction(state, target)
        if not reaction.accepted:
            raise ValueError(reaction.message)
        target_with_reaction = _actor_by_string_id(reaction.state, str(target.id))
        spell_use = consume_spell_resource(
            target_with_reaction,
            action.spell_level,
            spell_id=action.id,
        )
        target_after_cast = spell_use.actor_after
        reaction_state = replace_actor(reaction.state, target_after_cast)

        effect = ActiveCombatEffect(
            id=f"spell-ac:{target.id}:{action.id}",
            actor_id=str(target.id),
            kind="spell_ac_bonus",
            label=action.label,
            object_id=f"spell:{action.id}",
            value=action.value,
            source_actor_id=str(target.id),
            source=EffectSource(EffectSourceType.SPELL, action.id, action.label),
            duration=EffectDuration.UNTIL_TURN_START,
            expiration_actor_id=str(target.id),
            stacking_key=f"spell_ac_bonus:{target.id}",
            spell_level=action.spell_level,
        )
        updated_effects = (active_effects if uses_physical_mana(target) and action.id == "shield"
                           else apply_active_effect(active_effects, effect).active_effects)

        target_snapshot = replace(
            enemy_result.target,
            ac=enemy_result.target.ac + action.value,
        )
        declaration = replace(
            enemy_result.attack_resolution.declaration,
            target=target_snapshot,
        )
        updated_attack = resolve_attack(
            declaration,
            enemy_result.attack_roll,
            ActionUse.ACTION_AVAILABLE,
        )

        merged_state = replace(
            enemy_result.state,
            spent_reaction_actor_ids=reaction_state.spent_reaction_actor_ids,
            condition_states=(
                enemy_result.state.condition_states
                if updated_attack.hit
                else state.condition_states
            ),
        )
        merged_state = replace_actor(merged_state, target_after_cast)
        applied_damage = None
        updated_target = None
        damage = enemy_result.damage if updated_attack.hit else None
        if updated_attack.hit and damage is not None:
            applied_damage = apply_damage_result(
                target_after_cast,
                damage,
                critical=updated_attack.critical,
            )
            updated_target = applied_damage.actor_after
            merged_state = replace_actor(merged_state, updated_target)

        prevented_hit = not updated_attack.hit
        message = (
            f"{target.name} rzuca {action.label}: AC rośnie do {target_snapshot.ac}. "
            + (
                f"Wynik ataku {enemy_result.attack_roll.total} staje się pudłem."
                if prevented_hit
                else f"Wynik ataku {enemy_result.attack_roll.total} nadal trafia."
            )
        )
        updated_result = replace(
            enemy_result,
            state=merged_state,
            target=target_snapshot,
            attack_resolution=updated_attack,
            damage=damage,
            applied_damage=applied_damage,
            updated_target=updated_target,
            message=message,
        )
        return DefensiveSpellReactionResolution(
            state=reaction_state,
            active_effects=updated_effects,
            result=updated_result,
            effect=effect,
            prevented_hit=prevented_hit,
            message=message,
        )


@dataclass(frozen=True, slots=True)
class CuttingWordsReactionResolution:
    state: CombatState
    result: EnemyAutoTurnResult
    die_roll: int
    previous_attack_total: int
    attack_total: int
    prevented_hit: bool
    message: str
    resolution_stage: str = "attack_roll_revealed"
    previous_damage_total: int | None = None
    damage_total: int | None = None


@dataclass(frozen=True, slots=True)
class DistractingShoutReactionResolution:
    state: CombatState
    result: EnemyAutoTurnResult
    die_roll: int
    reduction: int
    damage_before: int
    damage_after: int
    message: str


@dataclass(frozen=True, slots=True)
class DeflectMissilesReactionResolution:
    state: CombatState
    result: EnemyAutoTurnResult
    die_roll: int
    reduction: int
    damage_before: int
    damage_after: int
    caught: bool
    can_return_projectile: bool
    message: str


@dataclass(frozen=True, slots=True)
class DeflectedMissileReturnResolution:
    state: CombatState
    source: AttackSource
    attack_roll: D20RollResult
    hit: bool
    critical: bool
    message: str


class ClassFeatureReactionFlowService:
    """Resolve level 1–3 class reactions against an automated enemy attack."""

    def cutting_words_options(
        self,
        *,
        board: BoardState,
        state: CombatState,
        enemy_result: EnemyAutoTurnResult,
    ) -> tuple[ReactionOption, ...]:
        resolution = enemy_result.attack_resolution
        attack_roll = enemy_result.attack_roll
        if (
            resolution is None
            or attack_roll is None
            or not resolution.hit
            or resolution.critical
        ):
            return ()
        enemy = _actor_by_string_id(enemy_result.state, str(enemy_result.enemy.id))
        return tuple(
            ReactionOption(
                id=f"cutting-words:{actor.id}:{enemy.id}",
                kind=ReactionKind.CUTTING_WORDS,
                reactor_actor_id=str(actor.id),
                target_actor_id=str(enemy.id),
                trigger_event=CombatResolutionStage.ATTACK_ROLL_REVEALED.value,
                effect_id="cutting_words",
                label="Cutting Words",
                value=bardic_inspiration_die_sides(actor),
            )
            for actor in state.actors
            if not uses_shared_mana(actor)
            and actor.faction != enemy.faction
            and not actor.is_defeated()
            and actor_has_feature(actor, "cutting_words")
            and _lorian_audience_available(
                actor,
                state.actors,
                "cutting_words",
                condition_states=state.condition_states,
            )
            and reaction_available_for(state, actor)
            and grid_distance_feet(actor.position, enemy.position) <= 60
            and line_of_sight_clear(board, actor.position, enemy.position)
        )

    def distracting_shout_options(
        self,
        *,
        board: BoardState,
        state: CombatState,
        active_effects: tuple[ActiveCombatEffect, ...],
        enemy_result: EnemyAutoTurnResult,
    ) -> tuple[ReactionOption, ...]:
        """Offer the shout only for direct attack damage to an inspired ally."""

        target = enemy_result.target
        if (
            target is None
            or enemy_result.damage is None
            or enemy_result.damage.total_before_reduction <= 0
            or enemy_result.attack_resolution is None
            or not enemy_result.attack_resolution.hit
        ):
            return ()
        target_actor = _actor_by_string_id(state, target.id)
        enemy = _actor_by_string_id(state, str(enemy_result.enemy.id))
        return tuple(
            ReactionOption(
                id=f"distracting-shout:{bard.id}:{target_actor.id}",
                kind=ReactionKind.DISTRACTING_SHOUT,
                reactor_actor_id=str(bard.id),
                target_actor_id=str(target_actor.id),
                trigger_event=CombatResolutionStage.DAMAGE_ROLL_REVEALED.value,
                effect_id="distracting_shout",
                label="Rozpraszający okrzyk",
                value=6,
            )
            for bard in state.actors
            if bard.faction == target_actor.faction
            and bard.id != target_actor.id
            and not bard.is_defeated()
            and actor_has_feature(bard, "distracting_shout")
            and _lorian_audience_available(
                bard,
                state.actors,
                "distracting_shout",
                condition_states=state.condition_states,
            )
            and reaction_available_for(state, bard)
            and grid_distance_feet(bard.position, target_actor.position) <= 60
            and line_of_sight_clear(board, bard.position, enemy.position)
            and any(
                effect.actor_id == str(target_actor.id)
                and effect.kind == "bardic_inspiration"
                and effect.source_actor_id == str(bard.id)
                for effect in active_effects
            )
        )

    def apply_distracting_shout(
        self,
        *,
        state: CombatState,
        enemy_result: EnemyAutoTurnResult,
        option: ReactionOption,
        die_roll: int,
    ) -> DistractingShoutReactionResolution:
        if option.kind != ReactionKind.DISTRACTING_SHOUT:
            raise ValueError("Aktualna reakcja nie jest Rozpraszającym okrzykiem.")
        if not 1 <= int(die_roll) <= 6:
            raise ValueError("Rozpraszający okrzyk wymaga wyniku k6 od 1 do 6.")
        if (
            enemy_result.damage is None
            or enemy_result.target is None
            or enemy_result.attack_resolution is None
            or not enemy_result.attack_resolution.hit
        ):
            raise ValueError("Brak trafionego ataku z oczekującymi obrażeniami.")
        bard = _actor_by_string_id(state, option.reactor_actor_id)
        if not actor_has_feature(bard, "distracting_shout"):
            raise ValueError("Aktor nie posiada Rozpraszającego okrzyku.")
        require_lorian_audience(
            bard,
            state.actors,
            "distracting_shout",
            condition_states=state.condition_states,
        )
        reaction = use_actor_reaction(state, bard)
        if not reaction.accepted:
            raise ValueError(reaction.message)

        reduction = int(die_roll) + 2
        previous_damage = enemy_result.damage.total_before_reduction
        reduced_damage = _damage_after_flat_reduction(
            enemy_result.damage,
            reduction,
        )
        target_before = _actor_by_string_id(
            reaction.state,
            enemy_result.target.id,
        )
        applied = apply_damage_result(
            target_before,
            reduced_damage,
            critical=enemy_result.attack_resolution.critical,
        )
        merged_state = replace(
            enemy_result.state,
            spent_reaction_actor_ids=reaction.state.spent_reaction_actor_ids,
        )
        merged_state = replace_actor(merged_state, applied.actor_after)
        updated_result = replace(
            enemy_result,
            state=merged_state,
            damage=reduced_damage,
            applied_damage=applied,
            updated_target=applied.actor_after,
        )
        message = (
            f"{bard.name} używa Rozpraszającego okrzyku (k6: {die_roll}): "
            f"obrażenia {previous_damage} spadają do "
            f"{reduced_damage.total_before_reduction}."
        )
        updated_result = replace(updated_result, message=message)
        return DistractingShoutReactionResolution(
            state=reaction.state,
            result=updated_result,
            die_roll=int(die_roll),
            reduction=reduction,
            damage_before=previous_damage,
            damage_after=reduced_damage.total_before_reduction,
            message=message,
        )

    def cutting_words_damage_options(
        self,
        *,
        board: BoardState,
        state: CombatState,
        enemy_result: EnemyAutoTurnResult,
    ) -> tuple[ReactionOption, ...]:
        if (
            enemy_result.damage is None
            or enemy_result.target is None
            or enemy_result.damage.total_before_reduction <= 0
        ):
            return ()
        enemy = _actor_by_string_id(enemy_result.state, str(enemy_result.enemy.id))
        return tuple(
            ReactionOption(
                id=f"cutting-words-damage:{actor.id}:{enemy.id}",
                kind=ReactionKind.CUTTING_WORDS,
                reactor_actor_id=str(actor.id),
                target_actor_id=str(enemy.id),
                trigger_event=CombatResolutionStage.DAMAGE_ROLL_REVEALED.value,
                effect_id="cutting_words",
                label="Cutting Words",
                value=6 if uses_shared_mana(actor) else bardic_inspiration_die_sides(actor),
            )
            for actor in state.actors
            if actor.faction != enemy.faction
            and not actor.is_defeated()
            and actor_has_feature(actor, "cutting_words")
            and _lorian_audience_available(
                actor,
                state.actors,
                "cutting_words",
                condition_states=state.condition_states,
            )
            and reaction_available_for(state, actor)
            and grid_distance_feet(actor.position, enemy_result.target.position if uses_shared_mana(actor) else enemy.position) <= (30 if uses_shared_mana(actor) else 60)
            and line_of_sight_clear(board, actor.position, enemy_result.target.position if uses_shared_mana(actor) else enemy.position)
        )

    def apply_cutting_words(
        self,
        *,
        state: CombatState,
        enemy_result: EnemyAutoTurnResult,
        option: ReactionOption,
        die_roll: int,
    ) -> CuttingWordsReactionResolution:
        if option.kind != ReactionKind.CUTTING_WORDS:
            raise ValueError("Aktualna reakcja nie jest Cutting Words.")
        bard = _actor_by_string_id(state, option.reactor_actor_id)
        if not actor_has_feature(bard, "cutting_words"):
            raise ValueError("Aktor nie posiada Cutting Words.")
        require_lorian_audience(
            bard,
            state.actors,
            "cutting_words",
            condition_states=state.condition_states,
        )
        die_sides = 6 if uses_shared_mana(bard) else bardic_inspiration_die_sides(bard)
        if not 1 <= int(die_roll) <= die_sides:
            raise ValueError(f"Cutting Words wymaga wyniku k{die_sides} od 1 do {die_sides}.")
        if (
            enemy_result.attack_resolution is None
            or enemy_result.attack_roll is None
            or enemy_result.target is None
        ):
            raise ValueError("Brak oczekującego wrogiego rzutu ataku.")

        reaction = use_actor_reaction(state, bard)
        if not reaction.accepted:
            raise ValueError(reaction.message)
        reaction_state = reaction.state

        if option.trigger_event == CombatResolutionStage.DAMAGE_ROLL_REVEALED.value:
            if enemy_result.damage is None or enemy_result.target is None:
                raise ValueError("Brak oczekujących obrażeń przeciwnika.")
            previous_damage = enemy_result.damage.total_before_reduction
            reduced_damage = _damage_after_flat_reduction(
                enemy_result.damage,
                int(die_roll) + (ability_roll_modifier(bard, "charisma").value if uses_shared_mana(bard) else 0),
            )
            target_before = _actor_by_string_id(
                reaction_state,
                enemy_result.target.id,
            )
            applied_damage = apply_damage_result(
                target_before,
                reduced_damage,
                critical=bool(
                    enemy_result.attack_resolution
                    and enemy_result.attack_resolution.critical
                ),
            )
            merged_state = replace(
                enemy_result.state,
                spent_reaction_actor_ids=reaction_state.spent_reaction_actor_ids,
                shared_mana=reaction_state.shared_mana,
            )
            merged_state = replace_actor(merged_state, applied_damage.actor_after)
            message = (
                f"{bard.name} używa Cutting Words (k{die_sides}: {die_roll}): "
                f"obrażenia {previous_damage} spadają do "
                f"{reduced_damage.total_before_reduction}."
            )
            updated_result = replace(
                enemy_result,
                state=merged_state,
                damage=reduced_damage,
                applied_damage=applied_damage,
                updated_target=applied_damage.actor_after,
                message=message,
            )
            return CuttingWordsReactionResolution(
                state=reaction_state,
                result=updated_result,
                die_roll=int(die_roll),
                previous_attack_total=enemy_result.attack_roll.total,
                attack_total=enemy_result.attack_roll.total,
                prevented_hit=False,
                message=message,
                resolution_stage="damage_roll_revealed",
                previous_damage_total=previous_damage,
                damage_total=reduced_damage.total_before_reduction,
            )

        previous_total = enemy_result.attack_roll.total
        adjusted_roll = replace(
            enemy_result.attack_roll,
            total=previous_total - int(die_roll),
        )
        adjusted_attack = resolve_attack(
            enemy_result.attack_resolution.declaration,
            adjusted_roll,
            ActionUse.ACTION_AVAILABLE,
        )

        target_before = _actor_by_string_id(
            reaction_state,
            enemy_result.target.id,
        )
        merged_state = replace(
            enemy_result.state,
            spent_reaction_actor_ids=reaction_state.spent_reaction_actor_ids,
            condition_states=(
                enemy_result.state.condition_states
                if adjusted_attack.hit
                else state.condition_states
            ),
        )
        applied_damage = None
        updated_target = None
        damage = enemy_result.damage if adjusted_attack.hit else None
        if adjusted_attack.hit and damage is not None:
            applied_damage = apply_damage_result(
                target_before,
                damage,
                critical=adjusted_attack.critical,
            )
            updated_target = applied_damage.actor_after
            merged_state = replace_actor(merged_state, updated_target)
        else:
            merged_state = replace_actor(merged_state, target_before)

        prevented_hit = not adjusted_attack.hit
        message = (
            f"{bard.name} używa Cutting Words (k{die_sides}: {die_roll}): "
            f"atak {previous_total} spada do {adjusted_roll.total} i "
            + ("pudłuje." if prevented_hit else "nadal trafia.")
        )
        updated_result = replace(
            enemy_result,
            state=merged_state,
            attack_roll=adjusted_roll,
            attack_resolution=adjusted_attack,
            damage=damage,
            applied_damage=applied_damage,
            updated_target=updated_target,
            message=message,
        )
        return CuttingWordsReactionResolution(
            state=reaction_state,
            result=updated_result,
            die_roll=int(die_roll),
            previous_attack_total=previous_total,
            attack_total=adjusted_roll.total,
            prevented_hit=prevented_hit,
            message=message,
        )

    def deflect_missiles_option(
        self,
        *,
        state: CombatState,
        enemy_result: EnemyAutoTurnResult,
    ) -> ReactionOption | None:
        source = enemy_result.source
        target = enemy_result.target
        damage = enemy_result.damage
        if (
            source is None
            or target is None
            or damage is None
            or enemy_result.attack_resolution is None
            or not enemy_result.attack_resolution.hit
            or source.source_type != AttackSourceType.WEAPON
            or source.attack_kind != AttackKind.RANGED
        ):
            return None
        actor = next(
            (candidate for candidate in state.actors if str(candidate.id) == target.id),
            None,
        )
        if (
            actor is None
            or actor.is_defeated()
            or not actor_has_feature(actor, "deflect_missiles")
            or not reaction_available_for(state, actor)
        ):
            return None
        return ReactionOption(
            id=f"deflect-missiles:{actor.id}:{enemy_result.enemy.id}",
            kind=ReactionKind.DEFLECT_MISSILES,
            reactor_actor_id=str(actor.id),
            target_actor_id=str(enemy_result.enemy.id),
            trigger_event="hit_by_ranged_weapon_attack",
            effect_id="deflect_missiles",
            label="Deflect Missiles",
            value=damage.total_before_reduction,
        )

    def apply_deflect_missiles(
        self,
        *,
        state: CombatState,
        enemy_result: EnemyAutoTurnResult,
        option: ReactionOption,
        die_roll: int,
    ) -> DeflectMissilesReactionResolution:
        if option.kind != ReactionKind.DEFLECT_MISSILES:
            raise ValueError("Aktualna reakcja nie jest Deflect Missiles.")
        monk = _actor_by_string_id(state, option.reactor_actor_id)
        if (
            enemy_result.damage is None
            or enemy_result.target is None
            or enemy_result.target.id != str(monk.id)
        ):
            raise ValueError("Brak oczekujących obrażeń pocisku dla mnicha.")
        reduction = deflect_missiles(
            monk,
            natural_d10=int(die_roll),
            incoming_damage=enemy_result.damage.total_before_reduction,
            has_free_hand=free_hand_count(monk.inventory) > 0,
        )
        reaction = use_actor_reaction(state, monk)
        if not reaction.accepted:
            raise ValueError(reaction.message)
        monk_after_reaction = _actor_by_string_id(
            reaction.state,
            option.reactor_actor_id,
        )
        reduced_damage = _damage_after_flat_reduction(
            enemy_result.damage,
            reduction.reduction,
        )
        applied = apply_damage_result(
            monk_after_reaction,
            reduced_damage,
            critical=bool(
                enemy_result.attack_resolution
                and enemy_result.attack_resolution.critical
            ),
        )
        merged_state = replace(
            enemy_result.state,
            spent_reaction_actor_ids=reaction.state.spent_reaction_actor_ids,
        )
        merged_state = replace_actor(merged_state, applied.actor_after)
        message = (
            f"{monk.name} używa Deflect Missiles (k10: {die_roll}): "
            f"redukcja {reduction.reduction}, obrażenia "
            f"{enemy_result.damage.total_applied} → {applied.damage.total_applied}."
            + (
                " Pocisk został złapany i może zostać odrzucony za 1 Ki."
                if reduction.can_return_projectile
                else ""
            )
        )
        updated_result = replace(
            enemy_result,
            state=merged_state,
            damage=applied.damage,
            applied_damage=applied,
            updated_target=applied.actor_after,
            message=message,
        )
        return DeflectMissilesReactionResolution(
            state=reaction.state,
            result=updated_result,
            die_roll=int(die_roll),
            reduction=reduction.reduction,
            damage_before=enemy_result.damage.total_applied,
            damage_after=applied.damage.total_applied,
            caught=reduction.caught,
            can_return_projectile=(
                reduction.can_return_projectile
                and can_spend_actor_resource(monk_after_reaction, "ki_points")
            ),
            message=message,
        )

    def return_deflected_missile(
        self,
        *,
        board: BoardState,
        state: CombatState,
        actor_id: str,
        target_id: str,
        damage_type: DamageType,
        natural_roll: int,
        natural_roll_2: int | None = None,
    ) -> DeflectedMissileReturnResolution:
        monk = _actor_by_string_id(state, actor_id)
        target = _actor_by_string_id(state, target_id)
        if not actor_has_feature(monk, "deflect_missiles"):
            raise ValueError("Aktor nie posiada Deflect Missiles.")
        if target.faction == monk.faction or target.is_defeated():
            raise ValueError("Odrzucony pocisk wymaga żywego wrogiego celu.")
        distance = grid_distance_feet(monk.position, target.position)
        if distance > 60 or not line_of_sight_clear(
            board,
            monk.position,
            target.position,
        ):
            raise ValueError("Cel odrzucanego pocisku jest poza zasięgiem lub polem widzenia.")
        if not can_spend_actor_resource(monk, "ki_points"):
            raise ValueError("Brak 1 punktu Ki do odrzucenia pocisku.")
        spent = spend_actor_resource(monk, "ki_points")
        updated_state = replace_actor(state, spent.actor_after)
        source = deflected_missile_attack_source(
            spent.actor_after,
            damage_type=damage_type,
        )
        if distance > source.range_feet:
            source = replace(
                source,
                attack_roll_request=replace(
                    source.attack_roll_request,
                    mode=RollMode.DISADVANTAGE,
                ),
            )
        attack_roll = resolve_d20_roll(
            _manual_d20_input(
                source.attack_roll_request,
                int(natural_roll),
                (
                    int(natural_roll_2)
                    if natural_roll_2 is not None
                    else None
                ),
            )
        )
        attack = resolve_attack(
            AttackDeclaration(
                spent.actor_after,
                actor_as_combat_target(target),
                source,
            ),
            attack_roll,
            ActionUse.ACTION_AVAILABLE,
        )
        message = _player_attack_message(
            spent.actor_after.name,
            target.name,
            attack_roll.total,
            attack.hit,
            attack.critical,
        )
        return DeflectedMissileReturnResolution(
            state=updated_state,
            source=source,
            attack_roll=attack_roll,
            hit=attack.hit,
            critical=attack.critical,
            message=message,
        )


@dataclass(frozen=True, slots=True)
class CounterspellReactionResolution:
    state: CombatState
    result: EnemyAutoTurnResult
    cast_level: int
    interrupted_spell_level: int
    countered: bool
    check_request: D20RollRequest | None
    check_dc: int | None
    check_modifier: int
    check_roll: D20RollResult | None
    message: str


class CounterspellReactionFlowService:
    """Offer Counterspell before an enemy spell result is committed."""

    def option(
        self,
        *,
        board: BoardState,
        state: CombatState,
        enemy_result: EnemyAutoTurnResult,
        actions_by_actor: Mapping[ActorId, tuple[DefensiveSpellActionSpec, ...]],
    ) -> ReactionOption | None:
        source = enemy_result.source
        if (
            source is None
            or source.source_type != AttackSourceType.SPELL
            or enemy_result.spell_countered
            or not enemy_result.action_used
        ):
            return None
        enemy_caster = next(
            (
                actor
                for actor in enemy_result.state.actors
                if actor.id == enemy_result.enemy.id
            ),
            enemy_result.enemy,
        )
        for actor in state.actors:
            if (
                actor.faction == enemy_result.enemy.faction
                or actor.is_defeated()
                or not reaction_available_for(state, actor)
                or grid_distance_feet(actor.position, enemy_caster.position) > 60
                or not line_of_sight_clear(
                    board,
                    actor.position,
                    enemy_caster.position,
                )
            ):
                continue
            action = next(
                (
                    candidate
                    for candidate in actions_by_actor.get(actor.id, ())
                    if candidate.action_type == "spell_counter"
                    and _counterspell_cast_levels(
                        actor,
                        candidate,
                        condition_states=state.condition_states,
                    )
                ),
                None,
            )
            if action is None:
                continue
            return ReactionOption(
                id=f"counterspell:{actor.id}:{action.id}",
                kind=ReactionKind.SPELL_COUNTER,
                reactor_actor_id=str(actor.id),
                target_actor_id=str(enemy_result.enemy.id),
                trigger_event="enemy_casts_spell",
                effect_id=action.id,
                label=action.label,
                spell_level=action.spell_level,
                cast_levels=_counterspell_cast_levels(
                    actor,
                    action,
                    condition_states=state.condition_states,
                ),
            )
        return None

    def cast(
        self,
        *,
        state: CombatState,
        enemy_result: EnemyAutoTurnResult,
        option: ReactionOption,
        cast_level: int,
        actions_by_actor: Mapping[ActorId, tuple[DefensiveSpellActionSpec, ...]],
    ) -> CounterspellReactionResolution:
        if option.kind != ReactionKind.SPELL_COUNTER or option.effect_id is None:
            raise ValueError("Aktualna reakcja nie jest Kontrczarem.")
        caster = _actor_by_string_id(state, option.reactor_actor_id)
        action = next(
            (
                candidate
                for candidate in actions_by_actor.get(caster.id, ())
                if candidate.id == option.effect_id
                and candidate.action_type == "spell_counter"
            ),
            None,
        )
        if action is None:
            raise ValueError("Kontrczar nie jest dostępny dla tego aktora.")
        if cast_level not in _counterspell_cast_levels(
            caster,
            action,
            condition_states=state.condition_states,
        ):
            raise ValueError("Wybrany poziom slotu Kontrczaru nie jest dostępny.")
        source = enemy_result.source
        if source is None or source.source_type != AttackSourceType.SPELL:
            raise ValueError("Oczekująca akcja przeciwnika nie jest czarem.")

        reaction = use_actor_reaction(state, caster)
        if not reaction.accepted:
            raise ValueError(reaction.message)
        caster_with_reaction = _actor_by_string_id(
            reaction.state,
            option.reactor_actor_id,
        )
        spell_use = consume_spell_resource(
            caster_with_reaction,
            action.spell_level,
            cast_level,
            spell_id=action.id,
        )
        resource_state = replace_actor(reaction.state, spell_use.actor_after)
        interrupted_level = int(source.cast_level or source.spell_level)
        if interrupted_level <= cast_level:
            message = (
                f"{caster.name} rzuca {action.label} ze slotu {cast_level}. poziomu "
                f"i automatycznie przerywa {source.name}."
            )
            return CounterspellReactionResolution(
                state=resource_state,
                result=_countered_enemy_spell_result(
                    state=resource_state,
                    enemy_result=enemy_result,
                    caster=spell_use.actor_after,
                    message=message,
                ),
                cast_level=cast_level,
                interrupted_spell_level=interrupted_level,
                countered=True,
                check_request=None,
                check_dc=None,
                check_modifier=_spellcasting_ability_modifier(caster),
                check_roll=None,
                message=message,
            )

        modifier = _spellcasting_ability_modifier(caster)
        request = D20RollRequest(
            modifiers=(
                RollModifier(
                    "cecha bazowa rzucania czarów",
                    modifier,
                    RollModifierType.ABILITY,
                ),
            )
        )
        return CounterspellReactionResolution(
            state=resource_state,
            result=_enemy_spell_result_with_counterspell_resources(
                resource_state,
                enemy_result,
                spell_use.actor_after,
            ),
            cast_level=cast_level,
            interrupted_spell_level=interrupted_level,
            countered=False,
            check_request=request,
            check_dc=10 + interrupted_level,
            check_modifier=modifier,
            check_roll=None,
            message=(
                f"{caster.name} rzuca {action.label}. Wrogi czar {interrupted_level}. "
                f"poziomu wymaga testu cechy rzucania czarów ST {10 + interrupted_level}."
            ),
        )

    def resolve_check(
        self,
        *,
        state: CombatState,
        enemy_result: EnemyAutoTurnResult,
        caster_id: str,
        cast_level: int,
        interrupted_spell_level: int,
        natural_roll: int,
    ) -> CounterspellReactionResolution:
        caster = _actor_by_string_id(state, caster_id)
        modifier = _spellcasting_ability_modifier(caster)
        request = D20RollRequest(
            modifiers=(
                RollModifier(
                    "cecha bazowa rzucania czarów",
                    modifier,
                    RollModifierType.ABILITY,
                ),
            )
        )
        check = resolve_d20_roll(D20RollInput(request, int(natural_roll)))
        dc = 10 + interrupted_spell_level
        countered = check.total >= dc
        source_name = (
            enemy_result.source.name
            if enemy_result.source is not None
            else "wrogi czar"
        )
        message = (
            f"{caster.name}: test Kontrczaru {check.total} przeciw ST {dc} — "
            + (
                f"sukces, {source_name} zostaje przerwany."
                if countered
                else f"porażka, {source_name} działa normalnie."
            )
        )
        result = (
            _countered_enemy_spell_result(
                state=state,
                enemy_result=enemy_result,
                caster=caster,
                message=message,
            )
            if countered
            else _enemy_spell_result_with_counterspell_resources(
                state,
                enemy_result,
                caster,
            )
        )
        return CounterspellReactionResolution(
            state=state,
            result=result,
            cast_level=cast_level,
            interrupted_spell_level=interrupted_spell_level,
            countered=countered,
            check_request=request,
            check_dc=dc,
            check_modifier=modifier,
            check_roll=check,
            message=message,
        )


class CombatReactionFlowService:
    """Resolve opportunity attacks before a pending player movement."""

    def resolve_opportunity_movement(
        self,
        *,
        state: CombatState,
        actor_id: str,
        path: PathResult,
        threat_actor_ids: tuple[str, ...],
        attack_sources_by_actor: Mapping[ActorId, AttackSource],
        active_effects: tuple[ActiveCombatEffect, ...],
        roll_d20: Callable[[D20RollRequest], D20RollInput],
        roll_damage: Callable[[int], int],
    ) -> CombatReactionResolution:
        actor = next((candidate for candidate in state.actors if str(candidate.id) == actor_id), None)
        if actor is None:
            raise ValueError("Aktor oczekującego ruchu nie istnieje.")

        messages: list[str] = []
        applied_damages: list[AppliedDamageResult] = []
        updated_state = state
        updated_effects = active_effects
        reaction_window = open_reaction_window(
            interrupted_actor_id=actor_id,
            trigger_event="actor_leaves_reach",
            options=tuple(
                ReactionOption(
                    id=f"opportunity:{attacker_id}:{actor_id}",
                    kind=ReactionKind.OPPORTUNITY_ATTACK,
                    reactor_actor_id=attacker_id,
                    target_actor_id=actor_id,
                    trigger_event="actor_leaves_reach",
                    label="Atak okazyjny",
                )
                for attacker_id in threat_actor_ids
            ),
        )
        while reaction_window is not None:
            attacker_id = reaction_window.current_option.reactor_actor_id
            actor = next(
                (candidate for candidate in updated_state.actors if str(candidate.id) == actor_id),
                actor,
            )
            if actor.is_defeated():
                break
            attacker = next(
                (candidate for candidate in updated_state.actors if str(candidate.id) == attacker_id),
                None,
            )
            if attacker is None or attacker.is_defeated():
                reaction_window = advance_reaction_window(reaction_window)
                continue
            source = attack_sources_by_actor.get(attacker.id)
            if source is None:
                reaction_window = advance_reaction_window(reaction_window)
                continue
            if source.ammunition_type is not None and not has_ammunition(
                attacker,
                source.ammunition_type,
            ):
                reaction_window = advance_reaction_window(reaction_window)
                continue
            reaction = use_actor_reaction(updated_state, attacker)
            if not reaction.accepted:
                reaction_window = advance_reaction_window(reaction_window)
                continue
            updated_state = reaction.state
            if source.ammunition_type is not None:
                usage = consume_ammunition(attacker, source.ammunition_type)
                updated_state = record_ammunition_expenditure(
                    updated_state,
                    attacker,
                    usage,
                )
                updated_state = replace_actor(updated_state, usage.actor_after)
                attacker = usage.actor_after
            actor = next(candidate for candidate in updated_state.actors if str(candidate.id) == actor_id)
            if source.thrown and source.source_item_id is not None:
                updated_state = expend_thrown_weapon(
                    updated_state,
                    str(attacker.id),
                    source.source_item_id,
                    actor.position,
                )
                attacker = _actor_by_string_id(updated_state, str(attacker.id))
            source = attack_source_with_target_combat_effects(attacker, actor, source, updated_effects, allow_physical_turn_bonuses=False)
            source = attack_source_with_hidden_advantage(
                source,
                is_hidden_from(updated_state.hidden_states, str(attacker.id), str(actor.id)),
            )
            source = attack_source_with_exposed_mira_bonus(
                updated_state.hidden_states,
                attacker,
                actor,
                source,
            )
            source = attack_source_with_prone(
                source,
                updated_state.condition_states,
                attacker,
                actor,
            )
            rolled_input = roll_d20(source.attack_roll_request)
            attack_roll = resolve_d20_roll(
                D20RollInput(
                    source.attack_roll_request,
                    rolled_input.natural_roll,
                    rolled_input.natural_roll_2,
                )
            )
            declaration = AttackDeclaration(
                attacker=attacker,
                target=actor_as_combat_target(
                    actor,
                    updated_effects,
                    attacker=attacker,
                    actors=updated_state.actors,
                    opportunity_attack=True,
                ),
                source=source,
            )
            resolution = resolve_attack(declaration, attack_roll, ActionUse.ACTION_AVAILABLE)
            updated_state = replace(
                updated_state,
                hidden_states=reveal_actor(updated_state.hidden_states, str(attacker.id)),
            )
            updated_effects = consume_next_attack_effects(
                updated_effects,
                str(attacker.id),
                str(actor.id),
            )
            if resolution.hit:
                damage_result = resolve_damage(
                    roll_damage_components(
                        source.damage_components,
                        roll_damage,
                        critical=resolution.critical,
                    )
                )
                applied_damage = apply_damage_result(actor, damage_result, critical=resolution.critical)
                applied_damages.append(applied_damage)
                updated_state = replace_actor(updated_state, applied_damage.actor_after)
                defeated_text = " Cel zostaje pokonany." if applied_damage.defeated_by_damage else ""
                messages.append(
                    f"{attacker.name}: d20 {attack_roll.natural_roll}, razem {attack_roll.total}, trafienie. "
                    f"{_damage_application_message(applied_damage)}{defeated_text}"
                )
            else:
                messages.append(
                    f"{attacker.name}: d20 {attack_roll.natural_roll}, razem {attack_roll.total}, "
                    f"pudło przeciwko {actor.name}."
                )
            reaction_window = advance_reaction_window(reaction_window)

        actor = next(
            (candidate for candidate in updated_state.actors if str(candidate.id) == actor_id),
            actor,
        )
        movement_performed = False
        if not actor.is_defeated() and updated_state.status == CombatStatus.ACTIVE:
            movement = use_movement(updated_state, actor, path)
            if not movement.accepted:
                raise ValueError(movement.message)
            updated_state = movement.state
            movement_performed = True
            messages.append(movement.message)
        elif actor.is_defeated():
            messages.append(f"{actor.name} pada przed wykonaniem ruchu.")

        message = " ".join(messages) if messages else "Brak dostępnych reakcji. Ruch zostaje wykonany."
        return CombatReactionResolution(
            state=updated_state,
            active_effects=updated_effects,
            applied_damages=tuple(applied_damages),
            movement_performed=movement_performed,
            message_title="Atak okazyjny",
            message_body=message,
        )


class PlayerReactionFlowService:
    """Resolve manually rolled hero reactions during an enemy turn."""

    def resolve_attack_roll(
        self,
        *,
        state: CombatState,
        attacker_id: str,
        target_id: str,
        attack_sources_by_actor: Mapping[ActorId, AttackSource],
        active_effects: tuple[ActiveCombatEffect, ...],
        natural_roll: int,
        natural_roll_2: int | None = None,
        consumed_effect_id: str | None = None,
    ) -> PlayerReactionAttackResolution:
        attacker = _actor_by_string_id(state, attacker_id)
        target = _actor_by_string_id(state, target_id)
        source = attack_sources_by_actor.get(attacker.id)
        if source is None:
            raise ValueError(f"Aktor {attacker.name} nie ma zdefiniowanego ataku.")
        if source.ammunition_type is not None and not has_ammunition(
            attacker,
            source.ammunition_type,
        ):
            raise ValueError(f"Brak amunicji typu {source.ammunition_type} dla {source.name}.")
        reaction = use_actor_reaction(state, attacker)
        if not reaction.accepted:
            raise ValueError(reaction.message)
        updated_state = reaction.state
        attacker = _actor_by_string_id(updated_state, attacker_id)
        if source.ammunition_type is not None:
            usage = consume_ammunition(attacker, source.ammunition_type)
            updated_state = record_ammunition_expenditure(
                updated_state,
                attacker,
                usage,
            )
            updated_state = replace_actor(updated_state, usage.actor_after)
            attacker = usage.actor_after
        target = _actor_by_string_id(updated_state, target_id)
        if source.thrown and source.source_item_id is not None:
            updated_state = expend_thrown_weapon(
                updated_state,
                attacker_id,
                source.source_item_id,
                target.position,
            )
            attacker = _actor_by_string_id(updated_state, attacker_id)
        source = attack_source_with_target_combat_effects(
            attacker,
            target,
            source,
            active_effects,
            allow_physical_turn_bonuses=False,
        )
        source = attack_source_with_hidden_advantage(
            source,
            is_hidden_from(updated_state.hidden_states, str(attacker.id), str(target.id)),
        )
        source = attack_source_with_exposed_mira_bonus(
            updated_state.hidden_states,
            attacker,
            target,
            source,
        )
        source = attack_source_with_prone(
            source,
            updated_state.condition_states,
            attacker,
            target,
        )
        attack_roll = resolve_d20_roll(
            _manual_d20_input(source.attack_roll_request, natural_roll, natural_roll_2)
        )
        declaration = AttackDeclaration(
            attacker=attacker,
            target=actor_as_combat_target(target),
            source=source,
        )
        resolution = resolve_attack(declaration, attack_roll, ActionUse.ACTION_AVAILABLE)
        updated_state = replace(
            updated_state,
            hidden_states=reveal_actor(updated_state.hidden_states, str(attacker.id)),
        )
        updated_effects = active_effects
        if consumed_effect_id is not None:
            updated_effects = expire_active_effects(
                updated_effects,
                EffectEvent(
                    EffectEventType.EFFECT_CONSUMED,
                    effect_id=consumed_effect_id,
                ),
            ).active_effects
        updated_effects = consume_next_attack_effects(
            updated_effects,
            attacker_id,
            target_id,
        )
        return PlayerReactionAttackResolution(
            state=updated_state,
            active_effects=updated_effects,
            source=source,
            attack_roll=attack_roll,
            hit=resolution.hit,
            critical=resolution.critical,
            message=_player_attack_message(
                attacker.name,
                target.name,
                attack_roll.total,
                resolution.hit,
                resolution.critical,
            ),
        )

    def apply_damage(
        self,
        *,
        state: CombatState,
        attacker_id: str,
        target_id: str,
        attack_sources_by_actor: Mapping[ActorId, AttackSource],
        active_effects: tuple[ActiveCombatEffect, ...],
        damage: int | None = None,
        component_totals: Mapping[str, int] | None = None,
        critical: bool = False,
    ) -> PlayerReactionDamageResolution:
        attacker = _actor_by_string_id(state, attacker_id)
        target = _actor_by_string_id(state, target_id)
        source = attack_sources_by_actor.get(attacker.id)
        if source is None:
            raise ValueError(f"Aktor {attacker.name} nie ma zdefiniowanego ataku.")
        source = attack_source_with_target_combat_effects(
            attacker,
            target,
            source,
            active_effects,
            allow_physical_turn_bonuses=False,
        )
        if component_totals is not None:
            components = damage_components_from_totals(
                source.damage_components,
                component_totals,
            )
        else:
            if damage is None:
                raise ValueError("Brak wyniku obrażeń reakcji.")
            if len(source.damage_components) > 1:
                raise ValueError(
                    "Ten atak wymaga osobnego wyniku dla każdego składnika obrażeń."
                )
            component = source.damage_components[0]
            components = (
                DamageComponentInput(
                    max(0, int(damage)),
                    component.damage_type,
                    component.label or component.id,
                ),
            )
        damage_result = resolve_damage(components)
        applied_damage = apply_damage_result(target, damage_result, critical=critical)
        return PlayerReactionDamageResolution(
            state=replace_actor(state, applied_damage.actor_after),
            applied_damage=applied_damage,
            target_id=target_id,
        )

    def detect_ready_attack(
        self,
        *,
        state: CombatState,
        enemy_result: EnemyAutoTurnResult,
        board: BoardState,
        attack_sources_by_actor: Mapping[ActorId, AttackSource],
        active_effects: tuple[ActiveCombatEffect, ...],
    ) -> ReadyAttackTrigger | None:
        triggers = self.detect_ready_attacks(
            state=state,
            enemy_result=enemy_result,
            board=board,
            attack_sources_by_actor=attack_sources_by_actor,
            active_effects=active_effects,
        )
        return triggers[0] if triggers else None

    def detect_ready_attacks(
        self,
        *,
        state: CombatState,
        enemy_result: EnemyAutoTurnResult,
        board: BoardState,
        attack_sources_by_actor: Mapping[ActorId, AttackSource],
        active_effects: tuple[ActiveCombatEffect, ...],
    ) -> tuple[ReadyAttackTrigger, ...]:
        trigger = _ready_trigger_for_enemy_result(enemy_result)
        if trigger is None:
            return ()
        trigger_target = enemy_result.moved_enemy or enemy_result.enemy
        if trigger_target.is_defeated():
            return ()
        ready_attacks: list[ReadyAttackTrigger] = []
        for effect in active_effects:
            if effect.kind != "ready_attack":
                continue
            if effect.object_id != f"combat_action:ready:{trigger}":
                continue
            readied_actor = next(
                (actor for actor in state.actors if str(actor.id) == effect.actor_id),
                None,
            )
            if readied_actor is None or readied_actor.is_defeated():
                continue
            if not reaction_available_for(state, readied_actor):
                continue
            source = attack_sources_by_actor.get(readied_actor.id)
            if source is None:
                continue
            if source.ammunition_type is not None and not has_ammunition(
                readied_actor,
                source.ammunition_type,
            ):
                continue
            legal_targets = start_attack_action(
                board,
                readied_actor,
                enemy_result.state.actors,
                source,
            ).legal_targets
            if any(target.id == str(trigger_target.id) for target in legal_targets):
                ready_attacks.append(
                    ReadyAttackTrigger(
                        readied_actor_id=str(readied_actor.id),
                        target_id=str(trigger_target.id),
                        effect_id=effect.id,
                        trigger=trigger,
                    )
                )
        return tuple(ready_attacks)


def _ready_trigger_for_enemy_result(result: EnemyAutoTurnResult) -> str | None:
    if (
        result.movement_path is not None
        and result.movement_path.valid
        and result.movement_path.destination != result.movement_path.origin
    ):
        return "enemy_moves"
    if result.target is not None:
        return "enemy_attacks"
    return None


def _spell_action_is_available(
    actor: Actor,
    action: DefensiveSpellActionSpec,
    *,
    condition_states: Sequence[ConditionState] = (),
) -> bool:
    action_cost = getattr(action, "action_cost", None)
    if getattr(action_cost, "value", action_cost) != "reaction":
        return False
    validation = actor_spell_cast_validation(
        actor,
        action.id,
        condition_states=condition_states,
    )
    return validation is not None and validation.valid


def _counterspell_cast_levels(
    actor: Actor,
    action: DefensiveSpellActionSpec,
    *,
    condition_states: Sequence[ConditionState] = (),
) -> tuple[int, ...]:
    action_cost = getattr(action, "action_cost", None)
    if getattr(action_cost, "value", action_cost) != "reaction":
        return ()
    validation = actor_spell_cast_validation(
        actor,
        action.id,
        condition_states=condition_states,
    )
    if validation is None or not validation.valid:
        return ()
    return validation.available_cast_levels


def _spellcasting_ability_modifier(actor: Actor) -> int:
    if actor.spell_save_dc <= 0:
        return 0
    return actor.spell_save_dc - 8 - actor.proficiency_bonus


def _enemy_spell_result_with_counterspell_resources(
    state: CombatState,
    enemy_result: EnemyAutoTurnResult,
    caster: Actor,
) -> EnemyAutoTurnResult:
    merged_state = replace(
        enemy_result.state,
        spent_reaction_actor_ids=state.spent_reaction_actor_ids,
    )
    result_caster = next(
        (actor for actor in merged_state.actors if actor.id == caster.id),
        None,
    )
    if result_caster is not None:
        caster = replace(
            result_caster,
            inventory=caster.inventory,
            spell_slots=caster.spell_slots,
        )
    return replace(
        enemy_result,
        state=replace_actor(merged_state, caster),
    )


def _countered_enemy_spell_result(
    *,
    state: CombatState,
    enemy_result: EnemyAutoTurnResult,
    caster: Actor,
    message: str,
) -> EnemyAutoTurnResult:
    enemy_after_action = next(
        (
            actor
            for actor in enemy_result.state.actors
            if actor.id == enemy_result.enemy.id
        ),
        enemy_result.enemy,
    )
    countered_state = replace_actor(state, enemy_after_action)
    return replace(
        enemy_result,
        state=countered_state,
        message=message,
        attack_roll=None,
        attack_resolution=None,
        damage=None,
        applied_damage=None,
        updated_target=None,
        saving_throw_request=None,
        saving_throw_result=None,
        base_damage=None,
        base_damage_components=(),
        spell_countered=True,
        counterspell_actor_id=str(caster.id),
    )


def _actor_by_string_id(state: CombatState, actor_id: str) -> Actor:
    actor = next((candidate for candidate in state.actors if str(candidate.id) == actor_id), None)
    if actor is None:
        raise ValueError(f"Nieznany aktor walki: {actor_id}.")
    return actor


def _lorian_audience_available(
    actor: Actor,
    actors: Sequence[Actor],
    action_id: str,
    *,
    condition_states: Sequence[ConditionState] = (),
) -> bool:
    try:
        require_lorian_audience(
            actor,
            actors,
            action_id,
            condition_states=condition_states,
        )
    except ValueError:
        return False
    return True


def _manual_d20_input(
    request: D20RollRequest,
    natural_roll: int,
    natural_roll_2: int | None,
) -> D20RollInput:
    if request.mode == RollMode.NORMAL:
        return D20RollInput(request, int(natural_roll))
    if natural_roll_2 is None:
        raise ValueError("Ten rzut wymaga wpisania dwóch wyników d20.")
    return D20RollInput(request, int(natural_roll), int(natural_roll_2))


def _damage_after_flat_reduction(
    damage: DamageResult,
    reduction: int,
) -> DamageResult:
    """Apply a flat reduction to raw components before target affinities."""

    remaining_reduction = max(0, int(reduction))
    reduced_components: list[DamageComponentInput] = []
    for component in damage.components:
        removed = min(component.amount, remaining_reduction)
        remaining_reduction -= removed
        reduced_components.append(
            replace(component, amount=component.amount - removed)
        )
    return resolve_damage(tuple(reduced_components))


def _player_attack_message(
    attacker_name: str,
    target_name: str,
    total: int,
    hit: bool,
    critical: bool,
) -> str:
    if critical:
        return f"{attacker_name} trafia krytycznie {target_name}. Wynik ataku: {total}."
    if hit:
        return f"{attacker_name} trafia {target_name}. Wynik ataku: {total}."
    return f"{attacker_name} pudłuje przeciwko {target_name}. Wynik ataku: {total}."


def _damage_application_message(result: AppliedDamageResult) -> str:
    return applied_damage_message(result)
