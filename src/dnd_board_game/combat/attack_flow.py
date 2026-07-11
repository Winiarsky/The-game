from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Sequence

from dnd_board_game.actors import Actor, Faction
from dnd_board_game.rules import AttackRollOutcome, AttackRollResult, D20RollRequest, D20RollResult, resolve_attack_roll
from dnd_board_game.world import BoardState, Coordinate, line_of_sight_clear

from .action_economy import ActionUse, consume_action
from .spells import SpellArea
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
    damage_fixed: int | None = None
    damage_die_sides: int | None = None
    damage_modifier: int = 0
    damage_type: str = "slashing"
    id: str = ""
    ability: str | None = None
    spell_level: int = 0
    area: SpellArea | None = None
    save_ability: str | None = None
    save_dc: int = 0
    save_damage_on_success: str = "none"


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
    source = AttackSource("melee", AttackSourceType.WEAPON, 5, D20RollRequest())
    return legal_attack_targets(board, attacker, actors, source)


def legal_attack_targets(
    board: BoardState,
    attacker: Actor,
    actors: Sequence[Actor],
    source: AttackSource,
) -> tuple[CombatTarget, ...]:
    targets: list[CombatTarget] = []
    for actor in actors:
        if actor.id == attacker.id:
            continue
        if actor.faction == attacker.faction or actor.faction == Faction.NEUTRAL:
            continue
        target = actor_as_combat_target(actor)
        if not is_public_attack_target(target):
            continue
        if _target_in_range(attacker.position, actor.position, source.range_feet) and line_of_sight_clear(
            board, attacker.position, actor.position
        ):
            targets.append(target)
    return tuple(sorted(targets, key=lambda target: (target.position.col, target.position.row, target.id)))


def start_attack_action(
    board: BoardState,
    attacker: Actor,
    actors: Sequence[Actor],
    source: AttackSource,
) -> AttackActionState:
    return AttackActionState(attacker=attacker, source=source, legal_targets=legal_attack_targets(board, attacker, actors, source))


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


def _target_in_range(a: Coordinate, b: Coordinate, range_feet: int) -> bool:
    if range_feet <= 0:
        return False
    distance_feet = max(abs(a.col - b.col), abs(a.row - b.row)) * 5
    return 0 < distance_feet <= range_feet
