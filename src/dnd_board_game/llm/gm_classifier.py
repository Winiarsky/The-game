from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

import requests
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from dnd_board_game.combat import SceneAbilityCheck
from dnd_board_game.exploration import (
    ExplorationChallenge,
    ExplorationChallengeOption,
    ExplorationResource,
    ExplorationState,
    ExplorationZone,
    LlmChallengePolicy,
    LlmContext,
    available_challenge_options,
    challenge_state_for,
    visible_exploration_points,
)
from dnd_board_game.hardware import LedColor

from .content_config import load_freeform_grounding_terms, load_llm_core_rules
from .prompts import PromptId, load_prompt


# This module owns LLM transport, response parsing and mechanical validation.
# General vocabularies are loaded from content/llm/*.json, while specific
# obstacle details stay in scenario JSON via LlmContext and LlmChallengePolicy.


class GmIntentType(StrEnum):
    CHALLENGE_ATTEMPT = "challenge_attempt"
    ENVIRONMENT_SEARCH = "environment_search"
    UNSUPPORTED = "unsupported"


class GmDeclarationAnalysisType(StrEnum):
    PLAUSIBLE = "plausible"
    NEEDS_CLARIFICATION = "needs_clarification"
    UNSUPPORTED = "unsupported"
    PLAYER_QUESTION = "player_question"


class GmActionFlow(StrEnum):
    CHALLENGE_ATTEMPT = "challenge_attempt"
    PREPARATION = "preparation"
    COMBINED = "combined"
    PLAYER_QUESTION = "player_question"
    UNSUPPORTED = "unsupported"
    NEEDS_CLARIFICATION = "needs_clarification"


class GmConsequenceTrigger(StrEnum):
    CRITICAL_SUCCESS = "critical_success"
    SUCCESS = "success"
    FAILURE = "failure"
    CRITICAL_FAILURE = "critical_failure"


class GmConsequenceType(StrEnum):
    ADD_NOISE = "add_noise"
    ADD_COMPLICATION = "add_complication"
    REVEAL_POINT = "reveal_point"
    SET_FLAG = "set_flag"
    GRANT_RESOURCE = "grant_resource"
    CONSUME_RESOURCE = "consume_resource"
    UNLOCK_OPTION = "unlock_option"
    NONE = "none"


class PreparationEffectType(StrEnum):
    MODIFIER = "modifier"
    REDUCE_NEGATIVE_EFFECT = "reduce_negative_effect"
    ADVANTAGE = "advantage"
    DISADVANTAGE = "disadvantage"
    EFFECT_BOOST = "effect_boost"
    UNLOCK_OPTION = "unlock_option"
    GRANT_RESOURCE = "grant_resource"


class PreparationEffectDuration(StrEnum):
    NEXT_ATTEMPT = "next_attempt"


CORE_LLM_RULES = load_llm_core_rules()
CORE_DND_5E_ABILITIES = frozenset(CORE_LLM_RULES.abilities)
CORE_DND_5E_SKILLS = frozenset(CORE_LLM_RULES.skills)


class GmConsequence(BaseModel):
    model_config = ConfigDict(extra="ignore")

    trigger: GmConsequenceTrigger
    type: GmConsequenceType
    value: str | int | bool | None = None


class GmPreparationEffect(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: PreparationEffectType
    label: str = Field(default="", max_length=120)
    target_tags: tuple[str, ...] = ()
    value: int = Field(default=1, ge=0, le=5)
    duration: PreparationEffectDuration = PreparationEffectDuration.NEXT_ATTEMPT
    source: str = Field(default="preparation", max_length=80)
    resource_id: str | None = Field(default=None, max_length=80)
    option_id: str | None = Field(default=None, max_length=80)

    @field_validator("target_tags")
    @classmethod
    def _target_tags_must_be_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(tag.strip().lower() for tag in value if tag.strip()))


class GmClassifierProposal(BaseModel):
    model_config = ConfigDict(extra="ignore")

    intent_type: GmIntentType
    target_challenge_id: str | None = None
    approach_label: str = Field(default="", max_length=80)
    approach_tags: tuple[str, ...] = ()
    ability: str | None = None
    skill: str | None = None
    difficulty_tier: str | None = Field(default=None, max_length=40)
    difficulty_reason: str = Field(default="", max_length=800)
    dc: int | None = Field(default=None, ge=5, le=25)
    progress_on_success: int | None = Field(default=None, ge=0, le=3)
    progress_on_failure: int | None = Field(default=None, ge=0, le=1)
    used_resource_ids: tuple[str, ...] = ()
    action_flow: GmActionFlow = GmActionFlow.CHALLENGE_ATTEMPT
    preparation_effect: GmPreparationEffect | None = None
    requires_roll_now: bool = True
    consequences: tuple[GmConsequence, ...] = ()
    success_message: str = ""
    failure_message: str = ""
    critical_failure_message: str = ""
    player_narration: str = Field(default="", max_length=800)
    gm_notes: str = Field(default="", max_length=1000)

    @field_validator("approach_tags")
    @classmethod
    def _tags_must_be_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(dict.fromkeys(tag.strip().lower() for tag in value if tag.strip()))
        return normalized

    @field_validator("used_resource_ids")
    @classmethod
    def _resource_ids_must_be_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.strip() for item in value if item.strip()))

    @field_validator("ability", "skill")
    @classmethod
    def _lower_optional(cls, value: str | None) -> str | None:
        return value.strip().lower() if value else None

    @field_validator("difficulty_tier")
    @classmethod
    def _lower_tier(cls, value: str | None) -> str | None:
        return value.strip().lower() if value else None


@dataclass(frozen=True, slots=True)
class GmDeclarationThreadEntry:
    role: str
    content: str
    outcome: str = ""

    def as_payload(self) -> dict[str, str]:
        return {
            "role": self.role,
            "content": self.content,
            "outcome": self.outcome,
        }


@dataclass(frozen=True, slots=True)
class GmClassifierRequest:
    scenario_id: str
    scenario_name: str
    scenario_context: LlmContext
    zone: ExplorationZone
    challenge: ExplorationChallenge
    state: ExplorationState
    player_action: str
    declaration_thread: tuple[GmDeclarationThreadEntry, ...] = ()
    active_preparation_effects: tuple[GmPreparationEffect, ...] = ()

    def to_prompt_payload(self) -> dict[str, Any]:
        challenge_state = challenge_state_for(self.state, self.challenge.id)
        policy = self.challenge.llm_policy
        resources = [
            _resource_payload(resource)
            for resource in self.state.resources
            if resource.id in self.state.inventory_resource_ids
        ]
        return {
            "scenario": {"id": self.scenario_id, "name": self.scenario_name},
            "scenario_context": self.scenario_context.as_payload(),
            "zone": {
                "id": self.zone.id,
                "name": self.zone.name,
                "description": self.zone.description,
            },
            "zone_context": self.zone.llm_context.as_payload(),
            "challenge": {
                "id": self.challenge.id,
                "name": self.challenge.name,
                "progress_required": self.challenge.progress_required,
                "current_progress": challenge_state.current_progress,
                "completed": challenge_state.completed,
                "noise": challenge_state.noise,
                "complications": list(challenge_state.complications),
                "context": self.challenge.llm_context.as_payload(),
                "llm_policy": policy.as_payload(),
                "available_options": [
                    {
                        "id": option.id,
                        "label": option.label,
                        "ability": option.ability_check.ability,
                        "skill": option.ability_check.skill,
                        "dc": option.ability_check.dc,
                        "progress_on_success": option.progress_on_success,
                        "progress_on_failure": option.progress_on_failure,
                        "tags": list(option.tags),
                    }
                    for option in available_challenge_options(self.state, self.challenge)
                ],
            },
            "party_resources": resources,
            "dynamic_state": _dynamic_state_payload(self.state, self.challenge),
            "allowed_abilities": sorted(CORE_DND_5E_ABILITIES),
            "allowed_skills": sorted(_allowed_skills(policy)),
            "allowed_tags": sorted(policy.allowed_approach_tags),
            "allowed_consequence_types": list(policy.allowed_consequence_types),
            "allowed_complications": sorted(policy.allowed_complications),
            "declaration_thread": [entry.as_payload() for entry in self.declaration_thread],
            "active_preparation_effects": [effect.model_dump(mode="json") for effect in self.active_preparation_effects],
            "player_action": self.player_action,
        }


@dataclass(frozen=True, slots=True)
class GmValidatedProposal:
    proposal: GmClassifierProposal
    challenge: ExplorationChallenge
    resources: tuple[ExplorationResource, ...]


class GmProposalValidationError(ValueError):
    pass


class GmClassifierClient(Protocol):
    model: str

    def analyze(self, request: GmClassifierRequest) -> GmDeclarationAnalysis:
        ...

    def classify(self, request: GmClassifierRequest) -> GmClassifierProposal:
        ...


class GroqGmClassifierClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        prompt_path: Path | str | None = None,
        analyzer_prompt_path: Path | str | None = None,
        timeout_s: float = 30.0,
        max_retries: int = 3,
        retry_backoff_s: float = 1.0,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.environ.get("GROQ_API_KEY", "")
        self.model = model or os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
        self.prompt_path = Path(prompt_path) if prompt_path is not None else None
        self.analyzer_prompt_path = Path(analyzer_prompt_path) if analyzer_prompt_path is not None else None
        self.timeout_s = timeout_s
        self.max_retries = max(0, max_retries)
        self.retry_backoff_s = max(0.0, retry_backoff_s)

    def analyze(self, request: GmClassifierRequest) -> GmDeclarationAnalysis:
        system_prompt = (
            self.analyzer_prompt_path.read_text(encoding="utf-8")
            if self.analyzer_prompt_path is not None
            else load_prompt(PromptId.GM_DECLARATION_ANALYZER)
        )
        content = self._complete(system_prompt, request)
        try:
            return GmDeclarationAnalysis.model_validate_json(content)
        except ValidationError as exc:
            raise GmProposalValidationError(f"LLM returned invalid declaration analysis: {exc}") from exc

    def classify(self, request: GmClassifierRequest) -> GmClassifierProposal:
        system_prompt = (
            self.prompt_path.read_text(encoding="utf-8")
            if self.prompt_path is not None
            else load_prompt(PromptId.GM_CHALLENGE_CLASSIFIER)
        )
        content = self._complete(system_prompt, request)
        try:
            return GmClassifierProposal.model_validate_json(content)
        except ValidationError as exc:
            raise GmProposalValidationError(f"LLM returned invalid proposal: {exc}") from exc

    def _complete(self, system_prompt: str, request: GmClassifierRequest) -> str:
        if not self.api_key:
            raise RuntimeError("Missing GROQ_API_KEY. Ustaw klucz w .env i uruchom `source .env`.")
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(request.to_prompt_payload(), ensure_ascii=False),
                },
            ],
        }
        response = None
        for attempt in range(self.max_retries + 1):
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout_s,
            )
            if response.status_code not in {429, 500, 502, 503, 504} or attempt >= self.max_retries:
                break
            time.sleep(_retry_delay(response, attempt, self.retry_backoff_s))
        assert response is not None
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            if response.status_code == 429:
                raise RuntimeError(
                    "Groq zwrócił limit zapytań 429 po ponowieniach. Odczekaj chwilę albo zmniejsz liczbę prób."
                ) from exc
            raise
        data = response.json()
        return str(data["choices"][0]["message"]["content"])


class GeminiGmClassifierClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        prompt_path: Path | str | None = None,
        analyzer_prompt_path: Path | str | None = None,
        timeout_s: float = 30.0,
        max_retries: int = 3,
        retry_backoff_s: float = 1.0,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY", "")
        self.model = model or os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
        self.prompt_path = Path(prompt_path) if prompt_path is not None else None
        self.analyzer_prompt_path = Path(analyzer_prompt_path) if analyzer_prompt_path is not None else None
        self.timeout_s = timeout_s
        self.max_retries = max(0, max_retries)
        self.retry_backoff_s = max(0.0, retry_backoff_s)

    def analyze(self, request: GmClassifierRequest) -> GmDeclarationAnalysis:
        system_prompt = (
            self.analyzer_prompt_path.read_text(encoding="utf-8")
            if self.analyzer_prompt_path is not None
            else load_prompt(PromptId.GM_DECLARATION_ANALYZER)
        )
        content = self._complete(system_prompt, request)
        try:
            return GmDeclarationAnalysis.model_validate_json(content)
        except ValidationError as exc:
            raise GmProposalValidationError(f"Gemini returned invalid declaration analysis: {exc}") from exc

    def classify(self, request: GmClassifierRequest) -> GmClassifierProposal:
        system_prompt = (
            self.prompt_path.read_text(encoding="utf-8")
            if self.prompt_path is not None
            else load_prompt(PromptId.GM_CHALLENGE_CLASSIFIER)
        )
        content = self._complete(system_prompt, request)
        try:
            return GmClassifierProposal.model_validate_json(content)
        except ValidationError as exc:
            raise GmProposalValidationError(f"Gemini returned invalid proposal: {exc}") from exc

    def _complete(self, system_prompt: str, request: GmClassifierRequest) -> str:
        if not self.api_key:
            raise RuntimeError("Missing GEMINI_API_KEY. Ustaw klucz w .env i uruchom `source .env`.")
        payload = {
            "system_instruction": {
                "parts": [{"text": system_prompt}],
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": json.dumps(
                                request.to_prompt_payload(),
                                ensure_ascii=False,
                            )
                        }
                    ],
                }
            ],
            "generation_config": {
                "temperature": 0.2,
                "response_mime_type": "application/json",
            },
        }
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        response = None
        for attempt in range(self.max_retries + 1):
            response = requests.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": self.api_key,
                },
                json=payload,
                timeout=self.timeout_s,
            )
            if response.status_code not in {429, 500, 502, 503, 504} or attempt >= self.max_retries:
                break
            time.sleep(_retry_delay(response, attempt, self.retry_backoff_s))
        assert response is not None
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            if response.status_code == 429:
                raise RuntimeError(
                    "Gemini zwrócił limit zapytań 429 po ponowieniach. Odczekaj chwilę albo zmniejsz liczbę prób."
                ) from exc
            raise
        data = response.json()
        try:
            return str(data["candidates"][0]["content"]["parts"][0]["text"])
        except (KeyError, IndexError, TypeError) as exc:
            raise GmProposalValidationError(f"Gemini returned unexpected response shape: {data}") from exc


def _retry_delay(response: requests.Response, attempt: int, base_delay_s: float) -> float:
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return min(30.0, max(0.0, float(retry_after)))
        except ValueError:
            pass
    return min(30.0, base_delay_s * (2**attempt))


def build_gm_classifier_request(
    *,
    scenario_id: str,
    scenario_name: str,
    scenario_context: LlmContext = LlmContext(),
    state: ExplorationState,
    player_action: str,
    declaration_thread: tuple[GmDeclarationThreadEntry, ...] = (),
    active_preparation_effects: tuple[GmPreparationEffect, ...] = (),
) -> GmClassifierRequest:
    zone = next(zone for zone in state.zones if zone.id == state.party_position.zone_id)
    challenge = next((challenge for challenge in state.challenges if challenge.zone_id == zone.id), None)
    if challenge is None:
        raise GmProposalValidationError(f"Strefa {zone.name} nie ma aktywnego wyzwania eksploracyjnego.")
    return GmClassifierRequest(
        scenario_id,
        scenario_name,
        scenario_context,
        zone,
        challenge,
        state,
        player_action,
        declaration_thread,
        active_preparation_effects,
    )


def validate_gm_declaration_analysis(
    analysis: GmDeclarationAnalysis,
    request: GmClassifierRequest,
) -> None:
    if analysis.action_flow in {
        GmActionFlow.PLAYER_QUESTION,
        GmActionFlow.UNSUPPORTED,
        GmActionFlow.NEEDS_CLARIFICATION,
    }:
        return
    if analysis.missing_requirements:
        raise GmProposalValidationError("; ".join(analysis.missing_requirements))
    if analysis.assumed_new_facts:
        raise GmProposalValidationError(
            "Deklaracja zakłada nowe fakty spoza sceny: " + ", ".join(analysis.assumed_new_facts)
        )
    unknown_resources = _unknown_declared_resources(analysis, request)
    if unknown_resources:
        raise GmProposalValidationError("Drużyna nie ma zadeklarowanych zasobów: " + ", ".join(unknown_resources))


def validate_gm_classifier_proposal(
    proposal: GmClassifierProposal,
    request: GmClassifierRequest,
) -> GmValidatedProposal:
    policy = request.challenge.llm_policy
    # General guards: LLM may only propose an interpretation for the active
    # challenge; deterministic game code still owns state changes.
    if proposal.intent_type == GmIntentType.UNSUPPORTED:
        raise GmProposalValidationError(proposal.player_narration or "Deklaracja nie jest obsługiwana w tym MVP.")
    if proposal.intent_type == GmIntentType.ENVIRONMENT_SEARCH:
        raise GmProposalValidationError(
            proposal.player_narration
            or "Ta deklaracja wygląda jak ogólne przeszukiwanie okolicy, a nie konkretne podejście do aktywnego wyzwania."
        )
    if proposal.intent_type != GmIntentType.CHALLENGE_ATTEMPT:
        raise GmProposalValidationError(proposal.player_narration or "Ta deklaracja nie pasuje do aktywnego wyzwania.")
    if proposal.target_challenge_id != request.challenge.id:
        raise GmProposalValidationError("LLM wskazał inne wyzwanie niż aktywne wyzwanie w tej lokacji.")
    if challenge_state_for(request.state, request.challenge.id).completed:
        raise GmProposalValidationError("To wyzwanie jest już zakończone.")
    if not proposal.approach_label.strip():
        raise GmProposalValidationError("Propozycja LLM nie ma nazwy podejścia.")
    if proposal.preparation_effect is not None:
        _validate_preparation_effect(proposal.preparation_effect, policy, request)
    if proposal.action_flow == GmActionFlow.PREPARATION:
        if proposal.preparation_effect is None:
            raise GmProposalValidationError("Przygotowanie wymaga preparation_effect.")
        if proposal.requires_roll_now:
            raise GmProposalValidationError("Przygotowanie bez próby nie może wymagać rzutu teraz.")
        resources = _validate_resources(proposal, request.state)
        _validate_fact_grounding(proposal, request)
        return GmValidatedProposal(proposal, request.challenge, resources)
    if proposal.action_flow == GmActionFlow.COMBINED:
        if proposal.preparation_effect is None:
            raise GmProposalValidationError("Combined action wymaga preparation_effect.")
        if not proposal.requires_roll_now:
            raise GmProposalValidationError("Combined action musi wymagać rzutu teraz.")
    if proposal.action_flow != GmActionFlow.CHALLENGE_ATTEMPT and proposal.action_flow != GmActionFlow.COMBINED:
        raise GmProposalValidationError(f"Nieobsługiwany action_flow dla classifiera: {proposal.action_flow.value}.")
    if proposal.ability not in CORE_DND_5E_ABILITIES:
        raise GmProposalValidationError(f"Nieobsługiwana cecha testu: {proposal.ability}.")
    if proposal.skill is not None and proposal.skill not in _allowed_skills(policy):
        raise GmProposalValidationError(f"Nieobsługiwana umiejętność testu: {proposal.skill}.")
    if proposal.dc is None or proposal.progress_on_success is None or proposal.progress_on_failure is None:
        raise GmProposalValidationError("Propozycja LLM nie zawiera ST albo postępu.")
    _validate_difficulty_tier(proposal, policy)
    if not policy.dc_min <= proposal.dc <= policy.dc_max:
        raise GmProposalValidationError(f"ST {proposal.dc} jest poza zakresem policy: {policy.dc_min}-{policy.dc_max}.")
    if not policy.progress_success_min <= proposal.progress_on_success <= policy.progress_success_max:
        raise GmProposalValidationError(
            "Postęp przy sukcesie jest poza zakresem policy: "
            f"{policy.progress_success_min}-{policy.progress_success_max}."
        )
    if not policy.progress_failure_min <= proposal.progress_on_failure <= policy.progress_failure_max:
        raise GmProposalValidationError(
            "Postęp przy porażce jest poza zakresem policy: "
            f"{policy.progress_failure_min}-{policy.progress_failure_max}."
        )
    unknown_tags = set(proposal.approach_tags) - set(policy.allowed_approach_tags)
    if unknown_tags:
        raise GmProposalValidationError(f"Nieobsługiwane tagi podejścia: {', '.join(sorted(unknown_tags))}.")
    if proposal.preparation_effect is not None and not set(proposal.preparation_effect.target_tags).intersection(proposal.approach_tags):
        raise GmProposalValidationError("Efekt przygotowania nie pasuje tagami do próby challenge.")
    _validate_context_constraints(proposal, request)
    if len(proposal.used_resource_ids) > policy.max_resources_per_attempt:
        raise GmProposalValidationError(
            "Ta polityka wyzwania pozwala użyć maksymalnie "
            f"{policy.max_resources_per_attempt} zasobów naraz."
        )
    resources = _validate_resources(proposal, request.state)
    _validate_fact_grounding(proposal, request)
    _validate_consequences(proposal, policy)
    _validate_narration_consistency(proposal)
    return GmValidatedProposal(proposal, request.challenge, resources)


def challenge_option_from_validated_proposal(validated: GmValidatedProposal) -> ExplorationChallengeOption:
    proposal = validated.proposal
    noise = _noise_by_trigger(proposal)
    complications = _complications_by_trigger(proposal)
    return ExplorationChallengeOption(
        id="gm_generated",
        label=proposal.approach_label.strip(),
        ability_check=SceneAbilityCheck(
            ability=proposal.ability or "wisdom",
            skill=proposal.skill,
            dc=proposal.dc or 10,
        ),
        progress_on_success=proposal.progress_on_success or 1,
        progress_on_failure=proposal.progress_on_failure or 0,
        color=LedColor.MENU_PURPLE,
        description=proposal.player_narration,
        success_message=proposal.success_message or "Podejście działa.",
        failure_message=proposal.failure_message or "Podejście nie wychodzi czysto, ale sytuacja idzie naprzód.",
        critical_failure_message=proposal.critical_failure_message,
        tags=proposal.approach_tags,
        success_noise=noise[GmConsequenceTrigger.SUCCESS],
        failure_noise=noise[GmConsequenceTrigger.FAILURE],
        critical_failure_noise=noise[GmConsequenceTrigger.CRITICAL_FAILURE],
        success_complication=complications[GmConsequenceTrigger.SUCCESS],
        failure_complication=complications[GmConsequenceTrigger.FAILURE],
        critical_failure_complication=complications[GmConsequenceTrigger.CRITICAL_FAILURE],
    )


def _validate_resources(
    proposal: GmClassifierProposal,
    state: ExplorationState,
) -> tuple[ExplorationResource, ...]:
    owned = set(state.inventory_resource_ids)
    resources_by_id = {resource.id: resource for resource in state.resources}
    approach_tags = set(proposal.approach_tags)
    result: list[ExplorationResource] = []
    for resource_id in proposal.used_resource_ids:
        if resource_id not in owned:
            raise GmProposalValidationError(f"Drużyna nie ma zasobu: {resource_id}.")
        resource = resources_by_id.get(resource_id)
        if resource is None:
            raise GmProposalValidationError(f"Nieznany zasób: {resource_id}.")
        if not approach_tags.intersection(resource.bonus_tags):
            raise GmProposalValidationError(
                f"Zasób {resource_id} nie pasuje tagami do podejścia: {', '.join(sorted(approach_tags))}."
            )
        result.append(resource)
    return tuple(result)


def _validate_preparation_effect(
    effect: GmPreparationEffect,
    policy: LlmChallengePolicy,
    request: GmClassifierRequest,
) -> None:
    if effect.type.value not in policy.allowed_preparation_effect_types:
        raise GmProposalValidationError(f"Efekt przygotowania {effect.type.value} nie jest dozwolony w tym wyzwaniu.")
    if effect.duration != PreparationEffectDuration.NEXT_ATTEMPT:
        raise GmProposalValidationError("MVP obsługuje tylko przygotowania duration=next_attempt.")
    if not effect.target_tags:
        raise GmProposalValidationError("Efekt przygotowania musi wskazywać target_tags.")
    unknown_tags = set(effect.target_tags) - set(policy.allowed_approach_tags)
    if unknown_tags:
        raise GmProposalValidationError(
            f"Efekt przygotowania ma nieobsługiwane target_tags: {', '.join(sorted(unknown_tags))}."
        )
    if effect.type == PreparationEffectType.MODIFIER:
        if not policy.preparation_modifier_min <= effect.value <= policy.preparation_modifier_max:
            raise GmProposalValidationError(
                "Modyfikator przygotowania jest poza zakresem policy: "
                f"{policy.preparation_modifier_min}-{policy.preparation_modifier_max}."
            )
    elif effect.type == PreparationEffectType.REDUCE_NEGATIVE_EFFECT:
        if not policy.negative_effect_reduction_min <= effect.value <= policy.negative_effect_reduction_max:
            raise GmProposalValidationError(
                "Redukcja negatywnego efektu jest poza zakresem policy: "
                f"{policy.negative_effect_reduction_min}-{policy.negative_effect_reduction_max}."
            )
    elif effect.type in {PreparationEffectType.ADVANTAGE, PreparationEffectType.DISADVANTAGE}:
        if effect.value not in {0, 1}:
            raise GmProposalValidationError(f"Efekt {effect.type.value} musi mieć value 0 albo 1.")
    elif effect.type == PreparationEffectType.EFFECT_BOOST:
        if not policy.effect_boost_min <= effect.value <= policy.effect_boost_max:
            raise GmProposalValidationError(
                "Wzmocnienie efektu jest poza zakresem policy: "
                f"{policy.effect_boost_min}-{policy.effect_boost_max}."
            )
    elif effect.type == PreparationEffectType.GRANT_RESOURCE:
        if not effect.resource_id:
            raise GmProposalValidationError("grant_resource wymaga resource_id.")
        if effect.resource_id not in policy.allowed_grant_resource_ids:
            raise GmProposalValidationError(f"Zasób {effect.resource_id} nie może być przyznany przez to wyzwanie.")
        known_resource_ids = {resource.id for resource in request.state.resources}
        if effect.resource_id not in known_resource_ids:
            raise GmProposalValidationError(f"Nieznany zasób do przyznania: {effect.resource_id}.")
    elif effect.type == PreparationEffectType.UNLOCK_OPTION:
        if not effect.option_id:
            raise GmProposalValidationError("unlock_option wymaga option_id.")
        if effect.option_id not in policy.allowed_unlock_option_ids:
            raise GmProposalValidationError(f"Opcja {effect.option_id} nie może być odblokowana przez to wyzwanie.")
        known_option_ids = {option.id for option in request.challenge.options}
        if effect.option_id not in known_option_ids:
            raise GmProposalValidationError(f"Nieznana opcja do odblokowania: {effect.option_id}.")


def _validate_difficulty_tier(proposal: GmClassifierProposal, policy: LlmChallengePolicy) -> None:
    if not policy.dc_tiers:
        return
    if not proposal.difficulty_tier:
        raise GmProposalValidationError("Propozycja LLM musi zawierać difficulty_tier dla tego wyzwania.")
    allowed_tiers = set(policy.allowed_difficulty_tiers or tuple(tier.id for tier in policy.dc_tiers))
    if proposal.difficulty_tier not in allowed_tiers:
        raise GmProposalValidationError(
            f"Poziom trudności {proposal.difficulty_tier} nie jest dozwolony w tym wyzwaniu."
        )
    expected_dc = policy.dc_for_tier(proposal.difficulty_tier)
    if expected_dc is None:
        raise GmProposalValidationError(f"Nieznany poziom trudności: {proposal.difficulty_tier}.")
    if proposal.dc != expected_dc:
        raise GmProposalValidationError(
            f"ST {proposal.dc} nie zgadza się z dc_policy dla poziomu {proposal.difficulty_tier}: {expected_dc}."
        )
    if not proposal.difficulty_reason.strip():
        raise GmProposalValidationError("Propozycja LLM musi wyjaśnić wybór difficulty_tier.")


def _validate_fact_grounding(proposal: GmClassifierProposal, request: GmClassifierRequest) -> None:
    known_tokens = _known_resource_or_material_tokens(request)
    technical_text = " ".join(
        (
            request.player_action,
            proposal.approach_label,
            proposal.player_narration,
            proposal.success_message,
            proposal.failure_message,
            proposal.critical_failure_message,
        )
    )
    unknown_mentions = _unsupported_resource_mentions(technical_text, known_tokens)
    if unknown_mentions:
        raise GmProposalValidationError(
            "Propozycja używa zasobu albo faktu, którego nie ma w stanie gry: "
            + ", ".join(sorted(unknown_mentions))
            + "."
        )


def _unknown_declared_resources(
    analysis: GmDeclarationAnalysis,
    request: GmClassifierRequest,
) -> tuple[str, ...]:
    known_tokens = _known_resource_or_material_tokens(request)
    unknown: list[str] = []
    for resource_id in analysis.referenced_existing_resource_ids:
        if _normalize_fact_token(resource_id) not in known_tokens:
            unknown.append(resource_id)
    for resource in analysis.declared_resources:
        normalized = _normalize_fact_token(resource)
        if normalized and normalized not in known_tokens and not _resource_phrase_is_known(normalized, known_tokens):
            unknown.append(resource)
    return tuple(dict.fromkeys(unknown))


def _known_resource_or_material_tokens(request: GmClassifierRequest) -> set[str]:
    tokens: set[str] = set()
    for resource in request.state.resources:
        if resource.id in request.state.inventory_resource_ids:
            tokens.add(_normalize_fact_token(resource.id))
            tokens.add(_normalize_fact_token(resource.label))
    for context in (request.scenario_context, request.zone.llm_context, request.challenge.llm_context):
        for material in context.available_materials:
            tokens.add(_normalize_fact_token(material))
    return {token for token in tokens if token}


def _resource_phrase_is_known(normalized_phrase: str, known_tokens: set[str]) -> bool:
    if normalized_phrase in known_tokens:
        return True
    return any(
        normalized_phrase in known or known in normalized_phrase
        for known in known_tokens
        if len(normalized_phrase) >= 4 and len(known) >= 4
    )


def _unsupported_resource_mentions(text: str, known_tokens: set[str]) -> tuple[str, ...]:
    normalized = _normalize_fact_token(text)
    unknown: list[str] = []
    for mention in load_freeform_grounding_terms().guarded_resource_mentions:
        normalized_variants = tuple(_normalize_fact_token(variant) for variant in mention.variants)
        if any(variant in normalized for variant in normalized_variants):
            if not any(variant in known_tokens for variant in normalized_variants):
                unknown.append(mention.label)
    return tuple(dict.fromkeys(unknown))


def _normalize_fact_token(value: str) -> str:
    translation = str.maketrans({"ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o", "ś": "s", "ż": "z", "ź": "z"})
    return " ".join(value.strip().lower().translate(translation).split())


def _allowed_skills(policy: LlmChallengePolicy) -> frozenset[str]:
    return CORE_DND_5E_SKILLS | frozenset(policy.allowed_local_skills)


def _validate_consequences(proposal: GmClassifierProposal, policy: LlmChallengePolicy) -> None:
    for consequence in proposal.consequences:
        if consequence.type.value not in policy.allowed_consequence_types:
            raise GmProposalValidationError(f"Konsekwencja {consequence.type.value} nie jest dozwolona w tym wyzwaniu.")
        if consequence.type == GmConsequenceType.ADD_COMPLICATION and str(consequence.value) not in policy.allowed_complications:
            raise GmProposalValidationError(f"Nieobsługiwana komplikacja: {consequence.value}.")
        if consequence.type == GmConsequenceType.ADD_NOISE:
            if not isinstance(consequence.value, int) or consequence.value < 0 or consequence.value > 3:
                raise GmProposalValidationError("add_noise wymaga wartości całkowitej 0..3.")
        if consequence.type in {
            GmConsequenceType.REVEAL_POINT,
            GmConsequenceType.SET_FLAG,
            GmConsequenceType.GRANT_RESOURCE,
            GmConsequenceType.CONSUME_RESOURCE,
            GmConsequenceType.UNLOCK_OPTION,
        }:
            raise GmProposalValidationError(f"Konsekwencja {consequence.type.value} nie jest jeszcze wykonywana w MVP.")


def _validate_context_constraints(proposal: GmClassifierProposal, request: GmClassifierRequest) -> None:
    forbidden = _all_forbidden_assumptions(request)
    if not forbidden:
        return
    technical_text = " ".join(
        (
            proposal.approach_label,
            " ".join(proposal.approach_tags),
            proposal.success_message,
            proposal.failure_message,
            proposal.critical_failure_message,
        )
    ).lower()
    for assumption in forbidden:
        normalized = assumption.lower()
        if normalized and normalized in technical_text:
            raise GmProposalValidationError(f"Propozycja używa zakazanego założenia sceny: {assumption}.")


def _validate_narration_consistency(proposal: GmClassifierProposal) -> None:
    narration = proposal.player_narration.lower()
    if not narration:
        return
    label = proposal.approach_label.lower()
    tags = set(proposal.approach_tags)
    conflicts = (
        ("klin", "lever"),
        ("podważ", "lever"),
        ("wyważ", "heavy_force"),
        ("rozbieg", "heavy_force"),
        ("wspin", "climbing"),
        ("lina", "climbing"),
        ("pił", "saw"),
        ("przeci", "saw"),
    )
    narration_hints = {tag for marker, tag in conflicts if marker in narration}
    if not narration_hints:
        return
    label_hints = {tag for marker, tag in conflicts if marker in label}
    technical_hints = tags | label_hints
    if technical_hints and narration_hints.isdisjoint(technical_hints):
        raise GmProposalValidationError(
            "Narracja propozycji LLM opisuje inne podejście niż techniczne pola testu. "
            "Spróbuj opisać podejście jeszcze raz albo wybierz inną propozycję."
        )


def _all_forbidden_assumptions(request: GmClassifierRequest) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            (
                *request.scenario_context.forbidden_assumptions,
                *request.zone.llm_context.forbidden_assumptions,
                *request.challenge.llm_context.impossible_approaches,
            )
        )
    )


def _noise_by_trigger(proposal: GmClassifierProposal) -> dict[GmConsequenceTrigger, int]:
    values = {trigger: 0 for trigger in GmConsequenceTrigger}
    for consequence in proposal.consequences:
        if consequence.type == GmConsequenceType.ADD_NOISE and isinstance(consequence.value, int):
            values[consequence.trigger] = max(values[consequence.trigger], consequence.value)
    return values


def _complications_by_trigger(proposal: GmClassifierProposal) -> dict[GmConsequenceTrigger, str | None]:
    values: dict[GmConsequenceTrigger, str | None] = {trigger: None for trigger in GmConsequenceTrigger}
    for consequence in proposal.consequences:
        if consequence.type == GmConsequenceType.ADD_COMPLICATION and consequence.value is not None:
            values[consequence.trigger] = str(consequence.value)
    return values


def _resource_payload(resource: ExplorationResource) -> dict[str, Any]:
    return {
        "id": resource.id,
        "label": resource.label,
        "bonus_tags": list(resource.bonus_tags),
        "modifier": resource.modifier,
        "advantage": resource.advantage,
        "mitigates_complications": list(resource.mitigates_complications),
        "mitigates_noise": resource.mitigates_noise,
    }


def _dynamic_state_payload(state: ExplorationState, challenge: ExplorationChallenge) -> dict[str, Any]:
    challenge_state = challenge_state_for(state, challenge.id)
    visible_points = visible_exploration_points(state.points)
    return {
        "known_flags": [{"key": key, "value": value} for key, value in state.flags.values],
        "challenge_progress": {
            "challenge_id": challenge.id,
            "current": challenge_state.current_progress,
            "required": challenge.progress_required,
            "completed": challenge_state.completed,
        },
        "noise": challenge_state.noise,
        "complications": list(challenge_state.complications),
        "revealed_points": [
            {"id": point.id, "name": point.name, "zone_id": point.zone_id}
            for point in visible_points
        ],
        "inventory_resource_ids": list(state.inventory_resource_ids),
        "world_notes": _world_notes(state, challenge),
        "attempt_history": _attempt_history_payload(challenge_state),
    }


def _attempt_history_payload(challenge_state) -> list[dict[str, Any]]:
    return [
        {
            "challenge_id": attempt.challenge_id,
            "option_id": attempt.option_id,
            "approach_label": attempt.approach_label,
            "approach_tags": list(attempt.approach_tags),
            "resource_id": attempt.resource_id,
            "natural_roll": attempt.natural_roll,
            "total": attempt.total,
            "success": attempt.success,
            "critical_failure": attempt.critical_failure,
            "progress_added": attempt.progress_added,
            "noise_added": attempt.noise_added,
            "complications_added": list(attempt.complications_added),
        }
        for attempt in challenge_state.attempts
    ]


class GmDeclarationAnalysis(BaseModel):
    model_config = ConfigDict(extra="ignore")

    analysis_type: GmDeclarationAnalysisType
    action_flow: GmActionFlow | None = None
    player_message: str = Field(default="", max_length=800)
    normalized_intent: str = Field(default="", max_length=500)
    reason: str = Field(default="", max_length=1000)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    declared_resources: tuple[str, ...] = ()
    referenced_existing_resource_ids: tuple[str, ...] = ()
    assumed_new_facts: tuple[str, ...] = ()
    missing_requirements: tuple[str, ...] = ()

    @field_validator("declared_resources", "referenced_existing_resource_ids", "assumed_new_facts", "missing_requirements")
    @classmethod
    def _string_tuple_items(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.strip() for item in value if item.strip()))

    def model_post_init(self, __context: Any) -> None:
        if self.action_flow is None:
            default_flow = {
                GmDeclarationAnalysisType.PLAUSIBLE: GmActionFlow.CHALLENGE_ATTEMPT,
                GmDeclarationAnalysisType.NEEDS_CLARIFICATION: GmActionFlow.NEEDS_CLARIFICATION,
                GmDeclarationAnalysisType.UNSUPPORTED: GmActionFlow.UNSUPPORTED,
                GmDeclarationAnalysisType.PLAYER_QUESTION: GmActionFlow.PLAYER_QUESTION,
            }[self.analysis_type]
            object.__setattr__(self, "action_flow", default_flow)


def _world_notes(state: ExplorationState, challenge: ExplorationChallenge) -> list[str]:
    challenge_state = challenge_state_for(state, challenge.id)
    notes: list[str] = []
    if challenge_state.current_progress:
        notes.append(
            f"Wyzwanie `{challenge.name}` ma postęp {challenge_state.current_progress}/{challenge.progress_required}."
        )
    if challenge_state.noise:
        notes.append(f"Dotychczasowy hałas przy wyzwaniu: {challenge_state.noise}.")
    for complication in challenge_state.complications:
        notes.append(f"Aktywna komplikacja: {complication}.")
    for key, value in state.flags.values:
        if value is True:
            notes.append(f"Aktywna flaga sceny: {key}.")
    return notes
