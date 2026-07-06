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
    validate_exploration_effect,
)
from dnd_board_game.combat import scene_flag

from .gm_classifier import CORE_DND_5E_ABILITIES, CORE_DND_5E_SKILLS, GmProposalValidationError, _retry_delay
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

    @field_validator("action_type", "ability", "skill")
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

    def to_prompt_payload(self) -> dict[str, Any]:
        npc = self.point.npc_interaction
        if npc is None:
            raise ValueError(f"Exploration point {self.point.id} has no npc_interaction.")
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
            "npc": npc.as_payload(),
            "scene_flags": dict(self.state.flags.values),
            "player_action": self.player_action,
        }


@dataclass(frozen=True, slots=True)
class NpcValidatedInteraction:
    proposal: NpcInteractionProposal
    point: ExplorationPoint


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
) -> NpcInteractionRequest:
    return NpcInteractionRequest(
        scenario_id=scenario_id,
        scenario_name=scenario_name,
        zone=zone,
        point=point,
        state=state,
        player_action=player_action,
    )


def validate_npc_interaction_proposal(
    proposal: NpcInteractionProposal,
    request: NpcInteractionRequest,
) -> NpcValidatedInteraction:
    npc = request.point.npc_interaction
    if npc is None:
        raise ValueError(f"Exploration point {request.point.id} has no npc_interaction.")
    policy = npc.policy
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
    return NpcValidatedInteraction(proposal=proposal, point=request.point)


def _validate_npc_effects(
    effects: tuple[NpcEffect, ...],
    request: NpcInteractionRequest,
    field: str,
) -> None:
    npc = request.point.npc_interaction
    if npc is None:
        raise ValueError(f"Exploration point {request.point.id} has no npc_interaction.")
    allowed_effect_types = set(npc.policy.allowed_effect_types)
    allowed_flags = set(npc.policy.allowed_flags)
    for effect in effects:
        if allowed_effect_types and effect.type not in allowed_effect_types:
            raise ValueError(f"NPC effect is not allowed here: {effect.type}.")
        payload = effect.as_effect_payload()
        validate_exploration_effect(payload, request.state)
        if effect.type == "set_flag":
            key = str(effect.parameters.get("key", ""))
            if allowed_flags and key not in allowed_flags:
                raise ValueError(f"NPC effect flag is not allowed here: {key}.")


def _true_set_flag_keys(effects: tuple[NpcEffect, ...]) -> set[str]:
    result: set[str] = set()
    for effect in effects:
        if effect.type == "set_flag" and effect.parameters.get("value") is True:
            key = str(effect.parameters.get("key", "")).strip()
            if key:
                result.add(key)
    return result
