from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template_string, request

from dnd_board_game.actors import Actor
from dnd_board_game.combat import SceneFlags, scene_flag, set_scene_flag
from dnd_board_game.exploration import (
    CheckAggregation,
    CheckParticipants,
    ConsequenceTarget,
    ExplorationChallenge,
    ExplorationChallengeOption,
    ExplorationCheckPlan,
    ExplorationPoint,
    ExplorationResource,
    ExplorationState,
    ExplorationZone,
    PartyCheckInput,
    available_exploration_zones,
    challenge_for_zone,
    challenge_state_for,
    grant_resource,
    reveal_exploration_points,
    resolve_challenge_option,
    resolve_exploration_check,
    set_party_zone,
    visible_exploration_points,
    visible_exploration_zones,
)
from dnd_board_game.llm import (
    GmActionFlow,
    GmDeclarationAnalysis,
    GmDeclarationAnalysisType,
    GmDeclarationThreadEntry,
    GmClassifierProposal,
    GmPreparationEffect,
    NpcInteractionProposal,
    build_gm_classifier_request,
    build_npc_interaction_request,
    challenge_option_from_validated_proposal,
    validate_gm_declaration_analysis,
    validate_gm_classifier_proposal,
    validate_npc_interaction_proposal,
)
from dnd_board_game.rules import D20RollInput, D20RollRequest, RollModifier, RollModifierType, ability_modifier, resolve_d20_roll
from dnd_board_game.scenarios import LoadedExploration, build_exploration_from_scenario, load_scenario


class PendingKind(StrEnum):
    CHALLENGE = "challenge"
    NPC = "npc"


class PendingStage(StrEnum):
    DECISION = "decision"
    ROLL = "roll"


@dataclass(frozen=True, slots=True)
class UiMessage:
    title: str
    body: str

    def as_payload(self) -> dict[str, str]:
        return {"title": self.title, "body": self.body}


@dataclass(frozen=True, slots=True)
class PendingInteraction:
    kind: PendingKind
    stage: PendingStage
    proposal: GmClassifierProposal | NpcInteractionProposal
    challenge: ExplorationChallenge | None = None
    option: ExplorationChallengeOption | None = None
    resources: tuple[ExplorationResource, ...] = ()
    point: ExplorationPoint | None = None
    check_plan: ExplorationCheckPlan | None = None

    def as_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "kind": self.kind.value,
            "stage": self.stage.value,
            "proposal": self.proposal.model_dump(mode="json"),
        }
        if self.challenge is not None:
            payload["challenge_id"] = self.challenge.id
            payload["challenge_name"] = self.challenge.name
        if self.option is not None:
            payload["option"] = _challenge_option_payload(self.option)
        if self.resources:
            payload["resources"] = [_resource_payload(resource) for resource in self.resources]
        if self.point is not None:
            payload["point_id"] = self.point.id
            payload["point_name"] = self.point.name
        if self.check_plan is not None:
            payload["check_plan"] = self.check_plan.as_payload()
        return payload


class ExplorationUiSession:
    def __init__(
        self,
        scenario_path: str | Path,
        *,
        gm_client: object | None = None,
        npc_client: object | None = None,
        debug_point_id: str | None = None,
    ) -> None:
        self.scenario_path = Path(scenario_path)
        self.gm_client = gm_client
        self.npc_client = npc_client
        self.debug_point_id = debug_point_id or ""
        self.reset()

    def reset(self) -> None:
        self.exploration = build_exploration_from_scenario(load_scenario(self.scenario_path))
        self.state = ExplorationState(
            self.exploration.zones,
            self.exploration.points,
            self.exploration.party_position,
            SceneFlags(),
            challenges=self.exploration.challenges,
            resources=self.exploration.resources,
            inventory_resource_ids=self.exploration.initial_resource_ids,
        )
        if self.debug_point_id:
            self.state, _revealed = reveal_exploration_points(self.state, (self.debug_point_id,))
        self.messages: list[UiMessage] = []
        self.pending: PendingInteraction | None = None
        self.declaration_thread: list[GmDeclarationThreadEntry] = []
        self.active_preparation_effects: list[GmPreparationEffect] = []
        self.selected_lead_actor_id = str(self.exploration.actors[0].id)
        self.active_point_id = self.debug_point_id

    @property
    def current_zone(self) -> ExplorationZone:
        return next(zone for zone in self.state.zones if zone.id == self.state.party_position.zone_id)

    @property
    def active_point(self) -> ExplorationPoint | None:
        if not self.active_point_id:
            return None
        return next((point for point in self.state.points if point.id == self.active_point_id), None)

    def state_payload(self) -> dict[str, object]:
        active_challenge = self.active_challenge
        return {
            "scenario": {"id": self.exploration.scenario_id, "name": self.exploration.scenario_name},
            "current_zone": _zone_payload(self.current_zone),
            "available_zones": [_zone_payload(zone) for zone in visible_exploration_zones(self.state.zones) if zone_is_ui_available(self.state, zone)],
            "travel_options": [_zone_payload(zone) for zone in self.travel_options()],
            "visible_points": [_point_payload(point) for point in visible_exploration_points(self.state.points)],
            "current_zone_points": [_point_payload(point) for point in self.current_zone_points()],
            "active_challenge": _challenge_payload(self.state, active_challenge) if active_challenge else None,
            "active_point": _point_payload(self.active_point) if self.active_point else None,
            "resources": [_resource_payload(resource) for resource in self.state.resources if resource.id in self.state.inventory_resource_ids],
            "actors": [{"id": str(actor.id), "name": actor.name} for actor in self.exploration.actors],
            "flags": [{"key": key, "value": value} for key, value in self.state.flags.values],
            "messages": [message.as_payload() for message in self.messages],
            "pending": self.pending.as_payload() if self.pending else None,
            "required_rolls": self.required_rolls_payload(),
        }

    def submit_action(self, text: str) -> dict[str, object]:
        text = text.strip()
        if not text:
            raise ValueError("Deklaracja nie może być pusta.")
        point = self.active_point
        if point is not None and point.npc_interaction is not None:
            return self._submit_npc_action(point, text)
        challenge = self.active_challenge
        if challenge is None:
            raise ValueError("W aktualnej lokacji nie ma aktywnego wyzwania ani punktu NPC.")
        return self._submit_challenge_action(challenge, text)

    @property
    def active_challenge(self) -> ExplorationChallenge | None:
        challenge = challenge_for_zone(self.state, self.current_zone.id)
        if challenge is None:
            return None
        if challenge_state_for(self.state, challenge.id).completed:
            return None
        return challenge

    def travel_options(self) -> tuple[ExplorationZone, ...]:
        available_by_id = {zone.id: zone for zone in available_exploration_zones(self.state)}
        return tuple(
            available_by_id[zone_id]
            for zone_id in self.current_zone.adjacent_zone_ids
            if zone_id in available_by_id and zone_id != self.current_zone.id
        )

    def travel_to(self, zone_id: str) -> dict[str, object]:
        destination = next((zone for zone in self.travel_options() if zone.id == zone_id), None)
        if destination is None:
            raise ValueError("Ta lokacja nie jest teraz dostępna.")
        previous = self.current_zone
        self.state = set_party_zone(self.state, destination)
        self.pending = None
        self.active_point_id = ""
        self._add_message("Przejście", f"Drużyna przechodzi z {previous.name} do lokacji: {destination.name}.")
        return self.state_payload()

    def current_zone_points(self) -> tuple[ExplorationPoint, ...]:
        return tuple(point for point in visible_exploration_points(self.state.points) if point.zone_id == self.current_zone.id)

    def select_point(self, point_id: str) -> dict[str, object]:
        if not point_id:
            self.active_point_id = ""
            return self.state_payload()
        point = next((candidate for candidate in self.current_zone_points() if candidate.id == point_id), None)
        if point is None:
            raise ValueError("Ten punkt nie jest dostępny w aktualnej lokacji.")
        self.active_point_id = point.id
        self.pending = None
        if point.npc_interaction is not None and point.npc_interaction.dialogue_intro:
            self._add_message(point.npc_interaction.name, point.npc_interaction.dialogue_intro)
        return self.state_payload()

    def _submit_challenge_action(self, challenge: ExplorationChallenge, text: str) -> dict[str, object]:
        client = self._gm_client()
        request_data = build_gm_classifier_request(
            scenario_id=self.exploration.scenario_id,
            scenario_name=self.exploration.scenario_name,
            scenario_context=self.exploration.llm_context,
            state=self.state,
            player_action=text,
            declaration_thread=tuple(self.declaration_thread[-8:]),
            active_preparation_effects=tuple(self.active_preparation_effects),
        )
        analysis = _analyze(client, request_data)
        validate_gm_declaration_analysis(analysis, request_data)
        if analysis.analysis_type == GmDeclarationAnalysisType.PLAYER_QUESTION:
            self._add_message("Odpowiedź MG", analysis.player_message or "To pytanie nie zmienia stanu sceny.")
            return self.state_payload()
        if analysis.analysis_type in {GmDeclarationAnalysisType.NEEDS_CLARIFICATION, GmDeclarationAnalysisType.UNSUPPORTED}:
            self._add_message("Deklaracja wymaga doprecyzowania", analysis.player_message or analysis.reason)
            return self.state_payload()
        if analysis.normalized_intent:
            request_data = replace(request_data, player_action=analysis.normalized_intent)
        proposal = client.classify(request_data)
        validated = validate_gm_classifier_proposal(proposal, request_data)
        if proposal.action_flow == GmActionFlow.PREPARATION:
            effect = proposal.preparation_effect
            if effect is not None:
                self.active_preparation_effects.append(effect)
                self._add_message("Przygotowanie", f"Przygotowanie zapisane: {effect.label}.")
            return self.state_payload()
        option = challenge_option_from_validated_proposal(validated)
        resource = validated.resources[0] if validated.resources else None
        self.pending = PendingInteraction(
            kind=PendingKind.CHALLENGE,
            stage=PendingStage.DECISION,
            proposal=proposal,
            challenge=validated.challenge,
            option=option,
            resources=(resource,) if resource is not None else (),
        )
        self._add_message("Propozycja MG", _challenge_proposal_text(proposal, option, resource))
        return self.state_payload()

    def _submit_npc_action(self, point: ExplorationPoint, text: str) -> dict[str, object]:
        client = self._npc_client()
        zone = next(zone for zone in self.exploration.zones if zone.id == point.zone_id)
        request_data = build_npc_interaction_request(
            scenario_id=self.exploration.scenario_id,
            scenario_name=self.exploration.scenario_name,
            zone=zone,
            point=point,
            state=self.state,
            player_action=text,
        )
        proposal = client.interact_npc(request_data)
        validated = validate_npc_interaction_proposal(proposal, request_data)
        self.pending = PendingInteraction(
            kind=PendingKind.NPC,
            stage=PendingStage.DECISION,
            proposal=validated.proposal,
            point=point,
        )
        if proposal.player_narration:
            self._add_message("Narracja MG", proposal.player_narration)
        if proposal.npc_response:
            self._add_message("Odpowiedź NPC", proposal.npc_response)
        self._add_message("Propozycja interakcji", _npc_proposal_text(proposal))
        return self.state_payload()

    def decide(self, decision: str, *, lead_actor_id: str | None = None) -> dict[str, object]:
        if self.pending is None:
            raise ValueError("Brak propozycji oczekującej na decyzję.")
        normalized = decision.strip().lower()
        if normalized in {"reject", "odrzuc", "odrzuć", "-"}:
            self._add_message("Decyzja", "Odrzucono interpretację. Wpisz deklarację inaczej.")
            self.pending = None
            return self.state_payload()
        if normalized in {"explain", "wyjasnij", "wyjaśnij", "?"}:
            self._add_message("Wyjaśnienie", _pending_explanation(self.pending))
            return self.state_payload()
        if normalized in {"reinterpret", "r"}:
            self._add_message("Reinterpretacja", "Wpisz deklarację ponownie, akcentując korektę interpretacji.")
            self.pending = None
            return self.state_payload()
        if normalized not in {"accept", "akceptuj", "+"}:
            raise ValueError(f"Nieznana decyzja: {decision}.")
        if lead_actor_id and any(str(actor.id) == lead_actor_id for actor in self.exploration.actors):
            self.selected_lead_actor_id = lead_actor_id
        if self.pending.kind == PendingKind.CHALLENGE:
            return self._accept_challenge()
        return self._accept_npc()

    def _accept_challenge(self) -> dict[str, object]:
        assert self.pending is not None and self.pending.option is not None and self.pending.challenge is not None
        option = self.pending.option
        plan = _challenge_check_plan(option, self.lead_actor_id)
        self.pending = replace(self.pending, stage=PendingStage.ROLL, check_plan=plan)
        self._add_message("Rzut", f"Wpisz wyniki rzutów. {_check_plan_text(self.exploration.actors, plan)}")
        return self.state_payload()

    def _accept_npc(self) -> dict[str, object]:
        assert self.pending is not None
        proposal = self.pending.proposal
        assert isinstance(proposal, NpcInteractionProposal)
        if not proposal.requires_roll:
            self._apply_npc_flags(proposal, success=True)
            self._reveal_npc_information(proposal)
            self._add_message("Wynik interakcji NPC", "Interakcja nie wymagała rzutu.")
            self.pending = None
            return self.state_payload()
        plan = _npc_check_plan(proposal, self.lead_actor_id)
        self.pending = replace(self.pending, stage=PendingStage.ROLL, check_plan=plan)
        self._add_message("Rzut", f"Wpisz wyniki rzutów. {_check_plan_text(self.exploration.actors, plan)}")
        return self.state_payload()

    @property
    def lead_actor_id(self) -> str:
        return self.selected_lead_actor_id

    def resolve_rolls(self, raw_rolls: dict[str, object]) -> dict[str, object]:
        if self.pending is None or self.pending.stage != PendingStage.ROLL or self.pending.check_plan is None:
            raise ValueError("Brak oczekującego rzutu.")
        plan = self.pending.check_plan
        inputs = _check_inputs_from_payload(self.exploration.actors, plan, raw_rolls)
        check_result = resolve_exploration_check(plan, inputs)
        if self.pending.kind == PendingKind.CHALLENGE:
            self._resolve_challenge_roll(check_result)
        else:
            self._resolve_npc_roll(check_result)
        self.pending = None
        return self.state_payload()

    def _resolve_challenge_roll(self, check_result) -> None:
        assert self.pending is not None and self.pending.challenge is not None and self.pending.option is not None
        resource = self.pending.resources[0] if self.pending.resources else None
        challenge = self.pending.challenge
        if self.pending.option not in challenge.options:
            challenge = replace(challenge, options=(*challenge.options, self.pending.option))
        result = resolve_challenge_option(
            self.state,
            challenge,
            self.pending.option,
            check_result.selected_roll,
            resource,
        )
        self.state = result.state
        self._add_message("Wynik podejścia", result.message)
        if result.completed:
            self._reveal_completed_challenge_points(self.pending.challenge)

    def _resolve_npc_roll(self, check_result) -> None:
        assert self.pending is not None
        proposal = self.pending.proposal
        assert isinstance(proposal, NpcInteractionProposal)
        success = check_result.success
        message = proposal.success_message if success else proposal.failure_message
        self._add_message("Wynik interakcji NPC", message or ("Sukces." if success else "Porażka."))
        self._apply_npc_flags(proposal, success=success)
        self._reveal_npc_information(proposal)

    def _apply_npc_flags(self, proposal: NpcInteractionProposal, *, success: bool) -> None:
        changes = proposal.flag_changes_on_success if success else proposal.flag_changes_on_failure
        for change in changes:
            self.state = replace(self.state, flags=set_scene_flag(self.state.flags, change.key, change.value))

    def _reveal_npc_information(self, proposal: NpcInteractionProposal) -> None:
        if self.pending is None or self.pending.point is None or self.pending.point.npc_interaction is None:
            return
        npc = self.pending.point.npc_interaction
        known = {info.id: info for info in npc.locked_information}
        for info_id in proposal.revealed_information_ids:
            info = known.get(info_id)
            if info is None:
                continue
            if all(scene_flag(self.state.flags, flag, False) for flag in info.reveal_if_flags):
                for flag in info.sets_flags:
                    self.state = replace(self.state, flags=set_scene_flag(self.state.flags, flag, True))
                self._add_message(f"Informacja: {info.label}", info.text)

    def _reveal_completed_challenge_points(self, challenge: ExplorationChallenge) -> None:
        if not challenge.reveals_on_complete or not challenge_state_for(self.state, challenge.id).completed:
            return
        self.state, revealed = reveal_exploration_points(self.state, challenge.reveals_on_complete)
        for point in revealed:
            self._add_message("Nowy punkt odkryty", f"Odkrywacie nowy punkt w lokacji: {point.name}.")

    def required_rolls_payload(self) -> list[dict[str, object]]:
        if self.pending is None or self.pending.stage != PendingStage.ROLL or self.pending.check_plan is None:
            return []
        return [
            {"actor_id": str(actor.id), "actor_name": actor.name}
            for actor in _actors_for_plan(self.exploration.actors, self.pending.check_plan)
        ]

    def _add_message(self, title: str, body: str) -> None:
        self.messages.append(UiMessage(title, body))

    def _gm_client(self) -> object:
        if self.gm_client is None:
            raise RuntimeError("Brak klienta LLM dla challenge.")
        return self.gm_client

    def _npc_client(self) -> object:
        if self.npc_client is None:
            raise RuntimeError("Brak klienta LLM dla NPC.")
        return self.npc_client


def create_app(session: ExplorationUiSession) -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        return render_template_string(_HTML)

    @app.get("/api/state")
    def api_state():
        return jsonify(session.state_payload())

    @app.post("/api/action")
    def api_action():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.submit_action(str(data.get("text", ""))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/decision")
    def api_decision():
        data = request.get_json(silent=True) or {}
        try:
            lead_actor_id = data.get("lead_actor_id")
            return jsonify(session.decide(str(data.get("decision", "")), lead_actor_id=str(lead_actor_id) if lead_actor_id else None))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/rolls")
    def api_rolls():
        data = request.get_json(silent=True) or {}
        rolls = data.get("rolls", {})
        if not isinstance(rolls, dict):
            return jsonify({"error": "Pole rolls musi być obiektem.", "state": session.state_payload()}), 400
        try:
            return jsonify(session.resolve_rolls(rolls))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/travel")
    def api_travel():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.travel_to(str(data.get("zone_id", ""))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/point")
    def api_point():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.select_point(str(data.get("point_id", ""))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/reset")
    def api_reset():
        session.reset()
        return jsonify(session.state_payload())

    return app


def _analyze(client: object, request_data: object) -> GmDeclarationAnalysis:
    analyze = getattr(client, "analyze", None)
    if callable(analyze):
        return analyze(request_data)
    return GmDeclarationAnalysis(
        analysis_type=GmDeclarationAnalysisType.PLAUSIBLE,
        player_message="",
        normalized_intent=getattr(request_data, "player_action", ""),
        reason="Klient testowy bez analyzer; uznaję deklarację za wiarygodną.",
        confidence=1.0,
    )


def _challenge_check_plan(option: ExplorationChallengeOption, lead_actor_id: str) -> ExplorationCheckPlan:
    return ExplorationCheckPlan(
        participants=option.check_participants or CheckParticipants.SINGLE_ACTOR,
        aggregation=option.check_aggregation or CheckAggregation.LEAD_RESULT,
        consequence_targets=option.consequence_targets or (ConsequenceTarget.LEAD_ACTOR, ConsequenceTarget.SCENE),
        ability=option.ability_check.ability,
        skill=option.ability_check.skill,
        dc=option.ability_check.dc,
        lead_actor_id=lead_actor_id,
        reason_for_players=option.description,
    )


def _npc_check_plan(proposal: NpcInteractionProposal, lead_actor_id: str) -> ExplorationCheckPlan:
    participants = proposal.check_participants or (CheckParticipants.WHOLE_PARTY if proposal.action_type == "search" else CheckParticipants.SINGLE_ACTOR)
    aggregation = proposal.check_aggregation or (CheckAggregation.HIGHEST if participants == CheckParticipants.WHOLE_PARTY else CheckAggregation.LEAD_RESULT)
    consequence_targets = proposal.consequence_targets or (ConsequenceTarget.NPC,)
    return ExplorationCheckPlan(
        participants=participants,
        aggregation=aggregation,
        consequence_targets=tuple(consequence_targets),
        ability=proposal.ability or "wisdom",
        skill=proposal.skill,
        dc=proposal.dc or 10,
        lead_actor_id=lead_actor_id,
        reason_for_players=proposal.player_narration,
    )


def _check_inputs_from_payload(
    actors: tuple[Actor, ...],
    plan: ExplorationCheckPlan,
    raw_rolls: dict[str, object],
) -> tuple[PartyCheckInput, ...]:
    result: list[PartyCheckInput] = []
    for actor in _actors_for_plan(actors, plan):
        actor_id = str(actor.id)
        if actor_id not in raw_rolls:
            raise ValueError(f"Brakuje wyniku rzutu dla: {actor.name}.")
        natural_roll = int(raw_rolls[actor_id])
        request = D20RollRequest(modifiers=_ability_roll_modifiers(actor, plan.ability, plan.skill))
        result.append(PartyCheckInput(actor, natural_roll, request))
    return tuple(result)


def _actors_for_plan(actors: tuple[Actor, ...], plan: ExplorationCheckPlan) -> tuple[Actor, ...]:
    if plan.participants == CheckParticipants.WHOLE_PARTY:
        return actors
    if plan.participants == CheckParticipants.SELECTED_ACTORS:
        selected = tuple(actor for actor in actors if str(actor.id) in set(plan.selected_actor_ids))
        return selected or actors
    lead = next((actor for actor in actors if str(actor.id) == plan.lead_actor_id), actors[0])
    if plan.participants == CheckParticipants.LEAD_WITH_HELP:
        helper = next((actor for actor in actors if str(actor.id) == plan.helper_actor_id), None)
        if helper is not None and helper != lead:
            return (lead, helper)
    return (lead,)


def _ability_roll_modifiers(actor: Actor, ability: str, skill: str | None = None) -> tuple[RollModifier, ...]:
    score = getattr(actor.ability_scores, ability)
    label = f"Modyfikator {ability}"
    if skill:
        label = f"Modyfikator {ability}/{skill}"
    return (RollModifier(label, ability_modifier(score), RollModifierType.ABILITY, stacking_key=f"ability:{ability}"),)


def _challenge_proposal_text(
    proposal: GmClassifierProposal,
    option: ExplorationChallengeOption,
    resource: ExplorationResource | None,
) -> str:
    resource_text = f"\nZasób: {resource.label}" if resource else ""
    return (
        f"{proposal.player_narration}\n"
        f"Podejście: {option.label}. Test: {option.ability_check.ability}/{option.ability_check.skill or '-'}, "
        f"ST {option.ability_check.dc}. Sukces: +{option.progress_on_success} postępu, "
        f"porażka: +{option.progress_on_failure} postępu.{resource_text}"
    ).strip()


def _npc_proposal_text(proposal: NpcInteractionProposal) -> str:
    if proposal.requires_roll:
        skill = f"/{proposal.skill}" if proposal.skill else ""
        return f"Akcja: {proposal.action_type}. Test: {proposal.ability}{skill}, ST {proposal.dc}."
    return f"Akcja: {proposal.action_type}. Bez rzutu."


def _pending_explanation(pending: PendingInteraction) -> str:
    notes = getattr(pending.proposal, "gm_notes", "")
    if notes:
        return str(notes)
    return "Ta propozycja jest interpretacją deklaracji graczy zwalidowaną przez deterministyczny silnik."


def _check_plan_text(actors: tuple[Actor, ...], plan: ExplorationCheckPlan) -> str:
    names = ", ".join(actor.name for actor in _actors_for_plan(actors, plan))
    return (
        f"Uczestnicy: {plan.participants.value} ({names}). "
        f"Agregacja: {plan.aggregation.value}. Konsekwencje: "
        f"{', '.join(target.value for target in plan.consequence_targets)}."
    )


def _zone_payload(zone: ExplorationZone) -> dict[str, object]:
    return {
        "id": zone.id,
        "name": zone.name,
        "description": zone.description,
        "summary": zone.llm_context.summary,
        "available_materials": list(zone.llm_context.available_materials),
    }


def _point_payload(point: ExplorationPoint | None) -> dict[str, object] | None:
    if point is None:
        return None
    payload: dict[str, object] = {
        "id": point.id,
        "name": point.name,
        "zone_id": point.zone_id,
        "description": point.description,
        "has_npc": point.npc_interaction is not None,
    }
    if point.npc_interaction is not None:
        payload["npc"] = {
            "name": point.npc_interaction.name,
            "public_description": point.npc_interaction.public_description,
            "current_state": point.npc_interaction.current_state,
            "dialogue_intro": point.npc_interaction.dialogue_intro,
        }
    return payload


def _challenge_payload(state: ExplorationState, challenge: ExplorationChallenge | None) -> dict[str, object] | None:
    if challenge is None:
        return None
    challenge_state = challenge_state_for(state, challenge.id)
    return {
        "id": challenge.id,
        "name": challenge.name,
        "description": challenge.llm_context.summary,
        "summary": challenge.llm_context.summary,
        "reasonable_approaches": list(challenge.llm_context.reasonable_approaches),
        "risk_notes": list(challenge.llm_context.risk_notes),
        "progress_required": challenge.progress_required,
        "current_progress": challenge_state.current_progress,
        "noise": challenge_state.noise,
        "completed": challenge_state.completed,
        "complications": list(challenge_state.complications),
    }


def _resource_payload(resource: ExplorationResource) -> dict[str, object]:
    return {"id": resource.id, "label": resource.label, "bonus_tags": list(resource.bonus_tags)}


def _challenge_option_payload(option: ExplorationChallengeOption) -> dict[str, object]:
    return {
        "id": option.id,
        "label": option.label,
        "ability": option.ability_check.ability,
        "skill": option.ability_check.skill,
        "dc": option.ability_check.dc,
        "progress_on_success": option.progress_on_success,
        "progress_on_failure": option.progress_on_failure,
        "tags": list(option.tags),
    }


def zone_is_ui_available(state: ExplorationState, zone: ExplorationZone) -> bool:
    return zone.available_if_flag is None or scene_flag(state.flags, zone.available_if_flag, None) == zone.available_if_value


_HTML = """
<!doctype html>
<html lang="pl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Eksploracja</title>
  <style>
    body { margin: 0; font-family: system-ui, sans-serif; background: #101214; color: #ece7dc; }
    main { display: grid; grid-template-columns: 280px 1fr; min-height: 100vh; }
    aside { border-right: 1px solid #34383d; padding: 16px; background: #171a1e; overflow: auto; }
    section { padding: 18px; overflow: auto; }
    h1, h2, h3 { margin: 0 0 10px; }
    .muted { color: #a9a298; font-size: 13px; }
    .card { border: 1px solid #34383d; border-radius: 6px; padding: 12px; margin: 0 0 12px; background: #1d2126; }
    .message { border-left: 3px solid #58a6ff; padding: 10px 12px; margin: 0 0 10px; background: #171b20; }
    .result { border-left: 3px solid #3fb950; padding: 10px 12px; margin: 0 0 10px; background: #132018; }
    .scene-description h3 { margin-top: 0; }
    .scene-description p { margin: 7px 0; line-height: 1.45; }
    .scene-description ul { margin: 6px 0 0 20px; padding: 0; }
    .scene-description li { margin: 3px 0; }
    .hint-panel { margin-top: 10px; padding-top: 10px; border-top: 1px solid #34383d; }
    .hint-panel[hidden] { display: none; }
    .debug-panel { margin-top: 10px; }
    details.debug-panel summary { cursor: pointer; color: #a9a298; }
    .status { border-left: 3px solid #f5c542; padding: 10px 12px; margin: 0 0 12px; background: #211f16; color: #f5e3a1; }
    .status[hidden] { display: none; }
    .row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
    input, textarea, button { font: inherit; }
    textarea { width: 100%; min-height: 80px; box-sizing: border-box; background: #0f1113; color: #ece7dc; border: 1px solid #3a3f45; border-radius: 5px; padding: 10px; }
    input { width: 90px; background: #0f1113; color: #ece7dc; border: 1px solid #3a3f45; border-radius: 5px; padding: 8px; }
    button { background: #2f6feb; color: white; border: 0; border-radius: 5px; padding: 9px 12px; cursor: pointer; }
    button.secondary { background: #3a3f45; }
    button.danger { background: #b42318; }
    pre { white-space: pre-wrap; overflow: auto; }
  </style>
</head>
<body>
<main>
  <aside>
    <h2 id="scenario">Scenariusz</h2>
    <div class="card"><b>Lokacja</b><div id="zone"></div></div>
    <div class="card"><b>Wyzwanie</b><div id="challenge"></div></div>
    <div class="card"><b>Zasoby</b><div id="resources"></div></div>
    <div class="card"><b>Flagi debug</b><pre id="flags"></pre></div>
    <button class="secondary" onclick="resetSession()">Reset</button>
  </aside>
  <section>
    <h1>Eksploracja</h1>
    <div id="status" class="status" hidden></div>
    <div class="card scene-description">
      <h3>Opis sceny</h3>
      <div id="scene-description"></div>
    </div>
    <div class="card" id="result-panel">
      <h3>Wynik</h3>
      <div id="result"></div>
      <button onclick="ackResult()">Dalej</button>
    </div>
    <div class="card" id="travel-panel">
      <h3>Dostępne przejścia</h3>
      <div id="travel-options"></div>
    </div>
    <div class="card" id="points-panel">
      <h3>Odkryte punkty</h3>
      <div id="point-options"></div>
    </div>
    <div class="card" id="pending-panel">
      <h3>Decyzja MG</h3>
      <div id="pending"></div>
      <div id="lead-actor-choice"></div>
      <div class="row" style="margin-top:8px">
        <button onclick="decision('accept')">Akceptuj</button>
        <button class="danger" onclick="decision('reject')">Odrzuć</button>
        <button class="secondary" onclick="decision('explain')">Wyjaśnij</button>
      </div>
    </div>
    <div class="card" id="action-panel">
      <h3 id="action-title">Co robi drużyna?</h3>
      <textarea id="action"></textarea>
      <div class="row" style="margin-top:8px">
        <button onclick="sendAction()">Wyślij</button>
      </div>
    </div>
    <div class="card" id="roll-panel">
      <h3>Rzuty</h3>
      <div id="roll-prompt"></div>
      <div id="rolls"></div>
      <button onclick="sendRolls()">Rozstrzygnij rzuty</button>
    </div>
    <details class="card debug-panel">
      <summary>Historia komunikatów</summary>
      <div id="messages"></div>
    </details>
    <details class="card debug-panel">
      <summary>Debug payload</summary>
      <pre id="debug-payload"></pre>
    </details>
  </section>
</main>
<script>
let state = null;
let busy = false;
let resultAck = null;
function setBusy(message) {
  busy = Boolean(message);
  const status = document.getElementById('status');
  status.hidden = !busy;
  status.textContent = message || '';
  document.querySelectorAll('button, textarea, input').forEach(el => {
    if (el.closest('details.debug-panel')) return;
    el.disabled = busy;
  });
}
async function api(path, body, busyMessage) {
  setBusy(busyMessage || 'Czekam na odpowiedź...');
  try {
    const res = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body || {})});
    const data = await res.json();
    if (!res.ok) alert(data.error || 'Błąd');
    state = data.state || data;
    if (path === '/api/rolls' && res.ok) {
      resultAck = latestResultMessage(state);
    } else if (path !== '/api/decision') {
      resultAck = null;
    }
    render();
  } finally {
    setBusy('');
  }
}
async function loadState() {
  const res = await fetch('/api/state');
  state = await res.json();
  render();
}
function render() {
  document.getElementById('scenario').textContent = state.scenario.name;
  document.getElementById('zone').textContent = state.current_zone.name;
  document.getElementById('challenge').textContent = state.active_challenge ? `${state.active_challenge.name}: ${state.active_challenge.current_progress}/${state.active_challenge.progress_required}, hałas ${state.active_challenge.noise}` : 'Brak';
  document.getElementById('resources').innerHTML = state.resources.map(r => `<div>${r.label}</div>`).join('') || 'Brak';
  document.getElementById('flags').textContent = JSON.stringify(state.flags, null, 2);
  document.getElementById('scene-description').innerHTML = sceneDescriptionHtml(state);
  document.getElementById('messages').innerHTML = state.messages.map(m => `<div class="message"><b>${m.title}</b><br>${m.body}</div>`).join('');
  document.getElementById('pending').innerHTML = pendingHtml(state.pending);
  document.getElementById('lead-actor-choice').innerHTML = leadActorChoiceHtml();
  document.getElementById('result').innerHTML = resultAck ? `<div class="result"><b>${esc(resultAck.title)}</b><br>${esc(resultAck.body)}</div>` : '';
  document.getElementById('travel-options').innerHTML = travelOptionsHtml();
  document.getElementById('point-options').innerHTML = pointOptionsHtml();
  document.getElementById('roll-prompt').innerHTML = rollPromptHtml();
  document.getElementById('rolls').innerHTML = state.required_rolls.map(r => `<label>${r.actor_name}: <input data-actor="${r.actor_id}" type="number" min="1" max="20" value="10"></label>`).join(' ');
  document.getElementById('debug-payload').textContent = JSON.stringify(state, null, 2);
  document.getElementById('action-title').textContent = state.active_point && state.active_point.has_npc ? 'Co robicie wobec NPC?' : 'Co robi drużyna?';
  updateActivePanel();
}
function esc(value) {
  return String(value || '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
}
function listHtml(items) {
  if (!items || !items.length) return '';
  return `<ul>${items.map(item => `<li>${esc(item)}</li>`).join('')}</ul>`;
}
function sceneDescriptionHtml(state) {
  const zone = state.current_zone || {};
  const challenge = state.active_challenge;
  const parts = [
    `<p><b>${esc(zone.name)}</b></p>`,
    zone.description ? `<p>${esc(zone.description)}</p>` : '',
    zone.summary ? `<p>${esc(zone.summary)}</p>` : '',
  ];
  if (zone.available_materials && zone.available_materials.length) {
    parts.push(`<p><b>Widoczne elementy otoczenia:</b></p>${listHtml(zone.available_materials)}`);
  }
  if (challenge) {
    parts.push(`<p><b>${esc(challenge.name)}</b></p>`);
    if (challenge.summary) parts.push(`<p>${esc(challenge.summary)}</p>`);
    parts.push(`<p><b>Postęp:</b> ${challenge.current_progress}/${challenge.progress_required}. <b>Hałas:</b> ${challenge.noise}.</p>`);
    if (challenge.complications && challenge.complications.length) {
      parts.push(`<p><b>Komplikacje:</b> ${challenge.complications.map(esc).join(', ')}</p>`);
    }
    const hasHints = (challenge.reasonable_approaches && challenge.reasonable_approaches.length)
      || (challenge.risk_notes && challenge.risk_notes.length);
    if (hasHints) {
      const hints = [];
      if (challenge.reasonable_approaches && challenge.reasonable_approaches.length) {
        hints.push(`<p><b>Sensowne podejścia:</b></p>${listHtml(challenge.reasonable_approaches)}`);
      }
      if (challenge.risk_notes && challenge.risk_notes.length) {
        hints.push(`<p><b>Ryzyka:</b></p>${listHtml(challenge.risk_notes)}`);
      }
      parts.push(`
        <button class="secondary" type="button" onclick="toggleHints()">Pokaż wskazówki MG</button>
        <div id="gm-hints" class="hint-panel" hidden>${hints.join('')}</div>
      `);
    }
  }
  if (state.active_point) {
    const point = state.active_point;
    parts.push(`<p><b>${esc(point.name)}</b></p>`);
    parts.push(point.description ? `<p>${esc(point.description)}</p>` : '');
    if (point.npc) {
      parts.push(`<p>${esc(point.npc.public_description)}</p>`);
      if (point.npc.current_state) parts.push(`<p><b>Stan NPC:</b> ${esc(point.npc.current_state)}</p>`);
    }
  }
  if (!challenge && state.travel_options && state.travel_options.length) {
    parts.push(`<p><b>Droga dalej jest otwarta.</b> Wybierz jedną z dostępnych lokacji poniżej.</p>`);
  }
  return parts.filter(Boolean).join('');
}
function toggleHints() {
  const panel = document.getElementById('gm-hints');
  if (!panel) return;
  panel.hidden = !panel.hidden;
  const button = panel.previousElementSibling;
  if (button) button.textContent = panel.hidden ? 'Pokaż wskazówki MG' : 'Ukryj wskazówki MG';
}
function pendingHtml(pending) {
  if (!pending) return '';
  const proposal = pending.proposal || {};
  const option = pending.option || {};
  const lines = [];
  if (proposal.player_narration) lines.push(`<p>${esc(proposal.player_narration)}</p>`);
  if (proposal.npc_response) lines.push(`<p><b>NPC:</b> ${esc(proposal.npc_response)}</p>`);
  if (option.label) {
    const skill = option.skill ? `/${esc(option.skill)}` : '';
    lines.push(`<p><b>Podejście:</b> ${esc(option.label)}. Test: ${esc(option.ability)}${skill}, ST ${esc(option.dc)}.</p>`);
    lines.push(`<p><b>Postęp:</b> sukces +${esc(option.progress_on_success)}, porażka +${esc(option.progress_on_failure)}.</p>`);
  } else if (proposal.action_type) {
    if (proposal.requires_roll) {
      const skill = proposal.skill ? `/${esc(proposal.skill)}` : '';
      lines.push(`<p><b>Akcja:</b> ${esc(proposal.action_type)}. Test: ${esc(proposal.ability)}${skill}, ST ${esc(proposal.dc)}.</p>`);
    } else {
      lines.push(`<p><b>Akcja:</b> ${esc(proposal.action_type)}. Bez rzutu.</p>`);
    }
  }
  return lines.join('') || '<p>MG proponuje interpretację deklaracji.</p>';
}
function leadActorChoiceHtml() {
  if (!state.pending || state.pending.stage !== 'decision' || !state.actors || state.actors.length < 2) return '';
  const options = state.actors.map(actor => `<option value="${esc(actor.id)}">${esc(actor.name)}</option>`).join('');
  return `<label><b>Kto prowadzi test?</b> <select id="lead-actor">${options}</select></label>`;
}
function rollPromptHtml() {
  if (!state.pending || state.pending.stage !== 'roll') return '';
  const plan = state.pending.check_plan || {};
  const participants = {
    single_actor: 'rzuca jeden wybrany bohater',
    lead_with_help: 'rzuca prowadzący z pomocą',
    whole_party: 'rzuca cała drużyna',
    selected_actors: 'rzucają wybrani bohaterowie'
  }[plan.participants] || plan.participants || 'rzut eksploracyjny';
  const aggregation = {
    lead_result: 'liczy się wynik prowadzącego',
    highest: 'liczy się najwyższy wynik',
    lowest: 'liczy się najniższy wynik',
    majority_success: 'sukces, jeśli zda co najmniej połowa'
  }[plan.aggregation] || plan.aggregation || '';
  const names = (state.required_rolls || []).map(r => r.actor_name).join(', ');
  return `<p><b>Format rzutu:</b> ${esc(participants)}${aggregation ? `, ${esc(aggregation)}` : ''}.</p><p><b>Rzucają:</b> ${esc(names || '-')}</p>`;
}
function latestResultMessage(state) {
  const messages = state.messages || [];
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    if (messages[i].title && messages[i].title.startsWith('Wynik')) return messages[i];
  }
  return messages[messages.length - 1] || null;
}
function travelOptionsHtml() {
  const zones = state.travel_options || [];
  if (!zones.length) return '<p>Brak dostępnych przejść z tej lokacji.</p>';
  return zones.map(zone => `
    <div class="row" style="justify-content:space-between; margin: 6px 0">
      <div><b>${esc(zone.name)}</b><br><span class="muted">${esc(zone.description)}</span></div>
      <button onclick="travel('${esc(zone.id)}')">Przejdź</button>
    </div>
  `).join('');
}
function pointOptionsHtml() {
  const points = state.current_zone_points || [];
  if (!points.length) return '<p>Brak odkrytych punktów w tej lokacji.</p>';
  const rows = points.map(point => {
    const active = state.active_point && state.active_point.id === point.id;
    const label = point.has_npc ? 'Wejdź w interakcję' : 'Sprawdź';
    return `
      <div class="row" style="justify-content:space-between; margin: 6px 0">
        <div><b>${esc(point.name)}</b>${active ? ' <span class="muted">(aktywny)</span>' : ''}<br><span class="muted">${esc(point.description)}</span></div>
        <button onclick="selectPoint('${esc(point.id)}')">${label}</button>
      </div>
    `;
  });
  if (state.active_point) {
    rows.push('<button class="secondary" onclick="selectPoint(&quot;&quot;)">Wróć do lokacji</button>');
  }
  return rows.join('');
}
function updateActivePanel() {
  const hasPendingDecision = state.pending && state.pending.stage === 'decision';
  const hasRolls = state.required_rolls && state.required_rolls.length > 0;
  const hasResult = Boolean(resultAck);
  const hasTravel = !state.active_challenge && !state.active_point && !hasResult && !hasPendingDecision && !hasRolls && state.travel_options && state.travel_options.length > 0;
  const hasPoints = !hasResult && !hasPendingDecision && !hasRolls && state.current_zone_points && state.current_zone_points.length > 0;
  document.getElementById('result-panel').hidden = !hasResult;
  document.getElementById('travel-panel').hidden = !hasTravel;
  document.getElementById('points-panel').hidden = !hasPoints;
  document.getElementById('pending-panel').hidden = !hasPendingDecision;
  document.getElementById('roll-panel').hidden = !hasRolls;
  document.getElementById('action-panel').hidden = hasResult || hasTravel || hasPendingDecision || hasRolls;
}
function sendAction() { api('/api/action', {text: document.getElementById('action').value}, 'Czekam na decyzję MG...'); }
function decision(value) {
  const labels = {
    accept: 'Przyjmuję decyzję MG...',
    reject: 'Odrzucam decyzję MG...',
    explain: 'Proszę MG o wyjaśnienie...'
  };
  const leadActor = document.getElementById('lead-actor');
  api('/api/decision', {decision:value, lead_actor_id: leadActor ? leadActor.value : null}, labels[value] || 'Czekam na MG...');
}
function sendRolls() {
  const rolls = {};
  document.querySelectorAll('#rolls input').forEach(input => rolls[input.dataset.actor] = Number(input.value));
  api('/api/rolls', {rolls}, 'Rozstrzygam wynik rzutu...');
}
function resetSession() { api('/api/reset', {}, 'Resetuję scenę...'); }
function travel(zoneId) { api('/api/travel', {zone_id: zoneId}, 'Przechodzę do wybranej lokacji...'); }
function selectPoint(pointId) { api('/api/point', {point_id: pointId}, pointId ? 'Otwieram punkt eksploracji...' : 'Wracam do lokacji...'); }
function ackResult() {
  resultAck = null;
  render();
}
loadState();
</script>
</body>
</html>
"""
