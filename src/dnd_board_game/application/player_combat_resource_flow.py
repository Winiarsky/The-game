from __future__ import annotations

from dataclasses import dataclass, replace
from random import Random
from typing import Protocol

from dnd_board_game.actions import ActionResourceResolver
from dnd_board_game.actors import (
    Actor,
    ActorResourcePool,
    ExhaustionRollKind,
    Faction,
    RecoveryPeriod,
    apply_exhaustion_to_roll_request,
    actor_has_feature,
    saving_throw_roll_modifiers,
    spell_is_prepared,
)
from dnd_board_game.combat import (
    ActionEconomyCost,
    ActiveCombatEffect,
    AppliedDamageResult,
    CombatState,
    CombatStatus,
    ConditionState,
    HealingSource,
    HealingSourceType,
    SpellArea,
    SpellAreaShape,
    area_positions_for_center,
    area_positions_for_direction,
    apply_healing_result,
    legal_area_centers,
    direction_anchor_positions,
    end_invisibility_effects,
    end_sanctuary_effects,
    available_cast_levels,
    can_consume_spell_resource,
    current_actor,
    grid_distance_feet,
    replace_actor,
    resolve_spell_save,
    use_action_economy_cost,
)
from dnd_board_game.world import BoardState, Coordinate
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
    actor_is_immune_to_effect,
    SavingThrowEffectTag,
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
    concentration: bool
    instructions: str
    resource_pool_id: str | None
    resource_cost: int
    metamagic_ids: tuple[str, ...]
    duration_multiplier: int
    mechanic_family: str
    resolver_id: str
    cast_flag: str
    damage_die_sides: int
    damage_modifier: int
    upcast_value_per_level: int
    effect_options: tuple[str, ...]
    effect_kind: str | None
    condition: object | None
    save_ability: str | None
    save_dc: int | None
    save_timing: str | None
    duration: str
    hit_point_pool_dice_count: int
    upcast_hit_point_pool_dice_per_level: int
    excluded_creature_types: tuple[str, ...]
    ongoing_damage_dice_count: int
    damage_type: str
    save_damage_on_success: str
    damage_on_cast: bool
    area: SpellArea | None


@dataclass(frozen=True, slots=True)
class PendingConcentrationAction:
    caster_id: str
    action_id: str
    target_ids: tuple[str, ...]
    cast_level: int
    maximum_targets: int
    selected_target_ids: tuple[str, ...] = ()
    legal_positions: tuple[Coordinate, ...] = ()
    anchor: Coordinate | None = None
    area_positions: tuple[Coordinate, ...] = ()
    casting_minutes: int = 0
    prepared_roll_total: int | None = None


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
    scene_flag_changes: tuple[tuple[str, object], ...] = ()


class PlayerCombatResourceFlowService:
    """Resolve consumable combat actions and concentration lifecycle."""

    def __init__(self) -> None:
        self._resources = ActionResourceResolver()

    def use_assisted_spell(
        self,
        *,
        state: CombatState,
        active_effects: tuple[ActiveCombatEffect, ...],
        action: CombatActionSpec,
        cast_level: int | None = None,
    ) -> CombatResourceTransition:
        """Commit a legal cast whose table-facing consequence needs adjudication.

        This path is intentionally stricter than the old ``manual`` placeholder:
        it validates preparation, components and slot level, spends the correct
        action and resource, replaces concentration, and persists a traceable
        spell effect.  Only the consequence described by ``instructions`` stays
        in the hands of the players.
        """

        actor = _active_hero(state)
        if action.action_type != "assisted_spell":
            raise ValueError("To nie jest wspomagany czar.")
        instructions = str(getattr(action, "instructions", "")).strip()
        if not instructions:
            raise ValueError("Wspomagany czar nie ma instrukcji rozstrzygnięcia.")
        selected_level = _selected_cast_level(actor, action, cast_level)
        _require_usable_action(
            actor,
            action,
            selected_level,
            condition_states=state.condition_states,
            active_effects=active_effects,
        )
        resource_use = self._resources.consume_action_and_source_resource(
            state,
            actor,
            spell_level=action.spell_level,
            spell_id=action.id,
            cast_level=selected_level,
            action_cost=_action_cost(action),
            resource_pool_id=getattr(action, "resource_pool_id", None),
            resource_cost=int(getattr(action, "resource_cost", 1)),
        )
        updated_effects = end_invisibility_effects(
            active_effects,
            str(actor.id),
        )
        removed: tuple[ActiveCombatEffect, ...] = ()
        effect_id = ""
        if bool(getattr(action, "concentration", False)):
            removed = concentration_effects_for_actor(
                updated_effects,
                str(actor.id),
            )
            updated_effects = remove_concentration_effects(
                updated_effects,
                str(actor.id),
            )
            effect_id = f"concentration_assisted:{actor.id}:{action.id}"
            updated_effects = apply_active_effect(
                updated_effects,
                ActiveCombatEffect(
                    id=effect_id,
                    actor_id=str(actor.id),
                    kind="concentration_assisted",
                    label=action.label,
                    object_id=f"spell:{action.id}",
                    source_actor_id=str(actor.id),
                    source=EffectSource(
                        EffectSourceType.SPELL,
                        action.id,
                        action.label,
                    ),
                    duration=EffectDuration.CONCENTRATION,
                    stacking=EffectStackingPolicy.STACK,
                    stacking_key=f"concentration:{actor.id}",
                    spell_level=selected_level,
                ),
            ).active_effects
        slot_label = (
            f" ze slotu {selected_level}. poziomu"
            if action.spell_level > 0
            else ""
        )
        ended = (
            " Poprzednia koncentracja zakończona: "
            f"{', '.join(effect.label for effect in removed)}."
            if removed
            else ""
        )
        message = (
            f"{actor.name} rzuca {action.label}{slot_label}. "
            f"Rozstrzygnięcie przy stole: {instructions}"
            + (
                " Czas działania jest podwojony przez Extended Spell."
                if int(getattr(action, "duration_multiplier", 1)) > 1
                else ""
            )
            + (
                f" Metamagic: {', '.join(getattr(action, 'metamagic_ids', ()))}."
                if getattr(action, "metamagic_ids", ())
                else ""
            )
            + ended
        )
        return CombatResourceTransition(
            state=resource_use.state,
            active_effects=updated_effects,
            board_message=message,
            message_title="Czar wspomagany",
            message_body=message,
            event_type="ui_combat_assisted_spell_cast",
            event_payload=(
                ("caster_id", str(actor.id)),
                ("action_id", action.id),
                ("cast_level", selected_level),
                ("instructions", instructions),
                ("concentration_effect_id", effect_id),
                ("removed_effect_ids", [effect.id for effect in removed]),
                ("metamagic_ids", list(getattr(action, "metamagic_ids", ()))),
                (
                    "duration_multiplier",
                    int(getattr(action, "duration_multiplier", 1)),
                ),
            ),
            clear_player_choices=True,
            clear_movement_preview=True,
            scene_flag_changes=((action.cast_flag, True),),
        )

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
        board: BoardState | None = None,
    ) -> CombatResourceTransition:
        actor = _active_hero(state)
        if action.action_type not in {
            "concentration_attack_bonus",
            "targeted_status",
        }:
            raise ValueError("Nieznana akcja statusowa.")
        selected_cast_level = _selected_cast_level(actor, action, cast_level)
        _require_usable_action(
            actor,
            action,
            selected_cast_level,
            condition_states=state.condition_states,
            active_effects=active_effects,
        )
        area = getattr(action, "area", None)
        if area is not None and board is None:
            raise ValueError("Obszarowy czar statusowy wymaga aktywnej planszy.")
        targets = (
            ()
            if area is not None
            else _concentration_targets(state, actor, action)
        )
        if area is None and not targets:
            raise ValueError("Brak legalnego celu czaru koncentracyjnego.")
        maximum_targets = spell_target_count(
            base_targets=int(getattr(action, "target_count", 1)),
            spell_level=action.spell_level,
            cast_level=selected_cast_level,
            targets_per_slot_level=int(
                getattr(action, "upcast_targets_per_level", 0)
            ),
        )
        legal_positions = (
            legal_area_centers(board, actor.position, action.range_feet)
            if area is not None
            and area.shape in {SpellAreaShape.RADIUS, SpellAreaShape.CUBE}
            else direction_anchor_positions(board, actor.position)
            if area is not None
            else ()
        )
        pending = PendingConcentrationAction(
            caster_id=str(actor.id),
            action_id=action.id,
            target_ids=tuple(str(target.id) for target in targets),
            cast_level=selected_cast_level,
            maximum_targets=maximum_targets,
            legal_positions=legal_positions,
        )
        return CombatResourceTransition(
            state=state,
            active_effects=active_effects,
            pending_action=pending,
            board_message=(
                f"{action.label}: wybierz podświetlony środek lub kierunek na planszy."
                if area is not None
                else f"{action.label}: wybierz do {maximum_targets} legalnych celów na planszy."
            ),
            message_title="Koncentracja",
            message_body=(
                f"{actor.name} przygotowuje {action.label}. "
                + (
                    "Wybierz podświetlony środek lub kierunek obszaru na planszy."
                    if area is not None
                    else f"Wybierz od 1 do {maximum_targets} celów na planszy."
                )
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

    def select_concentration_area(
        self,
        *,
        state: CombatState,
        board: BoardState,
        action: CombatActionSpec,
        pending: PendingConcentrationAction,
        position: Coordinate,
    ) -> PendingConcentrationAction:
        area = getattr(action, "area", None)
        if area is None:
            raise ValueError("Ta akcja nie wybiera obszaru.")
        if position not in pending.legal_positions:
            raise ValueError("Kliknij podświetlony środek lub kierunek czaru.")
        caster = _active_hero(state)
        area_positions = (
            area_positions_for_center(board, position, area)
            if area.shape in {SpellAreaShape.RADIUS, SpellAreaShape.CUBE}
            else area_positions_for_direction(
                board,
                caster.position,
                position,
                area,
            )
        )
        legal_targets = _concentration_targets(
            state,
            caster,
            action,
            enforce_range=False,
        )
        targets = tuple(
            target
            for target in legal_targets
            if target.position in area_positions
        )
        target_ids = tuple(str(target.id) for target in targets)
        return replace(
            pending,
            target_ids=target_ids,
            selected_target_ids=target_ids,
            anchor=position,
            area_positions=area_positions,
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
        rng: Random | None = None,
        roll_total: int | None = None,
        effect_option: str = "",
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
        if (
            not selected_target_ids
            and int(getattr(action, "hit_point_pool_dice_count", 0)) > 0
        ):
            selected_target_ids = pending.target_ids
        is_persistent_zone = (
            str(getattr(action, "effect_kind", ""))
            in {
                "ongoing_damage_zone",
                "obscuring_zone",
                "silence_zone",
                "spike_growth_zone",
                "web_zone",
                "zone_of_truth_zone",
            }
            and pending.anchor is not None
        )
        if not selected_target_ids and not is_persistent_zone:
            raise ValueError("Wybierz co najmniej jeden cel czaru koncentracyjnego.")
        if len(selected_target_ids) != len(set(selected_target_ids)):
            raise ValueError("Ten sam cel czaru został wybrany więcej niż raz.")
        if len(selected_target_ids) > pending.maximum_targets:
            raise ValueError(
                f"Ten poziom czaru pozwala wybrać maksymalnie {pending.maximum_targets} celów."
            )
        if set(selected_target_ids) - set(pending.target_ids):
            raise ValueError("Wybrano nielegalny cel czaru koncentracyjnego.")
        _require_usable_action(
            caster,
            action,
            pending.cast_level,
            condition_states=state.condition_states,
            active_effects=active_effects,
        )
        targets = tuple(
            _actor_by_id(state, selected_id)
            for selected_id in selected_target_ids
        )
        magic_weapon_item_id = ""
        if action.id == "magic_weapon":
            if len(targets) != 1:
                raise ValueError("Magiczna broń wymaga jednego posiadacza broni.")
            magic_weapon_item_id = effect_option.strip()
            weapon = next(
                (
                    item
                    for item in targets[0].inventory
                    if item.id == magic_weapon_item_id and item.kind == "weapon"
                ),
                None,
            )
            if weapon is None:
                raise ValueError("Wybierz konkretną broń celu.")
            if (
                weapon.magic_effects
                or weapon.requires_attunement
                or "magical" in weapon.properties
            ):
                raise ValueError("Magiczna broń działa wyłącznie na niemagiczną broń.")
        resource_use = self._resources.consume_action_and_source_resource(
            state,
            caster,
            spell_level=action.spell_level,
            spell_id=action.id,
            cast_level=pending.cast_level,
            action_cost=_action_cost(action),
        )
        is_concentration = bool(getattr(action, "concentration", False)) or (
            action.action_type == "concentration_attack_bonus"
        )
        effects_after_cast = end_invisibility_effects(
            active_effects,
            str(caster.id),
        )
        if action.target_faction in {"enemy", "any"}:
            effects_after_cast = end_sanctuary_effects(
                effects_after_cast,
                str(caster.id),
            )
        removed = (
            concentration_effects_for_actor(effects_after_cast, str(caster.id))
            if is_concentration
            else ()
        )
        updated_effects = (
            remove_concentration_effects(effects_after_cast, str(caster.id))
            if is_concentration
            else effects_after_cast
        )
        if action.id == "find_familiar":
            updated_effects = tuple(
                effect
                for effect in updated_effects
                if not (
                    effect.source_actor_id == str(caster.id)
                    and effect.kind.startswith("familiar:")
                )
            )
        applied_effects: list[ActiveCombatEffect] = []
        die_sides = int(getattr(action, "damage_die_sides", 0))
        pool_dice_count = int(
            getattr(action, "hit_point_pool_dice_count", 0)
        ) + max(0, pending.cast_level - action.spell_level) * int(
            getattr(action, "upcast_hit_point_pool_dice_per_level", 0)
        )
        enhance_constitution = (
            action.id == "enhance_ability"
            and effect_option == "constitution"
        )
        value_dice_count = 2 if enhance_constitution else pool_dice_count
        manual_value_roll = pool_dice_count > 0 or str(
            getattr(action, "effect_kind", "")
        ) == "temporary_hit_points" or enhance_constitution
        if die_sides and manual_value_roll:
            maximum_roll = die_sides * max(1, value_dice_count)
            minimum_roll = max(1, value_dice_count)
            if (
                roll_total is None
                or not minimum_roll <= roll_total <= maximum_roll
            ):
                dice_label = (
                    f"{value_dice_count}k{die_sides}"
                    if value_dice_count
                    else f"k{die_sides}"
                )
                raise ValueError(f"Wpisz sumę fizycznego rzutu {dice_label}.")
            base_value = roll_total + int(getattr(action, "damage_modifier", 0))
        else:
            base_value = action.value
        if str(getattr(action, "effect_kind", "")) == "heroism_temp_hp":
            base_value = max(
                1,
                caster.spell_save_dc - 8 - caster.proficiency_bonus,
            )
        effect_value = base_value + max(
            0,
            pending.cast_level - action.spell_level,
        ) * int(getattr(action, "upcast_value_per_level", 0))
        if action.id == "magic_weapon":
            effect_value = min(3, 1 + max(0, (pending.cast_level - 2) // 2))
        base_effect_kind = str(
            getattr(action, "effect_kind", None)
            or "concentration_attack_bonus"
        )
        options = tuple(getattr(action, "effect_options", ()))
        if options:
            if effect_option not in options:
                raise ValueError("Wybierz jeden z wariantów efektu czaru.")
            effect_kind = f"{base_effect_kind}:{effect_option}"
        else:
            effect_kind = base_effect_kind
        if base_effect_kind in {"ongoing_damage", "ongoing_damage_zone"}:
            damage_dice_count = int(
                getattr(action, "ongoing_damage_dice_count", 0)
            ) + max(0, pending.cast_level - action.spell_level) * int(
                getattr(action, "upcast_value_per_level", 0)
            )
            effect_kind = ":".join(
                (
                    base_effect_kind,
                    str(damage_dice_count),
                    str(die_sides),
                    str(getattr(action, "damage_type", "force")),
                    str(getattr(action, "save_ability", "") or "-"),
                    str(getattr(action, "save_damage_on_success", "none")),
                )
            )
        save_results: list[tuple[str, object]] = []
        affected_targets: list[Actor] = []
        for target in targets:
            save_ability = getattr(action, "save_ability", None)
            save_is_required = save_ability is not None and (
                action.id != "levitate" or target.faction != caster.faction
            )
            if save_is_required and base_effect_kind != "ongoing_damage":
                if rng is None:
                    raise ValueError("Ten czar wymaga generatora rzutu obronnego.")
                save = resolve_spell_save(
                    target,
                    ability=save_ability,
                    dc=getattr(action, "save_dc", None)
                    or caster.spell_save_dc,
                    natural_roll=rng.randint(1, 20),
                    condition_states=resource_use.state.condition_states,
                    combat_actors=resource_use.state.actors,
                )
                save_results.append((str(target.id), save.as_payload()))
                if save.success:
                    continue
            affected_targets.append(target)
        if pool_dice_count and action.id != "prayer_of_healing":
            remaining_pool = effect_value
            pooled_targets: list[Actor] = []
            for target in sorted(affected_targets, key=lambda actor: actor.hp):
                if (
                    action.id == "sleep"
                    and actor_is_immune_to_effect(
                        target,
                        SavingThrowEffectTag.MAGICAL_SLEEP.value,
                    )
                ):
                    continue
                if target.hp > remaining_pool:
                    continue
                pooled_targets.append(target)
                remaining_pool -= target.hp
            affected_targets = pooled_targets
        if base_effect_kind in {
            "ongoing_damage_zone",
            "obscuring_zone",
            "silence_zone",
            "spike_growth_zone",
            "web_zone",
            "zone_of_truth_zone",
        }:
            assert pending.anchor is not None
            assert getattr(action, "area", None) is not None
            zone_effect = ActiveCombatEffect(
                id=f"{effect_kind}:{caster.id}:{action.id}",
                actor_id=str(caster.id),
                kind=effect_kind,
                label=action.label,
                object_id=f"combat_action:{action.id}",
                value=int(
                    action.area.radius_feet
                    if action.area.shape == SpellAreaShape.RADIUS
                    else action.area.length_feet
                ),
                anchor_position=pending.anchor,
                source_actor_id=str(caster.id),
                source=EffectSource(
                    EffectSourceType.SPELL,
                    action.id,
                    action.label,
                ),
                duration=(
                    EffectDuration.CONCENTRATION
                    if is_concentration
                    else _status_effect_duration(action.duration)
                ),
                stacking=EffectStackingPolicy.STACK,
                stacking_key=(
                    f"concentration:{caster.id}"
                    if is_concentration
                    else f"spell-zone:{caster.id}:{action.id}"
                ),
                spell_level=pending.cast_level,
            )
            updated_effects = apply_active_effect(
                updated_effects,
                zone_effect,
            ).active_effects
            applied_effects.append(zone_effect)
        if (
            base_effect_kind == "apply_condition"
            and action.id in {"entangle", "grease"}
            and pending.anchor is not None
            and getattr(action, "area", None) is not None
        ):
            terrain_zone = ActiveCombatEffect(
                id=f"{action.id}_zone:{caster.id}:{action.id}",
                actor_id=str(caster.id),
                kind=f"{action.id}_zone",
                label=action.label,
                object_id=f"combat_action:{action.id}",
                value=int(action.area.length_feet),
                anchor_position=pending.anchor,
                source_actor_id=str(caster.id),
                source=EffectSource(
                    EffectSourceType.SPELL,
                    action.id,
                    action.label,
                ),
                duration=(
                    EffectDuration.CONCENTRATION
                    if is_concentration
                    else _status_effect_duration(action.duration)
                ),
                stacking=EffectStackingPolicy.STACK,
                stacking_key=(
                    f"concentration:{caster.id}"
                    if is_concentration
                    else f"spell-zone:{caster.id}:{action.id}"
                ),
                spell_level=pending.cast_level,
            )
            updated_effects = apply_active_effect(
                updated_effects,
                terrain_zone,
            ).active_effects
            applied_effects.append(terrain_zone)
        for target in affected_targets:
            if base_effect_kind in {
                "ongoing_damage_zone",
                "obscuring_zone",
                "silence_zone",
                "spike_growth_zone",
                "web_zone",
                "zone_of_truth_zone",
            }:
                continue
            if base_effect_kind == "remove_condition":
                continue
            if base_effect_kind in {
                "goodberry_pool",
                "prayer_healing",
                "reveal_hidden_traps",
            }:
                continue
            if base_effect_kind == "apply_condition" and not is_concentration:
                continue
            effect = ActiveCombatEffect(
                id=f"{effect_kind}:{caster.id}:{target.id}:{action.id}",
                actor_id=(
                    str(caster.id)
                    if base_effect_kind == "next_attack_advantage"
                    else str(target.id)
                ),
                kind=(
                    "concentration_condition"
                    if base_effect_kind == "apply_condition"
                    else effect_kind
                ),
                label=action.label,
                object_id=(
                    f"weapon:{magic_weapon_item_id}"
                    if action.id == "magic_weapon"
                    else f"combat_action:{action.id}"
                ),
                value=effect_value,
                anchor_position=(
                    target.position
                    if base_effect_kind.endswith("_zone")
                    else None
                ),
                source_actor_id=str(caster.id),
                target_actor_id=str(target.id),
                source=EffectSource(EffectSourceType.SPELL, action.id, action.label),
                duration=(
                    EffectDuration.CONCENTRATION
                    if is_concentration
                    else _status_effect_duration(action.duration)
                ),
                stacking=EffectStackingPolicy.STACK,
                stacking_key=f"concentration:{caster.id}",
                spell_level=pending.cast_level,
            )
            updated_effects = apply_active_effect(
                updated_effects,
                effect,
            ).active_effects
            applied_effects.append(effect)
            if action.id == "heat_metal":
                heat_penalty = ActiveCombatEffect(
                    id=f"heat-metal-penalty:{caster.id}:{target.id}",
                    actor_id=str(target.id),
                    kind="heat_metal_disadvantage",
                    label="Rozgrzany metal",
                    object_id="combat_action:heat_metal",
                    value=0,
                    source_actor_id=str(caster.id),
                    target_actor_id=str(target.id),
                    source=EffectSource(
                        EffectSourceType.SPELL,
                        "heat_metal",
                        action.label,
                    ),
                    duration=EffectDuration.CONCENTRATION,
                    stacking=EffectStackingPolicy.REFRESH,
                    stacking_key=f"concentration:{caster.id}",
                    spell_level=pending.cast_level,
                )
                updated_effects = apply_active_effect(
                    updated_effects,
                    heat_penalty,
                ).active_effects
                applied_effects.append(heat_penalty)
        updated_state = resource_use.state
        if base_effect_kind == "goodberry_pool":
            current_caster = _actor_by_id(updated_state, str(caster.id))
            pool = ActorResourcePool(
                id="goodberry_charges",
                label="Dobre jagody",
                current=10,
                maximum=10,
                recovery=RecoveryPeriod.NEVER,
            )
            updated_caster = replace(
                current_caster,
                resource_pools=(
                    *tuple(
                        item
                        for item in current_caster.resource_pools
                        if item.id != pool.id
                    ),
                    pool,
                ),
            )
            updated_state = replace_actor(updated_state, updated_caster)
        elif base_effect_kind == "prayer_healing":
            modifier = max(
                0,
                caster.spell_save_dc - 8 - caster.proficiency_bonus,
            )
            healing_source = HealingSource(
                id="prayer_of_healing",
                name=action.label,
                source_type=HealingSourceType.SPELL,
                range_feet=30,
                healing_hint="",
                healing_fixed=effect_value + modifier,
                spell_level=action.spell_level,
                cast_level=pending.cast_level,
                excluded_creature_types=("construct", "undead"),
            )
            for target in affected_targets:
                if target.creature_type in healing_source.excluded_creature_types:
                    continue
                current = _actor_by_id(updated_state, str(target.id))
                healed = apply_healing_result(
                    current,
                    healing_source,
                    effect_value + modifier,
                    condition_states=updated_state.condition_states,
                )
                updated_state = replace_actor(updated_state, healed.actor_after)
        if (
            base_effect_kind == "ongoing_damage"
            and bool(getattr(action, "damage_on_cast", False))
        ):
            from dnd_board_game.combat import (
                DamageComponentInput,
                apply_damage_result,
                resolve_damage,
            )

            if rng is None:
                raise ValueError("Obrażenia okresowe wymagają generatora kości.")
            dice_count = int(getattr(action, "ongoing_damage_dice_count", 0))
            for target in affected_targets:
                rolled_damage = sum(rng.randint(1, die_sides) for _ in range(dice_count))
                applied = apply_damage_result(
                    target,
                    resolve_damage(
                        (
                            DamageComponentInput(
                                rolled_damage,
                                str(getattr(action, "damage_type", "force")),
                                action.label,
                            ),
                        )
                    ),
                )
                updated_state = replace_actor(updated_state, applied.actor_after)
        if base_effect_kind == "apply_condition":
            from dnd_board_game.combat import apply_condition, ConditionSaveTiming

            condition = getattr(action, "condition", None)
            if condition is None:
                raise ValueError("Czar nie określa nakładanego stanu.")
            for target in affected_targets:
                application = apply_condition(
                    updated_state.condition_states,
                    target,
                    condition,
                    source_actor_id=str(caster.id),
                    source_label=action.label,
                    duration=(
                        EffectDuration.CONCENTRATION
                        if is_concentration
                        else _status_effect_duration(action.duration)
                    ),
                    save_ability=(
                        action.save_ability
                        if action.save_timing is not None
                        else None
                    ),
                    save_dc=(
                        action.save_dc or caster.spell_save_dc
                        if action.save_timing is not None
                        else None
                    ),
                    save_timing=(
                        ConditionSaveTiming(action.save_timing)
                        if action.save_timing is not None
                        else None
                    ),
                    source_spell_id=action.id,
                    source_spell_level=pending.cast_level,
                )
                updated_state = replace(
                    updated_state,
                    condition_states=application.condition_states,
                )
        elif base_effect_kind == "remove_condition":
            from dnd_board_game.combat import CombatCondition, remove_condition

            removed_condition = CombatCondition(effect_option)
            for target in affected_targets:
                updated_state = replace(
                    updated_state,
                    condition_states=remove_condition(
                        updated_state.condition_states,
                        str(target.id),
                        removed_condition,
                    ),
                )
        elif effect_kind == "max_hit_points_bonus":
            for target in affected_targets:
                current = _actor_by_id(updated_state, str(target.id))
                updated_state = replace_actor(
                    updated_state,
                    replace(
                        current,
                        max_hp=current.max_hp + effect_value,
                        hp=current.hp + effect_value,
                    ),
                )
        elif effect_kind == "protection_from_poison":
            from dnd_board_game.combat import CombatCondition, remove_condition

            for target in affected_targets:
                updated_state = replace(
                    updated_state,
                    condition_states=remove_condition(
                        updated_state.condition_states,
                        str(target.id),
                        CombatCondition.POISONED,
                    ),
                )
        elif effect_kind in {"temporary_hit_points", "heroism_temp_hp"}:
            for target in affected_targets:
                current = _actor_by_id(updated_state, str(target.id))
                updated_state = replace_actor(
                    updated_state,
                    replace(current, temp_hp=max(current.temp_hp, effect_value)),
                )
            if effect_kind == "heroism_temp_hp":
                from dnd_board_game.combat import CombatCondition, remove_condition

                for target in affected_targets:
                    updated_state = replace(
                        updated_state,
                        condition_states=remove_condition(
                            updated_state.condition_states,
                            str(target.id),
                            CombatCondition.FRIGHTENED,
                        ),
                    )
        elif (
            base_effect_kind == "ability_check_advantage"
            and effect_option == "constitution"
        ):
            for target in affected_targets:
                current = _actor_by_id(updated_state, str(target.id))
                updated_state = replace_actor(
                    updated_state,
                    replace(current, temp_hp=max(current.temp_hp, effect_value)),
                )
        ended = (
            " Poprzednia koncentracja zakończona: "
            f"{', '.join(effect.label for effect in removed)}."
            if removed
            else ""
        )
        effect_description = (
            f"k{effect_value} do ataków i rzutów obronnych"
            if effect_kind == "bless_roll_bonus"
            else f"{effect_value:+d} do efektu"
        )
        message = (
            f"{caster.name} rzuca {action.label} ze slotu {pending.cast_level}. poziomu. "
            + (
                f"Środek strefy: {pending.anchor.as_tuple()}; "
                if base_effect_kind == "ongoing_damage_zone"
                and pending.anchor is not None
                else (
                    f"Cele objęte efektem: "
                    f"{', '.join(target.name for target in affected_targets) or 'brak'}; "
                )
            )
            + f"{effect_description}, dopóki koncentracja trwa.{ended}"
        )
        return CombatResourceTransition(
            state=updated_state,
            active_effects=updated_effects,
            board_message=message,
            message_title="Koncentracja",
            message_body=message,
            event_type="ui_combat_concentration_confirmed",
            event_payload=(
                ("caster_id", str(caster.id)),
                ("target_id", str(targets[0].id) if targets else ""),
                ("target_ids", [str(target.id) for target in targets]),
                ("action_id", action.id),
                ("cast_level", pending.cast_level),
                ("maximum_targets", pending.maximum_targets),
                ("value", effect_value),
                ("effect_kind", effect_kind),
                ("effect_ids", [effect.id for effect in applied_effects]),
                ("saving_throws", dict(save_results)),
                ("removed_effect_ids", [effect.id for effect in removed]),
            ),
            clear_pending_action=True,
            clear_movement_preview=True,
            scene_flag_changes=(
                ((action.cast_flag, True),)
                if str(getattr(action, "cast_flag", "")).strip()
                else ()
            ),
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
            if actor_has_feature(actor, "flaw_arcane_echo") and not any(
                effect.actor_id == actor_id and effect.kind == "flaw_arcane_echo_used"
                for effect in active_effects
            ):
                used = ActiveCombatEffect(
                    id=f"flaw_arcane_echo_used:{actor_id}",
                    actor_id=actor_id,
                    kind="flaw_arcane_echo_used",
                    label="Echo magicznego wycieku — wykorzystane",
                    object_id="feature:flaw_arcane_echo",
                    value=0,
                    source=EffectSource(
                        EffectSourceType.SYSTEM,
                        "flaw_arcane_echo",
                        "Skaza: Echo magicznego wycieku",
                    ),
                    duration=EffectDuration.UNTIL_ENCOUNTER_END,
                )
                echo = ActiveCombatEffect(
                    id=f"flaw_arcane_echo_active:{actor_id}",
                    actor_id=actor_id,
                    kind="flaw_arcane_echo_active",
                    label="Echo magicznego wycieku",
                    object_id="feature:flaw_arcane_echo",
                    value=0,
                    source=EffectSource(
                        EffectSourceType.SYSTEM,
                        "flaw_arcane_echo",
                        "Skaza: Echo magicznego wycieku",
                    ),
                    duration=EffectDuration.UNTIL_TURN_END,
                    expiration_actor_id=actor_id,
                )
                updated_effects = apply_active_effect(updated_effects, used).active_effects
                updated_effects = apply_active_effect(updated_effects, echo).active_effects
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
        if effect.duration == EffectDuration.CONCENTRATION
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


def _status_effect_duration(value: str) -> EffectDuration:
    return {
        "next_turn_start": EffectDuration.UNTIL_TURN_START,
        "next_attack": EffectDuration.UNTIL_NEXT_ATTACK,
        "turn_end": EffectDuration.UNTIL_TURN_END,
        "encounter": EffectDuration.UNTIL_ENCOUNTER_END,
        "short_rest": EffectDuration.UNTIL_SHORT_REST,
        "long_rest": EffectDuration.UNTIL_LONG_REST,
        "scenario": EffectDuration.UNTIL_SCENARIO_END,
        "permanent": EffectDuration.PERMANENT,
    }.get(value, EffectDuration.UNTIL_ENCOUNTER_END)


def _require_usable_action(
    actor: Actor,
    action: CombatActionSpec,
    cast_level: int | None = None,
    *,
    condition_states: tuple[ConditionState, ...] = (),
    active_effects: tuple[ActiveCombatEffect, ...] = (),
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
        action.id,
    ):
        raise ValueError(f"Brak slotów czaru dla {action.label}.")
    from dnd_board_game.combat import actor_spell_cast_validation

    validation = actor_spell_cast_validation(
        actor,
        action.id,
        cast_level=cast_level,
        ignore_verbal_somatic=(
            "metamagic_subtle" in getattr(action, "metamagic_ids", ())
        ),
        condition_states=condition_states,
        active_effects=active_effects,
    )
    if validation is not None and not validation.valid:
        raise ValueError(" ".join(validation.errors))


def _selected_cast_level(
    actor: Actor,
    action: CombatActionSpec,
    cast_level: int | None,
) -> int:
    if action.spell_level <= 0:
        if cast_level not in {None, 0}:
            raise ValueError("Cantrip nie korzysta ze slotu czaru.")
        return 0
    from dnd_board_game.combat import actor_spell_cast_validation

    validation = actor_spell_cast_validation(
        actor,
        action.id,
        cast_level=cast_level,
        ignore_verbal_somatic=(
            "metamagic_subtle" in getattr(action, "metamagic_ids", ())
        ),
    )
    if validation is not None:
        if not validation.valid:
            raise ValueError(" ".join(validation.errors))
        return validation.cast_level
    levels = available_cast_levels(actor, action.spell_level)
    selected = levels[0] if cast_level is None and levels else cast_level
    if selected is None or selected not in levels:
        raise ValueError(f"Brak slotu {cast_level}. poziomu dla {action.label}.")
    return selected


def _concentration_targets(
    state: CombatState,
    actor: Actor,
    action: CombatActionSpec,
    *,
    enforce_range: bool = True,
) -> tuple[Actor, ...]:
    if action.target_faction in {"ally", "enemy", "any"}:
        range_feet = int(getattr(action, "range_feet", 0))
        return tuple(
            candidate
            for candidate in state.actors
            if (
                True
                if action.target_faction == "any"
                else candidate.faction == actor.faction
                if action.target_faction == "ally"
                else candidate.faction not in {actor.faction, Faction.NEUTRAL}
            )
            and not candidate.is_defeated()
            and not (
                action.id == "warding_bond"
                and candidate.id == actor.id
            )
            and candidate.creature_type
            not in getattr(action, "excluded_creature_types", ())
            and (
                action.id != "heat_metal"
                or _actor_has_usable_metal_object(candidate)
            )
            and (
                candidate.id == actor.id
                or (
                    not enforce_range
                    or (
                        range_feet > 0
                        and grid_distance_feet(actor.position, candidate.position)
                        <= range_feet
                    )
                )
            )
        )
    return (actor,)


def _actor_has_usable_metal_object(actor: Actor) -> bool:
    return any(
        item.available
        and "metallic" in item.properties
        and (
            item.equipped
            or bool(getattr(item, "held_in", ()))
            or item.kind in {"weapon", "armor", "shield"}
        )
        for item in actor.inventory
    )


def _actor_by_id(state: CombatState, actor_id: str) -> Actor:
    actor = next((candidate for candidate in state.actors if str(candidate.id) == actor_id), None)
    if actor is None:
        raise ValueError(f"Nieznany aktor walki: {actor_id}.")
    return actor
