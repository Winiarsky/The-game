from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Protocol

import requests
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from dnd_board_game.exploration import (
    CheckAggregation,
    CheckParticipants,
    ConsequenceTarget,
    ExplorationPoint,
    ExplorationState,
    ExplorationZone,
    NpcAttemptPlan,
    NpcIntentActionPlan,
    SOCIAL_CHECK_SKILLS,
    SocialInteractionPlan,
    SocialRequestRisk,
    npc_runtime_state_for,
    interaction_goal,
    effective_narrative_style,
    plan_npc_attempt,
    plan_npc_intent_action,
    plan_social_interaction,
    validate_policy_exploration_effect,
)
from dnd_board_game.combat import scene_flag

from .gm_classifier import (
    CORE_DND_5E_ABILITIES,
    CORE_DND_5E_SKILLS,
    GmDeclarationThreadEntry,
    GmProposalValidationError,
    _retry_delay,
)
from .prompts import PromptId, load_prompt


class NpcFlagChange(BaseModel):
    model_config = ConfigDict(extra="ignore")

    key: str = Field(max_length=120)
    value: bool | int | str = True


class NpcEffect(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: str = Field(max_length=80)
    parameters: dict[str, Any] = Field(default_factory=dict)

    @field_validator("type")
    @classmethod
    def _normalize_type(cls, value: str) -> str:
        return value.strip().lower()

    def as_effect_payload(self) -> dict[str, object]:
        return {"type": self.type, "parameters": dict(self.parameters)}


class NpcInteractionProposal(BaseModel):
    model_config = ConfigDict(extra="ignore")

    action_type: str = Field(max_length=80)
    request_risk: SocialRequestRisk | None = None
    target_id: str | None = Field(default=None, max_length=120)
    quantity: int = Field(default=1, ge=1)
    grounded_response_variant_id: str | None = Field(default=None, max_length=120)
    player_narration: str = Field(default="", max_length=1000)
    npc_response: str = Field(default="", max_length=1000)
    requires_roll: bool = False
    ability: str | None = None
    skill: str | None = None
    dc: int | None = Field(default=None, ge=5, le=25)
    check_participants: CheckParticipants | None = None
    check_aggregation: CheckAggregation | None = None
    consequence_targets: tuple[ConsequenceTarget, ...] = ()
    success_message: str = Field(default="", max_length=1000)
    failure_message: str = Field(default="", max_length=1000)
    flag_changes_on_success: tuple[NpcFlagChange, ...] = ()
    flag_changes_on_failure: tuple[NpcFlagChange, ...] = ()
    effects_on_success: tuple[NpcEffect, ...] = ()
    effects_on_failure: tuple[NpcEffect, ...] = ()
    revealed_information_ids: tuple[str, ...] = ()
    gm_notes: str = Field(default="", max_length=1000)

    @field_validator(
        "action_type",
        "ability",
        "skill",
        "target_id",
        "grounded_response_variant_id",
    )
    @classmethod
    def _lower_optional(cls, value: str | None) -> str | None:
        return value.strip().lower() if value else value

    @field_validator("player_narration", "npc_response", "success_message", "failure_message", "gm_notes", mode="before")
    @classmethod
    def _none_to_empty_text(cls, value: object) -> object:
        return "" if value is None else value

    @field_validator("revealed_information_ids")
    @classmethod
    def _unique_information_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.strip() for item in value if item.strip()))


@dataclass(frozen=True, slots=True)
class NpcInteractionRequest:
    scenario_id: str
    scenario_name: str
    zone: ExplorationZone
    point: ExplorationPoint
    state: ExplorationState
    player_action: str
    conversation_thread: tuple[GmDeclarationThreadEntry, ...] = ()
    selected_goal_id: str | None = None
    routed_intent_id: str | None = None
    selected_social_skill: str | None = None
    conversation_only: bool = False

    def __post_init__(self) -> None:
        if (
            self.selected_social_skill is not None
            and self.selected_social_skill not in SOCIAL_CHECK_SKILLS
        ):
            raise ValueError(
                "Selected social skill must be persuasion, deception, or intimidation."
            )

    def to_prompt_payload(self) -> dict[str, Any]:
        npc = self.point.npc_interaction
        if npc is None:
            raise ValueError(f"Exploration point {self.point.id} has no npc_interaction.")
        runtime_state = npc_runtime_state_for(self.state, npc.id)
        selected_goal = interaction_goal(
            npc.goals,
            self.selected_goal_id,
            self.state.flags,
        )
        narrative_style = effective_narrative_style(
            npc.narrative_style,
            selected_goal,
        )
        npc_payload = npc.as_payload()
        if selected_goal is not None:
            npc_payload["goals"] = [selected_goal.as_payload()]
        if self.routed_intent_id is not None:
            # Guarded routes never need the scenario author's private truth or
            # hidden key-issue definitions. Deterministic code has already
            # matched key issues before the LLM is called.
            npc_payload["gm_context"] = ""
            npc_payload["current_state"] = ""
            npc_payload["key_issues"] = []
            permission = npc.policy.intent_permission(self.routed_intent_id)
            permission_payload = (
                permission.as_payload()
                if permission is not None
                else None
            )
            if permission_payload is not None:
                unlocked_reveal_ids = {
                    item.id
                    for item in npc.locked_information
                    if all(
                        scene_flag(self.state.flags, flag, False)
                        for flag in item.reveal_if_flags
                    )
                }
                permission_payload["reveals"] = [
                    info_id
                    for info_id in permission.reveals
                    if info_id in unlocked_reveal_ids
                ]
            npc_payload["policy"]["intent_permissions"] = (
                {
                    self.routed_intent_id: permission_payload,
                }
                if permission_payload is not None
                else {}
            )
            npc_payload["policy"]["allowed_flags"] = []
            npc_payload["policy"]["allowed_effect_types"] = []
            if permission is not None:
                reveal_ids = set(permission.reveals)
                npc_payload["locked_information"] = [
                    item
                    for item in npc_payload["locked_information"]
                    if item.get("id") in reveal_ids
                    and all(
                        scene_flag(self.state.flags, flag, False)
                        for flag in item.get("reveal_if_flags", ())
                    )
                ]
        grounded_response = (
            selected_goal.grounded_response
            if selected_goal is not None
            else None
        )
        return {
            "scenario": {"id": self.scenario_id, "name": self.scenario_name},
            "zone": {
                "id": self.zone.id,
                "name": self.zone.name,
                "description": self.zone.description,
            },
            "point": {
                "id": self.point.id,
                "name": self.point.name,
                "description": self.point.description,
            },
            "npc": npc_payload,
            "npc_runtime_state": (
                runtime_state.as_payload() if runtime_state is not None else None
            ),
            "scene_flags": dict(self.state.flags.values),
            "conversation_thread": [entry.as_payload() for entry in self.conversation_thread],
            "selected_goal": selected_goal.as_payload() if selected_goal is not None else None,
            "routed_intent_id": self.routed_intent_id,
            "selected_social_skill": self.selected_social_skill,
            "conversation_only": self.conversation_only,
            "effective_narrative_style": narrative_style.as_payload(),
            "grounding_contract": {
                "mode": (
                    "authored_variants"
                    if grounded_response is not None and grounded_response.variants
                    else "authored_response"
                    if grounded_response is not None
                    else "cosmetic_generation"
                ),
                "authored_response": (
                    grounded_response.as_prompt_payload()
                    if grounded_response is not None
                    else None
                ),
                "authorized_facts": [
                    fact
                    for fact in (
                        self.zone.description,
                        self.point.description,
                        npc.public_description,
                        (
                            npc.gm_context
                            if self.routed_intent_id is None
                            else ""
                        ),
                        (
                            npc.current_state
                            if self.routed_intent_id is None
                            else ""
                        ),
                        selected_goal.description
                        if selected_goal is not None
                        else "",
                    )
                    if fact.strip()
                ],
                "forbidden_claims_without_authored_effect": [
                    "new quest evidence or unseen events",
                    "a reward, price, debt, or payment",
                    "buying, selling, spending, receiving, or transferring currency",
                    "receiving or transferring an item",
                    "a promise that changes the NPC or world state",
                ],
            },
            "player_action": self.player_action,
        }


@dataclass(frozen=True, slots=True)
class NpcValidatedInteraction:
    proposal: NpcInteractionProposal
    point: ExplorationPoint
    social_plan: SocialInteractionPlan | None = None
    attempt_plan: NpcAttemptPlan | None = None
    action_plan: NpcIntentActionPlan | None = None


class NpcInteractionClient(Protocol):
    model: str

    def interact_npc(self, request: NpcInteractionRequest) -> NpcInteractionProposal:
        ...


class GroqNpcInteractionClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout_s: float = 30.0,
        max_retries: int = 3,
        retry_backoff_s: float = 1.0,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.environ.get("GROQ_API_KEY", "")
        self.model = model or os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
        self.timeout_s = timeout_s
        self.max_retries = max(0, max_retries)
        self.retry_backoff_s = max(0.0, retry_backoff_s)

    def interact_npc(self, request: NpcInteractionRequest) -> NpcInteractionProposal:
        if not self.api_key:
            raise RuntimeError("Missing GROQ_API_KEY. Ustaw klucz w .env i uruchom `source .env`.")
        payload = {
            "model": self.model,
            "temperature": 0.25,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": load_prompt(PromptId.GM_NPC_INTERACTION)},
                {"role": "user", "content": json.dumps(request.to_prompt_payload(), ensure_ascii=False)},
            ],
        }
        response = None
        for attempt in range(self.max_retries + 1):
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=self.timeout_s,
            )
            if response.status_code not in {429, 500, 502, 503, 504} or attempt >= self.max_retries:
                break
            time.sleep(_retry_delay(response, attempt, self.retry_backoff_s))
        assert response is not None
        response.raise_for_status()
        try:
            return NpcInteractionProposal.model_validate_json(str(response.json()["choices"][0]["message"]["content"]))
        except (KeyError, IndexError, TypeError, ValidationError) as exc:
            raise GmProposalValidationError(f"LLM returned invalid NPC interaction proposal: {exc}") from exc


class GeminiNpcInteractionClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout_s: float = 30.0,
        max_retries: int = 3,
        retry_backoff_s: float = 1.0,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY", "")
        self.model = model or os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
        self.timeout_s = timeout_s
        self.max_retries = max(0, max_retries)
        self.retry_backoff_s = max(0.0, retry_backoff_s)

    def interact_npc(self, request: NpcInteractionRequest) -> NpcInteractionProposal:
        if not self.api_key:
            raise RuntimeError("Missing GEMINI_API_KEY. Ustaw klucz w .env i uruchom `source .env`.")
        payload = {
            "system_instruction": {"parts": [{"text": load_prompt(PromptId.GM_NPC_INTERACTION)}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": json.dumps(request.to_prompt_payload(), ensure_ascii=False)}],
                }
            ],
            "generation_config": {"temperature": 0.25, "response_mime_type": "application/json"},
        }
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        response = None
        for attempt in range(self.max_retries + 1):
            response = requests.post(
                url,
                headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key},
                json=payload,
                timeout=self.timeout_s,
            )
            if response.status_code not in {429, 500, 502, 503, 504} or attempt >= self.max_retries:
                break
            time.sleep(_retry_delay(response, attempt, self.retry_backoff_s))
        assert response is not None
        response.raise_for_status()
        try:
            content = str(response.json()["candidates"][0]["content"]["parts"][0]["text"])
            return NpcInteractionProposal.model_validate_json(content)
        except (KeyError, IndexError, TypeError, ValidationError) as exc:
            raise GmProposalValidationError(f"Gemini returned invalid NPC interaction proposal: {exc}") from exc


def build_npc_interaction_request(
    *,
    scenario_id: str,
    scenario_name: str,
    zone: ExplorationZone,
    point: ExplorationPoint,
    state: ExplorationState,
    player_action: str,
    conversation_thread: tuple[GmDeclarationThreadEntry, ...] = (),
    selected_goal_id: str | None = None,
    routed_intent_id: str | None = None,
    selected_social_skill: str | None = None,
    conversation_only: bool = False,
) -> NpcInteractionRequest:
    return NpcInteractionRequest(
        scenario_id=scenario_id,
        scenario_name=scenario_name,
        zone=zone,
        point=point,
        state=state,
        player_action=player_action,
        conversation_thread=conversation_thread,
        selected_goal_id=selected_goal_id,
        routed_intent_id=routed_intent_id,
        selected_social_skill=(
            selected_social_skill.strip().lower()
            if selected_social_skill is not None
            else None
        ),
        conversation_only=conversation_only,
    )


def validate_npc_interaction_proposal(
    proposal: NpcInteractionProposal,
    request: NpcInteractionRequest,
) -> NpcValidatedInteraction:
    npc = request.point.npc_interaction
    if npc is None:
        raise ValueError(f"Exploration point {request.point.id} has no npc_interaction.")
    policy = npc.policy
    selected_goal = interaction_goal(
        npc.goals,
        request.selected_goal_id,
        request.state.flags,
    )
    if request.selected_goal_id is not None and selected_goal is None:
        raise ValueError(
            f"Selected NPC interaction goal is unavailable: {request.selected_goal_id}."
        )
    if (
        request.routed_intent_id is not None
        and proposal.action_type != request.routed_intent_id
    ):
        raise ValueError(
            f"NPC intent {proposal.action_type} does not match authored route "
            f"{request.routed_intent_id}."
        )
    if (
        selected_goal is not None
        and not selected_goal.custom
        and selected_goal.intent_ids
        and proposal.action_type not in selected_goal.intent_ids
    ):
        raise ValueError(
            f"NPC intent {proposal.action_type} does not match selected goal {selected_goal.id}."
        )
    success_flags = {
        *{change.key for change in proposal.flag_changes_on_success if change.value is True},
        *_true_set_flag_keys(proposal.effects_on_success),
    }
    permission = policy.intent_permission(proposal.action_type)
    if policy.intent_permissions:
        if permission is None:
            raise ValueError(f"NPC intent is not allowed here: {proposal.action_type}.")
        if permission.status == "blocked":
            raise ValueError(f"NPC intent is blocked here: {proposal.action_type}.")
        if permission.status == "locked":
            missing_flags = [
                flag
                for flag in permission.unlock_if_flags
                if not scene_flag(request.state.flags, flag, False) and flag not in success_flags
            ]
            if missing_flags:
                raise ValueError(
                    f"NPC intent {proposal.action_type} is locked by flags: {', '.join(missing_flags)}."
                )
    elif policy.allowed_actions and proposal.action_type not in policy.allowed_actions:
        raise ValueError(f"NPC action is not allowed here: {proposal.action_type}.")
    social_plan = None
    if (
        request.selected_social_skill is not None
        and (permission is None or not permission.uses_social_reaction)
    ):
        raise ValueError(
            "A player-selected social skill can only be used by a social reaction route."
        )
    if permission is not None and permission.uses_social_reaction:
        if proposal.request_risk is None:
            raise ValueError(
                f"NPC intent {proposal.action_type} requires request_risk classification."
            )
        if (
            request.selected_social_skill is not None
            and policy.allowed_skills
            and request.selected_social_skill not in policy.allowed_skills
        ):
            raise ValueError(
                f"NPC social skill is not allowed here: "
                f"{request.selected_social_skill}."
            )
        runtime_state = npc_runtime_state_for(request.state, npc.id)
        attitude = runtime_state.attitude if runtime_state is not None else npc.initial_attitude
        social_plan = plan_social_interaction(attitude, proposal.request_risk)
        if social_plan.requires_roll:
            social_skill = (
                request.selected_social_skill
                or proposal.skill
                or "persuasion"
            )
            if social_skill not in SOCIAL_CHECK_SKILLS:
                raise ValueError(
                    "A social reaction check must use persuasion, deception, or intimidation."
                )
            proposal = proposal.model_copy(
                update={
                    "requires_roll": True,
                    "ability": "charisma",
                    "skill": social_skill,
                    "dc": social_plan.dc,
                }
            )
        else:
            proposal = proposal.model_copy(
                update={"requires_roll": False, "ability": None, "skill": None, "dc": None}
            )
    action_plan = None
    if permission is not None and permission.targets:
        if proposal.target_id is None:
            raise ValueError(
                f"NPC intent {proposal.action_type} requires target_id classification."
            )
        action_plan = plan_npc_intent_action(
            request.state,
            permission=permission,
            target_id=proposal.target_id,
            quantity=proposal.quantity,
        )
        target = action_plan.target
        if target.ability is not None and not permission.uses_social_reaction:
            proposal = proposal.model_copy(
                update={
                    "requires_roll": True,
                    "ability": target.ability,
                    "skill": target.skill,
                    "dc": target.dc,
                }
            )
        if any(
            (
                proposal.effects_on_success,
                proposal.effects_on_failure,
                proposal.flag_changes_on_success,
                proposal.flag_changes_on_failure,
                proposal.revealed_information_ids,
            )
        ):
            raise ValueError(
                "NPC interaction with a structured target cannot define LLM-owned outcomes."
            )
        _validate_npc_action_plan(action_plan, request)
    if proposal.requires_roll:
        if proposal.ability is None or proposal.ability not in CORE_DND_5E_ABILITIES:
            raise ValueError(f"NPC interaction uses unknown ability: {proposal.ability}.")
        if policy.allowed_abilities and proposal.ability not in policy.allowed_abilities:
            raise ValueError(f"NPC ability is not allowed here: {proposal.ability}.")
        if proposal.skill is not None and proposal.skill not in CORE_DND_5E_SKILLS:
            raise ValueError(f"NPC interaction uses unknown skill: {proposal.skill}.")
        if proposal.skill is not None and policy.allowed_skills and proposal.skill not in policy.allowed_skills:
            raise ValueError(f"NPC skill is not allowed here: {proposal.skill}.")
        if proposal.dc is None or proposal.dc < policy.dc_min or proposal.dc > policy.dc_max:
            raise ValueError(f"NPC interaction DC must be in range {policy.dc_min}..{policy.dc_max}.")
    else:
        if proposal.dc is not None:
            raise ValueError("NPC interaction without roll cannot define DC.")
    attempt_plan = None
    if (
        permission is not None
        and permission.attempt_policy is not None
        and proposal.requires_roll
    ):
        attempt_plan = plan_npc_attempt(
            request.state,
            npc_id=npc.id,
            policy=permission.attempt_policy,
        )
    allowed_flags = set(policy.allowed_flags)
    for change in (*proposal.flag_changes_on_success, *proposal.flag_changes_on_failure):
        if allowed_flags and change.key not in allowed_flags:
            raise ValueError(f"NPC flag is not allowed here: {change.key}.")
    _validate_npc_effects(proposal.effects_on_success, request, "effects_on_success")
    _validate_npc_effects(proposal.effects_on_failure, request, "effects_on_failure")
    known_info = {info.id: info for info in npc.locked_information}
    for info_id in proposal.revealed_information_ids:
        if info_id not in known_info:
            raise ValueError(f"NPC tried to reveal unknown information: {info_id}.")
        missing_flags = [flag for flag in known_info[info_id].reveal_if_flags if not scene_flag(request.state.flags, flag, False)]
        missing_after_success = [flag for flag in missing_flags if flag not in success_flags]
        if missing_after_success:
            raise ValueError(
                f"NPC information {info_id} is still locked by flags: {', '.join(missing_after_success)}."
            )
    if (
        proposal.revealed_information_ids
        and (selected_goal is None or selected_goal.grounded_response is None)
    ):
        authorized_information = tuple(
            known_info[info_id]
            for info_id in proposal.revealed_information_ids
        )
        proposal = proposal.model_copy(
            update={
                "player_narration": (
                    f"{npc.name} zbiera myśli i odpowiada tylko o tym, "
                    "co zdołał zapamiętać."
                ),
                "npc_response": " ".join(
                    information.text for information in authorized_information
                ),
                "success_message": "NPC przekazuje dostępne informacje.",
                "failure_message": (
                    "NPC nie jest jeszcze gotowy, by powiedzieć coś więcej."
                ),
            }
        )
    if selected_goal is not None and selected_goal.grounded_response is not None:
        grounded = selected_goal.grounded_response
        selected_variant = grounded.variant(proposal.grounded_response_variant_id)
        authored = selected_variant or grounded
        proposal = proposal.model_copy(
            update={
                "grounded_response_variant_id": (
                    selected_variant.id if selected_variant is not None else None
                ),
                "player_narration": authored.player_narration,
                "npc_response": authored.npc_response,
                "success_message": authored.success_message,
                "failure_message": authored.failure_message,
            }
        )
    return NpcValidatedInteraction(
        proposal=proposal,
        point=request.point,
        social_plan=social_plan,
        attempt_plan=attempt_plan,
        action_plan=action_plan,
    )


def _validate_npc_effects(
    effects: tuple[NpcEffect, ...],
    request: NpcInteractionRequest,
    field: str,
) -> None:
    npc = request.point.npc_interaction
    if npc is None:
        raise ValueError(f"Exploration point {request.point.id} has no npc_interaction.")
    for index, effect in enumerate(effects):
        payload = effect.as_effect_payload()
        validate_policy_exploration_effect(
            payload,
            request.state,
            allowed_effect_types=npc.policy.allowed_effect_types,
            allowed_flags=npc.policy.allowed_flags,
            field=f"NPC {field}[{index}]",
        )


def _validate_npc_action_plan(
    plan: NpcIntentActionPlan,
    request: NpcInteractionRequest,
) -> None:
    npc = request.point.npc_interaction
    if npc is None:
        raise ValueError(f"Exploration point {request.point.id} has no npc_interaction.")
    known_information_ids = {item.id for item in npc.locked_information}
    for branch in plan.target.outcome_branches:
        unknown_information = set(branch.revealed_information_ids) - known_information_ids
        if unknown_information:
            raise ValueError(
                f"NPC target {plan.target.id} reveals unknown information: "
                + ", ".join(sorted(unknown_information))
                + "."
            )
        for index, effect in enumerate(branch.effects):
            validate_policy_exploration_effect(
                effect,
                request.state,
                allowed_effect_types=npc.policy.allowed_effect_types,
                allowed_flags=npc.policy.allowed_flags,
                field=(
                    f"NPC target {plan.target.id}.outcomes."
                    f"{branch.outcome.value}.effects[{index}]"
                ),
            )


def _true_set_flag_keys(effects: tuple[NpcEffect, ...]) -> set[str]:
    result: set[str] = set()
    for effect in effects:
        if effect.type == "set_flag" and effect.parameters.get("value") is True:
            key = str(effect.parameters.get("key", "")).strip()
            if key:
                result.add(key)
    return result
