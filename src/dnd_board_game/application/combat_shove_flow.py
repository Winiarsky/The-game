from __future__ import annotations

from dnd_board_game.combat.mana_charge import charged_check_request

from dataclasses import dataclass, replace
from enum import StrEnum
from random import Random

from dnd_board_game.actors import (
    Actor,
    Faction,
    can_grapple_or_shove_size,
    creature_size_label_pl,
    largest_grapple_or_shove_target,
    skill_modifier,
    skill_roll_modifiers,
)
from dnd_board_game.combat import (
    ActionUse,
    CombatCondition,
    CombatState,
    SceneObject,
    apply_condition,
    can_use_attack_action,
    condition_roll_request,
    current_actor,
    has_condition,
    is_hidden_from,
    replace_actor,
    reveal_actor,
    use_attack_action,
)
from dnd_board_game.rules import (
    ContestOutcome,
    ContestResult,
    ContestantRollInput,
    D20RollInput,
    D20RollRequest,
    RollModifier,
    resolve_contest,
    roll_instruction,
)
from dnd_board_game.world import BoardState, Coordinate


class ShoveMode(StrEnum):
    PRONE = "prone"
    PUSH = "push"


@dataclass(frozen=True, slots=True)
class PendingShove:
    attacker_id: str
    attacker_name: str
    target_id: str
    target_name: str
    mode: ShoveMode
    defender_skill: str
    attacker_request: D20RollRequest
    defender_request: D20RollRequest
    push_destination: Coordinate | None = None

    def as_payload(self) -> dict[str, object]:
        return {
            "attacker_id": self.attacker_id,
            "attacker_name": self.attacker_name,
            "target_id": self.target_id,
            "target_name": self.target_name,
            "mode": self.mode.value,
            "mode_label": "powalenie" if self.mode == ShoveMode.PRONE else "odepchnięcie o 5 ft",
            "attacker_check": _request_payload("Athletics", self.attacker_request),
            "defender_check": _request_payload(_skill_label(self.defender_skill), self.defender_request),
            "push_destination": (
                [self.push_destination.col, self.push_destination.row]
                if self.push_destination is not None
                else None
            ),
        }


@dataclass(frozen=True, slots=True)
class ShoveResolution:
    state: CombatState
    contest: ContestResult
    mode: ShoveMode
    succeeded: bool
    message_title: str
    message_body: str
    event_type: str
    event_payload: tuple[tuple[str, object], ...]


class CombatShoveFlowService:
    """Prepare and resolve the D&D 5e 2014 Shove special melee attack."""

    def available_modes(
        self,
        *,
        state: CombatState,
        board: BoardState,
        target_id: str,
        scene_objects: tuple[SceneObject, ...] = (),
    ) -> tuple[ShoveMode, ...]:
        attacker = current_actor(state)
        target = _actor_by_id(state, target_id)
        if not _base_shove_is_legal(state, attacker, target):
            return ()
        modes: list[ShoveMode] = []
        if (
            not has_condition(state.condition_states, target_id, CombatCondition.PRONE)
            and CombatCondition.PRONE.value not in target.condition_immunities
        ):
            modes.append(ShoveMode.PRONE)
        destination = shove_push_destination(attacker, target)
        if _push_destination_is_available(board, state, target, destination, scene_objects):
            modes.append(ShoveMode.PUSH)
        return tuple(modes)

    def prepare(
        self,
        *,
        state: CombatState,
        board: BoardState,
        target_id: str,
        mode: ShoveMode,
        scene_objects: tuple[SceneObject, ...] = (),
    ) -> PendingShove:
        attacker = current_actor(state)
        target = _actor_by_id(state, target_id)
        available = self.available_modes(
            state=state,
            board=board,
            target_id=target_id,
            scene_objects=scene_objects,
        )
        if mode not in available:
            raise ValueError(_unavailable_message(state, attacker, target, mode))
        defender_skill = _preferred_defense_skill(target)
        return PendingShove(
            attacker_id=str(attacker.id),
            attacker_name=attacker.name,
            target_id=str(target.id),
            target_name=target.name,
            mode=mode,
            defender_skill=defender_skill,
            attacker_request=condition_roll_request(
                charged_check_request(state, attacker, D20RollRequest(modifiers=skill_roll_modifiers(attacker, "athletics"))),
                state.condition_states,
                attacker,
                ability_check=True,
            ),
            defender_request=condition_roll_request(
                charged_check_request(state, target, D20RollRequest(modifiers=skill_roll_modifiers(target, defender_skill))),
                state.condition_states,
                target,
                ability_check=True,
            ),
            push_destination=(
                shove_push_destination(attacker, target)
                if mode == ShoveMode.PUSH
                else None
            ),
        )

    def resolve(
        self,
        *,
        state: CombatState,
        board: BoardState,
        pending: PendingShove,
        attacker_natural_roll: int,
        defender_natural_roll: int,
        scene_objects: tuple[SceneObject, ...] = (),
    ) -> ShoveResolution:
        attacker = current_actor(state)
        target = _actor_by_id(state, pending.target_id)
        if str(attacker.id) != pending.attacker_id:
            raise ValueError("Oczekujące Shove nie należy do aktywnego aktora.")
        available = self.available_modes(
            state=state,
            board=board,
            target_id=pending.target_id,
            scene_objects=scene_objects,
        )
        if pending.mode not in available:
            raise ValueError("Warunki zmieniły się i tego Shove nie można już wykonać.")
        if (
            pending.mode == ShoveMode.PUSH
            and pending.push_destination != shove_push_destination(attacker, target)
        ):
            raise ValueError("Pozycje zmieniły się i trzeba ponownie wybrać kierunek Shove.")
        contest = resolve_contest(
            ContestantRollInput(
                pending.attacker_id,
                "Strength (Athletics)",
                D20RollInput(pending.attacker_request, attacker_natural_roll),
            ),
            ContestantRollInput(
                pending.target_id,
                f"obrona {_skill_label(pending.defender_skill)}",
                D20RollInput(pending.defender_request, defender_natural_roll),
            ),
        )
        action = use_attack_action(state, attacker)
        if not action.accepted:
            raise ValueError(action.message)
        updated = replace(
            action.state,
            hidden_states=reveal_actor(action.state.hidden_states, pending.attacker_id),
        )
        succeeded = contest.outcome == ContestOutcome.INITIATOR_WINS
        if succeeded and pending.mode == ShoveMode.PRONE:
            application = apply_condition(
                updated.condition_states,
                target,
                CombatCondition.PRONE,
                source_actor_id=pending.attacker_id,
                source_label="Shove",
            )
            updated = replace(
                updated,
                condition_states=application.condition_states,
            )
            succeeded = application.applied
        elif succeeded and pending.push_destination is not None:
            updated = replace_actor(updated, replace(target, position=pending.push_destination))
        attacker_total = contest.initiator.roll.total
        defender_total = contest.defender.roll.total
        if succeeded and pending.mode == ShoveMode.PRONE:
            outcome_text = f"{target.name} zostaje powalony."
        elif succeeded:
            outcome_text = f"{target.name} zostaje odepchnięty o 5 ft."
        elif contest.outcome == ContestOutcome.TIE:
            outcome_text = "Remis zachowuje stan sprzed próby; cel odpiera Shove."
        else:
            outcome_text = f"{target.name} odpiera Shove."
        body = (
            f"{attacker.name}: Athletics {attacker_total}; {target.name}: "
            f"{_skill_label(pending.defender_skill)} {defender_total}. {outcome_text}"
        )
        return ShoveResolution(
            state=updated,
            contest=contest,
            mode=pending.mode,
            succeeded=succeeded,
            message_title="Shove",
            message_body=body,
            event_type="ui_combat_shove_resolved",
            event_payload=(
                ("attacker_id", pending.attacker_id),
                ("target_id", pending.target_id),
                ("mode", pending.mode.value),
                ("attacker_natural_roll", contest.initiator.roll.natural_roll),
                ("attacker_total", attacker_total),
                ("defender_skill", pending.defender_skill),
                ("defender_natural_roll", contest.defender.roll.natural_roll),
                ("defender_total", defender_total),
                ("outcome", contest.outcome.value),
                ("succeeded", succeeded),
            ),
        )


def shove_push_destination(attacker: Actor, target: Actor) -> Coordinate:
    return Coordinate(
        target.position.col + _direction(target.position.col - attacker.position.col),
        target.position.row + _direction(target.position.row - attacker.position.row),
    )


def forced_push_destination(
    *,
    board: BoardState,
    state: CombatState,
    attacker: Actor,
    target: Actor,
    distance_feet: int,
    scene_objects: tuple[SceneObject, ...] = (),
) -> Coordinate:
    """Return the farthest unobstructed tile on a straight forced-push line."""

    if distance_feet < 0 or distance_feet % 5:
        raise ValueError("Forced-push distance must be a non-negative multiple of 5 feet.")
    current = target
    destination = target.position
    for _ in range(distance_feet // 5):
        candidate = shove_push_destination(attacker, current)
        if not _push_destination_is_available(
            board,
            state,
            current,
            candidate,
            scene_objects,
        ):
            break
        destination = candidate
        current = replace(current, position=candidate)
    return destination


def automatic_defender_roll(pending: PendingShove, rng: Random) -> int:
    return rng.randint(1, 20)


def _base_shove_is_legal(state: CombatState, attacker: Actor, target: Actor) -> bool:
    return bool(
        can_use_attack_action(state, attacker)
        and attacker.faction == Faction.ALLY
        and not attacker.is_defeated()
        and target.faction not in {attacker.faction, Faction.NEUTRAL}
        and not target.is_defeated()
        and _within_five_feet(attacker, target)
        and can_grapple_or_shove_size(attacker.size, target.size)
        and not is_hidden_from(state.hidden_states, str(target.id), str(attacker.id))
    )


def _push_destination_is_available(
    board: BoardState,
    state: CombatState,
    target: Actor,
    destination: Coordinate,
    scene_objects: tuple[SceneObject, ...],
) -> bool:
    if not board.in_bounds(destination) or board.terrain_at(destination).blocks_movement:
        return False
    if any(
        candidate.position == destination
        and candidate.id != target.id
        and not candidate.is_defeated()
        for candidate in state.actors
    ):
        return False
    if any(obj.blocks_movement and destination in obj.positions for obj in scene_objects):
        return False
    dc = destination.col - target.position.col
    dr = destination.row - target.position.row
    if abs(dc) + abs(dr) == 1:
        return not board.blocks_edge(target.position, destination)
    side_a = Coordinate(destination.col, target.position.row)
    side_b = Coordinate(target.position.col, destination.row)
    return _diagonal_side_open(board, target.position, side_a) or _diagonal_side_open(
        board,
        target.position,
        side_b,
    )


def _diagonal_side_open(board: BoardState, start: Coordinate, side: Coordinate) -> bool:
    return bool(
        board.in_bounds(side)
        and not board.blocks_edge(start, side)
        and not board.terrain_at(side).blocks_movement
    )


def _preferred_defense_skill(target: Actor) -> str:
    athletics = skill_modifier(target, "athletics")
    acrobatics = skill_modifier(target, "acrobatics")
    return "acrobatics" if acrobatics > athletics else "athletics"


def _request_payload(label: str, request: D20RollRequest) -> dict[str, object]:
    instruction = roll_instruction(request)
    if any(m.stacking_key == "charge_accuracy" for m in request.modifiers):
        label = next((m.label for m in request.modifiers if m.modifier_type.value == "ability"), label)
    return {
        "label": label,
        "modifier_total": instruction.breakdown.modifier_total,
        "instruction": instruction.message,
        "active_modifiers": [_modifier_payload(item) for item in instruction.breakdown.active_modifiers],
        "ignored_modifiers": [_modifier_payload(item) for item in instruction.breakdown.ignored_modifiers],
    }


def _modifier_payload(modifier: RollModifier) -> dict[str, object]:
    return {"label": modifier.label, "value": modifier.value}


def _actor_by_id(state: CombatState, actor_id: str) -> Actor:
    actor = next((candidate for candidate in state.actors if str(candidate.id) == actor_id), None)
    if actor is None:
        raise ValueError(f"Nieznany aktor walki: {actor_id}.")
    return actor


def _within_five_feet(attacker: Actor, target: Actor) -> bool:
    distance = max(
        abs(attacker.position.col - target.position.col),
        abs(attacker.position.row - target.position.row),
    )
    return distance == 1


def _direction(value: int) -> int:
    return 0 if value == 0 else (1 if value > 0 else -1)


def _skill_label(skill: str) -> str:
    return "Athletics" if skill == "athletics" else "Acrobatics"


def _unavailable_message(
    state: CombatState,
    attacker: Actor,
    target: Actor,
    mode: ShoveMode,
) -> str:
    if not can_use_attack_action(state, attacker):
        return "Wykorzystano już wszystkie ataki tej akcji."
    if not _within_five_feet(attacker, target):
        return "Shove wymaga przeciwnika w zasięgu 5 ft."
    if not can_grapple_or_shove_size(attacker.size, target.size):
        maximum = largest_grapple_or_shove_target(attacker.size)
        return (
            f"{target.name} ma rozmiar {creature_size_label_pl(target.size)} i jest za duży. "
            f"{attacker.name} może odpychać cele najwyżej rozmiaru {creature_size_label_pl(maximum)}."
        )
    if mode == ShoveMode.PRONE and has_condition(
        state.condition_states,
        str(target.id),
        CombatCondition.PRONE,
    ):
        return f"{target.name} już jest powalony."
    if mode == ShoveMode.PUSH:
        return "Nie ma wolnego pola, na które można odepchnąć cel."
    return "Wybrany cel nie jest legalnym celem Shove."
