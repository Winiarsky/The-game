from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol

from dnd_board_game.actions import ActionResourceResolver
from dnd_board_game.actors import Actor
from dnd_board_game.combat import (
    ActionEconomyCost,
    ActiveCombatEffect,
    CombatState,
    DispellableSpellEffect,
    actor_spell_cast_validation,
    current_actor,
    dispellable_spell_effects_for_target,
    grid_distance_feet,
    is_hidden_from,
    remove_dispellable_spell_effect,
    reveal_actor,
)
from dnd_board_game.rules import (
    D20RollInput,
    D20RollRequest,
    RollModifier,
    RollModifierType,
    resolve_d20_roll,
)
from dnd_board_game.world import BoardState, line_of_sight_clear

from .summoning_flow import remove_orphaned_summons


class SpellDispelActionSpec(Protocol):
    id: str
    action_type: str
    label: str
    range_feet: int
    spell_level: int
    action_cost: ActionEconomyCost
    effect_kind: str | None


@dataclass(frozen=True, slots=True)
class PendingDispelCheck:
    effect_key: str
    spell_id: str
    label: str
    spell_level: int
    dc: int

    def as_payload(self) -> dict[str, object]:
        return {
            "effect_key": self.effect_key,
            "spell_id": self.spell_id,
            "label": self.label,
            "spell_level": self.spell_level,
            "dc": self.dc,
        }


@dataclass(frozen=True, slots=True)
class PendingSpellDispel:
    caster_id: str
    action_id: str
    cast_level: int
    legal_target_ids: tuple[str, ...]
    stage: str = "target_selection"
    target_id: str | None = None
    checks: tuple[PendingDispelCheck, ...] = ()

    @property
    def current_check(self) -> PendingDispelCheck | None:
        return self.checks[0] if self.checks else None

    def as_payload(self) -> dict[str, object]:
        return {
            "caster_id": self.caster_id,
            "action_id": self.action_id,
            "cast_level": self.cast_level,
            "legal_target_ids": list(self.legal_target_ids),
            "stage": self.stage,
            "target_id": self.target_id,
            "checks": [check.as_payload() for check in self.checks],
            "current_check": (
                self.current_check.as_payload()
                if self.current_check is not None
                else None
            ),
        }


@dataclass(frozen=True, slots=True)
class SpellDispelTransition:
    state: CombatState
    active_effects: tuple[ActiveCombatEffect, ...]
    pending: PendingSpellDispel | None
    message_title: str
    message_body: str
    event_type: str
    event_payload: tuple[tuple[str, object], ...]
    removed_actor_ids: tuple[str, ...] = ()


class SpellDispelFlowService:
    """Dispel spell-authored effects on a visible creature."""

    def __init__(self) -> None:
        self._resources = ActionResourceResolver()

    def prepare(
        self,
        *,
        board: BoardState,
        state: CombatState,
        active_effects: tuple[ActiveCombatEffect, ...],
        action: SpellDispelActionSpec,
        cast_level: int | None = None,
    ) -> SpellDispelTransition:
        caster = current_actor(state)
        _validate_action(action)
        validation = actor_spell_cast_validation(
            caster,
            action.id,
            cast_level=cast_level,
        )
        if validation is None or not validation.valid:
            raise ValueError(
                " ".join(validation.errors)
                if validation is not None
                else "Aktor nie zna tego czaru."
            )
        targets = _legal_targets(board, state, active_effects, caster, action)
        if not targets:
            raise ValueError("Brak widocznego celu z aktywnym efektem czaru.")
        pending = PendingSpellDispel(
            caster_id=str(caster.id),
            action_id=action.id,
            cast_level=validation.cast_level,
            legal_target_ids=tuple(str(target.id) for target in targets),
        )
        return SpellDispelTransition(
            state,
            active_effects,
            pending,
            "Rozproszenie magii",
            f"{caster.name} przygotowuje {action.label}. Wybierz podświetlony cel.",
            "ui_combat_spell_dispel_started",
            (
                ("caster_id", str(caster.id)),
                ("spell_id", action.id),
                ("cast_level", validation.cast_level),
                ("target_ids", list(pending.legal_target_ids)),
            ),
        )

    def confirm_target(
        self,
        *,
        board: BoardState,
        state: CombatState,
        active_effects: tuple[ActiveCombatEffect, ...],
        action: SpellDispelActionSpec,
        pending: PendingSpellDispel,
        target_id: str,
    ) -> SpellDispelTransition:
        caster = current_actor(state)
        _validate_pending(caster, action, pending, stage="target_selection")
        legal_ids = {
            str(target.id)
            for target in _legal_targets(board, state, active_effects, caster, action)
        }
        if target_id not in pending.legal_target_ids or target_id not in legal_ids:
            raise ValueError("Wybrany aktor nie jest legalnym celem rozproszenia.")
        validation = actor_spell_cast_validation(
            caster,
            action.id,
            cast_level=pending.cast_level,
        )
        if validation is None or not validation.valid:
            raise ValueError(
                " ".join(validation.errors)
                if validation is not None
                else "Aktor nie zna tego czaru."
            )
        resource = self._resources.consume_action_and_source_resource(
            state,
            caster,
            spell_level=action.spell_level,
            spell_id=action.id,
            cast_level=pending.cast_level,
            action_cost=action.action_cost,
        )
        updated_state = resource.state
        updated_effects = active_effects
        effects = dispellable_spell_effects_for_target(
            updated_state,
            updated_effects,
            target_id,
        )
        automatically_removed: list[str] = []
        checks: list[PendingDispelCheck] = []
        removed_actor_ids: set[str] = set()
        for effect in effects:
            if effect.spell_level <= pending.cast_level:
                removal = remove_dispellable_spell_effect(
                    updated_state,
                    updated_effects,
                    effect,
                )
                updated_state = removal.state
                updated_effects = removal.active_effects
                automatically_removed.append(effect.label)
            else:
                checks.append(_pending_check(effect))
        updated_state, updated_effects, removed = remove_orphaned_summons(
            updated_state,
            updated_effects,
        )
        removed_actor_ids.update(str(summon.actor_id) for summon in removed)
        updated_state = replace(
            updated_state,
            hidden_states=reveal_actor(
                updated_state.hidden_states,
                str(caster.id),
            ),
        )
        target = _actor_by_id(state, target_id)
        removed_text = (
            f" Automatycznie zakończone: {', '.join(automatically_removed)}."
            if automatically_removed
            else ""
        )
        if checks:
            next_pending = replace(
                pending,
                stage="ability_check",
                target_id=target_id,
                checks=tuple(checks),
            )
            current = next_pending.current_check
            assert current is not None
            message = (
                f"{caster.name} rzuca {action.label} na {target.name}.{removed_text} "
                f"{current.label} ({current.spell_level}. poziom) wymaga testu "
                f"cechy rzucania czarów ST {current.dc}."
            )
            return SpellDispelTransition(
                updated_state,
                updated_effects,
                next_pending,
                "Rozproszenie magii",
                message,
                "ui_combat_spell_dispel_check_required",
                (
                    ("caster_id", str(caster.id)),
                    ("target_id", target_id),
                    ("spell_id", action.id),
                    ("cast_level", pending.cast_level),
                    ("automatic_spell_ids", [
                        effect.spell_id
                        for effect in effects
                        if effect.spell_level <= pending.cast_level
                    ]),
                    ("check_spell_ids", [check.spell_id for check in checks]),
                ),
                tuple(sorted(removed_actor_ids)),
            )
        message = (
            f"{caster.name} rzuca {action.label} na {target.name}."
            f"{removed_text or ' Nie pozostał żaden efekt do rozproszenia.'}"
        )
        return SpellDispelTransition(
            updated_state,
            updated_effects,
            None,
            "Rozproszenie magii",
            message,
            "ui_combat_spell_dispel_confirmed",
            (
                ("caster_id", str(caster.id)),
                ("target_id", target_id),
                ("spell_id", action.id),
                ("cast_level", pending.cast_level),
                ("removed_labels", automatically_removed),
            ),
            tuple(sorted(removed_actor_ids)),
        )

    def resolve_check(
        self,
        *,
        state: CombatState,
        active_effects: tuple[ActiveCombatEffect, ...],
        action: SpellDispelActionSpec,
        pending: PendingSpellDispel,
        natural_roll: int,
    ) -> SpellDispelTransition:
        caster = current_actor(state)
        _validate_pending(caster, action, pending, stage="ability_check")
        current = pending.current_check
        if current is None or pending.target_id is None:
            raise ValueError("Brak oczekującego testu rozproszenia.")
        modifier = _spellcasting_ability_modifier(caster)
        roll = resolve_d20_roll(
            D20RollInput(
                D20RollRequest(
                    modifiers=(
                        RollModifier(
                            "cecha bazowa rzucania czarów",
                            modifier,
                            RollModifierType.ABILITY,
                        ),
                    )
                ),
                int(natural_roll),
            )
        )
        success = roll.total >= current.dc
        updated_state = state
        updated_effects = active_effects
        removed_actor_ids: set[str] = set()
        if success:
            effect = next(
                (
                    candidate
                    for candidate in dispellable_spell_effects_for_target(
                        state,
                        active_effects,
                        pending.target_id,
                    )
                    if candidate.key == current.effect_key
                ),
                None,
            )
            if effect is not None:
                removal = remove_dispellable_spell_effect(
                    state,
                    active_effects,
                    effect,
                )
                updated_state = removal.state
                updated_effects = removal.active_effects
                updated_state, updated_effects, removed = remove_orphaned_summons(
                    updated_state,
                    updated_effects,
                )
                removed_actor_ids.update(str(summon.actor_id) for summon in removed)
        remaining_checks = pending.checks[1:]
        next_pending = (
            replace(pending, checks=remaining_checks)
            if remaining_checks
            else None
        )
        outcome = "sukces — efekt zakończony" if success else "porażka — efekt pozostaje"
        message = (
            f"Test rozproszenia {current.label}: {roll.total}/{current.dc}, {outcome}."
        )
        if next_pending is not None:
            next_check = next_pending.current_check
            assert next_check is not None
            message += (
                f" Następny: {next_check.label}, ST {next_check.dc}."
            )
        return SpellDispelTransition(
            updated_state,
            updated_effects,
            next_pending,
            "Rozproszenie magii",
            message,
            (
                "ui_combat_spell_dispel_check_resolved"
                if next_pending is not None
                else "ui_combat_spell_dispel_confirmed"
            ),
            (
                ("caster_id", str(caster.id)),
                ("target_id", pending.target_id),
                ("spell_id", current.spell_id),
                ("natural_roll", natural_roll),
                ("modifier", modifier),
                ("total", roll.total),
                ("dc", current.dc),
                ("success", success),
            ),
            tuple(sorted(removed_actor_ids)),
        )

    def cancel(
        self,
        *,
        state: CombatState,
        active_effects: tuple[ActiveCombatEffect, ...],
        pending: PendingSpellDispel,
    ) -> SpellDispelTransition:
        if pending.stage != "target_selection":
            raise ValueError("Po rzuceniu czaru trzeba dokończyć testy rozproszenia.")
        return SpellDispelTransition(
            state,
            active_effects,
            None,
            "Rozproszenie magii",
            "Anulowano czar. Akcja i slot nie zostały zużyte.",
            "ui_combat_spell_dispel_cancelled",
            (
                ("caster_id", pending.caster_id),
                ("spell_id", pending.action_id),
            ),
        )


def _legal_targets(
    board: BoardState,
    state: CombatState,
    active_effects: tuple[ActiveCombatEffect, ...],
    caster: Actor,
    action: SpellDispelActionSpec,
) -> tuple[Actor, ...]:
    return tuple(
        target
        for target in state.actors
        if not target.is_defeated()
        and grid_distance_feet(caster.position, target.position) <= action.range_feet
        and line_of_sight_clear(board, caster.position, target.position)
        and not is_hidden_from(state.hidden_states, target, caster)
        and dispellable_spell_effects_for_target(
            state,
            active_effects,
            str(target.id),
        )
    )


def _pending_check(effect: DispellableSpellEffect) -> PendingDispelCheck:
    return PendingDispelCheck(
        effect_key=effect.key,
        spell_id=effect.spell_id,
        label=effect.label,
        spell_level=effect.spell_level,
        dc=10 + effect.spell_level,
    )


def _validate_action(action: SpellDispelActionSpec) -> None:
    if (
        action.action_type != "spell_dispel"
        or action.effect_kind != "dispel_magic"
        or action.range_feet <= 0
    ):
        raise ValueError("Ta akcja nie jest kompletnym czarem rozpraszającym.")


def _validate_pending(
    caster: Actor,
    action: SpellDispelActionSpec,
    pending: PendingSpellDispel,
    *,
    stage: str,
) -> None:
    _validate_action(action)
    if str(caster.id) != pending.caster_id or action.id != pending.action_id:
        raise ValueError("Oczekujące rozproszenie nie należy do aktywnego aktora.")
    if pending.stage != stage:
        raise ValueError("Rozproszenie magii jest na innym etapie.")


def _spellcasting_ability_modifier(actor: Actor) -> int:
    if actor.spell_save_dc <= 0:
        return 0
    return actor.spell_save_dc - 8 - actor.proficiency_bonus


def _actor_by_id(state: CombatState, actor_id: str) -> Actor:
    actor = next(
        (candidate for candidate in state.actors if str(candidate.id) == actor_id),
        None,
    )
    if actor is None:
        raise ValueError(f"Nieznany aktor: {actor_id}.")
    return actor
