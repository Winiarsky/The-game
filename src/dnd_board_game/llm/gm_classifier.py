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
    LlmContext,
    available_challenge_options,
    challenge_state_for,
    visible_exploration_points,
)
from dnd_board_game.hardware import LedColor

from .prompts import PromptId, load_prompt


# This module should own LLM transport, response parsing and mechanical validation.
# Scenario-specific content should live in content JSON and LlmContext. The MVP
# policy constants below are intentionally marked so they can be moved into
# scenario/challenge configuration in a later content-driven stage.


class GmIntentType(StrEnum):
    CHALLENGE_ATTEMPT = "challenge_attempt"
    ENVIRONMENT_SEARCH = "environment_search"
    UNSUPPORTED = "unsupported"


class GmDeclarationAnalysisType(StrEnum):
    PLAUSIBLE = "plausible"
    NEEDS_CLARIFICATION = "needs_clarification"
    UNSUPPORTED = "unsupported"
    PLAYER_QUESTION = "player_question"


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


CORE_DND_5E_ABILITIES = frozenset(
    {
        "strength",
        "dexterity",
        "constitution",
        "intelligence",
        "wisdom",
        "charisma",
    }
)
CORE_DND_5E_SKILLS = frozenset(
    {
        "acrobatics",
        "animal_handling",
        "arcana",
        "athletics",
        "deception",
        "history",
        "insight",
        "intimidation",
        "investigation",
        "medicine",
        "nature",
        "perception",
        "performance",
        "persuasion",
        "religion",
        "sleight_of_hand",
        "stealth",
        "survival",
    }
)

# MVP content policy. These are not general D&D rules; they describe the
# current exploration slices and should become scenario/challenge-level config.
MVP_LOCAL_SKILLS = frozenset({"crafting"})
MVP_APPROACH_TAGS = frozenset(
    {
        "arcane",
        "bribe",
        "climbing",
        "crafting",
        "fire",
        "heavy_force",
        "lever",
        "light",
        "lockpicking",
        "medicine",
        "nature",
        "noise",
        "picket",
        "quiet",
        "religious",
        "saw",
        "scouting",
        "social",
    }
)
MVP_COMPLICATION_IDS = frozenset(
    {
        "alarm_w_strażnicy",
        "bolesny_upadek",
        "drzazgi",
        "guards_alerted",
        "jammed_gate",
        "lost_resource",
        "minor_injury",
        "narastający_hałas",
        "ryzyko_upadku",
        "stracony_czas",
        "time_cost",
        "uszkodzony_mechanizm",
        "zaklinowana_sztacheta",
        "ślepy_trop",
    }
)
MVP_CONSEQUENCE_TYPES = (
    GmConsequenceType.ADD_NOISE,
    GmConsequenceType.ADD_COMPLICATION,
    GmConsequenceType.NONE,
)

ALLOWED_ABILITIES = CORE_DND_5E_ABILITIES
ALLOWED_SKILLS = CORE_DND_5E_SKILLS | MVP_LOCAL_SKILLS
ALLOWED_TAGS = MVP_APPROACH_TAGS
ALLOWED_COMPLICATIONS = MVP_COMPLICATION_IDS


class GmConsequence(BaseModel):
    model_config = ConfigDict(extra="ignore")

    trigger: GmConsequenceTrigger
    type: GmConsequenceType
    value: str | int | bool | None = None


class GmClassifierProposal(BaseModel):
    model_config = ConfigDict(extra="ignore")

    intent_type: GmIntentType
    target_challenge_id: str | None = None
    approach_label: str = Field(default="", max_length=80)
    approach_tags: tuple[str, ...] = ()
    ability: str | None = None
    skill: str | None = None
    dc: int | None = Field(default=None, ge=5, le=25)
    progress_on_success: int | None = Field(default=None, ge=0, le=3)
    progress_on_failure: int | None = Field(default=None, ge=0, le=1)
    used_resource_ids: tuple[str, ...] = ()
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


@dataclass(frozen=True, slots=True)
class GmClassifierRequest:
    scenario_id: str
    scenario_name: str
    scenario_context: LlmContext
    zone: ExplorationZone
    challenge: ExplorationChallenge
    state: ExplorationState
    player_action: str

    def to_prompt_payload(self) -> dict[str, Any]:
        challenge_state = challenge_state_for(self.state, self.challenge.id)
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
            "allowed_abilities": sorted(ALLOWED_ABILITIES),
            "allowed_skills": sorted(ALLOWED_SKILLS),
            "allowed_tags": sorted(ALLOWED_TAGS),
            "allowed_consequence_types": [item.value for item in MVP_CONSEQUENCE_TYPES],
            "allowed_complications": sorted(ALLOWED_COMPLICATIONS),
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
) -> GmClassifierRequest:
    zone = next(zone for zone in state.zones if zone.id == state.party_position.zone_id)
    challenge = next((challenge for challenge in state.challenges if challenge.zone_id == zone.id), None)
    if challenge is None:
        raise GmProposalValidationError(f"Strefa {zone.name} nie ma aktywnego wyzwania eksploracyjnego.")
    return GmClassifierRequest(scenario_id, scenario_name, scenario_context, zone, challenge, state, player_action)


def validate_gm_classifier_proposal(
    proposal: GmClassifierProposal,
    request: GmClassifierRequest,
) -> GmValidatedProposal:
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
    if proposal.ability not in ALLOWED_ABILITIES:
        raise GmProposalValidationError(f"Nieobsługiwana cecha testu: {proposal.ability}.")
    if proposal.skill is not None and proposal.skill not in ALLOWED_SKILLS:
        raise GmProposalValidationError(f"Nieobsługiwana umiejętność testu: {proposal.skill}.")
    if proposal.dc is None or proposal.progress_on_success is None or proposal.progress_on_failure is None:
        raise GmProposalValidationError("Propozycja LLM nie zawiera ST albo postępu.")
    if proposal.progress_on_success < 1:
        raise GmProposalValidationError("Podejście do wyzwania musi dawać co najmniej 1 punkt postępu przy sukcesie.")
    if proposal.progress_on_failure < 0:
        raise GmProposalValidationError("Postęp przy porażce nie może być ujemny.")
    # MVP policy: tags, complications and resource count are currently global.
    # Move them to scenario/challenge/interaction content when the format is
    # mature enough to express per-scene vocabularies and limits.
    unknown_tags = set(proposal.approach_tags) - ALLOWED_TAGS
    if unknown_tags:
        raise GmProposalValidationError(f"Nieobsługiwane tagi podejścia: {', '.join(sorted(unknown_tags))}.")
    _validate_context_constraints(proposal, request)
    if len(proposal.used_resource_ids) > 1:
        raise GmProposalValidationError("MVP obsługuje użycie maksymalnie jednego zasobu naraz.")
    resources = _validate_resources(proposal, request.state)
    _validate_consequences(proposal)
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


def _validate_consequences(proposal: GmClassifierProposal) -> None:
    for consequence in proposal.consequences:
        if consequence.type == GmConsequenceType.ADD_COMPLICATION and str(consequence.value) not in ALLOWED_COMPLICATIONS:
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
    player_message: str = Field(default="", max_length=800)
    normalized_intent: str = Field(default="", max_length=500)
    reason: str = Field(default="", max_length=1000)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


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
