from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Sequence

from dnd_board_game.actors import Actor, Faction
from dnd_board_game.rules import AttackRollOutcome, AttackRollResult, D20RollRequest, D20RollResult, resolve_attack_roll
from dnd_board_game.world import BoardState, Coordinate

from .action_economy import ActionUse, consume_action
from .targets import CombatTarget, actor_as_combat_target, is_public_attack_target


class AttackSourceType(StrEnum):
    WEAPON = "weapon"
    SPELL = "spell"
    ITEM = "item"
    CUSTOM = "custom"


class AttackActionStatus(StrEnum):
    SELECTING_TARGET = "selecting_target"
    TARGET_SELECTED = "target_selected"
    CANCELLED = "cancelled"
    RESOLVED = "resolved"


@dataclass(frozen=True, slots=True)
class AttackSource:
    name: str
    source_type: AttackSourceType
    range_feet: int
    attack_roll_request: D20RollRequest
    damage_hint: str = ""


@dataclass(frozen=True, slots=True)
class AttackActionState:
    attacker: Actor
    source: AttackSource
    legal_targets: tuple[CombatTarget, ...]
    selected_target: CombatTarget | None = None
    status: AttackActionStatus = AttackActionStatus.SELECTING_TARGET
    action_use: ActionUse = ActionUse.ACTION_AVAILABLE


@dataclass(frozen=True, slots=True)
class AttackDeclaration:
    attacker: Actor
    target: CombatTarget
    source: AttackSource


@dataclass(frozen=True, slots=True)
class AttackResolution:
    declaration: AttackDeclaration
    attack_roll: D20RollResult
    attack_roll_result: AttackRollResult
    outcome: AttackRollOutcome
    hit: bool
    critical: bool
    action_use: ActionUse


def legal_melee_targets(board: BoardState, attacker: Actor, actors: Sequence[Actor]) -> tuple[CombatTarget, ...]:
    targets: list[CombatTarget] = []
    for actor in actors:
        if actor.id == attacker.id:
            continue
        if actor.faction == attacker.faction or actor.faction == Faction.NEUTRAL:
            continue
        target = actor_as_combat_target(actor)
        if not is_public_attack_target(target):
            continue
        if _is_adjacent(attacker.position, actor.position) and _has_clear_melee_line(board, attacker.position, actor.position):
            targets.append(target)
    return tuple(sorted(targets, key=lambda target: (target.position.col, target.position.row, target.id)))


def start_attack_action(
    board: BoardState,
    attacker: Actor,
    actors: Sequence[Actor],
    source: AttackSource,
) -> AttackActionState:
    return AttackActionState(attacker=attacker, source=source, legal_targets=legal_melee_targets(board, attacker, actors))


def select_attack_target(
    state: AttackActionState,
    *,
    target_id: str | None = None,
    position: Coordinate | None = None,
) -> AttackActionState:
    for target in state.legal_targets:
        if target_id is not None and target.id == target_id:
            return replace(state, selected_target=target, status=AttackActionStatus.TARGET_SELECTED)
        if position is not None and target.position == position:
            return replace(state, selected_target=target, status=AttackActionStatus.TARGET_SELECTED)
    raise ValueError("Selected target is not a legal attack target.")


def cancel_attack_action(state: AttackActionState) -> AttackActionState:
    return replace(state, selected_target=None, status=AttackActionStatus.CANCELLED)


def attack_declaration_from_state(state: AttackActionState) -> AttackDeclaration:
    if state.selected_target is None:
        raise ValueError("Cannot declare an attack without a selected target.")
    return AttackDeclaration(attacker=state.attacker, target=state.selected_target, source=state.source)


def resolve_attack(declaration: AttackDeclaration, attack_roll: D20RollResult, action_use: ActionUse) -> AttackResolution:
    result = resolve_attack_roll(attack_roll, declaration.target.ac)
    used_action = consume_action(action_use)
    return AttackResolution(
        declaration=declaration,
        attack_roll=attack_roll,
        attack_roll_result=result,
        outcome=result.outcome,
        hit=result.hits,
        critical=result.outcome == AttackRollOutcome.CRITICAL_HIT,
        action_use=used_action,
    )


def _is_adjacent(a: Coordinate, b: Coordinate) -> bool:
    dc = abs(a.col - b.col)
    dr = abs(a.row - b.row)
    return max(dc, dr) == 1 and (dc != 0 or dr != 0)


def _has_clear_melee_line(board: BoardState, a: Coordinate, b: Coordinate) -> bool:
    dc = abs(a.col - b.col)
    dr = abs(a.row - b.row)
    if dc + dr == 1:
        return not board.blocks_edge(a, b)
    if dc == 1 and dr == 1:
        side_a = Coordinate(b.col, a.row)
        side_b = Coordinate(a.col, b.row)
        return not (board.blocks_edge(a, side_a) and board.blocks_edge(a, side_b))
    return False
