from __future__ import annotations

from dataclasses import dataclass, replace
from random import Random

from dnd_board_game.actions import ActionResourceResolver, SpellSaveAttackResolver
from dnd_board_game.actors import Actor, Faction, spell_is_prepared
from dnd_board_game.combat import (
    ActiveCombatEffect,
    AppliedDamageResult,
    AttackActionState,
    AttackDeclaration,
    AttackSource,
    CombatState,
    CombatStatus,
    HealingSource,
    SpellSaveResult,
    attack_source_with_combat_effects,
    attack_source_with_target_combat_effects,
    can_consume_spell_resource,
    consume_next_attack_effects,
    current_actor,
    resolve_attack,
    select_attack_target,
    start_attack_action,
)
from dnd_board_game.rules import D20RollInput, RollMode, resolve_d20_roll, roll_instruction
from dnd_board_game.world import BoardState, Coordinate


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
    ) -> PlayerAttackTransition:
        attacker = _active_hero(state)
        _require_usable_source(attacker, source)
        action = start_attack_action(board, attacker, state.actors, source)
        selected = select_attack_target(action, position=position)
        assert selected.selected_target is not None
        pending = PendingPlayerAttack(
            attacker_id=str(attacker.id),
            target_id=selected.selected_target.id,
            source_id=source.id,
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
    ) -> PlayerAttackTransition:
        if pending.stage != "confirm_attack":
            raise ValueError("Nie ma celu ataku do potwierdzenia.")
        attacker, target, selected = _validated_attack(state, board, source, pending)
        effective_source = attack_source_with_target_combat_effects(
            attacker,
            target,
            source,
            active_effects,
        )
        if effective_source.save_ability:
            _require_usable_source(attacker, effective_source)
            confirmation = self._spell_saves.confirm_target_save_spell(
                state,
                caster=attacker,
                target=target,
                source=effective_source,
                rng=rng,
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
        updated_pending = replace(pending, stage="attack_roll")
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
    ) -> PlayerAttackTransition:
        if pending.stage != "attack_roll":
            raise ValueError("Nie ma oczekującego rzutu ataku gracza.")
        attacker, target, selected = _validated_attack(state, board, source, pending)
        effective_source = attack_source_with_target_combat_effects(
            attacker,
            target,
            source,
            active_effects,
        )
        attack_roll = resolve_d20_roll(
            _manual_d20_input(
                effective_source,
                natural_roll,
                natural_roll_2,
            )
        )
        resource_use = self._resources.consume_action_and_source_resource(
            state,
            attacker,
            spell_level=effective_source.spell_level,
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
        )
        if not resolution.hit:
            return PlayerAttackTransition(
                state=resource_use.state,
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
        )
        return PlayerAttackTransition(
            state=resource_use.state,
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
        effective_source = attack_source_with_combat_effects(attacker, source, active_effects)
        target = _actor_by_id(state, pending.target_id)
        damage_amount = max(0, int(damage))
        save = pending.saving_throws[0] if pending.saving_throws else None
        resolution = self._spell_saves.apply_target_damage(
            state,
            target_id=pending.target_id,
            source=effective_source,
            base_damage=damage_amount,
            saving_throw=save,
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
    ) -> PlayerAttackTransition:
        attacker = _active_hero(state)
        _require_usable_source(attacker, source)
        pending = PendingPlayerAttack(str(attacker.id), target_id, source.id, "attack_roll")
        attacker, target, selected = _validated_attack(state, board, source, pending)
        effective_source = attack_source_with_target_combat_effects(
            attacker,
            target,
            source,
            active_effects,
        )
        attack_roll = resolve_d20_roll(
            _manual_d20_input(effective_source, natural_roll, natural_roll_2)
        )
        resource_use = self._resources.consume_action_and_source_resource(
            state,
            attacker,
            spell_level=effective_source.spell_level,
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
        updated_state = resource_use.state
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
) -> tuple[Actor, Actor, AttackActionState]:
    attacker = _require_pending_attacker(state, pending)
    action = start_attack_action(board, attacker, state.actors, source)
    selected = select_attack_target(action, target_id=pending.target_id)
    assert selected.selected_target is not None
    target = _actor_by_id(state, selected.selected_target.id)
    return attacker, target, selected


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
    defeated_text = " Cel zostaje pokonany." if result.defeated_by_damage else ""
    temp_text = ""
    if result.temp_hp_before > 0 or result.absorbed_by_temp_hp > 0:
        temp_text = (
            f" Temp HP {result.temp_hp_before} -> {result.temp_hp_after}, "
            f"pochłonięto {result.absorbed_by_temp_hp}."
        )
    return (
        f"Obrażenia: {result.damage.total_applied}. "
        f"{result.actor_before.name}: HP {result.hp_before} -> {result.hp_after} / "
        f"{result.actor_after.max_hp}.{temp_text}{defeated_text}"
    )


def _applied_damage_payload(result: AppliedDamageResult | None) -> dict[str, object] | None:
    if result is None:
        return None
    return {
        "damage": result.damage.total_applied,
        "hp_before": result.hp_before,
        "hp_after": result.hp_after,
        "temp_hp_before": result.temp_hp_before,
        "temp_hp_after": result.temp_hp_after,
        "absorbed_by_temp_hp": result.absorbed_by_temp_hp,
        "applied_to_hp": result.applied_to_hp,
        "defeated": result.defeated,
        "defeated_by_damage": result.defeated_by_damage,
    }
