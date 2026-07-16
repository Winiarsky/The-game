from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from dnd_board_game.actors import Actor, skill_roll_modifiers
from dnd_board_game.combat import CombatState, current_actor, replace_actor, stabilize_actor, use_turn_action
from dnd_board_game.inventory import consume_inventory_item, has_inventory_quantity
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_ability_check, resolve_d20_roll


HEALERS_KIT_ITEM_ID = "healers_kit"
MEDICINE_DC = 10


class StabilizationMethod(StrEnum):
    MEDICINE = "medicine"
    HEALERS_KIT = "healers_kit"


@dataclass(frozen=True, slots=True)
class CombatStabilizationResult:
    state: CombatState
    stabilizer: Actor
    target: Actor
    method: StabilizationMethod
    success: bool
    natural_roll: int | None = None
    total: int | None = None
    kit_remaining: int | None = None


def legal_stabilization_targets(state: CombatState, stabilizer: Actor) -> tuple[Actor, ...]:
    return tuple(
        sorted(
            (
                actor
                for actor in state.actors
                if actor.id != stabilizer.id
                and actor.faction == stabilizer.faction
                and actor.needs_death_save()
                and _distance_feet(stabilizer, actor) <= 5
            ),
            key=lambda actor: (actor.position.col, actor.position.row, str(actor.id)),
        )
    )


def resolve_combat_stabilization(
    state: CombatState,
    *,
    target_id: str,
    method: StabilizationMethod,
    natural_roll: int | None = None,
) -> CombatStabilizationResult:
    stabilizer = current_actor(state)
    target = next((actor for actor in legal_stabilization_targets(state, stabilizer) if str(actor.id) == target_id), None)
    if target is None:
        raise ValueError("Wybrany bohater nie jest legalnym celem stabilizacji w zasięgu 5 ft.")
    action = use_turn_action(state)
    if not action.accepted:
        raise ValueError(action.message)

    if method == StabilizationMethod.HEALERS_KIT:
        if not has_inventory_quantity(stabilizer, HEALERS_KIT_ITEM_ID):
            raise ValueError("Aktywny bohater nie ma użycia zestawu uzdrowiciela.")
        updated_stabilizer = consume_inventory_item(stabilizer, HEALERS_KIT_ITEM_ID)
        updated = replace_actor(action.state, updated_stabilizer)
        updated = replace_actor(updated, stabilize_actor(target))
        remaining = next(item.quantity for item in updated_stabilizer.inventory if item.id == HEALERS_KIT_ITEM_ID)
        return CombatStabilizationResult(
            updated,
            updated_stabilizer,
            target,
            method,
            True,
            kit_remaining=remaining,
        )

    if natural_roll is None:
        raise ValueError("Stabilizacja testem Medicine wymaga wyniku d20.")
    request = D20RollRequest(modifiers=skill_roll_modifiers(stabilizer, "medicine"))
    roll = resolve_d20_roll(D20RollInput(request, int(natural_roll)))
    check = resolve_ability_check(roll, MEDICINE_DC)
    updated = action.state
    if check.success:
        updated = replace_actor(updated, stabilize_actor(target))
    return CombatStabilizationResult(
        updated,
        stabilizer,
        target,
        method,
        check.success,
        natural_roll=roll.natural_roll,
        total=roll.total,
    )


def _distance_feet(first: Actor, second: Actor) -> int:
    return max(
        abs(first.position.col - second.position.col),
        abs(first.position.row - second.position.row),
    ) * 5
