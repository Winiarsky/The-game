from __future__ import annotations

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
    add_condition,
    can_use_attack_action,
    current_actor,
    grappled_actor_ids,
    grappled_by,
    has_condition,
    is_hidden_from,
    remove_grapple,
    reveal_actor,
    use_turn_action,
    use_attack_action,
)
from dnd_board_game.inventory import free_hand_count
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


class GrappleMode(StrEnum):
    START = "start"
    ESCAPE = "escape"


@dataclass(frozen=True, slots=True)
class PendingGrapple:
    actor_id: str
    actor_name: str
    opponent_id: str
    opponent_name: str
    mode: GrappleMode
    actor_skill: str
    opponent_skill: str
    actor_request: D20RollRequest
    opponent_request: D20RollRequest

    def as_payload(self) -> dict[str, object]:
        return {
            "actor_id": self.actor_id,
            "actor_name": self.actor_name,
            "opponent_id": self.opponent_id,
            "opponent_name": self.opponent_name,
            "mode": self.mode.value,
            "mode_label": "chwyt" if self.mode == GrappleMode.START else "ucieczka z chwytu",
            "actor_check": _request_payload(_skill_label(self.actor_skill), self.actor_request),
            "opponent_check": _request_payload(_skill_label(self.opponent_skill), self.opponent_request),
        }


@dataclass(frozen=True, slots=True)
class GrappleResolution:
    state: CombatState
    contest: ContestResult
    mode: GrappleMode
    succeeded: bool
    message_title: str
    message_body: str
    event_type: str
    event_payload: tuple[tuple[str, object], ...]


class CombatGrappleFlowService:
    """Prepare and resolve the D&D 5e 2014 Grapple and escape contests."""

    def can_start(self, state: CombatState, target_id: str) -> bool:
        actor = current_actor(state)
        target = _actor_by_id(state, target_id)
        return _start_is_legal(state, actor, target)

    def can_escape(self, state: CombatState) -> bool:
        actor = current_actor(state)
        return _escape_is_legal(state, actor)

    def prepare(
        self,
        *,
        state: CombatState,
        mode: GrappleMode,
        target_id: str = "",
    ) -> PendingGrapple:
        actor = current_actor(state)
        if mode == GrappleMode.START:
            target = _actor_by_id(state, target_id)
            if not _start_is_legal(state, actor, target):
                raise ValueError(_start_unavailable_message(state, actor, target))
            actor_skill = "athletics"
            opponent_skill = _preferred_skill(target)
        else:
            if not _escape_is_legal(state, actor):
                raise ValueError("Ten aktor nie może teraz próbować ucieczki z chwytu.")
            source_id = grappled_by(state.condition_states, str(actor.id))
            target = _actor_by_id(state, source_id or "")
            actor_skill = _preferred_skill(actor)
            opponent_skill = "athletics"
        return PendingGrapple(
            actor_id=str(actor.id),
            actor_name=actor.name,
            opponent_id=str(target.id),
            opponent_name=target.name,
            mode=mode,
            actor_skill=actor_skill,
            opponent_skill=opponent_skill,
            actor_request=D20RollRequest(modifiers=skill_roll_modifiers(actor, actor_skill)),
            opponent_request=D20RollRequest(modifiers=skill_roll_modifiers(target, opponent_skill)),
        )

    def resolve(
        self,
        *,
        state: CombatState,
        pending: PendingGrapple,
        actor_natural_roll: int,
        opponent_natural_roll: int,
    ) -> GrappleResolution:
        actor = current_actor(state)
        opponent = _actor_by_id(state, pending.opponent_id)
        if str(actor.id) != pending.actor_id:
            raise ValueError("Oczekujący Grapple nie należy do aktywnego aktora.")
        if pending.mode == GrappleMode.START and not _start_is_legal(state, actor, opponent):
            raise ValueError("Warunki zmieniły się i tego Grapple nie można już wykonać.")
        if pending.mode == GrappleMode.ESCAPE and (
            not _escape_is_legal(state, actor)
            or grappled_by(state.condition_states, str(actor.id)) != pending.opponent_id
        ):
            raise ValueError("Warunki chwytu zmieniły się; ucieczka nie jest już potrzebna.")
        contest = resolve_contest(
            ContestantRollInput(
                pending.actor_id,
                _skill_label(pending.actor_skill),
                D20RollInput(pending.actor_request, actor_natural_roll),
            ),
            ContestantRollInput(
                pending.opponent_id,
                _skill_label(pending.opponent_skill),
                D20RollInput(pending.opponent_request, opponent_natural_roll),
            ),
        )
        action = (
            use_attack_action(state, actor)
            if pending.mode == GrappleMode.START
            else use_turn_action(state)
        )
        if not action.accepted:
            raise ValueError(action.message)
        updated = replace(
            action.state,
            hidden_states=reveal_actor(action.state.hidden_states, pending.actor_id),
        )
        succeeded = contest.outcome == ContestOutcome.INITIATOR_WINS
        if succeeded and pending.mode == GrappleMode.START:
            updated = replace(
                updated,
                condition_states=add_condition(
                    updated.condition_states,
                    pending.opponent_id,
                    CombatCondition.GRAPPLED,
                    source_actor_id=pending.actor_id,
                ),
            )
        elif succeeded:
            updated = replace(
                updated,
                condition_states=remove_grapple(
                    updated.condition_states,
                    pending.actor_id,
                    source_actor_id=pending.opponent_id,
                ),
            )
        actor_total = contest.initiator.roll.total
        opponent_total = contest.defender.roll.total
        if succeeded and pending.mode == GrappleMode.START:
            outcome = f"{opponent.name} otrzymuje stan Grappled."
        elif succeeded:
            outcome = f"{actor.name} uwalnia się z chwytu."
        elif contest.outcome == ContestOutcome.TIE:
            outcome = "Remis zachowuje dotychczasowy stan chwytu."
        elif pending.mode == GrappleMode.START:
            outcome = f"{opponent.name} odpiera próbę chwytu."
        else:
            outcome = f"{actor.name} nie uwalnia się z chwytu."
        body = (
            f"{actor.name}: {_skill_label(pending.actor_skill)} {actor_total}; "
            f"{opponent.name}: {_skill_label(pending.opponent_skill)} {opponent_total}. {outcome}"
        )
        return GrappleResolution(
            state=updated,
            contest=contest,
            mode=pending.mode,
            succeeded=succeeded,
            message_title="Grapple",
            message_body=body,
            event_type="ui_combat_grapple_resolved",
            event_payload=(
                ("actor_id", pending.actor_id),
                ("opponent_id", pending.opponent_id),
                ("mode", pending.mode.value),
                ("actor_skill", pending.actor_skill),
                ("actor_natural_roll", contest.initiator.roll.natural_roll),
                ("actor_total", actor_total),
                ("opponent_skill", pending.opponent_skill),
                ("opponent_natural_roll", contest.defender.roll.natural_roll),
                ("opponent_total", opponent_total),
                ("outcome", contest.outcome.value),
                ("succeeded", succeeded),
            ),
        )


def automatic_grapple_opponent_roll(pending: PendingGrapple, rng: Random) -> int:
    return rng.randint(1, 20)


def _start_is_legal(state: CombatState, actor: Actor, target: Actor) -> bool:
    return bool(
        can_use_attack_action(state, actor)
        and actor.faction == Faction.ALLY
        and not actor.is_defeated()
        and target.faction not in {actor.faction, Faction.NEUTRAL}
        and not target.is_defeated()
        and _within_five_feet(actor, target)
        and can_grapple_or_shove_size(actor.size, target.size)
        and free_hand_count(actor.inventory) > 0
        and not has_condition(state.condition_states, str(target.id), CombatCondition.GRAPPLED)
        and not grappled_actor_ids(state.condition_states, str(actor.id))
        and not is_hidden_from(state.hidden_states, str(target.id), str(actor.id))
    )


def _escape_is_legal(state: CombatState, actor: Actor) -> bool:
    source_id = grappled_by(state.condition_states, str(actor.id))
    return bool(
        state.turn_action.action_use == ActionUse.ACTION_AVAILABLE
        and actor.faction == Faction.ALLY
        and not actor.is_defeated()
        and source_id is not None
    )


def _preferred_skill(actor: Actor) -> str:
    return (
        "acrobatics"
        if skill_modifier(actor, "acrobatics") > skill_modifier(actor, "athletics")
        else "athletics"
    )


def _within_five_feet(actor: Actor, target: Actor) -> bool:
    return max(
        abs(actor.position.col - target.position.col),
        abs(actor.position.row - target.position.row),
    ) == 1


def _actor_by_id(state: CombatState, actor_id: str) -> Actor:
    actor = next((candidate for candidate in state.actors if str(candidate.id) == actor_id), None)
    if actor is None:
        raise ValueError(f"Nieznany aktor walki: {actor_id}.")
    return actor


def _request_payload(label: str, request: D20RollRequest) -> dict[str, object]:
    instruction = roll_instruction(request)
    return {
        "label": label,
        "modifier_total": instruction.breakdown.modifier_total,
        "instruction": instruction.message,
        "active_modifiers": [_modifier_payload(item) for item in instruction.breakdown.active_modifiers],
        "ignored_modifiers": [_modifier_payload(item) for item in instruction.breakdown.ignored_modifiers],
    }


def _modifier_payload(modifier: RollModifier) -> dict[str, object]:
    return {"label": modifier.label, "value": modifier.value}


def _skill_label(skill: str) -> str:
    return "Athletics" if skill == "athletics" else "Acrobatics"


def _start_unavailable_message(state: CombatState, actor: Actor, target: Actor) -> str:
    if not can_use_attack_action(state, actor):
        return "Wykorzystano już wszystkie ataki tej akcji."
    if not _within_five_feet(actor, target):
        return "Grapple wymaga przeciwnika w zasięgu 5 ft."
    if not can_grapple_or_shove_size(actor.size, target.size):
        maximum = largest_grapple_or_shove_target(actor.size)
        return (
            f"{target.name} ma rozmiar {creature_size_label_pl(target.size)} i jest za duży. "
            f"{actor.name} może chwytać cele najwyżej rozmiaru {creature_size_label_pl(maximum)}."
        )
    if free_hand_count(actor.inventory) <= 0:
        return f"{actor.name} potrzebuje wolnej ręki, aby rozpocząć Grapple."
    if has_condition(state.condition_states, str(target.id), CombatCondition.GRAPPLED):
        return f"{target.name} już jest chwytany."
    if grappled_actor_ids(state.condition_states, str(actor.id)):
        return f"{actor.name} już trzyma inny cel."
    return "Wybrany cel nie jest legalnym celem Grapple."
