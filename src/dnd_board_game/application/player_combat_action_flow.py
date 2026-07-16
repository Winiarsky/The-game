from __future__ import annotations

from dataclasses import dataclass, replace
from random import Random

from dnd_board_game.actions import ActionResourceResolver, SpellSaveAttackResolver
from dnd_board_game.actors import Actor, Faction, spell_is_prepared
from dnd_board_game.combat import (
    ActiveCombatEffect,
    ActionUse,
    AppliedDamageResult,
    AttackPositioning,
    AttackActionState,
    AttackDeclaration,
    AttackSource,
    CombatState,
    CombatStatus,
    HealingSource,
    SpellSaveResult,
    attack_source_with_hidden_advantage,
    attack_source_with_prone,
    attack_source_with_positioning,
    attack_source_with_combat_effects,
    attack_source_with_target_combat_effects,
    can_consume_spell_resource,
    can_use_attack_action,
    consume_next_attack_effects,
    current_actor,
    dexterity_save_cover_modifiers,
    evaluate_attack_positioning,
    grappled_actor_ids,
    is_hidden_from,
    reveal_actor,
    resolve_attack,
    set_two_weapon_trigger,
    select_attack_target,
    start_attack_action,
    SceneObject,
    two_weapon_bonus_attack_source,
    two_weapon_bonus_source_is_legal,
    two_weapon_trigger_item_id,
    use_bonus_action,
    use_attack_action,
    versatile_two_handed_source_is_legal,
)
from dnd_board_game.rules import D20RollInput, RollMode, resolve_d20_roll, roll_instruction
from dnd_board_game.world import BoardState, Coordinate

from .damage_presentation import applied_damage_message, applied_damage_payload


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


class PlayerCombatActionFlowService:
    """Resolve player source selection and single-target attack transitions."""

    def __init__(self) -> None:
        self._resources = ActionResourceResolver()
        self._spell_saves = SpellSaveAttackResolver()

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
    ) -> PlayerAttackTransition:
        attacker = _active_hero(state)
        _require_usable_source(attacker, source)
        _require_attack_economy(state, attacker, source, two_weapon_bonus=two_weapon_bonus)
        action = start_attack_action(board, attacker, state.actors, source, state.hidden_states)
        selected = select_attack_target(action, position=position)
        assert selected.selected_target is not None
        target = _actor_by_id(state, selected.selected_target.id)
        positioning = evaluate_attack_positioning(
            board,
            attacker,
            target,
            source,
            state.actors,
            scene_objects,
        )
        pending = PendingPlayerAttack(
            attacker_id=str(attacker.id),
            target_id=selected.selected_target.id,
            source_id=source.id,
            two_weapon_bonus=two_weapon_bonus,
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
        if effective_source.save_ability:
            _require_usable_source(attacker, effective_source)
            confirmation = self._spell_saves.confirm_target_save_spell(
                state,
                caster=attacker,
                target=target,
                source=effective_source,
                rng=rng,
                saving_throw_modifiers=dexterity_save_cover_modifiers(
                    effective_source.save_ability,
                    positioning,
                ),
            )
            save = confirmation.saving_throw
            save_text = _spell_save_message(save)
            if save.damage_multiplier <= 0:
                return PlayerAttackTransition(
                    state=confirmation.state,
                    active_effects=active_effects,
                    pending=None,
                    board_message=(
                        f"{effective_source.name}: {save.actor_name} zdaje rzut obronny. "
                        "Brak obrażeń."
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
                saving_throws=(save,),
                hit=True,
            )
            return PlayerAttackTransition(
                state=confirmation.state,
                active_effects=active_effects,
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
        attack_roll = resolve_d20_roll(
            _manual_d20_input(
                effective_source,
                natural_roll,
                natural_roll_2,
            )
        )
        if pending.two_weapon_bonus:
            bonus_use = use_bonus_action(state)
            if not bonus_use.accepted:
                raise ValueError(bonus_use.message)
            state_after_resource = bonus_use.state
        else:
            if _uses_attack_action(effective_source):
                attack_use = use_attack_action(state, attacker)
                if not attack_use.accepted:
                    raise ValueError(attack_use.message)
                state_after_resource = attack_use.state
            else:
                resource_use = self._resources.consume_action_and_source_resource(
                    state,
                    attacker,
                    spell_level=effective_source.spell_level,
                )
                state_after_resource = resource_use.state
            state_after_resource = set_two_weapon_trigger(
                state_after_resource,
                two_weapon_trigger_item_id(attacker, source),
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
        message = _player_attack_message(
            attacker.name,
            selected.selected_target.name,
            attack_roll.total,
            resolution.hit,
            resolution.critical,
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
        )
        revealed_state = replace(
            state_after_resource,
            hidden_states=reveal_actor(state_after_resource.hidden_states, str(attacker.id)),
        )
        if not resolution.hit:
            return PlayerAttackTransition(
                state=revealed_state,
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
        damage: int,
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
        damage_amount = max(0, int(damage))
        save = pending.saving_throws[0] if pending.saving_throws else None
        resolution = self._spell_saves.apply_target_damage(
            state,
            target_id=pending.target_id,
            source=effective_source,
            base_damage=damage_amount,
            saving_throw=save,
            critical=pending.critical,
        )
        applied = resolution.applied_damage
        return PlayerAttackTransition(
            state=resolution.state,
            active_effects=active_effects,
            pending=None,
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
        scene_objects: tuple[SceneObject, ...] = (),
    ) -> PlayerAttackTransition:
        attacker = _active_hero(state)
        _require_usable_source(attacker, source)
        pending = PendingPlayerAttack(str(attacker.id), target_id, source.id, "attack_roll")
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
            _manual_d20_input(effective_source, natural_roll, natural_roll_2)
        )
        if _uses_attack_action(effective_source):
            attack_use = use_attack_action(state, attacker)
            if not attack_use.accepted:
                raise ValueError(attack_use.message)
            state_after_resource = attack_use.state
        else:
            resource_use = self._resources.consume_action_and_source_resource(
                state,
                attacker,
                spell_level=effective_source.spell_level,
            )
            state_after_resource = resource_use.state
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


def _require_usable_source(actor: Actor, source: AttackSource | HealingSource) -> None:
    source_item_id = getattr(source, "source_item_id", None)
    if source_item_id is not None:
        items = tuple(
            item
            for item in actor.inventory
            if item.id == source_item_id or item.source_ref == source_item_id
        )
        if not any(item.available and item.equipped for item in items):
            raise ValueError(f"{source.name} nie jest obecnie trzymane ani wyposażone.")
    if not spell_is_prepared(
        actor.spell_preparation,
        source.id,
        casting_kind=source.casting_kind.value,
        legacy_prepared=source.prepared,
    ):
        raise ValueError(f"Czar {source.name} nie został przygotowany.")
    if not can_consume_spell_resource(actor, getattr(source, "spell_level", 0)):
        raise ValueError(f"Brak slotów czaru dla {source.name}.")


def _validated_attack(
    state: CombatState,
    board: BoardState,
    source: AttackSource,
    pending: PendingPlayerAttack,
    scene_objects: tuple[SceneObject, ...] = (),
) -> tuple[Actor, Actor, AttackActionState, AttackPositioning]:
    attacker = _require_pending_attacker(state, pending)
    _require_attack_economy(
        state,
        attacker,
        source,
        two_weapon_bonus=pending.two_weapon_bonus,
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
    if _uses_attack_action(source):
        if not can_use_attack_action(state, actor):
            raise ValueError("Wykorzystano już wszystkie ataki tej akcji.")
    elif state.turn_action.action_use != ActionUse.ACTION_AVAILABLE:
        raise ValueError("Akcja w tej turze została już zużyta.")


def _uses_attack_action(source: AttackSource) -> bool:
    return source.source_type.value == "weapon" and source.area is None


def _require_pending_attacker(state: CombatState, pending: PendingPlayerAttack) -> Actor:
    attacker = _active_hero(state)
    if str(attacker.id) != pending.attacker_id:
        raise ValueError("Oczekujący atak nie należy do aktywnego aktora.")
    return attacker


def _actor_by_id(state: CombatState, actor_id: str) -> Actor:
    actor = next((candidate for candidate in state.actors if str(candidate.id) == actor_id), None)
    if actor is None:
        raise ValueError(f"Nieznany cel ataku: {actor_id}.")
    return actor


def _manual_d20_input(
    source: AttackSource,
    natural_roll: int,
    natural_roll_2: int | None,
) -> D20RollInput:
    request = source.attack_roll_request
    if request.mode == RollMode.NORMAL:
        return D20RollInput(request, int(natural_roll))
    if natural_roll_2 is None:
        raise ValueError("Ten rzut wymaga wpisania dwóch wyników d20.")
    return D20RollInput(request, int(natural_roll), int(natural_roll_2))


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
