from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping

from dnd_board_game.actors import (
    Actor,
    ActorId,
    Faction,
    ability_roll_modifier,
    skill_modifier,
    skill_roll_modifiers,
)
from dnd_board_game.inventory import armor_skill_roll_request, effective_speed_feet
from dnd_board_game.combat import (
    ActionUse,
    ActiveCombatEffect,
    AttackSource,
    CombatCondition,
    CombatState,
    CombatStatus,
    HiddenState,
    SceneObject,
    current_actor,
    condition_roll_request,
    drop_prone,
    hide_eligibility,
    resolve_hide,
    resolve_search,
    remove_condition,
    stand_up,
    use_dash,
    use_turn_action,
)
from dnd_board_game.rules import (
    AdditionalEffectExpiration,
    EffectDuration,
    EffectSource,
    EffectSourceType,
    apply_active_effect,
    D20RollInput,
    D20RollRequest,
    resolve_d20_roll,
    roll_instruction,
)
from dnd_board_game.world import BoardState


@dataclass(frozen=True, slots=True)
class CombatTurnActionTransition:
    state: CombatState
    active_effects: tuple[ActiveCombatEffect, ...]
    actor_id: str
    message_title: str
    message_body: str
    event_type: str
    event_payload: tuple[tuple[str, object], ...]


@dataclass(frozen=True, slots=True)
class HelpPreparation:
    helper_id: str
    ally_ids: tuple[str, ...]
    target_ids: tuple[str, ...]
    board_message: str
    message_title: str
    message_body: str
    event_type: str
    event_payload: tuple[tuple[str, object], ...]


@dataclass(frozen=True, slots=True)
class ReadyPreparation:
    actor_id: str
    triggers: tuple[str, ...]
    board_message: str
    message_title: str
    message_body: str
    event_type: str
    event_payload: tuple[tuple[str, object], ...]


@dataclass(frozen=True, slots=True)
class PendingCombatSkillCheck:
    actor_id: str
    action: str
    skill: str
    modifier: int
    instruction: str
    opposing_actor_ids: tuple[str, ...]
    roll_mode: str = "normal"

    def as_payload(self) -> dict[str, object]:
        return {
            "actor_id": self.actor_id,
            "action": self.action,
            "skill": self.skill,
            "modifier": self.modifier,
            "instruction": self.instruction,
            "opposing_actor_ids": list(self.opposing_actor_ids),
            "roll_mode": self.roll_mode,
            "requires_second_roll": self.roll_mode != "normal",
        }


class CombatTurnActionFlowService:
    """Resolve common player turn actions without UI or hardware concerns."""

    def use_dash(
        self,
        *,
        state: CombatState,
        active_effects: tuple[ActiveCombatEffect, ...],
    ) -> CombatTurnActionTransition:
        actor = _active_hero(state)
        result = use_dash(state, actor)
        if not result.accepted:
            raise ValueError(result.message)
        return CombatTurnActionTransition(
            state=result.state,
            active_effects=active_effects,
            actor_id=str(actor.id),
            message_title="Dash",
            message_body=result.message,
            event_type="ui_combat_dash",
            event_payload=(
                ("actor_id", str(actor.id)),
                ("extra_movement_feet", effective_speed_feet(actor)),
            ),
        )

    def use_dodge(
        self,
        *,
        state: CombatState,
        active_effects: tuple[ActiveCombatEffect, ...],
    ) -> CombatTurnActionTransition:
        actor = _active_hero(state)
        effect = ActiveCombatEffect(
            id=f"dodge_until_next_turn:{actor.id}",
            actor_id=str(actor.id),
            kind="dodge_until_next_turn",
            label="Unik",
            object_id="combat_action:dodge",
            value=0,
            source=EffectSource(EffectSourceType.ACTION, "dodge", "Unik"),
            duration=EffectDuration.UNTIL_TURN_START,
        )
        return CombatTurnActionTransition(
            state=_consume_action(state),
            active_effects=_replace_actor_effect(active_effects, actor, effect),
            actor_id=str(actor.id),
            message_title="Unik",
            message_body=(
                f"Unik: ataki przeciwko {actor.name} mają utrudnienie do początku "
                "następnej tury tego aktora."
            ),
            event_type="ui_combat_dodge",
            event_payload=(("actor_id", str(actor.id)), ("attack_mode", "disadvantage")),
        )

    def use_disengage(
        self,
        *,
        state: CombatState,
        active_effects: tuple[ActiveCombatEffect, ...],
    ) -> CombatTurnActionTransition:
        actor = _active_hero(state)
        effect = ActiveCombatEffect(
            id=f"disengage_until_turn_end:{actor.id}",
            actor_id=str(actor.id),
            kind="disengage_until_turn_end",
            label="Odwrót",
            object_id="combat_action:disengage",
            value=0,
            source=EffectSource(EffectSourceType.ACTION, "disengage", "Odwrót"),
            duration=EffectDuration.UNTIL_TURN_END,
        )
        return CombatTurnActionTransition(
            state=_consume_action(state),
            active_effects=_replace_actor_effect(active_effects, actor, effect),
            actor_id=str(actor.id),
            message_title="Odwrót",
            message_body=f"Odwrót: {actor.name} może bezpiecznie odejść do końca tej tury.",
            event_type="ui_combat_disengage",
            event_payload=(("actor_id", str(actor.id)),),
        )

    def drop_prone(
        self,
        *,
        state: CombatState,
        active_effects: tuple[ActiveCombatEffect, ...],
    ) -> CombatTurnActionTransition:
        actor = _active_hero(state)
        result = drop_prone(state, actor)
        if not result.accepted:
            raise ValueError(result.message)
        return CombatTurnActionTransition(
            state=result.state,
            active_effects=active_effects,
            actor_id=str(actor.id),
            message_title="Powalenie",
            message_body=result.message,
            event_type="ui_combat_prone_applied",
            event_payload=(("actor_id", str(actor.id)),),
        )

    def stand_up(
        self,
        *,
        state: CombatState,
        active_effects: tuple[ActiveCombatEffect, ...],
    ) -> CombatTurnActionTransition:
        actor = _active_hero(state)
        result = stand_up(state, actor)
        if not result.accepted:
            raise ValueError(result.message)
        return CombatTurnActionTransition(
            state=result.state,
            active_effects=active_effects,
            actor_id=str(actor.id),
            message_title="Wstawanie",
            message_body=result.message,
            event_type="ui_combat_prone_removed",
            event_payload=(
                ("actor_id", str(actor.id)),
                ("movement_cost_feet", result.movement_cost_feet),
            ),
        )

    def prepare_hide(
        self,
        *,
        state: CombatState,
        board: BoardState,
        scene_objects: tuple[SceneObject, ...] = (),
    ) -> PendingCombatSkillCheck:
        actor = _active_hero(state)
        if state.turn_action.action_use != ActionUse.ACTION_AVAILABLE:
            raise ValueError("Akcja w tej turze została już zużyta.")
        eligibility = hide_eligibility(board, actor, state.actors, scene_objects)
        if not eligibility.allowed:
            names = ", ".join(
                _actor_by_string_id(state, actor_id).name
                for actor_id in eligibility.blocking_observer_ids
            )
            raise ValueError(f"Nie możesz się ukryć: nadal wyraźnie widzą cię: {names}.")
        request = _skill_request(state, actor, "stealth")
        opponents = tuple(
            str(candidate.id)
            for candidate in state.actors
            if candidate.faction not in {actor.faction, Faction.NEUTRAL}
            and not candidate.is_defeated()
        )
        return PendingCombatSkillCheck(
            actor_id=str(actor.id),
            action="hide",
            skill="stealth",
            modifier=skill_modifier(actor, "stealth"),
            instruction=roll_instruction(request).message,
            opposing_actor_ids=opponents,
            roll_mode=request.mode.value,
        )

    def resolve_hide(
        self,
        *,
        state: CombatState,
        board: BoardState,
        pending: PendingCombatSkillCheck,
        natural_roll: int,
        natural_roll_2: int | None = None,
        active_effects: tuple[ActiveCombatEffect, ...],
        scene_objects: tuple[SceneObject, ...] = (),
    ) -> CombatTurnActionTransition:
        actor = _validate_pending_skill_actor(state, pending, "hide")
        eligibility = hide_eligibility(board, actor, state.actors, scene_objects)
        if not eligibility.allowed:
            raise ValueError("Warunki zmieniły się i nie można już wykonać Hide.")
        request = _skill_request(state, actor, "stealth")
        if request.mode.value != "normal" and natural_roll_2 is None:
            raise ValueError("Ten test wymaga wpisania dwóch wyników d20.")
        result = resolve_d20_roll(D20RollInput(request, natural_roll, natural_roll_2))
        hiding = resolve_hide(state.hidden_states, actor, state.actors, result.total)
        updated_state = replace(
            _consume_action(state),
            hidden_states=hiding.hidden_states,
        )
        hidden_names = _actor_names(state, hiding.hidden_state.hidden_from_actor_ids) if hiding.hidden_state else ()
        detected_names = _actor_names(state, hiding.detected_by_actor_ids)
        if hidden_names:
            body = f"{actor.name} ukrywa się z wynikiem {result.total} przed: {', '.join(hidden_names)}."
            if detected_names:
                body += f" Nadal wykrywają go: {', '.join(detected_names)}."
        else:
            body = f"{actor.name} uzyskuje {result.total}, ale każdy przeciwnik go wykrywa."
        return CombatTurnActionTransition(
            state=updated_state,
            active_effects=active_effects,
            actor_id=str(actor.id),
            message_title="Hide",
            message_body=body,
            event_type="ui_combat_hide_resolved",
            event_payload=(
                ("actor_id", str(actor.id)),
                ("natural_roll", result.natural_roll),
                ("total", result.total),
                ("hidden_from_actor_ids", list(hiding.hidden_state.hidden_from_actor_ids) if hiding.hidden_state else []),
                ("detected_by_actor_ids", list(hiding.detected_by_actor_ids)),
            ),
        )

    def prepare_search(self, *, state: CombatState) -> PendingCombatSkillCheck:
        actor = _active_hero(state)
        if state.turn_action.action_use != ActionUse.ACTION_AVAILABLE:
            raise ValueError("Akcja w tej turze została już zużyta.")
        hidden_actor_ids = tuple(
            hidden.actor_id
            for hidden in state.hidden_states
            if str(actor.id) in hidden.hidden_from_actor_ids
        )
        if not hidden_actor_ids:
            raise ValueError("Nie ma obecnie ukrytego przeciwnika, którego można aktywnie szukać.")
        request = _skill_request(state, actor, "perception")
        return PendingCombatSkillCheck(
            actor_id=str(actor.id),
            action="search",
            skill="perception",
            modifier=skill_modifier(actor, "perception"),
            instruction=roll_instruction(request).message,
            opposing_actor_ids=hidden_actor_ids,
        )

    def resolve_search(
        self,
        *,
        state: CombatState,
        pending: PendingCombatSkillCheck,
        natural_roll: int,
        active_effects: tuple[ActiveCombatEffect, ...],
    ) -> CombatTurnActionTransition:
        actor = _validate_pending_skill_actor(state, pending, "search")
        result = resolve_d20_roll(D20RollInput(_skill_request(state, actor, "perception"), natural_roll))
        search = resolve_search(state.hidden_states, actor, result.total)
        updated_state = replace(_consume_action(state), hidden_states=search.hidden_states)
        found_names = _actor_names(state, search.found_actor_ids)
        body = (
            f"{actor.name} uzyskuje {result.total} i odnajduje: {', '.join(found_names)}."
            if found_names
            else f"{actor.name} uzyskuje {result.total}, ale nie odnajduje ukrytego przeciwnika."
        )
        return CombatTurnActionTransition(
            state=updated_state,
            active_effects=active_effects,
            actor_id=str(actor.id),
            message_title="Search",
            message_body=body,
            event_type="ui_combat_search_resolved",
            event_payload=(
                ("actor_id", str(actor.id)),
                ("natural_roll", result.natural_roll),
                ("total", result.total),
                ("found_actor_ids", list(search.found_actor_ids)),
            ),
        )

    def prepare_net_escape(self, *, state: CombatState) -> PendingCombatSkillCheck:
        actor = _active_hero(state)
        if state.turn_action.action_use != ActionUse.ACTION_AVAILABLE:
            raise ValueError("Akcja w tej turze została już zużyta.")
        if not _actor_is_restrained_by_net(state, actor):
            raise ValueError("Ten aktor nie jest unieruchomiony przez sieć.")
        request = _net_escape_request(state, actor)
        instruction = roll_instruction(request)
        return PendingCombatSkillCheck(
            actor_id=str(actor.id),
            action="escape_net",
            skill="strength",
            modifier=instruction.breakdown.modifier_total,
            instruction=instruction.message,
            opposing_actor_ids=(),
            roll_mode=request.mode.value,
        )

    def resolve_net_escape(
        self,
        *,
        state: CombatState,
        pending: PendingCombatSkillCheck,
        natural_roll: int,
        natural_roll_2: int | None = None,
        active_effects: tuple[ActiveCombatEffect, ...],
    ) -> CombatTurnActionTransition:
        actor = _validate_pending_skill_actor(state, pending, "escape_net")
        if not _actor_is_restrained_by_net(state, actor):
            raise ValueError("Sieć nie unieruchamia już tego aktora.")
        request = _net_escape_request(state, actor)
        if request.mode.value != "normal" and natural_roll_2 is None:
            raise ValueError("Ten test wymaga wpisania dwóch wyników d20.")
        result = resolve_d20_roll(
            D20RollInput(request, natural_roll, natural_roll_2)
        )
        escaped = result.total >= 10
        conditions = (
            remove_condition(
                state.condition_states,
                str(actor.id),
                CombatCondition.RESTRAINED,
            )
            if escaped
            else state.condition_states
        )
        updated = replace(_consume_action(state), condition_states=conditions)
        return CombatTurnActionTransition(
            state=updated,
            active_effects=active_effects,
            actor_id=str(actor.id),
            message_title="Sieć",
            message_body=(
                f"{actor.name} uwalnia się z sieci (Strength {result.total} przeciw ST 10)."
                if escaped
                else f"{actor.name} nie uwalnia się z sieci (Strength {result.total} przeciw ST 10)."
            ),
            event_type="ui_combat_net_escape",
            event_payload=(
                ("actor_id", str(actor.id)),
                ("natural_roll", result.natural_roll),
                ("total", result.total),
                ("dc", 10),
                ("escaped", escaped),
            ),
        )

    def prepare_help(self, *, state: CombatState) -> HelpPreparation:
        actor = _active_hero(state)
        if state.turn_action.action_use != ActionUse.ACTION_AVAILABLE:
            raise ValueError("Akcja w tej turze została już zużyta.")
        allies = tuple(
            candidate
            for candidate in state.actors
            if candidate.faction == actor.faction
            and candidate.id != actor.id
            and not candidate.is_defeated()
        )
        targets = tuple(
            candidate
            for candidate in state.actors
            if candidate.faction not in {actor.faction, Faction.NEUTRAL}
            and not candidate.is_defeated()
            and _coordinates_in_reach(actor, candidate, 5)
        )
        if not allies:
            raise ValueError("Brak żywego sojusznika, któremu można pomóc.")
        if not targets:
            raise ValueError("Brak przeciwnika w zasięgu 5 ft pomagającego.")
        ally_ids = tuple(str(ally.id) for ally in allies)
        target_ids = tuple(str(target.id) for target in targets)
        return HelpPreparation(
            helper_id=str(actor.id),
            ally_ids=ally_ids,
            target_ids=target_ids,
            board_message="Wybierz sojusznika i cel pomocy w panelu walki.",
            message_title="Pomoc",
            message_body=f"{actor.name} przygotowuje akcję Help.",
            event_type="ui_combat_help_started",
            event_payload=(
                ("helper_id", str(actor.id)),
                ("ally_ids", list(ally_ids)),
                ("target_ids", list(target_ids)),
            ),
        )

    def confirm_help(
        self,
        *,
        state: CombatState,
        active_effects: tuple[ActiveCombatEffect, ...],
        helper_id: str,
        ally_ids: tuple[str, ...],
        target_ids: tuple[str, ...],
        ally_id: str,
        target_id: str,
    ) -> CombatTurnActionTransition:
        helper = _active_hero(state)
        if str(helper.id) != helper_id:
            raise ValueError("Oczekująca akcja Help nie należy do aktywnego aktora.")
        if ally_id not in ally_ids:
            raise ValueError("Wybrany sojusznik nie jest legalnym celem Help.")
        if target_id not in target_ids:
            raise ValueError("Wybrany przeciwnik nie jest legalnym celem Help.")
        ally = _actor_by_string_id(state, ally_id)
        target = _actor_by_string_id(state, target_id)
        effect = ActiveCombatEffect(
            id=f"help_attack_advantage:{helper.id}:{ally.id}:{target.id}",
            actor_id=str(ally.id),
            kind="help_attack_advantage",
            label=f"Pomoc: {helper.name}",
            object_id="combat_action:help",
            value=0,
            source_actor_id=str(helper.id),
            target_actor_id=str(target.id),
            source=EffectSource(EffectSourceType.ACTION, "help", "Pomoc"),
            duration=EffectDuration.UNTIL_NEXT_ATTACK,
            expiration_actor_id=str(ally.id),
            stacking_key=f"help:{helper.id}",
            additional_expirations=(
                AdditionalEffectExpiration(
                    EffectDuration.UNTIL_TURN_START,
                    actor_id=str(helper.id),
                ),
                AdditionalEffectExpiration(EffectDuration.UNTIL_ENCOUNTER_END),
            ),
        )
        return CombatTurnActionTransition(
            state=_consume_action(state),
            active_effects=apply_active_effect(active_effects, effect).active_effects,
            actor_id=str(helper.id),
            message_title="Pomoc",
            message_body=(
                f"Help: {helper.name} pomaga {ally.name}. Następny atak {ally.name} "
                f"przeciwko {target.name} ma przewagę."
            ),
            event_type="ui_combat_help_confirmed",
            event_payload=(
                ("helper_id", str(helper.id)),
                ("ally_id", str(ally.id)),
                ("target_id", str(target.id)),
            ),
        )

    def prepare_ready(
        self,
        *,
        state: CombatState,
        attack_sources_by_actor: Mapping[ActorId, AttackSource],
        triggers: tuple[str, ...] = ("enemy_moves", "enemy_attacks"),
    ) -> ReadyPreparation:
        actor = _active_hero(state)
        if state.turn_action.action_use != ActionUse.ACTION_AVAILABLE:
            raise ValueError("Akcja w tej turze została już zużyta.")
        if attack_sources_by_actor.get(actor.id) is None:
            raise ValueError(f"Aktor {actor.name} nie ma zdefiniowanego ataku do przygotowania.")
        return ReadyPreparation(
            actor_id=str(actor.id),
            triggers=triggers,
            board_message="Wybierz warunek przygotowanej akcji w panelu walki.",
            message_title="Ready",
            message_body=f"{actor.name} przygotowuje akcję.",
            event_type="ui_combat_ready_started",
            event_payload=(("actor_id", str(actor.id)),),
        )

    def confirm_ready(
        self,
        *,
        state: CombatState,
        active_effects: tuple[ActiveCombatEffect, ...],
        actor_id: str,
        triggers: tuple[str, ...],
        trigger: str,
    ) -> CombatTurnActionTransition:
        if trigger not in triggers:
            raise ValueError("Nieznany warunek przygotowanej akcji.")
        actor = _active_hero(state)
        if str(actor.id) != actor_id:
            raise ValueError("Oczekująca akcja Ready nie należy do aktywnego aktora.")
        effect = ActiveCombatEffect(
            id=f"ready_attack:{actor.id}:{trigger}",
            actor_id=str(actor.id),
            kind="ready_attack",
            label="Ready",
            object_id=f"combat_action:ready:{trigger}",
            value=0,
            source=EffectSource(EffectSourceType.ACTION, "ready", "Ready"),
            duration=EffectDuration.UNTIL_TURN_START,
        )
        return CombatTurnActionTransition(
            state=_consume_action(state),
            active_effects=apply_active_effect(active_effects, effect).active_effects,
            actor_id=str(actor.id),
            message_title="Ready",
            message_body=f"Ready: {actor.name} przygotowuje atak, {_ready_trigger_label(trigger)}.",
            event_type="ui_combat_ready_confirmed",
            event_payload=(("actor_id", str(actor.id)), ("trigger", trigger)),
        )


def _active_hero(state: CombatState) -> Actor:
    if state.status != CombatStatus.ACTIVE:
        raise ValueError("Walka nie jest aktywna.")
    actor = current_actor(state)
    if actor.faction != Faction.ALLY:
        raise ValueError("To nie jest tura bohatera.")
    return actor


def _consume_action(state: CombatState) -> CombatState:
    result = use_turn_action(state)
    if not result.accepted:
        raise ValueError(result.message)
    return result.state


def _replace_actor_effect(
    active_effects: tuple[ActiveCombatEffect, ...],
    actor: Actor,
    replacement: ActiveCombatEffect,
) -> tuple[ActiveCombatEffect, ...]:
    if replacement.actor_id != str(actor.id):
        raise ValueError("Replacement effect belongs to a different actor.")
    return apply_active_effect(active_effects, replacement).active_effects


def _actor_by_string_id(state: CombatState, actor_id: str) -> Actor:
    actor = next((candidate for candidate in state.actors if str(candidate.id) == actor_id), None)
    if actor is None:
        raise ValueError(f"Nieznany aktor walki: {actor_id}.")
    return actor


def _coordinates_in_reach(a: Actor, b: Actor, reach_feet: int) -> bool:
    distance_feet = max(
        abs(a.position.col - b.position.col),
        abs(a.position.row - b.position.row),
    ) * 5
    return reach_feet > 0 and 0 < distance_feet <= reach_feet


def _ready_trigger_label(trigger: str) -> str:
    labels = {
        "enemy_moves": "gdy przeciwnik się poruszy",
        "enemy_attacks": "gdy przeciwnik zaatakuje",
    }
    return labels.get(trigger, trigger)


def _skill_request(state: CombatState, actor: Actor, skill: str) -> D20RollRequest:
    request = armor_skill_roll_request(
        actor,
        skill,
        D20RollRequest(modifiers=skill_roll_modifiers(actor, skill)),
    )
    return condition_roll_request(
        request,
        state.condition_states,
        actor,
        ability_check=True,
    )


def _actor_is_restrained_by_net(state: CombatState, actor: Actor) -> bool:
    return any(
        condition.actor_id == str(actor.id)
        and condition.condition == CombatCondition.RESTRAINED
        and condition.source_label.startswith("Sieć:")
        for condition in state.condition_states
    )


def _net_escape_request(state: CombatState, actor: Actor) -> D20RollRequest:
    return condition_roll_request(
        D20RollRequest(modifiers=(ability_roll_modifier(actor, "strength"),)),
        state.condition_states,
        actor,
        ability_check=True,
    )


def _validate_pending_skill_actor(
    state: CombatState,
    pending: PendingCombatSkillCheck,
    action: str,
) -> Actor:
    actor = _active_hero(state)
    if pending.action != action or pending.actor_id != str(actor.id):
        raise ValueError("Oczekujący test nie należy do tej akcji ani aktywnego aktora.")
    return actor


def _actor_names(state: CombatState, actor_ids: tuple[str, ...]) -> tuple[str, ...]:
    names: list[str] = []
    for actor_id in actor_ids:
        names.append(_actor_by_string_id(state, actor_id).name)
    return tuple(names)
