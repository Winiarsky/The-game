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

from dnd_board_game.actors import Actor
from dnd_board_game.combat import SceneAbilityCheck, scene_flag
from dnd_board_game.exploration import (
    CheckAggregation,
    CheckParticipants,
    ConsequenceTarget,
    CraftingComponentSelection,
    CraftingSourceKind,
    CraftingDraft,
    CraftingPlan,
    CraftingPolicy,
    CraftingValidationError,
    ExplorationChallenge,
    ExplorationChallengeOption,
    ExplorationMechanicId,
    ExplorationObservation,
    ExplorationResource,
    ExplorationSituationalModifier,
    ExplorationSituationalModifierSource,
    ExplorationState,
    ExplorationZone,
    FixtureOperation,
    ImprovisedToolUse,
    LlmChallengePolicy,
    LlmContext,
    LlmGuidanceFactKind,
    MECHANIC_TOOLS,
    available_challenge_options,
    interaction_goal,
    effective_narrative_style,
    matched_method_rules,
    build_crafting_source_registry,
    challenge_state_for,
    infer_mechanic_id,
    mechanic_payload_for_option,
    plan_fixture_action,
    validate_mechanic_selection,
    validate_source_property_query,
    visible_exploration_points,
    validate_crafting_draft,
    validate_policy_exploration_effect,
)
from dnd_board_game.hardware import LedColor
from dnd_board_game.rules import RollMode
from dnd_board_game.actions import PlayerIntentHint

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
    WORLD_ACTION = "world_action"
    NEEDS_CLARIFICATION = "needs_clarification"
    UNSUPPORTED = "unsupported"
    PLAYER_QUESTION = "player_question"


class GmConversationResponseKind(StrEnum):
    OBSERVATION = "observation"
    CLARIFICATION = "clarification"
    GENTLE_HINT = "gentle_hint"
    STRONG_HINT = "strong_hint"
    REQUIRES_CHECK = "requires_check"
    IMPOSSIBLE = "impossible"


class GmActionFlow(StrEnum):
    CHALLENGE_ATTEMPT = "challenge_attempt"
    WORLD_ACTION = "world_action"
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
    CREATE_TEMPORARY_ITEM = "create_temporary_item"


class PreparationEffectDuration(StrEnum):
    NEXT_ATTEMPT = "next_attempt"


CORE_LLM_RULES = load_llm_core_rules()
CORE_DND_5E_ABILITIES = frozenset(CORE_LLM_RULES.abilities)
CORE_DND_5E_SKILLS = frozenset(CORE_LLM_RULES.skills)
MAX_SITUATIONAL_MODIFIERS = 3


class GmConsequence(BaseModel):
    model_config = ConfigDict(extra="ignore")

    trigger: GmConsequenceTrigger
    type: GmConsequenceType
    value: str | int | bool | None = None


class GmCraftingComponent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    source_id: str = Field(max_length=200)
    quantity: int = Field(default=1, ge=1)

    @field_validator("source_id")
    @classmethod
    def _source_id_must_not_be_empty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("source_id cannot be empty")
        return normalized


class GmCraftingDraft(BaseModel):
    model_config = ConfigDict(extra="ignore")

    label: str = Field(max_length=120)
    description: str = Field(max_length=800)
    purpose_id: str = Field(max_length=80)
    components: tuple[GmCraftingComponent, ...] = ()
    auto_select_missing_components: bool = True

    @field_validator("label", "description", "purpose_id")
    @classmethod
    def _text_must_not_be_empty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("field cannot be empty")
        return normalized

    def as_domain(self) -> CraftingDraft:
        return CraftingDraft(
            label=self.label,
            description=self.description,
            purpose_id=self.purpose_id,
            components=tuple(
                CraftingComponentSelection(component.source_id, component.quantity)
                for component in self.components
            ),
            auto_select_missing_components=self.auto_select_missing_components,
        )


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
    temporary_item_template_id: str | None = Field(default=None, max_length=80)
    source_materials: tuple[str, ...] = ()
    crafting_draft: GmCraftingDraft | None = None

    @field_validator("target_tags", "source_materials")
    @classmethod
    def _target_tags_must_be_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(tag.strip().lower() for tag in value if tag.strip()))


class GmSituationalModifier(BaseModel):
    model_config = ConfigDict(extra="ignore")

    label: str = Field(max_length=120)
    modifier: int = Field(default=0, ge=-2, le=2)
    source: ExplorationSituationalModifierSource
    reason: str = Field(max_length=400)
    roll_mode: RollMode = RollMode.NORMAL

    @field_validator("label", "reason")
    @classmethod
    def _text_must_not_be_empty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("field cannot be empty")
        return normalized

    def as_domain(self) -> ExplorationSituationalModifier:
        return ExplorationSituationalModifier(
            label=self.label,
            modifier=self.modifier,
            source=self.source,
            reason=self.reason,
            roll_mode=self.roll_mode,
        )


class GmImprovisedToolUse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    label: str = Field(max_length=120)
    source: ExplorationSituationalModifierSource
    source_detail: str = Field(max_length=200)
    source_id: str | None = Field(default=None, max_length=240)
    effect_modifier: int = Field(default=1, ge=-2, le=2)
    risk: str = Field(default="", max_length=200)
    reason: str = Field(max_length=500)

    @field_validator("label", "source_detail", "reason")
    @classmethod
    def _text_must_not_be_empty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("field cannot be empty")
        return normalized

    def as_domain(self) -> ImprovisedToolUse:
        return ImprovisedToolUse(
            label=self.label,
            source=self.source,
            source_detail=self.source_detail,
            source_id=self.source_id,
            effect_modifier=self.effect_modifier,
            risk=self.risk,
            reason=self.reason,
        )


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
    selected_mechanic: ExplorationMechanicId | None = None
    roll_mode: RollMode = RollMode.NORMAL
    situational_modifiers: tuple[GmSituationalModifier, ...] = ()
    improvised_tool: GmImprovisedToolUse | None = None
    preparation_effect: GmPreparationEffect | None = None
    requires_roll_now: bool = True
    check_participants: CheckParticipants | None = None
    check_aggregation: CheckAggregation | None = None
    consequence_targets: tuple[ConsequenceTarget, ...] = ()
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
    grounded_fact_ids: tuple[str, ...] = ()
    hint_level: int = 0

    def as_payload(self) -> dict[str, object]:
        return {
            "role": self.role,
            "content": self.content,
            "outcome": self.outcome,
            "grounded_fact_ids": list(self.grounded_fact_ids),
            "hint_level": self.hint_level,
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
    actors: tuple[Actor, ...] = ()
    crafting_policy: CraftingPolicy = CraftingPolicy()
    player_intent_hint: PlayerIntentHint | None = None
    explicit_player_intent_hint: PlayerIntentHint | None = None
    observations: tuple[ExplorationObservation, ...] = ()
    referenced_crafting_source_ids: tuple[str, ...] = ()
    selected_use_source_id: str | None = None
    selected_fixture_source_id: str | None = None
    selected_fixture_operation: FixtureOperation | None = None
    selected_goal_id: str | None = None
    selected_flow_transition_id: str | None = None
    selected_flow_route_kind: str | None = None
    selected_flow_option_id: str | None = None
    selected_flow_observation_ids: tuple[str, ...] = ()
    selected_check_participants: CheckParticipants | None = None
    selected_participant_actor_ids: tuple[str, ...] = ()
    conversation_only: bool = False

    def to_prompt_payload(self) -> dict[str, Any]:
        challenge_state = challenge_state_for(self.state, self.challenge.id)
        policy = self.challenge.llm_policy
        uses_progress = not bool(
            self.challenge.completion_all_flags
            or self.challenge.completion_any_flags
        )
        policy_payload = policy.as_payload()
        if not uses_progress:
            policy_payload["progress_on_success_range"] = [0, 0]
            policy_payload["progress_on_failure_range"] = [0, 0]
        resources = [
            _resource_payload(resource)
            for resource in self.state.resources
            if resource.id in self.state.inventory_resource_ids
        ]
        resources.extend(
            {
                **_resource_payload(item.as_resource()),
                "temporary": True,
                "uses_remaining": item.uses_remaining,
                "risk": item.risk,
                "source_materials": list(item.source_materials),
            }
            for item in self.state.temporary_items
            if item.available
        )
        crafting_registry = build_crafting_source_registry(self.state, self.actors)
        referenced_sources = tuple(
            source
            for source_id in self.referenced_crafting_source_ids
            for source in (crafting_registry.source_by_id(source_id),)
            if source is not None and source.usable
        )
        conversation_knowledge = _conversation_knowledge(self, crafting_registry)
        selected_goal = interaction_goal(
            self.challenge.goals,
            self.selected_goal_id,
            self.state.flags,
        )
        method_rules = matched_method_rules(
            self.challenge,
            self.player_action,
            self.selected_goal_id,
        )
        narrative_style = effective_narrative_style(
            self.challenge.narrative_style,
            selected_goal,
        )
        selected_flow_option = next(
            (
                option
                for option in self.challenge.options
                if option.id == self.selected_flow_option_id
            ),
            None,
        )
        selected_participant_ids = set(self.selected_participant_actor_ids)
        selected_participants = [
            {
                "actor_id": str(actor.id),
                "actor_name": actor.name,
                "role": (
                    "group_member"
                    if selected_goal is not None
                    and (
                        self.selected_check_participants
                        or selected_goal.check_participants
                    )
                    == CheckParticipants.WHOLE_PARTY
                    else "lead"
                    if self.selected_participant_actor_ids
                    and str(actor.id) == self.selected_participant_actor_ids[0]
                    else "helper"
                ),
            }
            for actor in self.actors
            if str(actor.id) in selected_participant_ids
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
                **(
                    {
                        "progress_required": self.challenge.progress_required,
                        "current_progress": challenge_state.current_progress,
                    }
                    if uses_progress
                    else {}
                ),
                "uses_progress": uses_progress,
                "completion_all_flags": list(self.challenge.completion_all_flags),
                "completion_any_flags": list(self.challenge.completion_any_flags),
                "completed": challenge_state.completed,
                "noise": challenge_state.noise,
                "complications": list(challenge_state.complications),
                "context": self.challenge.llm_context.as_payload(),
                "llm_policy": policy_payload,
                "selected_goal": selected_goal.as_payload() if selected_goal is not None else None,
                "selected_flow_route": (
                    {
                        "transition_id": self.selected_flow_transition_id,
                        "route_kind": self.selected_flow_route_kind,
                        "option_id": selected_flow_option.id,
                        "mechanics_owned_by_runtime": True,
                        "ability": selected_flow_option.ability_check.ability,
                        "skill": selected_flow_option.ability_check.skill,
                        "tool": selected_flow_option.ability_check.tool,
                        "dc": selected_flow_option.ability_check.dc,
                    }
                    if self.selected_flow_transition_id is not None
                    and selected_flow_option is not None
                    else None
                ),
                "selected_check_participants": (
                    self.selected_check_participants.value
                    if self.selected_check_participants is not None
                    else None
                ),
                "selected_participants": selected_participants,
                "matched_method_rules": [rule.as_payload() for rule in method_rules],
                "effective_narrative_style": narrative_style.as_payload(),
                "available_options": [
                    {
                        "id": option.id,
                        "label": option.label,
                        "ability": option.ability_check.ability,
                        "skill": option.ability_check.skill,
                        "tool": option.ability_check.tool,
                        "dc": option.ability_check.dc,
                        "progress_on_success": option.progress_on_success if uses_progress else 0,
                        "progress_on_failure": option.progress_on_failure if uses_progress else 0,
                        "tags": list(option.tags),
                        "requirements": _option_requirements_payload(option),
                        "mechanic": mechanic_payload_for_option(option),
                    }
                    for option in available_challenge_options(self.state, self.challenge)
                ],
            },
            "interaction_object": {
                "id": self.challenge.id,
                "name": self.challenge.name,
                "context": self.challenge.llm_context.as_payload(),
                "available_options": [
                    {
                        "id": option.id,
                        "label": option.label,
                        "description": option.description,
                        "tags": list(option.tags),
                        "requirements": _option_requirements_payload(option),
                    }
                    for option in available_challenge_options(self.state, self.challenge)
                ],
            },
            "party_resources": resources,
            "party_actors": [_actor_grounding_payload(actor) for actor in self.actors],
            "dynamic_state": _dynamic_state_payload(self.state, self.challenge),
            "situational_modifier_policy": {
                "max_count": MAX_SITUATIONAL_MODIFIERS,
                "modifier_range": [-2, 2],
                "roll_modes": [mode.value for mode in RollMode],
                "sources": [source.value for source in ExplorationSituationalModifierSource],
                "requires_source_and_reason": True,
            },
            "improvised_tool_policy": {
                "mechanic_id": ExplorationMechanicId.IMPROVISED_TOOL_CHECK.value,
                "effect_modifier_range": [-2, 2],
                "requires_source_detail": True,
                "requires_gm_approval": True,
                "does_not_create_inventory_item": True,
                "sources": [source.value for source in ExplorationSituationalModifierSource],
            },
            "crafting": {
                "available_property_ids": list(self.crafting_policy.property_ids),
                "purposes": [
                    {
                        "id": purpose.id,
                        "label": purpose.label,
                        "requirements": [
                            {
                                "properties": list(requirement.properties),
                                "minimum_quantity": requirement.minimum_quantity,
                            }
                            for requirement in purpose.requirements
                        ],
                        "bonus_tags": list(purpose.bonus_tags),
                    }
                    for purpose in self.crafting_policy.purposes
                ],
                "available_sources": [
                    {
                        "id": source.id,
                        "kind": source.kind.value,
                        "label": source.label,
                        "properties": list(source.properties),
                        "quantity": source.quantity,
                        "condition": source.condition,
                        "owner_actor_id": source.owner_actor_id,
                        "portable": source.portable,
                        "detachable": source.detachable,
                        "requires_detachment": (
                            source.kind.value == "scene_fixture"
                            and not source.portable
                            and source.detachable
                        ),
                    }
                    for source in crafting_registry.available_sources
                ],
                "rules": {
                    "requires_confirmation": True,
                    "requires_build_roll_by_default": False,
                    "engine_owns_time_cost_modifier_uses_and_risk": True,
                    "llm_selects_only_purpose_and_grounded_components": True,
                    "detachable_fixtures_can_be_acquired_during_crafting": True,
                },
            },
            "player_grounded_sources": [
                {
                    "id": source.id,
                    "reference_id": source.reference_id,
                    "kind": source.kind.value,
                    "label": source.label,
                    "properties": list(source.properties),
                    "quantity": source.quantity,
                    "condition": source.condition,
                }
                for source in referenced_sources
            ],
            "selected_use_source_id": self.selected_use_source_id,
            "selected_fixture_action": (
                {
                    "source_id": self.selected_fixture_source_id,
                    "operation": self.selected_fixture_operation.value,
                }
                if self.selected_fixture_source_id is not None
                and self.selected_fixture_operation is not None
                else None
            ),
            "fixture_action_policies": [
                {
                    "source_id": f"zone:{self.zone.id}:fixture:{fixture.id}",
                    "fixture_id": fixture.id,
                    "label": fixture.name,
                    "condition": next(
                        (
                            runtime.condition
                            for runtime in self.state.fixture_states
                            if runtime.zone_id == self.zone.id and runtime.fixture_id == fixture.id
                        ),
                        fixture.condition,
                    ),
                    "available": not any(
                        runtime.zone_id == self.zone.id
                        and runtime.fixture_id == fixture.id
                        and (runtime.unavailable or runtime.detached or runtime.destroyed)
                        for runtime in self.state.fixture_states
                    ),
                    "operations": [
                        {
                            "operation": item.operation.value,
                            "allowed_conditions": list(item.allowed_conditions),
                            "result_condition": item.result_condition,
                        }
                        for item in fixture.action_policies
                    ],
                }
                for fixture in self.zone.fixtures
                if fixture.action_policies
            ],
            "conversation_knowledge": conversation_knowledge,
            "available_observations": [
                observation.as_prompt_payload(self.state.flags)
                for observation in _active_observations(self)
            ],
            "conversation_policy": {
                "next_hint_level": _allowed_hint_level(self),
                "hint_levels": {
                    "1": "subtelne naprowadzenie bez podania rozwiązania",
                    "2": "wskazanie użytecznej właściwości, ryzyka albo kierunku",
                    "3": "konkretna propozycja rozwiązania na wyraźną prośbę",
                },
                "visible_facts_can_be_answered_without_check": True,
                "hidden_facts_must_not_be_revealed": True,
                "uncertain_observations_should_use_requires_check": True,
            },
            "allowed_abilities": sorted(CORE_DND_5E_ABILITIES),
            "allowed_skills": sorted(_allowed_skills(policy)),
            "allowed_tags": sorted(policy.allowed_approach_tags),
            "allowed_consequence_types": list(policy.allowed_consequence_types),
            "allowed_complications": sorted(policy.allowed_complications),
            "allowed_mechanics": [tool.as_payload() for tool in MECHANIC_TOOLS.values()],
            "declaration_thread": [entry.as_payload() for entry in self.declaration_thread],
            "active_preparation_effects": [effect.model_dump(mode="json") for effect in self.active_preparation_effects],
            "player_intent_hint": self.player_intent_hint.value if self.player_intent_hint is not None else None,
            "explicit_player_intent_hint": (
                self.explicit_player_intent_hint.value
                if self.explicit_player_intent_hint is not None
                else None
            ),
            "conversation_only": self.conversation_only,
            "player_action": self.player_action,
        }


@dataclass(frozen=True, slots=True)
class GmValidatedProposal:
    proposal: GmClassifierProposal
    challenge: ExplorationChallenge
    resources: tuple[ExplorationResource, ...]
    required_actor_item_ids: tuple[str, ...] = ()
    crafting_plan: CraftingPlan | None = None


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
    actors: tuple[Actor, ...] = (),
    crafting_policy: CraftingPolicy = CraftingPolicy(),
    player_intent_hint: PlayerIntentHint | None = None,
    explicit_player_intent_hint: PlayerIntentHint | None = None,
    observations: tuple[ExplorationObservation, ...] = (),
    referenced_crafting_source_ids: tuple[str, ...] = (),
    selected_use_source_id: str | None = None,
    selected_fixture_source_id: str | None = None,
    selected_fixture_operation: FixtureOperation | None = None,
    selected_goal_id: str | None = None,
    selected_flow_transition_id: str | None = None,
    selected_flow_route_kind: str | None = None,
    selected_flow_option_id: str | None = None,
    selected_flow_observation_ids: tuple[str, ...] = (),
    selected_check_participants: CheckParticipants | None = None,
    selected_participant_actor_ids: tuple[str, ...] = (),
    conversation_only: bool = False,
) -> GmClassifierRequest:
    zone = next(zone for zone in state.zones if zone.id == state.party_position.zone_id)
    challenge = next((challenge for challenge in state.challenges if challenge.zone_id == zone.id), None)
    if challenge is None:
        raise GmProposalValidationError(f"Strefa {zone.name} nie ma aktywnego wyzwania eksploracyjnego.")
    return GmClassifierRequest(
        scenario_id=scenario_id,
        scenario_name=scenario_name,
        scenario_context=scenario_context,
        zone=zone,
        challenge=challenge,
        state=state,
        player_action=player_action,
        declaration_thread=declaration_thread,
        active_preparation_effects=active_preparation_effects,
        actors=actors,
        crafting_policy=crafting_policy,
        player_intent_hint=player_intent_hint,
        explicit_player_intent_hint=explicit_player_intent_hint,
        observations=observations,
        referenced_crafting_source_ids=referenced_crafting_source_ids,
        selected_use_source_id=selected_use_source_id,
        selected_fixture_source_id=selected_fixture_source_id,
        selected_fixture_operation=selected_fixture_operation,
        selected_goal_id=selected_goal_id,
        selected_flow_transition_id=selected_flow_transition_id,
        selected_flow_route_kind=selected_flow_route_kind,
        selected_flow_option_id=selected_flow_option_id,
        selected_flow_observation_ids=selected_flow_observation_ids,
        selected_check_participants=selected_check_participants,
        selected_participant_actor_ids=selected_participant_actor_ids,
        conversation_only=conversation_only,
    )


def validate_gm_declaration_analysis(
    analysis: GmDeclarationAnalysis,
    request: GmClassifierRequest,
) -> GmDeclarationAnalysis:
    if analysis.source_query is not None:
        try:
            validate_source_property_query(
                required_properties=analysis.source_query.required_properties,
                preferred_properties=analysis.source_query.preferred_properties,
                allowed_property_ids=request.crafting_policy.property_ids,
            )
        except ValueError as exc:
            raise GmProposalValidationError(str(exc)) from exc
    analysis = _normalize_question_response(analysis, request)
    analysis = _normalize_explicit_build_analysis(analysis, request)
    _validate_player_intent_hint(analysis, request)
    if analysis.analysis_type == GmDeclarationAnalysisType.PLAYER_QUESTION:
        _validate_conversation_response(analysis, request)
        return analysis
    if analysis.analysis_type == GmDeclarationAnalysisType.WORLD_ACTION:
        _validate_world_action(analysis, request)
        return analysis
    if analysis.action_flow in {
        GmActionFlow.UNSUPPORTED,
        GmActionFlow.NEEDS_CLARIFICATION,
    }:
        return analysis
    if analysis.missing_requirements:
        raise GmProposalValidationError("; ".join(analysis.missing_requirements))
    unsupported_facts = tuple(
        fact for fact in analysis.assumed_new_facts
        if not _constructed_fact_is_grounded(fact, request)
    )
    if unsupported_facts:
        raise GmProposalValidationError(
            "Deklaracja zakłada nowe fakty spoza sceny: " + ", ".join(unsupported_facts)
        )
    unknown_resources = tuple(
        resource for resource in _unknown_declared_resources(analysis, request)
        if not _constructed_fact_is_grounded(resource, request)
    )
    if unknown_resources:
        raise GmProposalValidationError("Drużyna nie ma zadeklarowanych zasobów: " + ", ".join(unknown_resources))
    return analysis


def _validate_world_action(
    analysis: GmDeclarationAnalysis,
    request: GmClassifierRequest,
) -> None:
    if analysis.action_flow != GmActionFlow.WORLD_ACTION:
        raise GmProposalValidationError("Działanie w świecie wymaga action_flow=world_action.")
    if not analysis.player_message.strip():
        raise GmProposalValidationError("Działanie w świecie wymaga narracyjnej odpowiedzi MG.")
    if analysis.missing_requirements:
        raise GmProposalValidationError("; ".join(analysis.missing_requirements))
    unsupported_facts = tuple(
        fact for fact in analysis.assumed_new_facts
        if not _constructed_fact_is_grounded(fact, request)
    )
    if unsupported_facts:
        raise GmProposalValidationError(
            "Deklaracja zakłada nowe fakty spoza sceny: " + ", ".join(unsupported_facts)
        )
    unknown_resources = tuple(
        resource for resource in _unknown_declared_resources(analysis, request)
        if not _constructed_fact_is_grounded(resource, request)
    )
    if unknown_resources:
        raise GmProposalValidationError(
            "Drużyna nie ma zadeklarowanych zasobów: " + ", ".join(unknown_resources)
        )
    allowed_types = tuple(
        effect_type
        for effect_type in ("add_noise", "add_complication")
        if effect_type in request.challenge.llm_policy.allowed_consequence_types
    )
    seen_effect_types: set[str] = set()
    for index, effect in enumerate(analysis.immediate_effects):
        if effect.type not in allowed_types:
            raise GmProposalValidationError(
                f"Natychmiastowa konsekwencja {effect.type} nie jest dozwolona w tym wyzwaniu."
            )
        if effect.type in seen_effect_types:
            raise GmProposalValidationError(
                f"Natychmiastowa konsekwencja {effect.type} może wystąpić tylko raz."
            )
        seen_effect_types.add(effect.type)
        payload = effect.as_effect_payload()
        try:
            validate_policy_exploration_effect(
                payload,
                request.state,
                allowed_effect_types=allowed_types,
                field=f"world_action.immediate_effects[{index}]",
            )
        except ValueError as exc:
            raise GmProposalValidationError(str(exc)) from exc
        challenge_id = str(effect.parameters.get("challenge_id", "")).strip()
        if challenge_id != request.challenge.id:
            raise GmProposalValidationError(
                "Natychmiastowa konsekwencja może zmieniać tylko aktywne wyzwanie."
            )
        if effect.type == "add_noise":
            noise = effect.parameters.get("value")
            if not isinstance(noise, int) or isinstance(noise, bool) or not 0 <= noise <= 3:
                raise GmProposalValidationError(
                    "Natychmiastowy hałas musi być liczbą całkowitą od 0 do 3."
                )
        if (
            effect.type == "add_complication"
            and str(effect.parameters.get("value", ""))
            not in request.challenge.llm_policy.allowed_complications
        ):
            raise GmProposalValidationError("Niedozwolona natychmiastowa komplikacja sceny.")


def _normalize_explicit_build_analysis(
    analysis: GmDeclarationAnalysis,
    request: GmClassifierRequest,
) -> GmDeclarationAnalysis:
    if (
        request.explicit_player_intent_hint == PlayerIntentHint.BUILD
        and analysis.analysis_type == GmDeclarationAnalysisType.PLAUSIBLE
        and analysis.action_flow != GmActionFlow.PREPARATION
    ):
        return analysis.model_copy(update={"action_flow": GmActionFlow.PREPARATION})
    return analysis


def _normalize_question_response(
    analysis: GmDeclarationAnalysis,
    request: GmClassifierRequest,
) -> GmDeclarationAnalysis:
    """Repair harmless LLM disagreement between response kind and grounded hint facts."""

    if (
        analysis.analysis_type != GmDeclarationAnalysisType.PLAYER_QUESTION
        or analysis.response_kind is None
    ):
        return analysis
    knowledge = _conversation_knowledge(
        request,
        build_crafting_source_registry(request.state, request.actors),
    )
    facts_by_id = {fact["id"]: fact for fact in knowledge["facts"]}
    known_facts = tuple(
        facts_by_id[fact_id]
        for fact_id in analysis.grounded_fact_ids
        if fact_id in facts_by_id
    )
    required_level = max(
        (int(fact["minimum_hint_level"]) for fact in known_facts),
        default=0,
    )
    hint_kinds = {
        GmConversationResponseKind.GENTLE_HINT,
        GmConversationResponseKind.STRONG_HINT,
    }
    normalizable_kinds = {
        GmConversationResponseKind.OBSERVATION,
        GmConversationResponseKind.CLARIFICATION,
        *hint_kinds,
    }
    if analysis.response_kind not in normalizable_kinds:
        return analysis
    declares_hint = analysis.response_kind in hint_kinds or analysis.hint_level > 0 or required_level > 0
    if not declares_hint:
        return analysis
    normalized_level = max(1, analysis.hint_level, required_level)
    allowed_level = _allowed_hint_level(request)
    if normalized_level > allowed_level:
        if analysis.hint_level > allowed_level:
            return analysis
        return _downgrade_question_hint(analysis, request, knowledge, allowed_level)
    response_kind = analysis.response_kind
    if response_kind not in hint_kinds:
        response_kind = GmConversationResponseKind.GENTLE_HINT
    return analysis.model_copy(
        update={
            "response_kind": response_kind,
            "hint_level": normalized_level,
        }
    )


def _downgrade_question_hint(
    analysis: GmDeclarationAnalysis,
    request: GmClassifierRequest,
    knowledge: dict[str, object],
    allowed_level: int,
) -> GmDeclarationAnalysis:
    """Replace an over-informative answer with the closest safe content fact."""

    action_stems = _hint_matching_stems(request.player_action)
    candidates = tuple(
        fact
        for fact in knowledge["facts"]
        if fact["kind"] == "gm_hint"
        and bool(fact.get("revealed", True))
        and int(fact["minimum_hint_level"]) <= allowed_level
        and action_stems.intersection(_hint_matching_stems(str(fact["text"])))
    )
    if candidates:
        fact = candidates[0]
        fact_text = str(fact["text"]).strip()
        message = (
            f"{fact_text[:1].upper()}{fact_text[1:]} wygląda na możliwe podejście. "
            "Jeśli chcecie działać, zadeklarujcie dokładnie kto i w jaki sposób to robi."
        )
        return analysis.model_copy(
            update={
                "player_message": message,
                "response_kind": GmConversationResponseKind.GENTLE_HINT,
                "grounded_fact_ids": (str(fact["id"]),),
                "hint_level": max(1, int(fact["minimum_hint_level"])),
                "requires_check": False,
                "suggested_followup": "",
                "observation_id": None,
            }
        )
    return analysis.model_copy(
        update={
            "player_message": (
                "To pytanie wymagałoby mocniejszej podpowiedzi, niż wynika z dotychczasowej rozmowy. "
                "Doprecyzujcie, który element sceny chcecie wykorzystać albo co dokładnie sprawdzacie."
            ),
            "response_kind": GmConversationResponseKind.CLARIFICATION,
            "grounded_fact_ids": (),
            "hint_level": 0,
            "requires_check": False,
            "suggested_followup": "",
            "observation_id": None,
        }
    )


def _hint_matching_stems(value: str) -> frozenset[str]:
    return frozenset(
        token[:4]
        for token in _normalize_fact_token(value).split()
        if len(token) >= 4
    )


def _validate_player_intent_hint(
    analysis: GmDeclarationAnalysis,
    request: GmClassifierRequest,
) -> None:
    hint = request.player_intent_hint
    if hint is None or analysis.analysis_type in {
        GmDeclarationAnalysisType.NEEDS_CLARIFICATION,
        GmDeclarationAnalysisType.UNSUPPORTED,
    }:
        return
    if hint == PlayerIntentHint.QUESTION:
        if analysis.analysis_type != GmDeclarationAnalysisType.PLAYER_QUESTION:
            raise GmProposalValidationError(
                "Jawna komenda rozmowy musi zostać obsłużona jako odpowiedź MG, bez uruchamiania działania."
            )
        return
    if hint in {PlayerIntentHint.BUILD, PlayerIntentHint.USE, PlayerIntentHint.ACTION}:
        if analysis.analysis_type == GmDeclarationAnalysisType.PLAYER_QUESTION:
            if analysis.requires_check and analysis.observation_id is not None:
                return
            raise GmProposalValidationError(
                "Jawna komenda działania nie może zostać obsłużona wyłącznie jako pytanie."
            )
    if (
        request.explicit_player_intent_hint == PlayerIntentHint.USE
        and analysis.analysis_type == GmDeclarationAnalysisType.PLAUSIBLE
    ):
        if not analysis.use_source_id:
            raise GmProposalValidationError("Komenda /użyj wymaga wskazania istniejącego źródła.")
        if analysis.use_source_id not in request.referenced_crafting_source_ids:
            raise GmProposalValidationError(
                "Komenda /użyj wskazuje źródło, którego nie dopasowano do deklaracji gracza."
            )
    if (
        request.explicit_player_intent_hint == PlayerIntentHint.ACTION
        and analysis.analysis_type == GmDeclarationAnalysisType.PLAUSIBLE
        and (analysis.action_target_source_id is not None or analysis.fixture_operation is not None)
    ):
        if analysis.action_target_source_id is None or analysis.fixture_operation is None:
            raise GmProposalValidationError(
                "Operacja na fixture wymaga action_target_source_id oraz fixture_operation."
            )
        if analysis.action_target_source_id not in request.referenced_crafting_source_ids:
            raise GmProposalValidationError(
                "Komenda /akcja wskazuje fixture, którego nie dopasowano do deklaracji gracza."
            )
        try:
            plan_fixture_action(
                request.state,
                source_id=analysis.action_target_source_id,
                operation=analysis.fixture_operation,
            )
        except ValueError as exc:
            raise GmProposalValidationError(str(exc)) from exc


def validate_gm_classifier_proposal(
    proposal: GmClassifierProposal,
    request: GmClassifierRequest,
) -> GmValidatedProposal:
    if (
        request.selected_goal_id is not None
        and interaction_goal(
            request.challenge.goals,
            request.selected_goal_id,
            request.state.flags,
        )
        is None
    ):
        raise GmProposalValidationError(
            f"Selected interaction goal is unavailable: {request.selected_goal_id}."
        )
    proposal = _ground_explicit_build_proposal(proposal, request)
    proposal = _ground_temporary_item_preparation(proposal, request)
    proposal = _ground_fixture_action_proposal(proposal, request)
    proposal = _apply_authored_method_rules(proposal, request)
    proposal = _apply_authored_participant_model(proposal, request)
    proposal = _ground_selected_flow_mechanics(proposal, request)
    proposal = _drop_noop_situational_modifiers(proposal)
    policy = request.challenge.llm_policy
    if request.selected_flow_option_id is None:
        proposal = _ground_proposal_dc(proposal, policy)
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
    if request.explicit_player_intent_hint == PlayerIntentHint.BUILD:
        effect = proposal.preparation_effect
        if (
            effect is None
            or effect.type != PreparationEffectType.CREATE_TEMPORARY_ITEM
            or effect.crafting_draft is None
        ):
            raise GmProposalValidationError(
                "Komenda /zbuduj wymaga propozycji dynamicznej konstrukcji z dostępnych komponentów."
            )
    crafting_plan = None
    if proposal.preparation_effect is not None:
        crafting_plan = _validate_preparation_effect(proposal.preparation_effect, policy, request)
        if (
            proposal.preparation_effect.type == PreparationEffectType.CREATE_TEMPORARY_ITEM
            and proposal.action_flow != GmActionFlow.PREPARATION
        ):
            raise GmProposalValidationError(
                "Przedmiot tymczasowy można utworzyć tylko jako osobne przygotowanie; "
                "złożenie i natychmiastowe użycie jest improvised_tool_check."
            )
    if proposal.action_flow == GmActionFlow.PREPARATION:
        if proposal.roll_mode != RollMode.NORMAL or proposal.situational_modifiers:
            raise GmProposalValidationError("Przygotowanie bez rzutu nie może mieć modyfikatorów sytuacyjnych obecnego rzutu.")
        if proposal.preparation_effect is None:
            raise GmProposalValidationError("Przygotowanie wymaga preparation_effect.")
        if proposal.requires_roll_now:
            raise GmProposalValidationError("Przygotowanie bez próby nie może wymagać rzutu teraz.")
        resources, actor_item_ids = _validate_resources(proposal, request)
        _validate_fact_grounding(proposal, request)
        return GmValidatedProposal(
            proposal=proposal,
            challenge=request.challenge,
            resources=resources,
            required_actor_item_ids=actor_item_ids,
            crafting_plan=crafting_plan,
        )
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
    uses_progress = not bool(
        request.challenge.completion_all_flags
        or request.challenge.completion_any_flags
    )
    if not uses_progress:
        proposal = proposal.model_copy(
            update={
                "progress_on_success": 0,
                "progress_on_failure": 0,
            }
        )
    if request.selected_flow_option_id is None:
        _validate_difficulty_tier(proposal, policy)
    if not policy.dc_min <= proposal.dc <= policy.dc_max:
        raise GmProposalValidationError(f"ST {proposal.dc} jest poza zakresem policy: {policy.dc_min}-{policy.dc_max}.")
    if uses_progress and not policy.progress_success_min <= proposal.progress_on_success <= policy.progress_success_max:
        raise GmProposalValidationError(
            "Postęp przy sukcesie jest poza zakresem policy: "
            f"{policy.progress_success_min}-{policy.progress_success_max}."
        )
    if uses_progress and not policy.progress_failure_min <= proposal.progress_on_failure <= policy.progress_failure_max:
        raise GmProposalValidationError(
            "Postęp przy porażce jest poza zakresem policy: "
            f"{policy.progress_failure_min}-{policy.progress_failure_max}."
        )
    unknown_tags = set(proposal.approach_tags) - set(policy.allowed_approach_tags)
    if unknown_tags:
        raise GmProposalValidationError(f"Nieobsługiwane tagi podejścia: {', '.join(sorted(unknown_tags))}.")
    if proposal.preparation_effect is not None and not set(proposal.preparation_effect.target_tags).intersection(proposal.approach_tags):
        raise GmProposalValidationError("Efekt przygotowania nie pasuje tagami do próby challenge.")
    if (
        proposal.selected_mechanic is not None
        and proposal.selected_mechanic != ExplorationMechanicId.PREPARATION_EFFECT
        and proposal.requires_roll_now
        and (proposal.check_participants is None or proposal.check_aggregation is None)
    ):
        raise GmProposalValidationError("selected_mechanic dla rzutu wymaga check_participants i check_aggregation.")
    mechanic_id = _proposal_mechanic_id(proposal)
    _validate_improvised_tool(proposal, mechanic_id, request)
    try:
        validate_mechanic_selection(
            mechanic_id,
            participants=proposal.check_participants,
            aggregation=proposal.check_aggregation,
        )
    except ValueError as exc:
        raise GmProposalValidationError(str(exc)) from exc
    _validate_context_constraints(proposal, request)
    if len(proposal.used_resource_ids) > policy.max_resources_per_attempt:
        raise GmProposalValidationError(
            "Ta polityka wyzwania pozwala użyć maksymalnie "
            f"{policy.max_resources_per_attempt} zasobów naraz."
        )
    resources, actor_item_ids = _validate_resources(proposal, request)
    _validate_fact_grounding(proposal, request)
    _validate_situational_modifiers(proposal)
    _validate_consequences(proposal, policy)
    _validate_narration_consistency(proposal)
    return GmValidatedProposal(
        proposal=proposal,
        challenge=request.challenge,
        resources=resources,
        required_actor_item_ids=actor_item_ids,
    )


def _apply_authored_participant_model(
    proposal: GmClassifierProposal,
    request: GmClassifierRequest,
) -> GmClassifierProposal:
    if (
        proposal.action_flow == GmActionFlow.PREPARATION
        or not proposal.requires_roll_now
        or request.selected_goal_id is None
    ):
        return proposal
    goal = interaction_goal(
        request.challenge.goals,
        request.selected_goal_id,
        request.state.flags,
    )
    if goal is None:
        return proposal
    participants = request.selected_check_participants or goal.check_participants
    aggregation = (
        CheckAggregation.MAJORITY
        if participants == CheckParticipants.WHOLE_PARTY
        else CheckAggregation.LEAD_RESULT
    )
    mechanic = {
        CheckParticipants.SINGLE_ACTOR: ExplorationMechanicId.SINGLE_ACTOR_CHECK,
        CheckParticipants.LEAD_WITH_HELP: ExplorationMechanicId.LEAD_WITH_HELP_CHECK,
        CheckParticipants.WHOLE_PARTY: ExplorationMechanicId.GROUP_CHECK,
    }[participants]
    return proposal.model_copy(
        update={
            "selected_mechanic": mechanic,
            "check_participants": participants,
            "check_aggregation": aggregation,
        }
    )


def _apply_authored_method_rules(
    proposal: GmClassifierProposal,
    request: GmClassifierRequest,
) -> GmClassifierProposal:
    rules = matched_method_rules(
        request.challenge,
        request.player_action,
        request.selected_goal_id,
    )
    if not rules or proposal.action_flow != GmActionFlow.CHALLENGE_ATTEMPT:
        return proposal
    modifiers = list(proposal.situational_modifiers)
    consequences = list(proposal.consequences)
    for rule in rules:
        if rule.modifier:
            normalized_label = rule.label.strip().casefold()
            modifiers = [
                modifier
                for modifier in modifiers
                if modifier.label.strip().casefold() != normalized_label
            ]
            modifiers = modifiers[: MAX_SITUATIONAL_MODIFIERS - 1]
            modifiers.append(
                GmSituationalModifier(
                    label=rule.label,
                    modifier=rule.modifier,
                    source=ExplorationSituationalModifierSource.GM,
                    reason=rule.reason,
                )
            )
        if rule.noise_delta:
            consequences = [
                consequence.model_copy(
                    update={"value": max(0, int(consequence.value) + rule.noise_delta)}
                )
                if consequence.type == GmConsequenceType.ADD_NOISE
                and isinstance(consequence.value, int)
                and not isinstance(consequence.value, bool)
                else consequence
                for consequence in consequences
            ]
    return proposal.model_copy(
        update={
            "situational_modifiers": tuple(modifiers),
            "consequences": tuple(consequences),
        }
    )


def _ground_explicit_build_proposal(
    proposal: GmClassifierProposal,
    request: GmClassifierRequest,
) -> GmClassifierProposal:
    if request.explicit_player_intent_hint != PlayerIntentHint.BUILD:
        return proposal
    effect = proposal.preparation_effect
    if effect is None:
        return proposal

    draft = effect.crafting_draft
    if draft is None:
        requested_tags = set(effect.target_tags or proposal.approach_tags)
        purposes = tuple(
            purpose
            for purpose in request.crafting_policy.purposes
            if requested_tags.intersection(purpose.bonus_tags)
        )
        if len(purposes) == 1:
            purpose = purposes[0]
            label = effect.label.strip() or proposal.approach_label.strip() or purpose.label
            draft = GmCraftingDraft(
                label=label,
                description=proposal.player_narration.strip() or f"Prowizoryczna konstrukcja: {label}.",
                purpose_id=purpose.id,
                components=(),
                auto_select_missing_components=True,
            )
            effect = effect.model_copy(
                update={
                    "type": PreparationEffectType.CREATE_TEMPORARY_ITEM,
                    "target_tags": purpose.bonus_tags,
                    "temporary_item_template_id": None,
                    "source_materials": (),
                    "crafting_draft": draft,
                }
            )
    if draft is None or effect.type != PreparationEffectType.CREATE_TEMPORARY_ITEM:
        return proposal

    purpose = request.crafting_policy.purpose_by_id(draft.purpose_id)
    target_tags = purpose.bonus_tags if purpose is not None else effect.target_tags
    grounded_effect = effect.model_copy(
        update={
            "target_tags": target_tags,
            "temporary_item_template_id": None,
            "source_materials": (),
        }
    )
    return proposal.model_copy(
        update={
            "action_flow": GmActionFlow.PREPARATION,
            "approach_tags": target_tags,
            "ability": None,
            "skill": None,
            "difficulty_tier": None,
            "difficulty_reason": "",
            "dc": None,
            "progress_on_success": None,
            "progress_on_failure": None,
            "used_resource_ids": (),
            "selected_mechanic": ExplorationMechanicId.PREPARATION_EFFECT,
            "roll_mode": RollMode.NORMAL,
            "situational_modifiers": (),
            "improvised_tool": None,
            "preparation_effect": grounded_effect,
            "requires_roll_now": False,
            "check_participants": None,
            "check_aggregation": None,
            "consequence_targets": (),
            "consequences": (),
        }
    )


def _ground_temporary_item_preparation(
    proposal: GmClassifierProposal,
    request: GmClassifierRequest,
) -> GmClassifierProposal:
    effect = proposal.preparation_effect
    if effect is None or effect.type != PreparationEffectType.CREATE_TEMPORARY_ITEM:
        return proposal
    if effect.crafting_draft is not None:
        return proposal
    templates = request.challenge.llm_policy.temporary_item_templates
    inferred_template = not bool(effect.temporary_item_template_id)
    if effect.temporary_item_template_id:
        candidates = tuple(template for template in templates if template.id == effect.temporary_item_template_id)
    else:
        target_tags = set(effect.target_tags)
        candidates = tuple(
            template
            for template in templates
            if (not target_tags or target_tags.intersection(template.bonus_tags))
        )
    if len(candidates) != 1:
        return proposal
    template = candidates[0]
    known_materials = _known_resource_or_material_tokens(request)
    grounded_template_materials = tuple(
        material
        for material in template.allowed_materials
        if _normalize_fact_token(material) in known_materials
    )
    normalized_effect = effect.model_copy(
        update={
            "temporary_item_template_id": template.id,
            "source_materials": (
                grounded_template_materials
                if inferred_template
                else (effect.source_materials or grounded_template_materials)
            ),
        }
    )
    return proposal.model_copy(update={"preparation_effect": normalized_effect})


def _ground_fixture_action_proposal(
    proposal: GmClassifierProposal,
    request: GmClassifierRequest,
) -> GmClassifierProposal:
    if request.selected_fixture_source_id is None or request.selected_fixture_operation is None:
        return proposal
    try:
        plan = plan_fixture_action(
            request.state,
            source_id=request.selected_fixture_source_id,
            operation=request.selected_fixture_operation,
        )
    except ValueError as exc:
        raise GmProposalValidationError(str(exc)) from exc
    dc = request.challenge.llm_policy.dc_for_tier(plan.policy.difficulty_tier)
    if dc is None:
        raise GmProposalValidationError(
            f"Fixture action wskazuje nieznany difficulty_tier: {plan.policy.difficulty_tier}."
        )
    consequences: list[GmConsequence] = []
    if plan.policy.success_noise:
        consequences.append(
            GmConsequence(
                trigger=GmConsequenceTrigger.SUCCESS,
                type=GmConsequenceType.ADD_NOISE,
                value=plan.policy.success_noise,
            )
        )
    if plan.policy.failure_noise:
        consequences.extend(
            GmConsequence(
                trigger=trigger,
                type=GmConsequenceType.ADD_NOISE,
                value=plan.policy.failure_noise,
            )
            for trigger in (
                GmConsequenceTrigger.FAILURE,
                GmConsequenceTrigger.CRITICAL_FAILURE,
            )
        )
    if plan.policy.failure_complication:
        consequences.extend(
            GmConsequence(
                trigger=trigger,
                type=GmConsequenceType.ADD_COMPLICATION,
                value=plan.policy.failure_complication,
            )
            for trigger in (
                GmConsequenceTrigger.FAILURE,
                GmConsequenceTrigger.CRITICAL_FAILURE,
            )
        )
    return proposal.model_copy(
        update={
            "ability": plan.policy.ability,
            "skill": plan.policy.skill,
            "difficulty_tier": plan.policy.difficulty_tier,
            "difficulty_reason": (
                f"Parametry operacji {plan.policy.operation.value} dla {plan.fixture.name} "
                "pochodzą z polityki fixture'a."
            ),
            "dc": dc,
            "progress_on_success": plan.policy.progress_on_success,
            "progress_on_failure": plan.policy.progress_on_failure,
            "consequences": tuple(consequences),
            "requires_roll_now": True,
        }
    )


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
        progress_on_success=(
            proposal.progress_on_success
            if proposal.progress_on_success is not None
            else 1
        ),
        progress_on_failure=(
            proposal.progress_on_failure
            if proposal.progress_on_failure is not None
            else 0
        ),
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
        check_participants=proposal.check_participants,
        check_aggregation=proposal.check_aggregation,
        consequence_targets=proposal.consequence_targets,
        mechanic_id=_proposal_mechanic_id(proposal).value,
        roll_mode=_combined_roll_mode(proposal.roll_mode, tuple(modifier.roll_mode for modifier in proposal.situational_modifiers)),
        situational_modifiers=tuple(modifier.as_domain() for modifier in proposal.situational_modifiers),
        improvised_tool=proposal.improvised_tool.as_domain() if proposal.improvised_tool else None,
        requires_item_ids=validated.required_actor_item_ids,
    )


def _proposal_mechanic_id(proposal: GmClassifierProposal) -> ExplorationMechanicId:
    if proposal.selected_mechanic is not None:
        return proposal.selected_mechanic
    return infer_mechanic_id(
        participants=proposal.check_participants,
        aggregation=proposal.check_aggregation,
        action_flow_is_preparation=proposal.action_flow == GmActionFlow.PREPARATION,
    )


def _validate_resources(
    proposal: GmClassifierProposal,
    request: GmClassifierRequest,
) -> tuple[tuple[ExplorationResource, ...], tuple[str, ...]]:
    state = request.state
    owned = set(state.inventory_resource_ids) | {item.id for item in state.temporary_items if item.available}
    actor_item_ids = {
        item.id
        for actor in request.actors
        for item in actor.inventory
        if item.available and item.quantity > 0
    }
    actor_item_ids_by_source_id = {
        f"actor:{actor.id}:item:{item.id}": item.id
        for actor in request.actors
        for item in actor.inventory
        if item.available and item.quantity > 0
    }
    resources_by_id = {resource.id: resource for resource in state.resources}
    resources_by_id.update({item.id: item.as_resource() for item in state.temporary_items if item.available})
    approach_tags = set(proposal.approach_tags)
    result: list[ExplorationResource] = []
    required_actor_items: list[str] = []
    for declared_resource_id in proposal.used_resource_ids:
        resource_id = actor_item_ids_by_source_id.get(
            declared_resource_id,
            declared_resource_id,
        )
        if resource_id in actor_item_ids:
            required_actor_items.append(resource_id)
            continue
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
    return tuple(result), tuple(required_actor_items)


def _validate_situational_modifiers(proposal: GmClassifierProposal) -> None:
    if len(proposal.situational_modifiers) > MAX_SITUATIONAL_MODIFIERS:
        raise GmProposalValidationError(
            f"Można dodać maksymalnie {MAX_SITUATIONAL_MODIFIERS} modyfikatory sytuacyjne."
        )
    seen: set[tuple[str, str]] = set()
    for modifier in proposal.situational_modifiers:
        key = (modifier.source.value, modifier.label.strip().lower())
        if key in seen:
            raise GmProposalValidationError(f"Powtórzony modyfikator sytuacyjny: {modifier.label}.")
        seen.add(key)


def _drop_noop_situational_modifiers(proposal: GmClassifierProposal) -> GmClassifierProposal:
    effective_modifiers = tuple(
        modifier
        for modifier in proposal.situational_modifiers
        if modifier.modifier != 0 or modifier.roll_mode != RollMode.NORMAL
    )
    if effective_modifiers == proposal.situational_modifiers:
        return proposal
    return proposal.model_copy(update={"situational_modifiers": effective_modifiers})


def _validate_improvised_tool(
    proposal: GmClassifierProposal,
    mechanic_id: ExplorationMechanicId,
    request: GmClassifierRequest,
) -> None:
    if request.selected_use_source_id is not None:
        selected_source = build_crafting_source_registry(
            request.state,
            request.actors,
        ).source_by_id(request.selected_use_source_id)
        if selected_source is None or not selected_source.usable:
            raise GmProposalValidationError("Wybrany element nie jest już dostępny do użycia.")
        if (
            selected_source.kind
            in {CraftingSourceKind.SCENE_ITEM, CraftingSourceKind.SCENE_FIXTURE}
            and mechanic_id != ExplorationMechanicId.IMPROVISED_TOOL_CHECK
        ):
            raise GmProposalValidationError(
                "Bezpośrednie użycie elementu sceny wymaga mechaniki improvised_tool_check."
            )
    if mechanic_id == ExplorationMechanicId.IMPROVISED_TOOL_CHECK:
        if proposal.improvised_tool is None:
            raise GmProposalValidationError("improvised_tool_check wymaga pola improvised_tool.")
        if proposal.improvised_tool.effect_modifier == 0:
            raise GmProposalValidationError("Improwizowane narzędzie musi mieć niezerowy efekt mechaniczny.")
        if request.selected_use_source_id is not None:
            if proposal.improvised_tool.source_id != request.selected_use_source_id:
                raise GmProposalValidationError(
                    "Improwizowane narzędzie musi wskazywać wybrany przez gracza source_id."
                )
        return
    if proposal.improvised_tool is not None:
        raise GmProposalValidationError("Pole improvised_tool jest dozwolone tylko dla improvised_tool_check.")


def _combined_roll_mode(base_mode: RollMode, modifier_modes: tuple[RollMode, ...]) -> RollMode:
    modes = {mode for mode in (base_mode, *modifier_modes) if mode != RollMode.NORMAL}
    if RollMode.ADVANTAGE in modes and RollMode.DISADVANTAGE in modes:
        return RollMode.NORMAL
    if RollMode.DISADVANTAGE in modes:
        return RollMode.DISADVANTAGE
    if RollMode.ADVANTAGE in modes:
        return RollMode.ADVANTAGE
    return RollMode.NORMAL


def _validate_preparation_effect(
    effect: GmPreparationEffect,
    policy: LlmChallengePolicy,
    request: GmClassifierRequest,
) -> CraftingPlan | None:
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
    elif effect.type == PreparationEffectType.CREATE_TEMPORARY_ITEM:
        if effect.crafting_draft is not None:
            try:
                draft = effect.crafting_draft.as_domain()
                plan = validate_crafting_draft(
                    request.state,
                    draft,
                    build_crafting_source_registry(request.state, request.actors),
                    request.crafting_policy,
                )
            except (CraftingValidationError, ValueError) as exc:
                raise GmProposalValidationError(str(exc)) from exc
            if not set(effect.target_tags).issubset(plan.purpose.bonus_tags):
                raise GmProposalValidationError(
                    "Cel konstrukcji nie obsługuje wszystkich zadeklarowanych target_tags."
                )
            return plan
        if not effect.temporary_item_template_id:
            raise GmProposalValidationError("create_temporary_item wymaga temporary_item_template_id.")
        templates = {template.id: template for template in policy.temporary_item_templates}
        template = templates.get(effect.temporary_item_template_id)
        if template is None:
            raise GmProposalValidationError(
                f"Nieznany szablon przedmiotu tymczasowego: {effect.temporary_item_template_id}."
            )
        if any(item.template_id == template.id for item in request.state.temporary_items):
            raise GmProposalValidationError(
                f"Przedmiot tymczasowy {template.label} został już utworzony w tym scenariuszu."
            )
        if not effect.source_materials:
            raise GmProposalValidationError("create_temporary_item wymaga source_materials.")
        known_materials = _known_resource_or_material_tokens(request)
        unknown_materials = {
            material for material in effect.source_materials
            if _normalize_fact_token(material) not in known_materials
        }
        if unknown_materials:
            raise GmProposalValidationError(
                "Przedmiot tymczasowy używa materiałów spoza sceny: " + ", ".join(sorted(unknown_materials))
            )
        allowed_materials = {_normalize_fact_token(material) for material in template.allowed_materials}
        disallowed_materials = {
            material for material in effect.source_materials
            if _normalize_fact_token(material) not in allowed_materials
        }
        if disallowed_materials:
            raise GmProposalValidationError(
                "Szablon przedmiotu nie obsługuje materiałów: " + ", ".join(sorted(disallowed_materials))
            )
    return None


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


def _ground_selected_flow_mechanics(
    proposal: GmClassifierProposal,
    request: GmClassifierRequest,
) -> GmClassifierProposal:
    """Make an authored graph edge authoritative over LLM check parameters."""

    option_id = request.selected_flow_option_id
    if (
        option_id is None
        or proposal.action_flow == GmActionFlow.PREPARATION
        or not proposal.requires_roll_now
    ):
        return proposal
    profile = next(
        (
            option
            for option in request.challenge.options
            if option.id == option_id
        ),
        None,
    )
    if profile is None:
        raise GmProposalValidationError(
            f"Aktywna krawędź flowgrafu wskazuje nieistniejącą opcję: {option_id}."
        )
    uses_progress = not bool(
        request.challenge.completion_all_flags
        or request.challenge.completion_any_flags
    )
    flow_note = (
        "Mechanika testu pochodzi z aktywnej krawędzi flowgrafu "
        f"{request.selected_flow_transition_id or option_id}."
    )
    return proposal.model_copy(
        update={
            "target_challenge_id": request.challenge.id,
            "approach_tags": tuple(
                dict.fromkeys((*proposal.approach_tags, *profile.tags))
            ),
            "ability": profile.ability_check.ability,
            "skill": profile.ability_check.skill,
            "dc": profile.ability_check.dc,
            "difficulty_reason": flow_note,
            "progress_on_success": (
                profile.progress_on_success if uses_progress else 0
            ),
            "progress_on_failure": (
                profile.progress_on_failure if uses_progress else 0
            ),
            "consequences": (),
            "success_message": profile.success_message,
            "failure_message": profile.failure_message,
            "critical_failure_message": profile.critical_failure_message,
            "gm_notes": " ".join(
                part
                for part in (proposal.gm_notes.strip(), flow_note)
                if part
            ),
        }
    )


def _ground_proposal_dc(
    proposal: GmClassifierProposal,
    policy: LlmChallengePolicy,
) -> GmClassifierProposal:
    """Let the LLM choose a tier while deterministic content owns its numeric DC."""

    if not proposal.difficulty_tier or proposal.dc is None:
        return proposal
    allowed_tiers = set(policy.allowed_difficulty_tiers or tuple(tier.id for tier in policy.dc_tiers))
    if proposal.difficulty_tier not in allowed_tiers:
        return proposal
    expected_dc = policy.dc_for_tier(proposal.difficulty_tier)
    if expected_dc is None or proposal.dc == expected_dc:
        return proposal
    return proposal.model_copy(update={"dc": expected_dc})


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
        if (
            normalized
            and normalized not in known_tokens
            and not _resource_phrase_is_known(normalized, known_tokens)
            and not _phrase_matches_grounded_player_source(normalized, request)
        ):
            unknown.append(resource)
    return tuple(dict.fromkeys(unknown))


def _known_resource_or_material_tokens(request: GmClassifierRequest) -> set[str]:
    tokens: set[str] = set()
    for resource in request.state.resources:
        if resource.id in request.state.inventory_resource_ids:
            tokens.add(_normalize_fact_token(resource.id))
            tokens.add(_normalize_fact_token(resource.label))
    for item in request.state.temporary_items:
        if item.available:
            tokens.add(_normalize_fact_token(item.id))
            tokens.add(_normalize_fact_token(item.label))
    for source in build_crafting_source_registry(request.state, request.actors).available_sources:
        tokens.add(_normalize_fact_token(source.id))
        tokens.add(_normalize_fact_token(f"source:{source.id}"))
        tokens.add(_normalize_fact_token(source.reference_id))
        tokens.add(_normalize_fact_token(source.label))
    for context in (request.scenario_context, request.zone.llm_context, request.challenge.llm_context):
        for material in context.available_materials:
            tokens.add(_normalize_fact_token(material))
    return {token for token in tokens if token}


def _constructed_fact_is_grounded(fact: str, request: GmClassifierRequest) -> bool:
    normalized = _normalize_fact_token(fact)
    if request.explicit_player_intent_hint == PlayerIntentHint.BUILD:
        fact_stems = _meaningful_word_stems(normalized)
        action_stems = _meaningful_word_stems(_normalize_fact_token(request.player_action))
        if fact_stems.intersection(action_stems):
            return True
    template_labels = {
        _normalize_fact_token(template.label)
        for template in request.challenge.llm_policy.temporary_item_templates
    }
    if any(label in normalized or normalized in label for label in template_labels if label):
        return True
    if _phrase_matches_grounded_player_source(normalized, request):
        return True
    fact_words = {word for word in normalized.split() if len(word) >= 5}
    return any(
        entry.role == "gm"
        and len(fact_words.intersection(_normalize_fact_token(entry.content).split())) >= 2
        for entry in request.declaration_thread
    )


def _phrase_matches_grounded_player_source(normalized_phrase: str, request: GmClassifierRequest) -> bool:
    if not request.referenced_crafting_source_ids:
        return False
    phrase_stems = _meaningful_word_stems(normalized_phrase)
    action_stems = _meaningful_word_stems(_normalize_fact_token(request.player_action))
    return bool(phrase_stems.intersection(action_stems))


def _meaningful_word_stems(value: str) -> frozenset[str]:
    ignored = {"chce", "tego", "tym", "jako", "ktory", "prowizoryczny", "prowizoryczne"}
    return frozenset(
        word[:3]
        for word in value.split()
        if len(word) >= 3 and word not in ignored
    )


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
    structured_constraints = tuple(
        phrase
        for fact in request.challenge.llm_context.guidance_facts
        if fact.kind == LlmGuidanceFactKind.CONSTRAINT
        for phrase in (fact.match_phrases or (fact.text,))
    )
    return tuple(
        dict.fromkeys(
            (
                *request.scenario_context.forbidden_assumptions,
                *request.zone.llm_context.forbidden_assumptions,
                *request.challenge.llm_context.impossible_approaches,
                *structured_constraints,
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
        "consume_on_use": resource.consume_on_use,
    }


def _actor_grounding_payload(actor: Actor) -> dict[str, Any]:
    return {
        "id": str(actor.id),
        "name": actor.name,
        "ability_scores": {
            "strength": actor.ability_scores.strength,
            "dexterity": actor.ability_scores.dexterity,
            "constitution": actor.ability_scores.constitution,
            "intelligence": actor.ability_scores.intelligence,
            "wisdom": actor.ability_scores.wisdom,
            "charisma": actor.ability_scores.charisma,
        },
        "inventory": [
            {
                "id": item.id,
                "name": item.name,
                "kind": item.kind,
                "quantity": item.quantity,
                "equipped": item.equipped,
                "broken": item.broken,
            }
            for item in actor.inventory
            if item.quantity > 0
        ],
        "spell_ids": list(actor.spell_ids),
    }


def _option_requirements_payload(option: ExplorationChallengeOption) -> dict[str, Any]:
    return {
        "item_ids": list(option.requires_item_ids),
        "spell_ids": list(option.requires_spell_ids),
        "ability_scores": [
            {"ability": ability, "minimum": minimum}
            for ability, minimum in option.requires_ability_scores
        ],
        "bonuses": [bonus.as_payload() for bonus in option.bonuses],
    }


def _dynamic_state_payload(state: ExplorationState, challenge: ExplorationChallenge) -> dict[str, Any]:
    challenge_state = challenge_state_for(state, challenge.id)
    visible_points = visible_exploration_points(state.points)
    uses_progress = not bool(
        challenge.completion_all_flags
        or challenge.completion_any_flags
    )
    challenge_progress: dict[str, Any] = {
        "challenge_id": challenge.id,
        "uses_progress": uses_progress,
        "completed": challenge_state.completed,
    }
    if uses_progress:
        challenge_progress.update(
            {
                "current": challenge_state.current_progress,
                "required": challenge.progress_required,
            }
        )
    return {
        "known_flags": [{"key": key, "value": value} for key, value in state.flags.values],
        "challenge_progress": challenge_progress,
        "noise": challenge_state.noise,
        "complications": list(challenge_state.complications),
        "revealed_points": [
            {"id": point.id, "name": point.name, "zone_id": point.zone_id}
            for point in visible_points
        ],
        "inventory_resource_ids": list(state.inventory_resource_ids),
        "temporary_items": [
            {
                "id": item.id,
                "label": item.label,
                "uses_remaining": item.uses_remaining,
                "source_materials": list(item.source_materials),
            }
            for item in state.temporary_items
            if item.available
        ],
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


def _active_observations(
    request: GmClassifierRequest,
) -> tuple[ExplorationObservation, ...]:
    selected_goal = interaction_goal(
        request.challenge.goals,
        request.selected_goal_id,
        request.state.flags,
    )
    allowed_ids = (
        set(request.selected_flow_observation_ids)
        if request.selected_flow_observation_ids
        else set(selected_goal.observation_ids)
        if selected_goal is not None
        else set()
    )
    return tuple(
        observation
        for observation in request.observations
        if observation.zone_id == request.zone.id
        and (
            observation.challenge_id is None
            or observation.challenge_id == request.challenge.id
        )
        and (not allowed_ids or observation.id in allowed_ids)
    )


def _conversation_knowledge(request: GmClassifierRequest, crafting_registry) -> dict[str, object]:
    facts: list[dict[str, object]] = []

    def add_fact(
        fact_id: str,
        text: str,
        *,
        kind: str,
        minimum_hint_level: int = 0,
        revealed: bool = True,
    ) -> None:
        normalized = text.strip()
        if normalized:
            facts.append(
                {
                    "id": fact_id,
                    "text": normalized,
                    "kind": kind,
                    "minimum_hint_level": minimum_hint_level,
                    "revealed": revealed,
                }
            )

    add_fact(
        f"zone:{request.zone.id}:description",
        request.zone.description,
        kind="visible_observation",
    )
    add_fact(
        f"zone:{request.zone.id}:summary",
        request.zone.llm_context.summary,
        kind="visible_observation",
    )
    add_fact(
        f"challenge:{request.challenge.id}:summary",
        request.challenge.llm_context.summary,
        kind="visible_observation",
    )
    for source in crafting_registry.available_sources:
        properties = ", ".join(source.properties)
        add_fact(
            f"source:{source.id}",
            f"{source.label}; ilość {source.quantity}; właściwości: {properties}; stan: {source.condition}.",
            kind="visible_source",
        )
    for point in visible_exploration_points(request.state.points):
        if point.zone_id == request.zone.id:
            add_fact(
                f"point:{point.id}",
                f"{point.name}: {point.description}",
                kind="visible_point",
            )
    guidance_facts = request.challenge.llm_context.guidance_facts
    if guidance_facts:
        fact_kind = {
            LlmGuidanceFactKind.OBSERVATION: "visible_observation",
            LlmGuidanceFactKind.AFFORDANCE: "gm_hint",
            LlmGuidanceFactKind.RISK: "gm_hint",
            LlmGuidanceFactKind.CONSTRAINT: "world_constraint",
        }
        for fact in guidance_facts:
            add_fact(
                f"fact:{fact.id}",
                fact.text,
                kind=fact_kind[fact.kind],
                minimum_hint_level=fact.minimum_hint_level,
                revealed=fact.is_revealed(request.state.flags),
            )
    else:
        for index, approach in enumerate(request.challenge.llm_context.reasonable_approaches, start=1):
            add_fact(
                f"challenge:{request.challenge.id}:approach:{index}",
                approach,
                kind="gm_hint",
                minimum_hint_level=1,
            )
    for purpose in request.crafting_policy.purposes:
        add_fact(
            f"crafting:purpose:{purpose.id}",
            f"Dostępne materiały mogą zostać ocenione pod kątem celu: {purpose.label}.",
            kind="gm_hint",
            minimum_hint_level=2,
        )
    if not guidance_facts:
        for index, risk in enumerate(request.challenge.llm_context.risk_notes, start=1):
            add_fact(
                f"challenge:{request.challenge.id}:risk:{index}",
                risk,
                kind="gm_hint",
                minimum_hint_level=2,
            )
        for index, impossible in enumerate(request.challenge.llm_context.impossible_approaches, start=1):
            add_fact(
                f"challenge:{request.challenge.id}:constraint:{index}",
                impossible,
                kind="world_constraint",
            )
    for observation in _active_observations(request):
        for fact in observation.facts:
            add_fact(
                f"observation:{observation.id}:fact:{fact.id}",
                fact.narration,
                kind="graded_observation",
                revealed=bool(scene_flag(request.state.flags, fact.reveal_flag, False)),
            )
    return {
        "facts": facts,
        "already_revealed_fact_ids": list(
            dict.fromkeys(
                fact_id
                for entry in request.declaration_thread
                for fact_id in entry.grounded_fact_ids
            )
        ),
    }


def _allowed_hint_level(request: GmClassifierRequest) -> int:
    normalized_action = _normalize_fact_token(request.player_action)
    if any(marker in normalized_action for marker in ("wprost", "konkret", "gotowe rozwiazanie", "dokladna podpowiedz")):
        return 3
    previous = max((entry.hint_level for entry in request.declaration_thread), default=0)
    return min(3, max(1, previous + 1))


def _validate_conversation_response(
    analysis: GmDeclarationAnalysis,
    request: GmClassifierRequest,
) -> None:
    if analysis.response_kind is None:
        # Compatibility with older classifier fixtures and saved integrations.
        return
    knowledge = _conversation_knowledge(
        request,
        build_crafting_source_registry(request.state, request.actors),
    )
    facts_by_id = {fact["id"]: fact for fact in knowledge["facts"]}
    unknown_fact_ids = set(analysis.grounded_fact_ids) - set(facts_by_id)
    if unknown_fact_ids:
        raise GmProposalValidationError(
            "Odpowiedź MG powołuje się na fakty spoza sceny: " + ", ".join(sorted(unknown_fact_ids))
        )
    hint_kinds = {
        GmConversationResponseKind.GENTLE_HINT,
        GmConversationResponseKind.STRONG_HINT,
    }
    if analysis.response_kind in hint_kinds:
        if analysis.hint_level < 1:
            raise GmProposalValidationError("Podpowiedź MG wymaga hint_level od 1 do 3.")
        if analysis.hint_level > _allowed_hint_level(request):
            raise GmProposalValidationError("Odpowiedź MG zdradza zbyt silną podpowiedź na tym etapie rozmowy.")
        if analysis.response_kind == GmConversationResponseKind.STRONG_HINT and analysis.hint_level < 2:
            raise GmProposalValidationError("Strong hint wymaga hint_level 2 albo 3.")
    elif analysis.response_kind == GmConversationResponseKind.REQUIRES_CHECK:
        if analysis.hint_level > _allowed_hint_level(request):
            raise GmProposalValidationError(
                "Sugestia sprawdzenia zdradza zbyt silną podpowiedź na tym etapie rozmowy."
            )
    elif analysis.hint_level != 0:
        raise GmProposalValidationError("Zwykła odpowiedź MG nie może zwiększać poziomu podpowiedzi.")
    for fact_id in analysis.grounded_fact_ids:
        if not bool(facts_by_id[fact_id].get("revealed", True)):
            raise GmProposalValidationError(
                f"Fakt {fact_id} wymaga najpierw rozstrzygnięcia obserwacji."
            )
        required_level = int(facts_by_id[fact_id]["minimum_hint_level"])
        if required_level > analysis.hint_level:
            raise GmProposalValidationError(
                f"Fakt {fact_id} wymaga podpowiedzi poziomu {required_level}."
            )
    if analysis.response_kind == GmConversationResponseKind.REQUIRES_CHECK:
        if not analysis.requires_check or not analysis.suggested_followup.strip():
            raise GmProposalValidationError(
                "Odpowiedź requires_check musi wskazywać, co gracze mogą zadeklarować dalej."
            )
        if analysis.observation_id is not None:
            active_observation_ids = {
                observation.id for observation in _active_observations(request)
            }
            if analysis.observation_id not in active_observation_ids:
                raise GmProposalValidationError("MG wskazał obserwację niedostępną w aktualnej scenie.")
    elif analysis.requires_check:
        raise GmProposalValidationError("requires_check jest dozwolone tylko dla response_kind=requires_check.")
    elif analysis.observation_id is not None:
        raise GmProposalValidationError("observation_id jest dozwolone tylko dla odpowiedzi requires_check.")
    unknown_mentions = _unsupported_resource_mentions(
        analysis.player_message,
        _known_resource_or_material_tokens(request),
    )
    if unknown_mentions:
        raise GmProposalValidationError(
            "Odpowiedź MG wymyśla zasób spoza sceny: " + ", ".join(sorted(unknown_mentions))
        )


class GmSceneSourceQuery(BaseModel):
    """Abstract function requested by a player, without selecting a scene object."""

    model_config = ConfigDict(extra="forbid")

    purpose: str = Field(default="", max_length=300)
    requested_name: str | None = Field(default=None, max_length=120)
    required_properties: tuple[str, ...] = ()
    preferred_properties: tuple[str, ...] = ()

    @field_validator("required_properties", "preferred_properties")
    @classmethod
    def _property_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.strip() for item in value if item.strip()))

    def model_post_init(self, __context: Any) -> None:
        if not self.required_properties and not self.preferred_properties:
            raise ValueError("Source query needs at least one required or preferred property.")
        required = frozenset(self.required_properties)
        object.__setattr__(
            self,
            "preferred_properties",
            tuple(item for item in self.preferred_properties if item not in required),
        )
        if self.requested_name is not None:
            normalized_name = self.requested_name.strip()
            object.__setattr__(self, "requested_name", normalized_name or None)


class GmWorldEffect(BaseModel):
    """Immediate, policy-limited consequence of an action outside challenge resolution."""

    model_config = ConfigDict(extra="ignore")

    type: str = Field(max_length=80)
    parameters: dict[str, Any] = Field(default_factory=dict)

    @field_validator("type")
    @classmethod
    def _normalize_type(cls, value: str) -> str:
        return value.strip().lower()

    def as_effect_payload(self) -> dict[str, object]:
        return {"type": self.type, "parameters": dict(self.parameters)}


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
    response_kind: GmConversationResponseKind | None = None
    grounded_fact_ids: tuple[str, ...] = ()
    hint_level: int = Field(default=0, ge=0, le=3)
    suggested_followup: str = Field(default="", max_length=500)
    requires_check: bool = False
    observation_id: str | None = Field(default=None, max_length=120)
    source_query: GmSceneSourceQuery | None = None
    use_source_id: str | None = Field(default=None, max_length=240)
    action_target_source_id: str | None = Field(default=None, max_length=240)
    fixture_operation: FixtureOperation | None = None
    immediate_effects: tuple[GmWorldEffect, ...] = Field(default=(), max_length=2)

    @field_validator(
        "declared_resources",
        "referenced_existing_resource_ids",
        "assumed_new_facts",
        "missing_requirements",
        "grounded_fact_ids",
    )
    @classmethod
    def _string_tuple_items(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.strip() for item in value if item.strip()))

    def model_post_init(self, __context: Any) -> None:
        if self.action_flow is None:
            default_flow = {
                GmDeclarationAnalysisType.PLAUSIBLE: GmActionFlow.CHALLENGE_ATTEMPT,
                GmDeclarationAnalysisType.WORLD_ACTION: GmActionFlow.WORLD_ACTION,
                GmDeclarationAnalysisType.NEEDS_CLARIFICATION: GmActionFlow.NEEDS_CLARIFICATION,
                GmDeclarationAnalysisType.UNSUPPORTED: GmActionFlow.UNSUPPORTED,
                GmDeclarationAnalysisType.PLAYER_QUESTION: GmActionFlow.PLAYER_QUESTION,
            }[self.analysis_type]
            object.__setattr__(self, "action_flow", default_flow)


def _world_notes(state: ExplorationState, challenge: ExplorationChallenge) -> list[str]:
    challenge_state = challenge_state_for(state, challenge.id)
    notes: list[str] = []
    if (
        not challenge.completion_all_flags
        and not challenge.completion_any_flags
        and challenge_state.current_progress
    ):
        notes.append(
            f"Wyzwanie `{challenge.name}` ma postęp {challenge_state.current_progress}/{challenge.progress_required}."
        )
    if challenge_state.noise:
        notes.append(
            f"Dotychczasowy poziom hałasu/czujności przy wyzwaniu: "
            f"{challenge_state.noise}."
        )
    for complication in challenge_state.complications:
        notes.append(f"Aktywna komplikacja: {complication}.")
    for key, value in state.flags.values:
        if value is True:
            notes.append(f"Aktywna flaga sceny: {key}.")
    return notes
