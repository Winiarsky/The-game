from __future__ import annotations

from dataclasses import dataclass, replace
from random import Random
from typing import Mapping

from dnd_board_game.actions import (
    ActionResourceResolver,
    AreaSpellResolver,
    SpellSaveAttackResolver,
)
from dnd_board_game.actors import (
    Actor,
    Faction,
    actor_has_feature,
    can_spend_actor_resource,
    spend_actor_resource,
    spell_is_prepared,
)
from dnd_board_game.combat import (
    ActiveCombatEffect,
    ActionEconomyCost,
    ActionUse,
    AppliedDamageResult,
    AttackPositioning,
    AttackActionState,
    AttackDeclaration,
    AttackSource,
    AttackSourceType,
    CombatState,
    CombatStatus,
    CombatCondition,
    ConditionSaveTiming,
    DamageComponentInput,
    HealingSource,
    SpellSaveResult,
    attack_source_with_hidden_advantage,
    attack_source_with_prone,
    attack_source_with_positioning,
    attack_source_with_combat_effects,
    attack_source_with_target_combat_effects,
    apply_mirror_image_outcome,
    can_consume_spell_resource,
    can_use_attack_action,
    consume_next_attack_effects,
    colossus_slayer_damage,
    condition_hit_is_automatic_critical,
    commit_colossus_slayer_hit,
    commit_sneak_attack_hit,
    consume_spell_resource,
    damage_components_from_totals,
    dark_ones_blessing_temporary_hit_points,
    divine_smite_damage,
    current_actor,
    dexterity_save_cover_modifiers,
    evaluate_attack_positioning,
    expend_thrown_weapon,
    end_sanctuary_effects,
    grappled_actor_ids,
    grant_bonus_attacks,
    grid_distance_feet,
    is_hidden_from,
    plan_sneak_attack,
    reveal_actor,
    replace_actor,
    record_ammunition_expenditure,
    resolve_attack,
    resolve_actor_saving_throw,
    resolve_mirror_image_redirect,
    set_two_weapon_trigger,
    select_attack_target,
    start_attack_action,
    SceneObject,
    two_weapon_bonus_attack_source,
    two_weapon_bonus_source_is_legal,
    two_weapon_trigger_item_id,
    use_bonus_action,
    use_bonus_attack,
    use_attack_action,
    versatile_two_handed_source_is_legal,
    apply_condition,
)
from dnd_board_game.rules import (
    D20RollInput,
    EffectDuration,
    AdditionalEffectExpiration,
    EffectSource,
    EffectSourceType,
    EffectStackingPolicy,
    RollMode,
    RollModifier,
    SaveDamageOnSuccess,
    SavingThrowRequest,
    apply_active_effect,
    resolve_d20_roll,
    roll_instruction,
)
from dnd_board_game.inventory import (
    consume_ammunition,
    free_hand_count,
    has_ammunition,
    hands_required,
    item_power_available,
)
from dnd_board_game.world import BoardState, Coordinate

from .damage_presentation import applied_damage_message, applied_damage_payload
from .player_combat_resource_flow import remove_concentration_effects


@dataclass(frozen=True, slots=True)
class PendingPlayerAttack:
    attacker_id: str
    target_id: str
    source_id: str = ""
    stage: str = "confirm_attack"
    natural_roll: int | None = None
    natural_rolls: tuple[int, ...] = ()
    total: int | None = None
    hit: bool | None = None
    critical: bool = False
    saving_throws: tuple[SpellSaveResult, ...] = ()
    cover_level: str = "none"
    cover_bonus: int = 0
    cover_sources: tuple[str, ...] = ()
    ranged_threat_actor_ids: tuple[str, ...] = ()
    flanking_ally_ids: tuple[str, ...] = ()
    two_weapon_bonus: bool = False
    cast_level: int | None = None
    sneak_attack: bool = False
    colossus_slayer: bool = False
    divine_smite_slot_level: int = 0
    class_bonus_attack: bool = False
    open_hand_technique: bool = False
    horde_breaker: bool = False
    metamagic_ids: tuple[str, ...] = ()
    twinned_target_id: str | None = None
    twinned_second_attack: bool = False
    repelling_blast: bool = False
    miss_half_damage: bool = False


@dataclass(frozen=True, slots=True)
class CombatSourceSelectionTransition:
    actor_id: str
    source_id: str
    board_message: str
    message_title: str
    message_body: str
    event_type: str
    event_payload: tuple[tuple[str, object], ...]


@dataclass(frozen=True, slots=True)
class PlayerAttackTransition:
    state: CombatState
    active_effects: tuple[ActiveCombatEffect, ...]
    pending: PendingPlayerAttack | None
    board_message: str
    message_title: str
    message_body: str
    event_type: str
    event_payload: tuple[tuple[str, object], ...]
    clear_combat_help: bool = False
    clear_movement_preview: bool = False
    applied_damage: AppliedDamageResult | None = None
    additional_applied_damages: tuple[AppliedDamageResult, ...] = ()


class PlayerCombatActionFlowService:
    """Resolve player source selection and single-target attack transitions."""

    def __init__(self) -> None:
        self._resources = ActionResourceResolver()
        self._spell_saves = SpellSaveAttackResolver()
        self._area_spells = AreaSpellResolver()

    def select_attack_source(
        self,
        *,
        state: CombatState,
        sources: tuple[AttackSource, ...],
        source_id: str,
    ) -> CombatSourceSelectionTransition:
        actor = _active_hero(state)
        source = next((candidate for candidate in sources if candidate.id == source_id), None)
        if source is None:
            raise ValueError("Nieznane źródło ataku.")
        _require_usable_source(actor, source)
        return CombatSourceSelectionTransition(
            actor_id=str(actor.id),
            source_id=source.id,
            board_message=(
                f"Wybrano źródło ataku: {source.name}. "
                "Kliknij Skanuj planszę i wskaż legalny czerwony cel."
            ),
            message_title="Atak",
            message_body=f"{actor.name} wybiera: {source.name}.",
            event_type="ui_combat_attack_source_selected",
            event_payload=(("actor_id", str(actor.id)), ("source_id", source.id)),
        )

    def select_healing_source(
        self,
        *,
        state: CombatState,
        sources: tuple[HealingSource, ...],
        source_id: str,
    ) -> CombatSourceSelectionTransition:
        actor = _active_hero(state)
        source = next((candidate for candidate in sources if candidate.id == source_id), None)
        if source is None:
            raise ValueError("Nieznane źródło leczenia.")
        _require_usable_source(actor, source)
        return CombatSourceSelectionTransition(
            actor_id=str(actor.id),
            source_id=source.id,
            board_message=(
                f"Wybrano leczenie: {source.name}. "
                "Kliknij Skanuj planszę i wskaż rannego sojusznika."
            ),
            message_title="Leczenie",
            message_body=f"{actor.name} wybiera: {source.name}.",
            event_type="ui_combat_healing_source_selected",
            event_payload=(("actor_id", str(actor.id)), ("source_id", source.id)),
        )

    def select_attack_target(
        self,
        *,
        state: CombatState,
        board: BoardState,
        source: AttackSource,
        position: Coordinate,
        active_effects: tuple[ActiveCombatEffect, ...],
        scene_objects: tuple[SceneObject, ...] = (),
        two_weapon_bonus: bool = False,
        class_bonus_attack: bool = False,
    ) -> PlayerAttackTransition:
        attacker = _active_hero(state)
        _require_usable_source(
            attacker,
            source,
            active_effects=active_effects,
        )
        _require_attack_economy(
            state,
            attacker,
            source,
            two_weapon_bonus=two_weapon_bonus,
            class_bonus_attack=class_bonus_attack,
        )
        action = start_attack_action(board, attacker, state.actors, source, state.hidden_states)
        selected = select_attack_target(action, position=position)
        assert selected.selected_target is not None
        horde_breaker_effect = next(
            (
                effect
                for effect in active_effects
                if effect.actor_id == str(attacker.id)
                and effect.kind == "horde_breaker_pending"
            ),
            None,
        )
        if class_bonus_attack and horde_breaker_effect is not None:
            original_target_id = horde_breaker_effect.object_id.removeprefix(
                "actor:"
            )
            if selected.selected_target.id == original_target_id:
                raise ValueError("Horde Breaker wymaga innego celu niż pierwszy atak.")
            original_target = _actor_by_id(state, original_target_id)
            if (
                grid_distance_feet(
                    original_target.position,
                    selected.selected_target.position,
                )
                > 5
            ):
                raise ValueError(
                    "Cel Horde Breaker musi znajdować się do 5 ft od pierwszego celu."
                )
        target = _actor_by_id(state, selected.selected_target.id)
        positioning = evaluate_attack_positioning(
            board,
            attacker,
            target,
            source,
            state.actors,
            scene_objects,
            state.condition_states,
        )
        pending = PendingPlayerAttack(
            attacker_id=str(attacker.id),
            target_id=selected.selected_target.id,
            source_id=source.id,
            two_weapon_bonus=two_weapon_bonus,
            class_bonus_attack=class_bonus_attack,
            horde_breaker=horde_breaker_effect is not None,
            cast_level=source.cast_level,
            metamagic_ids=source.metamagic_ids,
            **_positioning_pending_fields(positioning),
        )
        return PlayerAttackTransition(
            state=state,
            active_effects=active_effects,
            pending=pending,
            board_message=(
                f"Wybrano cel ataku: {selected.selected_target.name}. "
                "Potwierdź atak Enterem albo przyciskiem."
            ),
            message_title="Podgląd ataku",
            message_body=(
                f"{attacker.name} celuje w {selected.selected_target.name}. "
                "Sprawdź warunki ataku i potwierdź przed rzutem."
            ),
            event_type="ui_combat_player_attack_target_selected",
            event_payload=(
                ("attacker_id", str(attacker.id)),
                ("target_id", selected.selected_target.id),
                ("cover_level", positioning.cover_level.value),
                ("cover_bonus", positioning.cover_bonus),
                ("cover_sources", list(positioning.cover_sources)),
                ("ranged_in_melee", bool(positioning.ranged_threat_actor_ids)),
                ("flanking_ally_ids", list(positioning.flanking_ally_ids)),
                ("two_weapon_bonus", two_weapon_bonus),
            ),
            clear_combat_help=True,
        )

    def confirm_attack_target(
        self,
        *,
        state: CombatState,
        board: BoardState,
        source: AttackSource,
        pending: PendingPlayerAttack,
        active_effects: tuple[ActiveCombatEffect, ...],
        rng: Random,
        scene_objects: tuple[SceneObject, ...] = (),
    ) -> PlayerAttackTransition:
        if pending.stage != "confirm_attack":
            raise ValueError("Nie ma celu ataku do potwierdzenia.")
        attacker, target, selected, positioning = _validated_attack(
            state, board, source, pending, scene_objects
        )
        effective_source = _source_for_pending(attacker, source, pending)
        effective_source = attack_source_with_target_combat_effects(
            attacker,
            target,
            effective_source,
            active_effects,
        )
        effective_source = attack_source_with_hidden_advantage(
            effective_source,
            is_hidden_from(state.hidden_states, str(attacker.id), str(target.id)),
        )
        effective_source = attack_source_with_positioning(effective_source, positioning)
        effective_source = attack_source_with_prone(
            effective_source,
            state.condition_states,
            attacker,
            target,
        )
        sanctuary = next(
            (
                effect
                for effect in active_effects
                if effect.actor_id == str(target.id)
                and effect.kind == "sanctuary"
            ),
            None,
        )
        if sanctuary is not None:
            caster = (
                _actor_by_id(state, sanctuary.source_actor_id)
                if sanctuary.source_actor_id is not None
                else target
            )
            save = resolve_actor_saving_throw(
                attacker,
                SavingThrowRequest(
                    "wisdom",
                    caster.spell_save_dc,
                    "Sanktuarium",
                    SaveDamageOnSuccess.NONE,
                    dc_source_label=f"ST czarów: {caster.name}",
                ),
                natural_roll=rng.randint(1, 20),
                condition_states=state.condition_states,
                combat_actors=state.actors,
            )
            if not save.success:
                blocked_effect = ActiveCombatEffect(
                    id=f"sanctuary-block:{attacker.id}:{target.id}",
                    actor_id=str(attacker.id),
                    kind="sanctuary_block_target",
                    label=f"Sanktuarium: {target.name}",
                    object_id=f"spell:sanctuary:{target.id}",
                    value=0,
                    source_actor_id=sanctuary.source_actor_id,
                    target_actor_id=str(target.id),
                    duration=EffectDuration.UNTIL_TURN_END,
                    stacking=EffectStackingPolicy.REFRESH,
                    stacking_key=f"sanctuary-block:{attacker.id}:{target.id}",
                )
                updated_effects = apply_active_effect(
                    active_effects,
                    blocked_effect,
                ).active_effects
                return PlayerAttackTransition(
                    state=state,
                    active_effects=updated_effects,
                    pending=None,
                    board_message=(
                        f"{attacker.name} nie przełamuje Sanktuarium "
                        f"(Wis {save.total} przeciw ST {save.dc}). "
                        "Wybierz na planszy inny legalny cel albo zakończ atak."
                    ),
                    message_title="Sanktuarium",
                    message_body=(
                        f"{attacker.name}: rzut Mądrości {save.total} przeciw "
                        f"ST {save.dc} — porażka. {target.name} nie może być "
                        "celem tego ataku; plansza pokaże pozostałe cele."
                    ),
                    event_type="ui_combat_sanctuary_blocked_attack",
                    event_payload=(
                        ("attacker_id", str(attacker.id)),
                        ("target_id", str(target.id)),
                        ("saving_throw", save.as_payload()),
                    ),
                    clear_combat_help=True,
                    clear_movement_preview=True,
                )
        if effective_source.save_ability:
            _require_usable_source(
                attacker,
                effective_source,
                active_effects=active_effects,
            )
            offensive_effects = end_sanctuary_effects(
                active_effects,
                str(attacker.id),
            )
            if pending.twinned_target_id is not None:
                twin = _actor_by_id(state, pending.twinned_target_id)
                confirmation = self._area_spells.confirm_area_spell(
                    state,
                    caster=attacker,
                    source=effective_source,
                    target_ids=(pending.target_id, pending.twinned_target_id),
                    rng=rng,
                    saving_throw_modifiers_by_target={
                        pending.target_id: _spell_save_cover_modifiers(
                            effective_source,
                            positioning,
                        ),
                    },
                )
                saves = confirmation.saving_throws
            else:
                state_after_ammunition = _consume_attack_ammunition(
                    state,
                    str(attacker.id),
                    effective_source,
                )
                single = self._spell_saves.confirm_target_save_spell(
                    state_after_ammunition,
                    caster=attacker,
                    target=target,
                    source=effective_source,
                    rng=rng,
                    saving_throw_modifiers=_spell_save_cover_modifiers(
                        effective_source,
                        positioning,
                    ),
                    heightened="metamagic_heightened" in effective_source.metamagic_ids,
                )
                confirmation = single
                saves = (single.saving_throw,)
            save_text = " ".join(_spell_save_message(save) for save in saves)
            save = saves[0]
            if all(save.damage_multiplier <= 0 for save in saves):
                return PlayerAttackTransition(
                    state=confirmation.state,
                    active_effects=offensive_effects,
                    pending=None,
                    board_message=(
                        f"{effective_source.name}: wszystkie cele unikają obrażeń."
                    ),
                    message_title="Czar",
                    message_body=(
                        f"{attacker.name} rzuca {effective_source.name}. "
                        f"{save_text} Sukces: brak obrażeń."
                    ),
                    event_type="ui_combat_player_save_spell_resolved",
                    event_payload=(
                        ("attacker_id", str(attacker.id)),
                        ("target_id", selected.selected_target.id),
                        ("source_id", effective_source.id),
                        ("saving_throw", save.as_payload()),
                        ("damage_required", False),
                    ),
                    clear_combat_help=True,
                    clear_movement_preview=True,
                )
            updated_pending = replace(
                pending,
                stage="damage_roll",
                saving_throws=saves,
                hit=True,
            )
            return PlayerAttackTransition(
                state=confirmation.state,
                active_effects=offensive_effects,
                pending=updated_pending,
                board_message=(
                    f"{effective_source.name}: {save.actor_name} nie zdaje rzutu obronnego. "
                    "Wpisz obrażenia."
                ),
                message_title="Czar",
                message_body=(
                    f"{attacker.name} rzuca {effective_source.name}. "
                    f"{save_text} Wpisz obrażenia {effective_source.damage_hint}."
                ),
                event_type="ui_combat_player_save_spell_confirmed",
                event_payload=(
                    ("attacker_id", str(attacker.id)),
                    ("target_id", selected.selected_target.id),
                    ("source_id", effective_source.id),
                    ("saving_throw", save.as_payload()),
                    ("damage_required", True),
                ),
                clear_movement_preview=True,
            )
        updated_pending = replace(
            pending,
            stage="attack_roll",
            **_positioning_pending_fields(positioning),
        )
        instruction = roll_instruction(effective_source.attack_roll_request)
        return PlayerAttackTransition(
            state=state,
            active_effects=active_effects,
            pending=updated_pending,
            board_message=(
                f"Potwierdzono atak: {attacker.name} -> {selected.selected_target.name}. "
                "Wpisz rzut d20 w panelu walki."
            ),
            message_title="Atak",
            message_body=(
                f"{attacker.name} atakuje {selected.selected_target.name}. "
                f"{instruction.message}"
            ),
            event_type="ui_combat_player_attack_target_confirmed",
            event_payload=(
                ("attacker_id", str(attacker.id)),
                ("target_id", selected.selected_target.id),
                ("target_ac", selected.selected_target.ac),
                ("cover_bonus", positioning.cover_bonus),
                ("ranged_in_melee", bool(positioning.ranged_threat_actor_ids)),
            ),
        )

    def cancel_attack_target(
        self,
        *,
        state: CombatState,
        pending: PendingPlayerAttack,
        active_effects: tuple[ActiveCombatEffect, ...],
    ) -> PlayerAttackTransition:
        if pending.stage not in {"confirm_attack", "attack_roll"}:
            raise ValueError("Nie ma wyboru celu ataku do anulowania.")
        return PlayerAttackTransition(
            state=state,
            active_effects=active_effects,
            pending=None,
            board_message=(
                "Anulowano wybór celu ataku. "
                "Kliknij Skanuj planszę, żeby wybrać ruch albo cel."
            ),
            message_title="Atak",
            message_body="Anulowano wybór celu ataku.",
            event_type="ui_combat_player_attack_target_cancelled",
            event_payload=(
                ("attacker_id", pending.attacker_id),
                ("target_id", pending.target_id),
            ),
        )

    def submit_attack_roll(
        self,
        *,
        state: CombatState,
        board: BoardState,
        source: AttackSource,
        pending: PendingPlayerAttack,
        active_effects: tuple[ActiveCombatEffect, ...],
        natural_roll: int,
        natural_roll_2: int | None = None,
        natural_rerolls: tuple[int, ...] = (),
        mirror_image_roll: int | None = None,
        scene_objects: tuple[SceneObject, ...] = (),
    ) -> PlayerAttackTransition:
        if pending.stage != "attack_roll":
            raise ValueError("Nie ma oczekującego rzutu ataku gracza.")
        attacker, target, selected, positioning = _validated_attack(
            state, board, source, pending, scene_objects
        )
        effective_source = _source_for_pending(attacker, source, pending)
        effective_source = attack_source_with_target_combat_effects(
            attacker,
            target,
            effective_source,
            active_effects,
        )
        effective_source = attack_source_with_hidden_advantage(
            effective_source,
            is_hidden_from(state.hidden_states, str(attacker.id), str(target.id)),
        )
        effective_source = attack_source_with_positioning(effective_source, positioning)
        effective_source = attack_source_with_prone(
            effective_source,
            state.condition_states,
            attacker,
            target,
        )
        sneak_attack = plan_sneak_attack(
            state=state,
            active_effects=active_effects,
            attacker=attacker,
            target=selected.selected_target,
            source=effective_source,
            roll_mode=effective_source.attack_roll_request.mode,
        )
        if sneak_attack.eligible:
            effective_source = sneak_attack.source
        colossus_component = (
            colossus_slayer_damage(
                attacker,
                selected.selected_target,
                damage_type=effective_source.damage_components[0].damage_type,
            )
            if effective_source.source_type == AttackSourceType.WEAPON
            and effective_source.damage_components
            and not any(
                effect.actor_id == str(attacker.id)
                and effect.kind == "colossus_slayer_used"
                for effect in active_effects
            )
            else None
        )
        if colossus_component is not None:
            effective_source = replace(
                effective_source,
                damage_components=(
                    *effective_source.damage_components,
                    colossus_component,
                ),
                damage_hint=(
                    f"{effective_source.damage_hint} + "
                    f"{colossus_component.hint()}"
                ),
            )
        attack_roll = resolve_d20_roll(
            _manual_d20_input(
                effective_source,
                natural_roll,
                natural_roll_2,
                natural_rerolls,
            )
        )
        mirror_image = next(
            (
                effect
                for effect in active_effects
                if effect.actor_id == str(target.id)
                and effect.kind == "mirror_image"
                and effect.value > 0
            ),
            None,
        )
        if mirror_image is not None and mirror_image_roll is None:
            raise ValueError("Rzuć dodatkowe k20 dla Lustrzanych odbić.")
        mirror_outcome = resolve_mirror_image_redirect(
            target,
            attack_total=attack_roll.total,
            active_effects=active_effects,
            redirect_roll=int(mirror_image_roll or 1),
        )
        if pending.twinned_second_attack:
            state_after_resource = state
        elif pending.class_bonus_attack:
            bonus_use = use_bonus_attack(
                state,
                source_id=effective_source.id,
            )
            if not bonus_use.accepted:
                raise ValueError(bonus_use.message)
            state_after_resource = bonus_use.state
        elif pending.two_weapon_bonus:
            bonus_use = use_bonus_action(state)
            if not bonus_use.accepted:
                raise ValueError(bonus_use.message)
            state_after_resource = bonus_use.state
        else:
            if _uses_attack_action(effective_source):
                attack_use = use_attack_action(
                    state,
                    attacker,
                    maximum_attacks=1
                    if effective_source.loading or effective_source.limited_attacks
                    else None,
                )
                if not attack_use.accepted:
                    raise ValueError(attack_use.message)
                state_after_resource = attack_use.state
            else:
                resource_use = self._resources.consume_action_and_source_resource(
                    state,
                    attacker,
                    spell_level=effective_source.spell_level,
                    spell_id=effective_source.id,
                    cast_level=effective_source.cast_level,
                    action_cost=effective_source.action_cost,
                    resource_pool_id=effective_source.resource_pool_id,
                    resource_cost=effective_source.resource_cost,
                )
                state_after_resource = resource_use.state
            state_after_resource = set_two_weapon_trigger(
                state_after_resource,
                two_weapon_trigger_item_id(attacker, source),
            )
        if (
            not pending.twinned_second_attack
            and (
            pending.class_bonus_attack
            or pending.two_weapon_bonus
            or _uses_attack_action(effective_source)
            )
        ):
            state_after_resource = _consume_attack_source_resource(
                state_after_resource,
                str(attacker.id),
                effective_source,
            )
        if not pending.twinned_second_attack:
            state_after_resource = _consume_attack_ammunition(
                state_after_resource,
                str(attacker.id),
                effective_source,
            )
        if effective_source.thrown and effective_source.source_item_id is not None:
            state_after_resource = expend_thrown_weapon(
                state_after_resource,
                str(attacker.id),
                effective_source.source_item_id,
                selected.selected_target.position,
            )
        attack_target = (
            replace(selected.selected_target, ac=mirror_outcome.duplicate_ac)
            if mirror_outcome is not None and mirror_outcome.redirected
            else selected.selected_target
        )
        resolution = resolve_attack(
            AttackDeclaration(attacker, attack_target, effective_source),
            attack_roll,
            selected.action_use,
        )
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
            state.condition_states,
            str(target.id),
            within_five_feet=(
                max(
                    abs(attacker.position.col - target.position.col),
                    abs(attacker.position.row - target.position.row),
                )
                <= 1
            ),
        ):
            resolution = replace(resolution, critical=True)
        updated_effects = consume_next_attack_effects(
            active_effects,
            str(attacker.id),
            selected.selected_target.id,
        )
        updated_effects = apply_mirror_image_outcome(
            updated_effects,
            mirror_outcome,
        )
        if effective_source.concentration and not pending.twinned_second_attack:
            updated_effects = remove_concentration_effects(
                updated_effects,
                str(attacker.id),
            )
        if pending.horde_breaker:
            updated_effects = tuple(
                effect
                for effect in updated_effects
                if not (
                    effect.actor_id == str(attacker.id)
                    and effect.kind == "horde_breaker_pending"
                )
            )
            updated_effects = (
                *updated_effects,
                ActiveCombatEffect(
                    id=f"horde-breaker-used:{attacker.id}",
                    actor_id=str(attacker.id),
                    kind="horde_breaker_used",
                    label="Horde Breaker wykorzystany",
                    object_id="class_feature:horde_breaker",
                    value=1,
                    source_actor_id=str(attacker.id),
                    duration=EffectDuration.UNTIL_TURN_START,
                    expiration_actor_id=str(attacker.id),
                ),
            )
        elif (
            not pending.class_bonus_attack
            and not pending.two_weapon_bonus
            and effective_source.source_type == AttackSourceType.WEAPON
            and actor_has_feature(attacker, "horde_breaker")
            and not any(
                effect.actor_id == str(attacker.id)
                and effect.kind in {
                    "horde_breaker_pending",
                    "horde_breaker_used",
                }
                for effect in updated_effects
            )
            and _has_horde_breaker_target(
                board=board,
                state=state_after_resource,
                attacker=attacker,
                original_target=target,
                source=effective_source,
            )
        ):
            state_after_resource = grant_bonus_attacks(
                state_after_resource,
                count=1,
                source_id=effective_source.id,
            )
            updated_effects = (
                *updated_effects,
                ActiveCombatEffect(
                    id=f"horde-breaker-pending:{attacker.id}",
                    actor_id=str(attacker.id),
                    kind="horde_breaker_pending",
                    label="Horde Breaker",
                    object_id=f"actor:{target.id}",
                    value=1,
                    source_actor_id=str(attacker.id),
                    duration=EffectDuration.UNTIL_TURN_START,
                    expiration_actor_id=str(attacker.id),
                ),
            )
        message = _player_attack_message(
            attacker.name,
            selected.selected_target.name,
            attack_roll.total,
            resolution.hit,
            resolution.critical,
        )
        if mirror_outcome is not None:
            if mirror_outcome.redirected and duplicate_was_hit:
                message += (
                    f" Lustrzane odbicia: k20 {mirror_outcome.redirect_roll}; "
                    f"atak trafia KP {mirror_outcome.duplicate_ac} i niszczy duplikat "
                    f"({mirror_outcome.duplicates_after} pozostało)."
                )
            elif mirror_outcome.redirected:
                message += (
                    f" Lustrzane odbicia: k20 {mirror_outcome.redirect_roll}; "
                    f"atak zostaje przekierowany, ale nie trafia KP "
                    f"{mirror_outcome.duplicate_ac} duplikatu."
                )
            else:
                message += (
                    f" Lustrzane odbicia: k20 {mirror_outcome.redirect_roll}; "
                    "atak nie został przekierowany."
                )
        event_payload = (
            ("attacker_id", str(attacker.id)),
            ("target_id", selected.selected_target.id),
            ("natural_roll", attack_roll.natural_roll),
            ("natural_rolls", list(attack_roll.natural_rolls)),
            ("total", attack_roll.total),
            ("hit", resolution.hit),
            ("critical", resolution.critical),
            ("target_ac", selected.selected_target.ac),
            ("cover_level", positioning.cover_level.value),
            ("cover_bonus", positioning.cover_bonus),
            ("cover_sources", list(positioning.cover_sources)),
            ("ranged_in_melee", bool(positioning.ranged_threat_actor_ids)),
            ("two_weapon_bonus", pending.two_weapon_bonus),
            ("resource_pool_id", effective_source.resource_pool_id),
            ("resource_cost", effective_source.resource_cost if effective_source.resource_pool_id else 0),
            (
                "mirror_image",
                (
                    {
                        "redirect_roll": mirror_outcome.redirect_roll,
                        "redirected": mirror_outcome.redirected,
                        "duplicate_ac": mirror_outcome.duplicate_ac,
                        "duplicate_hit": mirror_outcome.duplicate_hit,
                        "duplicates_after": mirror_outcome.duplicates_after,
                    }
                    if mirror_outcome is not None
                    else None
                ),
            ),
        )
        revealed_state = replace(
            state_after_resource,
            hidden_states=reveal_actor(state_after_resource.hidden_states, str(attacker.id)),
        )
        if not resolution.hit:
            if effective_source.miss_damage_on_failure == "half":
                return PlayerAttackTransition(
                    state=revealed_state,
                    active_effects=updated_effects,
                    pending=replace(
                        pending,
                        stage="damage_roll",
                        natural_roll=attack_roll.natural_roll,
                        natural_rolls=attack_roll.natural_rolls,
                        total=attack_roll.total,
                        hit=False,
                        critical=False,
                        miss_half_damage=True,
                    ),
                    board_message="",
                    message_title="Atak",
                    message_body=(
                        f"{message} Czar zadaje połowę wyniku obrażeń mimo pudła."
                    ),
                    event_type="ui_combat_player_attack_roll",
                    event_payload=event_payload,
                    clear_combat_help=True,
                    clear_movement_preview=True,
                )
            next_pending = _twinned_second_attack_pending(pending)
            return PlayerAttackTransition(
                state=revealed_state,
                active_effects=updated_effects,
                pending=next_pending,
                board_message="",
                message_title="Atak",
                message_body=message,
                event_type="ui_combat_player_attack_roll",
                event_payload=event_payload,
                clear_combat_help=True,
                clear_movement_preview=True,
            )
        if effective_source.on_hit_condition is not None:
            target_actor = _actor_by_id(revealed_state, pending.target_id)
            if (
                effective_source.weapon_special_rule is not None
                and effective_source.weapon_special_rule.value == "net"
                and target_actor.size.value in {"large", "huge", "gargantuan"}
            ):
                condition_message = (
                    f"{target_actor.name} jest zbyt duży, aby sieć go unieruchomiła."
                )
                conditioned_state = revealed_state
            else:
                application = apply_condition(
                    revealed_state.condition_states,
                    target_actor,
                    CombatCondition(effective_source.on_hit_condition),
                    source_actor_id=str(attacker.id),
                    source_label=effective_source.name,
                    duration=effective_source.on_hit_condition_duration,
                    expiration_actor_id=(
                        str(attacker.id)
                        if effective_source.on_hit_condition_expiration == "source"
                        else str(target_actor.id)
                    ),
                    source_spell_id=(
                        effective_source.id
                        if effective_source.source_type == AttackSourceType.SPELL
                        else None
                    ),
                    source_spell_level=(
                        effective_source.spell_level
                        if effective_source.source_type == AttackSourceType.SPELL
                        else None
                    ),
                )
                conditioned_state = replace(
                    revealed_state,
                    condition_states=application.condition_states,
                )
                condition_message = application.message
            message = f"{message} {condition_message}"
            revealed_state = conditioned_state
            if not _source_deals_damage(effective_source):
                return PlayerAttackTransition(
                    state=conditioned_state,
                    active_effects=updated_effects,
                    pending=None,
                    board_message="",
                    message_title="Atak",
                    message_body=message,
                    event_type="ui_combat_player_attack_roll",
                    event_payload=event_payload,
                    clear_combat_help=True,
                    clear_movement_preview=True,
                )
        updated_pending = replace(
            pending,
            stage="damage_roll",
            natural_roll=attack_roll.natural_roll,
            natural_rolls=attack_roll.natural_rolls,
            total=attack_roll.total,
            hit=True,
            critical=resolution.critical,
            sneak_attack=sneak_attack.eligible,
            colossus_slayer=colossus_component is not None,
            open_hand_technique=(
                pending.class_bonus_attack
                and effective_source.id == "unarmed_strike"
                and actor_has_feature(attacker, "open_hand_technique")
                and any(
                    effect.actor_id == str(attacker.id)
                    and effect.kind == "flurry_of_blows"
                    for effect in active_effects
                )
            ),
            repelling_blast=(
                effective_source.id == "eldritch_blast"
                and actor_has_feature(attacker, "repelling_blast")
            ),
            **_positioning_pending_fields(positioning),
        )
        return PlayerAttackTransition(
            state=revealed_state,
            active_effects=updated_effects,
            pending=updated_pending,
            board_message="",
            message_title="Atak",
            message_body=(
                f"{message} Trafienie: rzuć obrażenia {effective_source.damage_hint} "
                "i wpisz sumę."
            ),
            event_type="ui_combat_player_attack_roll",
            event_payload=event_payload,
            clear_movement_preview=True,
        )

    def submit_damage(
        self,
        *,
        state: CombatState,
        source: AttackSource,
        pending: PendingPlayerAttack,
        active_effects: tuple[ActiveCombatEffect, ...],
        damage: int | None = None,
        component_totals: Mapping[str, int] | None = None,
    ) -> PlayerAttackTransition:
        if pending.stage != "damage_roll":
            raise ValueError("Nie ma oczekującego rzutu obrażeń gracza.")
        attacker = _active_hero(state)
        if str(attacker.id) != pending.attacker_id:
            raise ValueError("Oczekujące obrażenia nie należą do aktywnego aktora.")
        effective_source = attack_source_with_combat_effects(
            attacker,
            _source_for_pending(attacker, source, pending),
            active_effects,
        )
        target = _actor_by_id(state, pending.target_id)
        effective_source = attack_source_with_target_combat_effects(
            attacker,
            target,
            effective_source,
            active_effects,
        )
        if pending.sneak_attack:
            effective_source = plan_sneak_attack(
                state=state,
                active_effects=active_effects,
                attacker=attacker,
                target=target,
                source=effective_source,
                roll_mode=RollMode.NORMAL,
            ).source
        if pending.colossus_slayer and effective_source.damage_components:
            component = colossus_slayer_damage(
                attacker,
                target,
                damage_type=effective_source.damage_components[0].damage_type,
            )
            if component is not None:
                effective_source = replace(
                    effective_source,
                    damage_components=(*effective_source.damage_components, component),
                    damage_hint=f"{effective_source.damage_hint} + {component.hint()}",
                )
        state_for_damage = state
        if pending.divine_smite_slot_level:
            if (
                effective_source.source_type != AttackSourceType.WEAPON
                or effective_source.attack_kind.value != "melee"
            ):
                raise ValueError("Divine Smite wymaga trafienia bronią w zwarciu.")
            smite = divine_smite_damage(
                attacker,
                slot_level=pending.divine_smite_slot_level,
                target_creature_type=target.creature_type,
            )
            effective_source = replace(
                effective_source,
                damage_components=(*effective_source.damage_components, smite),
                damage_hint=f"{effective_source.damage_hint} + {smite.hint()}",
            )
            resource = consume_spell_resource(
                attacker,
                spell_level=1,
                cast_level=pending.divine_smite_slot_level,
            )
            state_for_damage = replace_actor(state, resource.actor_after)
        if component_totals is not None:
            damage_components = damage_components_from_totals(
                effective_source.damage_components,
                component_totals,
            )
        else:
            if len(effective_source.damage_components) > 1:
                raise ValueError(
                    "To źródło zadaje kilka typów obrażeń. Wpisz wynik każdego składnika osobno."
                )
            damage_amount = max(0, int(damage or 0))
            component = effective_source.damage_components[0]
            damage_components = (
                DamageComponentInput(
                    damage_amount,
                    component.damage_type,
                    component.label or component.id,
                ),
            )
        damage_amount = sum(component.amount for component in damage_components)
        if effective_source.damage_divisor > 1:
            damage_components = tuple(
                replace(
                    component,
                    amount=component.amount // effective_source.damage_divisor,
                )
                for component in damage_components
            )
            damage_amount = sum(component.amount for component in damage_components)
        if pending.miss_half_damage:
            damage_components = tuple(
                replace(component, amount=component.amount // 2)
                for component in damage_components
            )
            damage_amount = sum(component.amount for component in damage_components)
        save = next(
            (
                candidate
                for candidate in pending.saving_throws
                if candidate.actor_id == pending.target_id
            ),
            None,
        )
        resolution = self._spell_saves.apply_target_damage(
            state_for_damage,
            target_id=pending.target_id,
            source=effective_source,
            base_damage=damage_amount,
            damage_components=damage_components,
            saving_throw=save,
            critical=pending.critical,
            active_effects=active_effects,
        )
        applied = resolution.applied_damage
        resolved_state = resolution.state
        additional_applied: list[AppliedDamageResult] = []
        if pending.twinned_target_id is not None and pending.saving_throws:
            twin_save = next(
                (
                    candidate
                    for candidate in pending.saving_throws
                    if candidate.actor_id == pending.twinned_target_id
                ),
                None,
            )
            twin_resolution = self._spell_saves.apply_target_damage(
                resolved_state,
                target_id=pending.twinned_target_id,
                source=effective_source,
                base_damage=damage_amount,
                damage_components=damage_components,
                saving_throw=twin_save,
                critical=False,
                active_effects=active_effects,
            )
            resolved_state = twin_resolution.state
            additional_applied.append(twin_resolution.applied_damage)
        defeated_target = any(
            result.defeated_by_damage
            for result in (applied, *additional_applied)
        )
        if defeated_target and actor_has_feature(
            attacker,
            "dark_ones_blessing",
        ):
            current_attacker = _actor_by_id(resolved_state, str(attacker.id))
            resolved_state = replace_actor(
                resolved_state,
                replace(
                    current_attacker,
                    temp_hp=max(
                        current_attacker.temp_hp,
                        dark_ones_blessing_temporary_hit_points(current_attacker),
                    ),
                ),
            )
        branding_smite = next(
            (
                effect
                for effect in active_effects
                if effect.actor_id == str(attacker.id)
                and effect.kind == "branding_smite"
            ),
            None,
        )
        updated_effects = active_effects
        if pending.sneak_attack:
            updated_effects = commit_sneak_attack_hit(
                updated_effects,
                str(attacker.id),
            )
        if pending.colossus_slayer:
            updated_effects = commit_colossus_slayer_hit(
                updated_effects,
                str(attacker.id),
            )
        if applied.damage.total_applied > 0:
            updated_effects = tuple(
                effect
                for effect in updated_effects
                if not (
                    effect.actor_id == str(attacker.id)
                    and effect.kind == "branding_smite"
                )
            )
            if branding_smite is not None:
                updated_effects = tuple(
                    effect
                    for effect in updated_effects
                    if not (
                        effect.actor_id == str(target.id)
                        and effect.kind == "invisibility"
                    )
                )
                glow = ActiveCombatEffect(
                    id=f"branding-smite-glow:{attacker.id}:{target.id}",
                    actor_id=str(target.id),
                    kind="branding_smite_glow",
                    label="Piętnujące porażenie: świeci",
                    object_id="spell:branding_smite",
                    value=5,
                    source_actor_id=str(attacker.id),
                    target_actor_id=str(target.id),
                    source=EffectSource(
                        EffectSourceType.SPELL,
                        "branding_smite",
                        "Piętnujące porażenie",
                    ),
                    duration=EffectDuration.CONCENTRATION,
                    stacking=EffectStackingPolicy.REFRESH,
                    stacking_key=f"concentration:{attacker.id}",
                    spell_level=branding_smite.spell_level,
                )
                updated_effects = apply_active_effect(
                    updated_effects,
                    glow,
                ).active_effects
        if (
            pending.hit is not False
            and effective_source.on_hit_effect_kind is not None
        ):
            on_hit_effect = ActiveCombatEffect(
                id=(
                    f"{effective_source.on_hit_effect_kind}:"
                    f"{attacker.id}:{target.id}:{effective_source.id}"
                ),
                actor_id=str(target.id),
                kind=effective_source.on_hit_effect_kind,
                label=effective_source.name,
                object_id=f"spell:{effective_source.id}",
                value=effective_source.on_hit_effect_value,
                source_actor_id=str(attacker.id),
                target_actor_id=str(target.id),
                source=EffectSource(
                    EffectSourceType.SPELL,
                    effective_source.id,
                    effective_source.name,
                ),
                duration=effective_source.on_hit_effect_duration,
                expiration_actor_id=(
                    str(attacker.id)
                    if effective_source.on_hit_effect_kind
                    == "guiding_bolt_mark"
                    else None
                ),
                additional_expirations=(
                    (
                        AdditionalEffectExpiration(
                            EffectDuration.UNTIL_TURN_END,
                            actor_id=str(attacker.id),
                        ),
                    )
                    if effective_source.on_hit_effect_kind
                    == "guiding_bolt_mark"
                    else ()
                ),
                stacking=EffectStackingPolicy.REFRESH,
                stacking_key=(
                    f"{effective_source.on_hit_effect_kind}:{target.id}"
                ),
                spell_level=effective_source.cast_level
                or effective_source.spell_level,
            )
            updated_effects = apply_active_effect(
                updated_effects,
                on_hit_effect,
            ).active_effects
            if effective_source.on_hit_effect_kind == "ray_of_enfeeblement":
                target_actor = _actor_by_id(resolved_state, str(target.id))
                application = apply_condition(
                    resolved_state.condition_states,
                    target_actor,
                    CombatCondition.ENFEEBLED,
                    source_actor_id=str(attacker.id),
                    source_label=effective_source.name,
                    duration=EffectDuration.CONCENTRATION,
                    save_ability="constitution",
                    save_dc=attacker.spell_save_dc,
                    save_timing=ConditionSaveTiming.TURN_END,
                    source_spell_id=effective_source.id,
                    source_spell_level=(
                        effective_source.cast_level
                        or effective_source.spell_level
                    ),
                )
                resolved_state = replace(
                    resolved_state,
                    condition_states=application.condition_states,
                )
        next_pending = (
            _twinned_second_attack_pending(pending)
            if pending.twinned_target_id is not None
            and not pending.saving_throws
            and not pending.twinned_second_attack
            else None
        )
        return PlayerAttackTransition(
            state=resolved_state,
            active_effects=updated_effects,
            pending=(
                replace(pending, stage="open_hand_choice")
                if pending.open_hand_technique and not applied.defeated
                else replace(pending, stage="repelling_blast_choice")
                if pending.repelling_blast and not applied.defeated
                else next_pending
            ),
            board_message="",
            message_title="Obrażenia",
            message_body=(
                f"{attacker.name} zadaje obrażenia. {_damage_application_message(applied)}"
            ),
            event_type="ui_combat_player_damage_roll",
            event_payload=(
                ("attacker_id", str(attacker.id)),
                ("target_id", str(target.id)),
                ("base_damage", damage_amount),
                ("damage", applied.damage.total_applied),
                ("saving_throw", save.as_payload() if save is not None else None),
                ("damage_result", _applied_damage_payload(applied)),
                ("two_weapon_bonus", pending.two_weapon_bonus),
            ),
            clear_combat_help=True,
            applied_damage=applied,
            additional_applied_damages=tuple(additional_applied),
        )

    def resolve_direct_attack(
        self,
        *,
        state: CombatState,
        board: BoardState,
        source: AttackSource,
        target_id: str,
        active_effects: tuple[ActiveCombatEffect, ...],
        natural_roll: int,
        damage: int = 0,
        natural_roll_2: int | None = None,
        natural_rerolls: tuple[int, ...] = (),
        scene_objects: tuple[SceneObject, ...] = (),
    ) -> PlayerAttackTransition:
        attacker = _active_hero(state)
        _require_usable_source(
            attacker,
            source,
            active_effects=active_effects,
        )
        pending = PendingPlayerAttack(
            str(attacker.id),
            target_id,
            source.id,
            "attack_roll",
            cast_level=source.cast_level,
            metamagic_ids=source.metamagic_ids,
        )
        attacker, target, selected, positioning = _validated_attack(
            state, board, source, pending, scene_objects
        )
        effective_source = attack_source_with_target_combat_effects(
            attacker,
            target,
            source,
            active_effects,
        )
        effective_source = attack_source_with_hidden_advantage(
            effective_source,
            is_hidden_from(state.hidden_states, str(attacker.id), str(target.id)),
        )
        effective_source = attack_source_with_positioning(effective_source, positioning)
        effective_source = attack_source_with_prone(
            effective_source,
            state.condition_states,
            attacker,
            target,
        )
        attack_roll = resolve_d20_roll(
            _manual_d20_input(
                effective_source,
                natural_roll,
                natural_roll_2,
                natural_rerolls,
            )
        )
        if _uses_attack_action(effective_source):
            attack_use = use_attack_action(
                state,
                attacker,
                maximum_attacks=1
                if effective_source.loading or effective_source.limited_attacks
                else None,
            )
            if not attack_use.accepted:
                raise ValueError(attack_use.message)
            state_after_resource = attack_use.state
        else:
            resource_use = self._resources.consume_action_and_source_resource(
                state,
                attacker,
                spell_level=effective_source.spell_level,
                spell_id=effective_source.id,
                cast_level=effective_source.cast_level,
                action_cost=effective_source.action_cost,
                resource_pool_id=effective_source.resource_pool_id,
                resource_cost=effective_source.resource_cost,
            )
            state_after_resource = resource_use.state
        if _uses_attack_action(effective_source):
            state_after_resource = _consume_attack_source_resource(
                state_after_resource,
                str(attacker.id),
                effective_source,
            )
        state_after_resource = _consume_attack_ammunition(
            state_after_resource,
            str(attacker.id),
            effective_source,
        )
        if effective_source.thrown and effective_source.source_item_id is not None:
            state_after_resource = expend_thrown_weapon(
                state_after_resource,
                str(attacker.id),
                effective_source.source_item_id,
                selected.selected_target.position,
            )
        resolution = resolve_attack(
            AttackDeclaration(attacker, selected.selected_target, effective_source),
            attack_roll,
            selected.action_use,
        )
        updated_effects = consume_next_attack_effects(
            active_effects,
            str(attacker.id),
            selected.selected_target.id,
        )
        triggered_state = set_two_weapon_trigger(
            state_after_resource,
            two_weapon_trigger_item_id(attacker, source),
        )
        updated_state = replace(
            triggered_state,
            hidden_states=reveal_actor(triggered_state.hidden_states, str(attacker.id)),
        )
        applied: AppliedDamageResult | None = None
        message = _player_attack_message(
            attacker.name,
            selected.selected_target.name,
            attack_roll.total,
            resolution.hit,
            resolution.critical,
        )
        if resolution.hit:
            if effective_source.on_hit_condition is not None:
                target_actor = _actor_by_id(updated_state, selected.selected_target.id)
                if not (
                    effective_source.weapon_special_rule is not None
                    and effective_source.weapon_special_rule.value == "net"
                    and target_actor.size.value in {"large", "huge", "gargantuan"}
                ):
                    application = apply_condition(
                        updated_state.condition_states,
                        target_actor,
                        CombatCondition(effective_source.on_hit_condition),
                        source_actor_id=str(attacker.id),
                        source_label=effective_source.name,
                        duration=effective_source.on_hit_condition_duration,
                        expiration_actor_id=(
                            str(attacker.id)
                            if effective_source.on_hit_condition_expiration == "source"
                            else str(target_actor.id)
                        ),
                        source_spell_id=(
                            effective_source.id
                            if effective_source.source_type == AttackSourceType.SPELL
                            else None
                        ),
                        source_spell_level=(
                            effective_source.spell_level
                            if effective_source.source_type == AttackSourceType.SPELL
                            else None
                        ),
                    )
                    updated_state = replace(
                        updated_state,
                        condition_states=application.condition_states,
                    )
                    message = f"{message} {application.message}"
                else:
                    message = f"{message} {target_actor.name} jest zbyt duży dla sieci."
            if (
                effective_source.on_hit_condition is None
                or _source_deals_damage(effective_source)
            ):
                damage_resolution = self._spell_saves.apply_target_damage(
                    updated_state,
                    target_id=selected.selected_target.id,
                    source=effective_source,
                    base_damage=max(0, int(damage)),
                    critical=resolution.critical,
                )
                updated_state = damage_resolution.state
                applied = damage_resolution.applied_damage
                message = f"{message} {_damage_application_message(applied)}"
        return PlayerAttackTransition(
            state=updated_state,
            active_effects=updated_effects,
            pending=None,
            board_message="",
            message_title="Atak",
            message_body=message,
            event_type="ui_combat_player_attack",
            event_payload=(
                ("attacker_id", str(attacker.id)),
                ("target_id", selected.selected_target.id),
                ("natural_roll", attack_roll.natural_roll),
                ("natural_rolls", list(attack_roll.natural_rolls)),
                ("total", attack_roll.total),
                ("hit", resolution.hit),
                ("critical", resolution.critical),
                ("damage", int(damage) if resolution.hit else 0),
                ("target_ac", selected.selected_target.ac),
                ("cover_level", positioning.cover_level.value),
                ("cover_bonus", positioning.cover_bonus),
                ("cover_sources", list(positioning.cover_sources)),
                ("ranged_in_melee", bool(positioning.ranged_threat_actor_ids)),
                ("damage_result", _applied_damage_payload(applied)),
                ("resource_pool_id", effective_source.resource_pool_id),
                ("resource_cost", effective_source.resource_cost if effective_source.resource_pool_id else 0),
            ),
            clear_combat_help=True,
            clear_movement_preview=True,
            applied_damage=applied,
        )


def _active_hero(state: CombatState) -> Actor:
    if state.status != CombatStatus.ACTIVE:
        raise ValueError("Walka nie jest aktywna.")
    actor = current_actor(state)
    if actor.faction != Faction.ALLY:
        raise ValueError("To nie jest tura bohatera.")
    return actor


def _require_usable_source(
    actor: Actor,
    source: AttackSource | HealingSource,
    *,
    active_effects: tuple[ActiveCombatEffect, ...] = (),
) -> None:
    source_item_id = getattr(source, "source_item_id", None)
    if source_item_id is not None:
        items = tuple(
            item
            for item in actor.inventory
            if item.id == source_item_id or item.source_ref == source_item_id
        )
        if not any(item_power_available(item) and item.equipped for item in items):
            raise ValueError(f"{source.name} nie jest obecnie trzymane ani wyposażone.")
    if not spell_is_prepared(
        actor.spell_preparation,
        source.id,
        casting_kind=source.casting_kind.value,
        legacy_prepared=source.prepared,
    ):
        raise ValueError(f"Czar {source.name} nie został przygotowany.")
    if not can_consume_spell_resource(
        actor,
        getattr(source, "spell_level", 0),
        getattr(source, "cast_level", None),
        source.id,
    ):
        raise ValueError(f"Brak slotów albo użycia wrodzonego czaru dla {source.name}.")
    from dnd_board_game.combat import actor_spell_cast_validation

    cast_validation = actor_spell_cast_validation(
        actor,
        source.id,
        cast_level=getattr(source, "cast_level", None),
        ignore_verbal_somatic=(
            "metamagic_subtle" in getattr(source, "metamagic_ids", ())
        ),
        verbal_components_blocked=(
            "metamagic_subtle" not in getattr(source, "metamagic_ids", ())
            and _actor_is_silenced(actor, active_effects)
        ),
    )
    if cast_validation is not None and not cast_validation.valid:
        raise ValueError(" ".join(cast_validation.errors))
    resource_pool_id = getattr(source, "resource_pool_id", None)
    resource_cost = int(getattr(source, "resource_cost", 1))
    if resource_pool_id is not None and not can_spend_actor_resource(
        actor,
        resource_pool_id,
        resource_cost,
    ):
        raise ValueError(f"Brak dostępnych użyć: {source.name}.")
    ammunition_type = getattr(source, "ammunition_type", None)
    if ammunition_type is not None and not has_ammunition(actor, ammunition_type):
        raise ValueError(f"Brak amunicji typu {ammunition_type} dla {source.name}.")
    if ammunition_type is not None and source_item_id is not None:
        weapon = next(
            (
                item
                for item in actor.inventory
                if item.id == source_item_id or item.source_ref == source_item_id
            ),
            None,
        )
        if (
            weapon is not None
            and hands_required(weapon) == 1
            and free_hand_count(actor.inventory) < 1
        ):
            raise ValueError(
                f"{source.name} wymaga wolnej drugiej ręki do załadowania amunicji."
            )


def _actor_is_silenced(
    actor: Actor,
    active_effects: tuple[ActiveCombatEffect, ...],
) -> bool:
    from dnd_board_game.combat import actor_in_silence_zone

    return actor_in_silence_zone(actor, active_effects)


def _consume_attack_source_resource(
    state: CombatState,
    actor_id: str,
    source: AttackSource,
) -> CombatState:
    if source.resource_pool_id is None:
        return state
    actor = _actor_by_id(state, actor_id)
    usage = spend_actor_resource(actor, source.resource_pool_id, source.resource_cost)
    return replace_actor(state, usage.actor_after)


def _consume_attack_ammunition(
    state: CombatState,
    actor_id: str,
    source: AttackSource,
) -> CombatState:
    if source.ammunition_type is None:
        return state
    actor = _actor_by_id(state, actor_id)
    usage = consume_ammunition(actor, source.ammunition_type)
    recorded = record_ammunition_expenditure(state, actor, usage)
    return replace_actor(recorded, usage.actor_after)


def _validated_attack(
    state: CombatState,
    board: BoardState,
    source: AttackSource,
    pending: PendingPlayerAttack,
    scene_objects: tuple[SceneObject, ...] = (),
) -> tuple[Actor, Actor, AttackActionState, AttackPositioning]:
    attacker = _require_pending_attacker(state, pending)
    if not pending.twinned_second_attack:
        _require_attack_economy(
            state,
            attacker,
            source,
            two_weapon_bonus=pending.two_weapon_bonus,
            class_bonus_attack=pending.class_bonus_attack,
        )
    action = start_attack_action(board, attacker, state.actors, source, state.hidden_states)
    selected = select_attack_target(action, target_id=pending.target_id)
    assert selected.selected_target is not None
    target = _actor_by_id(state, selected.selected_target.id)
    positioning = evaluate_attack_positioning(
        board,
        attacker,
        target,
        source,
        state.actors,
        scene_objects,
        state.condition_states,
    )
    if positioning.total_cover:
        raise ValueError("Cel ma pełną osłonę i nie może zostać zaatakowany.")
    selected = replace(
        selected,
        selected_target=replace(
            selected.selected_target,
            ac=selected.selected_target.ac + positioning.cover_bonus,
        ),
    )
    return attacker, target, selected, positioning


def _positioning_pending_fields(positioning: AttackPositioning) -> dict[str, object]:
    return {
        "cover_level": positioning.cover_level.value,
        "cover_bonus": positioning.cover_bonus,
        "cover_sources": positioning.cover_sources,
        "ranged_threat_actor_ids": positioning.ranged_threat_actor_ids,
        "flanking_ally_ids": positioning.flanking_ally_ids,
    }


def _source_for_pending(
    actor: Actor,
    source: AttackSource,
    pending: PendingPlayerAttack,
) -> AttackSource:
    if not pending.two_weapon_bonus:
        return source
    return two_weapon_bonus_attack_source(actor, source)


def _require_attack_economy(
    state: CombatState,
    actor: Actor,
    source: AttackSource,
    *,
    two_weapon_bonus: bool,
    class_bonus_attack: bool = False,
) -> None:
    reserved_hands = len(grappled_actor_ids(state.condition_states, str(actor.id)))
    if not versatile_two_handed_source_is_legal(
        actor,
        source,
        reserved_hands=reserved_hands,
    ):
        raise ValueError("Atak oburącz wymaga wolnej drugiej ręki.")
    if two_weapon_bonus:
        if state.turn_action.bonus_action_use != ActionUse.ACTION_AVAILABLE:
            raise ValueError("Akcja bonusowa w tej turze została już zużyta.")
        if not two_weapon_bonus_source_is_legal(
            actor,
            state.turn_action.two_weapon_trigger_item_id,
            source,
        ):
            raise ValueError("Ten atak nie jest legalnym atakiem drugą bronią.")
        return
    if class_bonus_attack:
        if (
            state.turn_action.bonus_attacks_remaining < 1
            or state.turn_action.bonus_attack_source_id != source.id
        ):
            raise ValueError("Ten klasowy bonusowy atak nie jest dostępny.")
        return
    if _uses_attack_action(source):
        if (
            (source.loading or source.limited_attacks)
            and state.turn_action.attack_action_active
            and state.turn_action.attacks_used >= 1
        ):
            if source.loading:
                raise ValueError(
                    "Właściwość loading pozwala oddać tylko jeden strzał na akcję."
                )
            raise ValueError("Ta broń pozwala wykonać tylko jeden atak w ramach akcji.")
        if not can_use_attack_action(state, actor):
            raise ValueError("Wykorzystano już wszystkie ataki tej akcji.")
    elif (
        source.action_cost == ActionEconomyCost.ACTION
        and state.turn_action.action_use != ActionUse.ACTION_AVAILABLE
    ):
        raise ValueError("Akcja w tej turze została już zużyta.")
    elif (
        source.action_cost == ActionEconomyCost.BONUS_ACTION
        and state.turn_action.bonus_action_use != ActionUse.ACTION_AVAILABLE
    ):
        raise ValueError("Akcja bonusowa w tej turze została już zużyta.")


def _uses_attack_action(source: AttackSource) -> bool:
    return source.source_type.value == "weapon" and source.area is None


def _twinned_second_attack_pending(
    pending: PendingPlayerAttack,
) -> PendingPlayerAttack | None:
    if pending.twinned_target_id is None or pending.twinned_second_attack:
        return None
    return replace(
        pending,
        target_id=pending.twinned_target_id,
        twinned_target_id=None,
        twinned_second_attack=True,
        stage="attack_roll",
        natural_roll=None,
        natural_rolls=(),
        total=None,
        hit=None,
        critical=False,
        saving_throws=(),
    )


def _require_pending_attacker(state: CombatState, pending: PendingPlayerAttack) -> Actor:
    attacker = _active_hero(state)
    if str(attacker.id) != pending.attacker_id:
        raise ValueError("Oczekujący atak nie należy do aktywnego aktora.")
    return attacker


def _has_horde_breaker_target(
    *,
    board: BoardState,
    state: CombatState,
    attacker: Actor,
    original_target: Actor,
    source: AttackSource,
) -> bool:
    legal_targets = start_attack_action(
        board,
        attacker,
        state.actors,
        source,
        state.hidden_states,
    ).legal_targets
    return any(
        target.id != str(original_target.id)
        and grid_distance_feet(target.position, original_target.position) <= 5
        for target in legal_targets
    )


def _actor_by_id(state: CombatState, actor_id: str) -> Actor:
    actor = next((candidate for candidate in state.actors if str(candidate.id) == actor_id), None)
    if actor is None:
        raise ValueError(f"Nieznany cel ataku: {actor_id}.")
    return actor


def _source_deals_damage(source: AttackSource) -> bool:
    return any(
        component.dice is not None
        or int(component.fixed or 0) + component.modifier > 0
        for component in source.damage_components
    )


def _spell_save_cover_modifiers(
    source: AttackSource,
    positioning: AttackPositioning,
) -> tuple[RollModifier, ...]:
    if source.id == "sacred_flame":
        return ()
    return dexterity_save_cover_modifiers(
        source.save_ability,
        positioning,
    )


def _manual_d20_input(
    source: AttackSource,
    natural_roll: int,
    natural_roll_2: int | None,
    natural_rerolls: tuple[int, ...] = (),
) -> D20RollInput:
    request = source.attack_roll_request
    if request.mode == RollMode.NORMAL:
        return D20RollInput(
            request,
            int(natural_roll),
            natural_rerolls=tuple(int(value) for value in natural_rerolls),
        )
    if natural_roll_2 is None:
        raise ValueError("Ten rzut wymaga wpisania dwóch wyników d20.")
    return D20RollInput(
        request,
        int(natural_roll),
        int(natural_roll_2),
        tuple(int(value) for value in natural_rerolls),
    )


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


def _spell_save_message(save: SpellSaveResult) -> str:
    payload = save.as_payload()
    outcome = "sukces" if save.success else "porażka"
    return (
        f"{save.actor_name}: rzut obronny na {payload['ability_label']} "
        f"d20 {save.natural_roll}, modyfikator {_format_signed(save.modifier)}, "
        f"razem {save.total} przeciw ST {save.dc}: {outcome}."
    )


def _format_signed(value: int) -> str:
    return f"+{value}" if value >= 0 else str(value)


def _damage_application_message(result: AppliedDamageResult) -> str:
    return applied_damage_message(result)


def _applied_damage_payload(result: AppliedDamageResult | None) -> dict[str, object] | None:
    return applied_damage_payload(result)


def _defeat_message(result: AppliedDamageResult) -> str:
    if result.instant_death:
        return " Obrażenia powodują natychmiastową śmierć."
    if result.death_save_failures_added:
        return f" Porażki death saves: +{result.death_save_failures_added}."
    if result.defeated_by_damage and result.actor_after.needs_death_save():
        return " Cel traci przytomność i zaczyna wykonywać death saves."
    return " Cel zostaje pokonany." if result.defeated_by_damage else ""
