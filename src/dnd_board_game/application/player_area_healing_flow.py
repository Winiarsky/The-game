from __future__ import annotations

from dataclasses import dataclass, replace
from random import Random
from typing import Mapping

from dnd_board_game.actions import AreaSpellResolver, HealingActionResolver
from dnd_board_game.actors import (
    Actor,
    Faction,
    can_spend_actor_resource,
    spell_is_prepared,
)
from dnd_board_game.combat import (
    ActiveCombatEffect,
    AppliedDamageResult,
    AttackPositioning,
    AttackSource,
    CombatState,
    CombatStatus,
    ConditionState,
    DamageComponentInput,
    HealingSource,
    SceneObject,
    SpellAreaShape,
    SpellSaveResult,
    actors_in_area,
    apply_healing_result,
    area_positions_for_center,
    area_positions_for_direction,
    can_consume_spell_resource,
    current_actor,
    direction_anchor_positions,
    dexterity_save_cover_modifiers,
    damage_components_from_totals,
    evaluate_cover_from_origin,
    forced_movement_destination,
    legal_area_centers,
    legal_healing_targets,
    replace_actor,
    MagicMovementKind,
)
from dnd_board_game.world import BoardState, Coordinate

from .damage_presentation import applied_damage_payload


@dataclass(frozen=True, slots=True)
class PendingPlayerHealing:
    healer_id: str
    target_id: str
    source_id: str
    stage: str = "healing_roll"
    cast_level: int | None = None
    metamagic_ids: tuple[str, ...] = ()
    twinned_target_id: str | None = None


@dataclass(frozen=True, slots=True)
class PendingAreaSpell:
    caster_id: str
    source_id: str
    origin: Coordinate
    anchor: Coordinate
    area_positions: tuple[Coordinate, ...]
    target_ids: tuple[str, ...]
    target_positioning: tuple[tuple[str, AttackPositioning], ...] = ()
    stage: str = "confirm_area"
    saving_throws: tuple[SpellSaveResult, ...] = ()
    cast_level: int | None = None
    protected_target_ids: tuple[str, ...] = ()
    careful_target_ids: tuple[str, ...] = ()
    heightened_target_id: str | None = None
    metamagic_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PlayerHealingTransition:
    state: CombatState
    pending: PendingPlayerHealing | None
    board_message: str
    message_title: str
    message_body: str
    event_type: str
    event_payload: tuple[tuple[str, object], ...]


@dataclass(frozen=True, slots=True)
class PlayerAreaSpellTransition:
    state: CombatState
    pending: PendingAreaSpell | None
    board_message: str
    message_title: str
    message_body: str
    event_type: str
    event_payload: tuple[tuple[str, object], ...]
    clear_movement_preview: bool = False
    applied_damages: tuple[AppliedDamageResult, ...] = ()


class PlayerAreaHealingFlowService:
    """Resolve player healing and area-spell flows without UI side effects."""

    def __init__(self) -> None:
        self._area_spells = AreaSpellResolver()
        self._healing = HealingActionResolver()

    def select_healing_target(
        self,
        *,
        state: CombatState,
        board: BoardState,
        source: HealingSource,
        position: Coordinate,
    ) -> PlayerHealingTransition:
        healer = _active_hero(state)
        targets = legal_healing_targets(board, healer, state.actors, source)
        target = next((candidate for candidate in targets if candidate.position == position), None)
        if target is None:
            raise ValueError("Wybrane pole nie jest legalnym celem leczenia.")
        pending = PendingPlayerHealing(
            healer_id=str(healer.id),
            target_id=target.id,
            source_id=source.id,
            cast_level=source.cast_level,
            metamagic_ids=source.metamagic_ids,
        )
        return PlayerHealingTransition(
            state=state,
            pending=pending,
            board_message=(
                f"Wybrano leczenie: {source.name} -> {target.name}. Wpisz wynik leczenia."
            ),
            message_title="Leczenie",
            message_body=(
                f"{healer.name} leczy {target.name}. "
                f"Rzuć {source.healing_hint} i wpisz sumę."
            ),
            event_type="ui_combat_player_healing_target_selected",
            event_payload=(
                ("healer_id", str(healer.id)),
                ("target_id", target.id),
                ("source_id", source.id),
            ),
        )

    def submit_healing(
        self,
        *,
        state: CombatState,
        source: HealingSource,
        pending: PendingPlayerHealing,
        healing: int,
        active_effects: tuple[ActiveCombatEffect, ...] = (),
    ) -> PlayerHealingTransition:
        if pending.stage != "healing_roll":
            raise ValueError("Nie ma oczekującego rzutu leczenia gracza.")
        healer = _active_hero(state)
        if str(healer.id) != pending.healer_id:
            raise ValueError("Oczekujące leczenie nie należy do aktywnego aktora.")
        _require_usable_source(
            healer,
            source,
            condition_states=state.condition_states,
            active_effects=active_effects,
        )
        resolution = self._healing.apply_healing(
            state,
            healer=healer,
            target_id=pending.target_id,
            source=source,
            amount=int(healing),
        )
        applied = resolution.applied_healing
        state_after_healing = resolution.state
        twin_applied = None
        if pending.twinned_target_id is not None:
            twin = next(
                actor
                for actor in state_after_healing.actors
                if str(actor.id) == pending.twinned_target_id
            )
            twin_applied = apply_healing_result(
                twin,
                source,
                int(healing),
                condition_states=state_after_healing.condition_states,
            )
            state_after_healing = replace_actor(
                state_after_healing,
                twin_applied.actor_after,
            )
        target = applied.actor_before
        return PlayerHealingTransition(
            state=state_after_healing,
            pending=None,
            board_message="",
            message_title="Leczenie",
            message_body=(
                f"{healer.name} używa {source.name}. {target.name}: "
                f"HP {applied.hp_before} -> {applied.hp_after} "
                f"({applied.effective_healing} realnie przywrócone)."
                + (
                    f" {twin_applied.actor_before.name}: "
                    f"HP {twin_applied.hp_before} -> {twin_applied.hp_after} "
                    f"({twin_applied.effective_healing} realnie przywrócone)."
                    if twin_applied is not None
                    else ""
                )
            ),
            event_type="ui_combat_player_healing_roll",
            event_payload=(
                ("healer_id", str(healer.id)),
                ("target_id", str(target.id)),
                ("source_id", source.id),
                ("healing", applied.amount),
                ("effective_healing", applied.effective_healing),
                ("hp_before", applied.hp_before),
                ("hp_after", applied.hp_after),
                (
                    "twinned_target_id",
                    pending.twinned_target_id,
                ),
            ),
        )

    def cancel_healing(
        self,
        *,
        state: CombatState,
        pending: PendingPlayerHealing,
    ) -> PlayerHealingTransition:
        return PlayerHealingTransition(
            state=state,
            pending=None,
            board_message=(
                "Anulowano leczenie. "
                "Kliknij Skanuj planszę, żeby wybrać ruch, cel albo akcję."
            ),
            message_title="Leczenie",
            message_body="Anulowano leczenie.",
            event_type="ui_combat_player_healing_cancelled",
            event_payload=(
                ("healer_id", pending.healer_id),
                ("target_id", pending.target_id),
            ),
        )

    def select_area_spell(
        self,
        *,
        state: CombatState,
        board: BoardState,
        source: AttackSource,
        position: Coordinate,
        scene_objects: tuple[SceneObject, ...] = (),
        active_effects: tuple[ActiveCombatEffect, ...] = (),
    ) -> PlayerAreaSpellTransition:
        caster = _active_hero(state)
        if source.area is None:
            raise ValueError("Wybrane źródło ataku nie jest czarem obszarowym.")
        _require_usable_source(
            caster,
            source,
            condition_states=state.condition_states,
            active_effects=active_effects,
        )
        if source.area.shape == SpellAreaShape.RADIUS:
            centers = legal_area_centers(board, caster.position, source.range_feet)
            if position not in centers:
                raise ValueError("Wybrane pole nie jest legalnym środkiem obszaru czaru.")
            area_positions = area_positions_for_center(board, position, source.area)
        else:
            anchors = direction_anchor_positions(board, caster.position)
            if position not in anchors:
                raise ValueError("Kliknij sąsiednie pole, żeby wybrać kierunek czaru.")
            area_positions = area_positions_for_direction(
                board,
                caster.position,
                position,
                source.area,
            )
        effect_origin = (
            position
            if source.area.shape == SpellAreaShape.RADIUS
            else caster.position
        )
        area_targets = actors_in_area(
            state.actors,
            area_positions,
            caster,
            source.area.target_mode,
        )
        positioned_targets = tuple(
            (
                target,
                evaluate_cover_from_origin(
                    board,
                    effect_origin,
                    target,
                    state.actors,
                    scene_objects,
                ),
            )
            for target in area_targets
        )
        targets = tuple(
            target for target, positioning in positioned_targets if not positioning.total_cover
        )
        target_positioning = tuple(
            (str(target.id), positioning)
            for target, positioning in positioned_targets
            if not positioning.total_cover
        )
        pending = PendingAreaSpell(
            caster_id=str(caster.id),
            source_id=source.id,
            origin=caster.position,
            anchor=position,
            area_positions=area_positions,
            target_ids=tuple(str(target.id) for target in targets),
            target_positioning=target_positioning,
            cast_level=source.cast_level,
            metamagic_ids=source.metamagic_ids,
        )
        target_names = ", ".join(target.name for target in targets) or "brak celów"
        return PlayerAreaSpellTransition(
            state=state,
            pending=pending,
            board_message=(
                f"{source.name}: podgląd obszaru gotowy. Cele: {target_names}. "
                "Potwierdź Enterem albo przyciskiem."
            ),
            message_title="Czar obszarowy",
            message_body=(
                f"{caster.name} wyznacza obszar {source.name}. "
                f"Cele w obszarze: {target_names}."
            ),
            event_type="ui_combat_area_spell_selected",
            event_payload=(
                ("caster_id", str(caster.id)),
                ("source_id", source.id),
                ("anchor", [position.col, position.row]),
                (
                    "area_positions",
                    [[tile.col, tile.row] for tile in area_positions],
                ),
                ("target_ids", [str(target.id) for target in targets]),
                (
                    "target_cover",
                    [_target_cover_payload(actor_id, positioning) for actor_id, positioning in target_positioning],
                ),
            ),
        )

    def confirm_area_spell(
        self,
        *,
        state: CombatState,
        source: AttackSource,
        pending: PendingAreaSpell,
        rng: Random,
        active_effects: tuple[ActiveCombatEffect, ...] = (),
    ) -> PlayerAreaSpellTransition:
        if pending.stage != "confirm_area":
            raise ValueError("Nie ma czaru obszarowego do potwierdzenia.")
        caster = _active_hero(state)
        if str(caster.id) != pending.caster_id:
            raise ValueError("Oczekujący czar nie należy do aktywnego aktora.")
        _require_usable_source(
            caster,
            source,
            condition_states=state.condition_states,
            active_effects=active_effects,
        )
        confirmation = self._area_spells.confirm_area_spell(
            state,
            caster=caster,
            source=source,
            target_ids=pending.target_ids,
            rng=rng,
            saving_throw_modifiers_by_target={
                actor_id: dexterity_save_cover_modifiers(
                    source.save_ability,
                    positioning,
                )
                for actor_id, positioning in pending.target_positioning
            },
            careful_target_ids=pending.careful_target_ids,
            heightened_target_id=pending.heightened_target_id,
        )
        saves = confirmation.saving_throws
        updated_pending = replace(pending, stage="damage_roll", saving_throws=saves)
        save_text = " ".join(_spell_save_message(save) for save in saves)
        return PlayerAreaSpellTransition(
            state=confirmation.state,
            pending=updated_pending,
            board_message=(
                f"{source.name} potwierdzony. Rzuć obrażenia {source.damage_hint}; "
                "sukces save oznacza "
                f"{_save_damage_on_success_label(source.save_damage_on_success)}."
            ),
            message_title="Czar obszarowy",
            message_body=(
                f"{caster.name} rzuca {source.name}. {save_text} "
                f"Rzuć obrażenia {source.damage_hint}."
            ),
            event_type="ui_combat_area_spell_confirmed",
            event_payload=(
                ("caster_id", str(caster.id)),
                ("source_id", source.id),
                ("saving_throws", [save.as_payload() for save in saves]),
            ),
            clear_movement_preview=True,
        )

    def submit_area_damage(
        self,
        *,
        state: CombatState,
        source: AttackSource,
        pending: PendingAreaSpell,
        damage: int | None = None,
        component_totals: Mapping[str, int] | None = None,
        board: BoardState | None = None,
        scene_objects: tuple[SceneObject, ...] = (),
    ) -> PlayerAreaSpellTransition:
        if pending.stage != "damage_roll":
            raise ValueError("Nie ma oczekujących obrażeń czaru obszarowego.")
        caster = _active_hero(state)
        if str(caster.id) != pending.caster_id:
            raise ValueError("Oczekujące obrażenia czaru nie należą do aktywnego aktora.")
        if component_totals is not None:
            components = damage_components_from_totals(
                source.damage_components,
                component_totals,
            )
        else:
            if damage is None:
                raise ValueError("Brak wyniku obrażeń czaru obszarowego.")
            if len(source.damage_components) > 1:
                raise ValueError(
                    "Ten czar wymaga osobnego wyniku dla każdego składnika obrażeń."
                )
            component = source.damage_components[0]
            components = (
                DamageComponentInput(
                    max(0, int(damage)),
                    component.damage_type,
                    component.label or component.id,
                ),
            )
        damage_amount = sum(component.amount for component in components)
        resolution = self._area_spells.apply_area_damage(
            state,
            source=source,
            target_ids=pending.target_ids,
            damage_components=components,
            saving_throws=pending.saving_throws,
        )
        resolved_state = resolution.state
        pushed_targets: list[tuple[str, Coordinate, Coordinate]] = []
        if source.failed_save_push_feet and board is not None:
            caster = _active_hero(resolved_state)
            for target_result in resolution.targets:
                if target_result.saving_throw.success:
                    continue
                target = _actor_by_id(resolved_state, target_result.target_id)
                destination = forced_movement_destination(
                    board,
                    resolved_state,
                    caster,
                    target,
                    kind=MagicMovementKind.PUSH,
                    distance_feet=source.failed_save_push_feet,
                    scene_objects=scene_objects,
                )
                if destination != target.position:
                    before = target.position
                    resolved_state = replace_actor(
                        resolved_state,
                        replace(target, position=destination),
                    )
                    pushed_targets.append((str(target.id), before, destination))
        applied_results = tuple(
            (target.applied_damage, target.saving_throw) for target in resolution.targets
        )
        if applied_results:
            result_text = "; ".join(
                f"{applied.actor_before.name}: HP {applied.hp_before} -> {applied.hp_after}"
                for applied, _save in applied_results
            )
        else:
            result_text = "brak trafionych celów."
        return PlayerAreaSpellTransition(
            state=resolved_state,
            pending=None,
            board_message="",
            message_title="Obrażenia obszarowe",
            message_body=f"{caster.name} kończy {source.name}: {result_text}",
            event_type="ui_combat_area_spell_damage",
            event_payload=(
                ("caster_id", str(caster.id)),
                ("source_id", source.id),
                ("base_damage", damage_amount),
                (
                    "targets",
                    [
                        {
                            "damage_result": _applied_damage_payload(applied),
                            "saving_throw": (
                                save.as_payload() if save is not None else None
                            ),
                        }
                        for applied, save in applied_results
                    ],
                ),
                (
                    "pushed_targets",
                    [
                        {
                            "actor_id": actor_id,
                            "from": [before.col, before.row],
                            "to": [after.col, after.row],
                        }
                        for actor_id, before, after in pushed_targets
                    ],
                ),
            ),
            applied_damages=tuple(applied for applied, _save in applied_results),
        )

    def cancel_area_spell(
        self,
        *,
        state: CombatState,
        pending: PendingAreaSpell,
    ) -> PlayerAreaSpellTransition:
        return PlayerAreaSpellTransition(
            state=state,
            pending=None,
            board_message=(
                "Anulowano czar obszarowy. "
                "Kliknij Skanuj planszę, żeby wybrać ruch, cel albo akcję."
            ),
            message_title="Czar obszarowy",
            message_body="Anulowano czar obszarowy.",
            event_type="ui_combat_area_spell_cancelled",
            event_payload=(
                ("caster_id", pending.caster_id),
                ("source_id", pending.source_id),
            ),
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
    condition_states: tuple[ConditionState, ...] = (),
    active_effects: tuple[ActiveCombatEffect, ...] = (),
) -> None:
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
        condition_states=condition_states,
        active_effects=active_effects,
    )
    if cast_validation is not None and not cast_validation.valid:
        raise ValueError(" ".join(cast_validation.errors))
    if source.resource_pool_id is not None and not can_spend_actor_resource(
        actor,
        source.resource_pool_id,
        source.resource_cost,
    ):
        raise ValueError(f"Brak dostępnych użyć: {source.name}.")


def _spell_save_message(save: SpellSaveResult) -> str:
    payload = save.as_payload()
    outcome = "sukces" if save.success else "porażka"
    return (
        f"{save.actor_name}: rzut obronny na {payload['ability_label']} "
        f"d20 {save.natural_roll}, modyfikator {_format_signed(save.modifier)}, "
        f"razem {save.total} przeciw ST {save.dc}: {outcome}."
    )


def _target_cover_payload(
    actor_id: str,
    positioning: AttackPositioning,
) -> dict[str, object]:
    return {
        "actor_id": actor_id,
        "cover_level": positioning.cover_level.value,
        "cover_bonus": positioning.cover_bonus,
        "cover_sources": list(positioning.cover_sources),
    }


def _format_signed(value: int) -> str:
    return f"+{value}" if value >= 0 else str(value)


def _save_damage_on_success_label(value: str) -> str:
    if value == "half":
        return "połowę obrażeń przy sukcesie"
    return "brak obrażeń przy sukcesie"


def _applied_damage_payload(result: AppliedDamageResult) -> dict[str, object]:
    payload = applied_damage_payload(result)
    assert payload is not None
    return payload
