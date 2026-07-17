from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from dnd_board_game.actors import Actor, spell_is_prepared
from dnd_board_game.combat import (
    CombatCondition,
    ConditionState,
    SceneAbilityCheck,
    SceneFlags,
    SetupVisibility,
    add_condition,
    remove_condition,
    scene_flag,
    set_scene_flag,
)
from dnd_board_game.hardware import LedColor, LedFeedback, LedFrame, LedRole
from dnd_board_game.inventory import ItemInstance
from dnd_board_game.rules import (
    D20RollInput,
    D20RollRequest,
    D20RollResult,
    RollMode,
    RollModifier,
    RollModifierType,
    SavingThrowRequest,
    resolve_ability_check,
    resolve_d20_roll,
)
from dnd_board_game.world import Coordinate


class SceneMode(StrEnum):
    ENCOUNTER = "encounter"
    EXPLORATION = "exploration"


class ExplorationOptionKind(StrEnum):
    MESSAGE = "message"
    SEARCH = "search"
    CHECK = "check"


class FixtureOperation(StrEnum):
    DETACH = "detach"
    DAMAGE = "damage"
    DESTROY = "destroy"
    MOVE = "move"
    OPEN = "open"
    CLOSE = "close"
    REPAIR = "repair"


@dataclass(frozen=True, slots=True)
class FixtureActionPolicy:
    operation: FixtureOperation
    result_condition: str
    ability: str
    difficulty_tier: str
    skill: str | None = None
    allowed_conditions: tuple[str, ...] = ()
    progress_on_success: int = 1
    progress_on_failure: int = 0
    success_noise: int = 0
    failure_noise: int = 0
    failure_complication: str | None = None
    makes_fixture_unavailable: bool = False
    release_yield_items: bool = False

    def __post_init__(self) -> None:
        if not self.result_condition.strip() or not self.ability.strip() or not self.difficulty_tier.strip():
            raise ValueError("Fixture action result, ability and difficulty tier cannot be empty.")
        if self.progress_on_success < 0 or self.progress_on_failure < 0:
            raise ValueError("Fixture action progress cannot be negative.")
        if self.success_noise < 0 or self.failure_noise < 0:
            raise ValueError("Fixture action noise cannot be negative.")


@dataclass(frozen=True, slots=True)
class SceneFixture:
    id: str
    name: str
    description: str = ""
    properties: tuple[str, ...] = ()
    condition: str = "normal"
    visible: bool = True
    portable: bool = False
    detachable: bool = False
    destructible: bool = False
    yield_items: tuple[ItemInstance, ...] = ()
    action_policies: tuple[FixtureActionPolicy, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Scene fixture id cannot be empty.")
        if not self.name.strip():
            raise ValueError("Scene fixture name cannot be empty.")
        if not self.condition.strip():
            raise ValueError("Scene fixture condition cannot be empty.")
        if any(not property_id.strip() for property_id in self.properties):
            raise ValueError(f"Scene fixture {self.id}.properties cannot contain empty ids.")
        if len(self.properties) != len(set(self.properties)):
            raise ValueError(f"Scene fixture {self.id}.properties cannot contain duplicate ids.")
        yield_ids = tuple(item.id for item in self.yield_items)
        if len(yield_ids) != len(set(yield_ids)):
            raise ValueError(f"Scene fixture {self.id}.yield_items cannot contain duplicate ids.")
        operations = tuple(policy.operation for policy in self.action_policies)
        if len(operations) != len(set(operations)):
            raise ValueError(f"Scene fixture {self.id}.action_policies cannot repeat operations.")


class RestSafety(StrEnum):
    SAFE = "safe"
    CONTESTED = "contested"


@dataclass(frozen=True, slots=True)
class ShortRestPolicy:
    id: str
    safety: RestSafety
    risk_summary: str
    duration_minutes: int = 60
    max_completions: int = 0
    completion_effects: tuple[dict[str, object], ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Short rest policy id cannot be empty.")
        if self.duration_minutes < 60:
            raise ValueError("A short rest must last at least 60 minutes.")
        if self.max_completions < 0:
            raise ValueError("Short rest max_completions cannot be negative.")
        if self.safety == RestSafety.CONTESTED and not self.risk_summary.strip():
            raise ValueError("A contested short rest requires a risk summary.")


class CheckParticipants(StrEnum):
    SINGLE_ACTOR = "single_actor"
    LEAD_WITH_HELP = "lead_with_help"
    WHOLE_PARTY = "whole_party"
    SELECTED_ACTORS = "selected_actors"


class CheckAggregation(StrEnum):
    LEAD_RESULT = "lead_result"
    HIGHEST = "highest"
    LOWEST = "lowest"
    MAJORITY = "majority"
    ALL_MUST_SUCCEED = "all_must_succeed"
    ANY_SUCCESS = "any_success"
    SUM_PROGRESS = "sum_progress"


class ExplorationSituationalModifierSource(StrEnum):
    SCENARIO_CONTEXT = "scenario_context"
    ZONE_CONTEXT = "zone_context"
    CHALLENGE_CONTEXT = "challenge_context"
    INTERACTION_OBJECT = "interaction_object"
    PLAYER_DECLARATION = "player_declaration"
    DYNAMIC_STATE = "dynamic_state"
    GM = "gm"


class ConsequenceTarget(StrEnum):
    LEAD_ACTOR = "lead_actor"
    HELPER_ACTOR = "helper_actor"
    FAILED_ACTORS = "failed_actors"
    WHOLE_PARTY = "whole_party"
    SCENE = "scene"
    NPC = "npc"
    OBJECT = "object"


class EncounterTriggerCondition(StrEnum):
    NOISE_AT_LEAST = "noise_at_least"
    FLAG_EQUALS = "flag_equals"
    POINT_REVEALED = "point_revealed"


class EncounterOpeningOutcome(StrEnum):
    PARTY_SURPRISES_ENEMIES = "party_surprises_enemies"
    NO_SURPRISE = "no_surprise"
    ENEMIES_SURPRISE_PARTY = "enemies_surprise_party"


class LlmGuidanceFactKind(StrEnum):
    OBSERVATION = "observation"
    AFFORDANCE = "affordance"
    RISK = "risk"
    CONSTRAINT = "constraint"


class LlmGuidanceFactVisibility(StrEnum):
    OBVIOUS = "obvious"
    HINT = "hint"
    HIDDEN = "hidden"


@dataclass(frozen=True, slots=True)
class LlmGuidanceFact:
    id: str
    text: str
    kind: LlmGuidanceFactKind
    visibility: LlmGuidanceFactVisibility
    minimum_hint_level: int = 0
    reveal_if_flags: tuple[str, ...] = ()
    match_phrases: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.text.strip():
            raise ValueError("LLM guidance fact id and text cannot be empty.")
        if not 0 <= self.minimum_hint_level <= 3:
            raise ValueError("LLM guidance fact minimum_hint_level must be between 0 and 3.")
        if self.visibility == LlmGuidanceFactVisibility.OBVIOUS and self.minimum_hint_level != 0:
            raise ValueError("Obvious LLM guidance facts must use minimum_hint_level 0.")
        if self.visibility == LlmGuidanceFactVisibility.HINT and self.minimum_hint_level < 1:
            raise ValueError("Hint LLM guidance facts must use minimum_hint_level 1 or higher.")

    def is_revealed(self, flags: SceneFlags) -> bool:
        if self.visibility != LlmGuidanceFactVisibility.HIDDEN:
            return True
        return bool(self.reveal_if_flags) and all(
            bool(scene_flag(flags, flag, False))
            for flag in self.reveal_if_flags
        )

    def as_payload(self) -> dict[str, object]:
        return {
            "id": self.id,
            "text": self.text,
            "kind": self.kind.value,
            "visibility": self.visibility.value,
            "minimum_hint_level": self.minimum_hint_level,
            "reveal_if_flags": list(self.reveal_if_flags),
            "match_phrases": list(self.match_phrases),
        }


@dataclass(frozen=True, slots=True)
class EncounterOutcome:
    title: str
    body: str
    effects: tuple[dict[str, object], ...] = ()
    next_instruction: str = ""


@dataclass(frozen=True, slots=True)
class EncounterOpeningRule:
    id: str
    outcome: EncounterOpeningOutcome
    title: str
    narration: str
    min_noise: int | None = None
    max_noise: int | None = None
    required_flags: tuple[str, ...] = ()
    forbidden_flags: tuple[str, ...] = ()
    completion_any_tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EncounterOpeningPolicy:
    challenge_id: str
    default_outcome: EncounterOpeningOutcome
    default_title: str
    default_narration: str
    rules: tuple[EncounterOpeningRule, ...] = ()


@dataclass(frozen=True, slots=True)
class EncounterOpeningResolution:
    rule_id: str
    outcome: EncounterOpeningOutcome
    title: str
    narration: str
    noise: int
    completion_tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PrecombatStealthAttempt:
    actor_id: str
    natural_roll: int
    total: int
    hidden_from_actor_ids: tuple[str, ...] = ()
    detected_by_actor_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.actor_id:
            raise ValueError("Precombat stealth actor id cannot be empty.")
        if not 1 <= self.natural_roll <= 20:
            raise ValueError("Precombat stealth natural roll must be between 1 and 20.")


@dataclass(frozen=True, slots=True)
class LlmContext:
    summary: str = ""
    available_materials: tuple[str, ...] = ()
    forbidden_assumptions: tuple[str, ...] = ()
    reasonable_approaches: tuple[str, ...] = ()
    impossible_approaches: tuple[str, ...] = ()
    risk_notes: tuple[str, ...] = ()
    guidance_facts: tuple[LlmGuidanceFact, ...] = ()

    def as_payload(self) -> dict[str, object]:
        return {
            "summary": self.summary,
            "available_materials": list(self.available_materials),
            "forbidden_assumptions": list(self.forbidden_assumptions),
            "reasonable_approaches": list(self.reasonable_approaches),
            "impossible_approaches": list(self.impossible_approaches),
            "risk_notes": list(self.risk_notes),
            "guidance_facts": [fact.as_payload() for fact in self.guidance_facts],
        }


@dataclass(frozen=True, slots=True)
class ExplorationEncounterTrigger:
    id: str
    name: str
    description: str
    encounter_scenario: str
    condition: EncounterTriggerCondition
    challenge_id: str | None = None
    noise: int | None = None
    flag_key: str | None = None
    flag_value: object = True
    point_id: str | None = None
    opening_policy: EncounterOpeningPolicy | None = None
    outcome_on_victory: EncounterOutcome | None = None
    outcome_on_defeat: EncounterOutcome | None = None


@dataclass(frozen=True, slots=True)
class PendingEncounter:
    trigger_id: str
    name: str
    description: str
    encounter_scenario: str
    reason: str
    opening_resolution: EncounterOpeningResolution | None = None
    precombat_stealth_completed: bool = False
    precombat_stealth_attempts: tuple[PrecombatStealthAttempt, ...] = ()


@dataclass(frozen=True, slots=True)
class LlmDcTier:
    id: str
    dc: int
    label: str = ""
    guidance: str = ""

    def as_payload(self) -> dict[str, object]:
        return {
            "id": self.id,
            "dc": self.dc,
            "label": self.label,
            "guidance": self.guidance,
        }


@dataclass(frozen=True, slots=True)
class TemporaryItemTemplate:
    id: str
    label: str
    description: str
    bonus_tags: tuple[str, ...]
    modifier: int = 0
    advantage: bool = False
    uses: int = 1
    risk: str = ""
    allowed_materials: tuple[str, ...] = ()

    def as_payload(self) -> dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "bonus_tags": list(self.bonus_tags),
            "modifier": self.modifier,
            "advantage": self.advantage,
            "uses": self.uses,
            "risk": self.risk,
            "allowed_materials": list(self.allowed_materials),
        }


@dataclass(frozen=True, slots=True)
class LlmChallengePolicy:
    allowed_local_skills: tuple[str, ...] = ()
    allowed_approach_tags: tuple[str, ...] = ()
    allowed_complications: tuple[str, ...] = ()
    allowed_consequence_types: tuple[str, ...] = ("none",)
    allowed_preparation_effect_types: tuple[str, ...] = ()
    allowed_grant_resource_ids: tuple[str, ...] = ()
    allowed_unlock_option_ids: tuple[str, ...] = ()
    max_resources_per_attempt: int = 1
    dc_min: int = 5
    dc_max: int = 25
    progress_success_min: int = 1
    progress_success_max: int = 3
    progress_failure_min: int = 0
    progress_failure_max: int = 1
    preparation_modifier_min: int = 1
    preparation_modifier_max: int = 2
    negative_effect_reduction_min: int = 1
    negative_effect_reduction_max: int = 1
    effect_boost_min: int = 1
    effect_boost_max: int = 1
    dc_tiers: tuple[LlmDcTier, ...] = ()
    allowed_difficulty_tiers: tuple[str, ...] = ()
    default_difficulty_tier: str | None = None
    difficulty_guidance: tuple[str, ...] = ()
    temporary_item_templates: tuple[TemporaryItemTemplate, ...] = ()

    def as_payload(self) -> dict[str, object]:
        return {
            "allowed_local_skills": list(self.allowed_local_skills),
            "allowed_approach_tags": list(self.allowed_approach_tags),
            "allowed_complications": list(self.allowed_complications),
            "allowed_consequence_types": list(self.allowed_consequence_types),
            "allowed_preparation_effect_types": list(self.allowed_preparation_effect_types),
            "allowed_grant_resource_ids": list(self.allowed_grant_resource_ids),
            "allowed_unlock_option_ids": list(self.allowed_unlock_option_ids),
            "max_resources_per_attempt": self.max_resources_per_attempt,
            "dc_range": [self.dc_min, self.dc_max],
            "progress_on_success_range": [self.progress_success_min, self.progress_success_max],
            "progress_on_failure_range": [self.progress_failure_min, self.progress_failure_max],
            "preparation_modifier_range": [self.preparation_modifier_min, self.preparation_modifier_max],
            "negative_effect_reduction_range": [self.negative_effect_reduction_min, self.negative_effect_reduction_max],
            "effect_boost_range": [self.effect_boost_min, self.effect_boost_max],
            "dc_policy": {
                "tiers": [tier.as_payload() for tier in self.dc_tiers],
                "allowed_tiers": list(self.allowed_difficulty_tiers),
                "default_tier": self.default_difficulty_tier,
                "guidance": list(self.difficulty_guidance),
            },
            "temporary_item_templates": [template.as_payload() for template in self.temporary_item_templates],
        }

    def dc_for_tier(self, tier_id: str) -> int | None:
        return next((tier.dc for tier in self.dc_tiers if tier.id == tier_id), None)


@dataclass(frozen=True, slots=True)
class ExplorationOption:
    id: str
    label: str
    kind: ExplorationOptionKind
    color: tuple[int, int, int]
    description: str = ""
    message: str = ""
    success_message: str = ""
    failure_message: str = ""
    ability_check: SceneAbilityCheck | None = None
    allow_help: bool = False
    success_flag: str | None = None
    failure_flag: str | None = None
    reveals: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ExplorationZone:
    id: str
    name: str
    positions: tuple[Coordinate, ...]
    color: tuple[int, int, int]
    anchor_position: Coordinate | None = None
    description: str = ""
    image: str = ""
    visibility: SetupVisibility = SetupVisibility.VISIBLE
    available_if_flag: str | None = None
    available_if_value: object = True
    options: tuple[ExplorationOption, ...] = ()
    adjacent_zone_ids: tuple[str, ...] = ()
    search_dc: int | None = None
    search_ability: str = "wisdom"
    search_skill: str | None = "perception"
    search_reveals: tuple[str, ...] = ()
    search_success_flag: str | None = None
    search_failure_flag: str | None = None
    llm_context: LlmContext = LlmContext()
    short_rest_policy: ShortRestPolicy | None = None
    item_instances: tuple[ItemInstance, ...] = ()
    fixtures: tuple[SceneFixture, ...] = ()

    @property
    def marker_position(self) -> Coordinate:
        if self.anchor_position is not None:
            return self.anchor_position
        if not self.positions:
            raise ValueError(f"Exploration zone {self.id} has no positions.")
        return self.positions[0]


@dataclass(frozen=True, slots=True)
class NpcLockedInformation:
    id: str
    label: str
    text: str
    reveal_if_flags: tuple[str, ...] = ()
    sets_flags: tuple[str, ...] = ()
    effects_on_reveal: tuple[dict[str, object], ...] = ()

    def as_payload(self) -> dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "text": self.text,
            "reveal_if_flags": list(self.reveal_if_flags),
            "sets_flags": list(self.sets_flags),
            "effects_on_reveal": list(self.effects_on_reveal),
        }


class NpcAttitude(StrEnum):
    HOSTILE = "hostile"
    INDIFFERENT = "indifferent"
    FRIENDLY = "friendly"


class NpcInteractionStatus(StrEnum):
    ACTIVE = "active"
    CLOSED = "closed"


@dataclass(frozen=True, slots=True)
class NpcStateUpdate:
    attitude: NpcAttitude | None = None
    physical_state: str | None = None
    emotional_state: str | None = None


def _npc_state_update_payload(update: NpcStateUpdate) -> dict[str, object]:
    payload: dict[str, object] = {}
    if update.attitude is not None:
        payload["attitude"] = update.attitude.value
    if update.physical_state is not None:
        payload["physical_state"] = update.physical_state
    if update.emotional_state is not None:
        payload["emotional_state"] = update.emotional_state
    return payload


@dataclass(frozen=True, slots=True)
class NpcRelationshipEvent:
    sequence: int
    intent: str
    outcome: str
    summary: str
    attempt_id: str | None = None

    def __post_init__(self) -> None:
        if self.sequence < 1:
            raise ValueError("NPC relationship event sequence must be positive.")
        if not self.intent.strip() or self.outcome not in {"success", "failure"}:
            raise ValueError("NPC relationship event requires an intent and outcome.")
        if not self.summary.strip():
            raise ValueError("NPC relationship event summary cannot be empty.")
        if self.attempt_id is not None and not self.attempt_id.strip():
            raise ValueError("NPC relationship event attempt id cannot be empty.")

    def as_payload(self) -> dict[str, object]:
        return {
            "sequence": self.sequence,
            "intent": self.intent,
            "outcome": self.outcome,
            "summary": self.summary,
            "attempt_id": self.attempt_id,
        }


@dataclass(frozen=True, slots=True)
class NpcRuntimeState:
    npc_id: str
    attitude: NpcAttitude = NpcAttitude.INDIFFERENT
    physical_state: str = ""
    emotional_state: str = ""
    revealed_information_ids: tuple[str, ...] = ()
    used_attempt_ids: tuple[str, ...] = ()
    relationship_events: tuple[NpcRelationshipEvent, ...] = ()
    interaction_status: NpcInteractionStatus = NpcInteractionStatus.ACTIVE
    closure_reason: str = ""

    def __post_init__(self) -> None:
        if not self.npc_id.strip():
            raise ValueError("NPC runtime state requires an id.")
        for field_name, values in (
            ("revealed_information_ids", self.revealed_information_ids),
            ("used_attempt_ids", self.used_attempt_ids),
        ):
            if any(not value.strip() for value in values):
                raise ValueError(f"NPC {field_name} cannot contain empty ids.")
            if len(values) != len(set(values)):
                raise ValueError(f"NPC {field_name} cannot contain duplicates.")
        expected_sequences = tuple(range(1, len(self.relationship_events) + 1))
        if tuple(event.sequence for event in self.relationship_events) != expected_sequences:
            raise ValueError("NPC relationship event sequence must be contiguous.")

    def as_payload(self) -> dict[str, object]:
        return {
            "npc_id": self.npc_id,
            "attitude": self.attitude.value,
            "physical_state": self.physical_state,
            "emotional_state": self.emotional_state,
            "revealed_information_ids": list(self.revealed_information_ids),
            "used_attempt_ids": list(self.used_attempt_ids),
            "relationship_events": [event.as_payload() for event in self.relationship_events],
            "interaction_status": self.interaction_status.value,
            "closure_reason": self.closure_reason,
        }


@dataclass(frozen=True, slots=True)
class NpcAttemptPolicy:
    attempt_id: str
    max_attempts: int = 1
    retry_requires_any_flags: tuple[str, ...] = ()
    retry_locked_message: str = "NPC nie zgadza się ponownie rozmawiać o tym bez zmiany sytuacji."
    exhausted_message: str = "To podejście zostało wyczerpane."

    def __post_init__(self) -> None:
        if not self.attempt_id.strip():
            raise ValueError("NPC attempt policy requires an id.")
        if self.max_attempts < 1:
            raise ValueError("NPC attempt policy max_attempts must be positive.")
        if any(not flag.strip() for flag in self.retry_requires_any_flags):
            raise ValueError("NPC retry flags cannot contain empty ids.")
        if len(self.retry_requires_any_flags) != len(set(self.retry_requires_any_flags)):
            raise ValueError("NPC retry flags cannot contain duplicates.")
        if not self.retry_locked_message.strip() or not self.exhausted_message.strip():
            raise ValueError("NPC attempt policy messages cannot be empty.")

    def as_payload(self) -> dict[str, object]:
        return {
            "attempt_id": self.attempt_id,
            "max_attempts": self.max_attempts,
            "retry_requires_any_flags": list(self.retry_requires_any_flags),
            "retry_locked_message": self.retry_locked_message,
            "exhausted_message": self.exhausted_message,
        }


class NpcOutcomeTier(StrEnum):
    CRITICAL_SUCCESS = "critical_success"
    SUCCESS = "success"
    FAILURE = "failure"
    CRITICAL_FAILURE = "critical_failure"


@dataclass(frozen=True, slots=True)
class NpcOutcomeBranch:
    outcome: NpcOutcomeTier
    message: str
    preview: str = ""
    effects: tuple[dict[str, object], ...] = ()
    state_update: NpcStateUpdate | None = None
    revealed_information_ids: tuple[str, ...] = ()
    transition_id: str | None = None

    def __post_init__(self) -> None:
        if not self.message.strip():
            raise ValueError("NPC outcome branch requires a player-facing message.")
        if self.transition_id is not None and not self.transition_id.strip():
            raise ValueError("NPC outcome branch transition id cannot be empty.")

    def as_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "message": self.message,
            "preview": self.preview or self.message,
            "effects": list(self.effects),
            "revealed_information_ids": list(self.revealed_information_ids),
            "transition_id": self.transition_id,
        }
        if self.state_update is not None:
            payload["state_update"] = _npc_state_update_payload(self.state_update)
        return payload


@dataclass(frozen=True, slots=True)
class NpcIntentTarget:
    id: str
    label: str
    description: str
    reward_label: str = ""
    risk_summary: str = ""
    max_quantity: int = 1
    requires_flags: tuple[str, ...] = ()
    ability: str | None = None
    skill: str | None = None
    dc: int | None = None
    outcome_branches: tuple[NpcOutcomeBranch, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.label.strip() or not self.description.strip():
            raise ValueError("NPC intent target requires id, label, and description.")
        if self.max_quantity < 1:
            raise ValueError("NPC intent target max_quantity must be positive.")
        if (self.ability is None) != (self.dc is None):
            raise ValueError("NPC intent target fixed check requires both ability and DC.")
        if self.ability is not None and self.ability not in {
            "strength",
            "dexterity",
            "constitution",
            "intelligence",
            "wisdom",
            "charisma",
        }:
            raise ValueError(f"NPC intent target uses unknown ability: {self.ability}.")
        if self.dc is not None and not 5 <= self.dc <= 30:
            raise ValueError("NPC intent target DC must be in range 5..30.")
        outcomes = tuple(branch.outcome for branch in self.outcome_branches)
        if self.outcome_branches and set(outcomes) != set(NpcOutcomeTier):
            raise ValueError("NPC intent target must define all four outcome branches.")
        if len(outcomes) != len(set(outcomes)):
            raise ValueError("NPC intent target cannot repeat outcome branches.")

    def branch(self, outcome: NpcOutcomeTier) -> NpcOutcomeBranch:
        branch = next((item for item in self.outcome_branches if item.outcome == outcome), None)
        if branch is None:
            raise ValueError(f"NPC target {self.id} has no branch for {outcome.value}.")
        return branch

    def as_payload(self) -> dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "reward_label": self.reward_label,
            "risk_summary": self.risk_summary,
            "max_quantity": self.max_quantity,
            "requires_flags": list(self.requires_flags),
            "ability": self.ability,
            "skill": self.skill,
            "dc": self.dc,
            "outcomes": {
                branch.outcome.value: branch.as_payload()
                for branch in self.outcome_branches
            },
        }


class NpcTransitionResultType(StrEnum):
    RESUME_DIALOGUE = "resume_dialogue"
    END_INTERACTION = "end_interaction"
    START_ENCOUNTER = "start_encounter"


@dataclass(frozen=True, slots=True)
class NpcTransitionReaction:
    id: str
    label: str
    description: str
    result_type: NpcTransitionResultType
    narration: str
    effects: tuple[dict[str, object], ...] = ()
    suppress_encounter_trigger_ids: tuple[str, ...] = ()
    encounter_trigger_id: str | None = None
    npc_status: NpcInteractionStatus | None = None

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.label.strip() or not self.description.strip():
            raise ValueError("NPC transition reaction requires id, label, and description.")
        if not self.narration.strip():
            raise ValueError("NPC transition reaction narration cannot be empty.")
        if self.result_type == NpcTransitionResultType.START_ENCOUNTER and not self.encounter_trigger_id:
            raise ValueError("NPC start-encounter reaction requires encounter_trigger_id.")
        if self.result_type != NpcTransitionResultType.START_ENCOUNTER and self.encounter_trigger_id is not None:
            raise ValueError("Only NPC start-encounter reaction can define encounter_trigger_id.")

    def as_payload(self) -> dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "result_type": self.result_type.value,
        }


@dataclass(frozen=True, slots=True)
class NpcTransitionVariant:
    id: str
    title: str
    narration: str
    reactions: tuple[NpcTransitionReaction, ...]
    required_flags: tuple[str, ...] = ()
    forbidden_flags: tuple[str, ...] = ()
    required_resolved_encounter_trigger_ids: tuple[str, ...] = ()
    forbidden_resolved_encounter_trigger_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.title.strip() or not self.narration.strip():
            raise ValueError("NPC transition variant requires id, title, and narration.")
        if not self.reactions:
            raise ValueError("NPC transition variant requires at least one reaction.")
        reaction_ids = tuple(reaction.id for reaction in self.reactions)
        if len(reaction_ids) != len(set(reaction_ids)):
            raise ValueError("NPC transition variant cannot repeat reaction ids.")
        if set(self.required_flags).intersection(self.forbidden_flags):
            raise ValueError("NPC transition variant cannot require and forbid the same flag.")

    def reaction(self, reaction_id: str) -> NpcTransitionReaction | None:
        normalized = reaction_id.strip().lower()
        return next((reaction for reaction in self.reactions if reaction.id == normalized), None)


@dataclass(frozen=True, slots=True)
class NpcSceneTransition:
    id: str
    npc_id: str
    variants: tuple[NpcTransitionVariant, ...]

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.npc_id.strip() or not self.variants:
            raise ValueError("NPC scene transition requires id, npc_id, and variants.")
        variant_ids = tuple(variant.id for variant in self.variants)
        if len(variant_ids) != len(set(variant_ids)):
            raise ValueError("NPC scene transition cannot repeat variant ids.")


@dataclass(frozen=True, slots=True)
class PendingNpcTransition:
    transition_id: str
    variant_id: str
    npc_id: str


@dataclass(frozen=True, slots=True)
class NpcIntentPermission:
    intent: str
    status: str
    notes: str = ""
    unlock_if_flags: tuple[str, ...] = ()
    limits: dict[str, object] | None = None
    consequences: dict[str, object] | None = None
    reveals: tuple[str, ...] = ()
    state_on_success: NpcStateUpdate | None = None
    state_on_failure: NpcStateUpdate | None = None
    uses_social_reaction: bool = False
    attempt_policy: NpcAttemptPolicy | None = None
    targets: tuple[NpcIntentTarget, ...] = ()

    def __post_init__(self) -> None:
        target_ids = tuple(target.id for target in self.targets)
        if len(target_ids) != len(set(target_ids)):
            raise ValueError(f"NPC intent {self.intent} cannot repeat target ids.")

    def target(self, target_id: str) -> NpcIntentTarget | None:
        normalized = target_id.strip().lower()
        return next((target for target in self.targets if target.id == normalized), None)

    def as_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "status": self.status,
            "notes": self.notes,
            "unlock_if_flags": list(self.unlock_if_flags),
            "reveals": list(self.reveals),
            "uses_social_reaction": self.uses_social_reaction,
        }
        if self.limits:
            payload["limits"] = self.limits
        if self.consequences:
            payload["consequences"] = self.consequences
        if self.attempt_policy is not None:
            payload["attempt_policy"] = self.attempt_policy.as_payload()
        if self.targets:
            payload["targets"] = [target.as_payload() for target in self.targets]
        if self.state_on_success is not None:
            payload["state_on_success"] = _npc_state_update_payload(self.state_on_success)
        if self.state_on_failure is not None:
            payload["state_on_failure"] = _npc_state_update_payload(self.state_on_failure)
        return payload


@dataclass(frozen=True, slots=True)
class NpcInteractionPolicy:
    allowed_actions: tuple[str, ...] = ()
    intent_permissions: tuple[NpcIntentPermission, ...] = ()
    allowed_flags: tuple[str, ...] = ()
    allowed_effect_types: tuple[str, ...] = ("set_flag",)
    allowed_abilities: tuple[str, ...] = ()
    allowed_skills: tuple[str, ...] = ()
    dc_min: int = 5
    dc_max: int = 25

    @property
    def allowed_intents(self) -> tuple[str, ...]:
        return tuple(item.intent for item in self.intent_permissions if item.status != "blocked")

    def intent_permission(self, intent: str) -> NpcIntentPermission | None:
        normalized = intent.strip().lower()
        for item in self.intent_permissions:
            if item.intent == normalized:
                return item
        return None

    def as_payload(self) -> dict[str, object]:
        return {
            "allowed_actions": list(self.allowed_actions),
            "intent_permissions": {
                permission.intent: permission.as_payload()
                for permission in self.intent_permissions
            },
            "allowed_flags": list(self.allowed_flags),
            "allowed_effect_types": list(self.allowed_effect_types),
            "allowed_abilities": list(self.allowed_abilities),
            "allowed_skills": list(self.allowed_skills),
            "dc_range": [self.dc_min, self.dc_max],
        }


@dataclass(frozen=True, slots=True)
class NpcInteraction:
    id: str
    name: str
    public_description: str
    gm_context: str = ""
    personality: str = ""
    current_state: str = ""
    initial_attitude: NpcAttitude = NpcAttitude.INDIFFERENT
    initial_physical_state: str = ""
    initial_emotional_state: str = ""
    dialogue_intro: str = ""
    capabilities: tuple[str, ...] = ()
    locked_information: tuple[NpcLockedInformation, ...] = ()
    policy: NpcInteractionPolicy = NpcInteractionPolicy()

    def as_payload(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "public_description": self.public_description,
            "gm_context": self.gm_context,
            "personality": self.personality,
            "current_state": self.current_state,
            "initial_runtime_state": {
                "attitude": self.initial_attitude.value,
                "physical_state": self.initial_physical_state,
                "emotional_state": self.initial_emotional_state,
            },
            "dialogue_intro": self.dialogue_intro,
            "capabilities": list(self.capabilities),
            "locked_information": [info.as_payload() for info in self.locked_information],
            "policy": self.policy.as_payload(),
        }


@dataclass(frozen=True, slots=True)
class ExplorationPoint:
    id: str
    name: str
    zone_id: str
    positions: tuple[Coordinate, ...]
    color: tuple[int, int, int]
    visibility: SetupVisibility = SetupVisibility.VISIBLE
    description: str = ""
    requires_setup: bool = True
    npc_interaction: NpcInteraction | None = None


@dataclass(frozen=True, slots=True)
class PartyPosition:
    zone_id: str
    marker_position: Coordinate | None = None


@dataclass(frozen=True, slots=True)
class PartyCheckInput:
    actor: Actor
    natural_roll: int
    request: D20RollRequest
    natural_roll_2: int | None = None


@dataclass(frozen=True, slots=True)
class ExplorationSituationalModifier:
    label: str
    modifier: int = 0
    source: ExplorationSituationalModifierSource = ExplorationSituationalModifierSource.GM
    reason: str = ""
    roll_mode: RollMode = RollMode.NORMAL

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("Situational modifier label cannot be empty.")
        if not -2 <= int(self.modifier) <= 2:
            raise ValueError("Situational modifier must be between -2 and +2.")
        if not self.reason.strip():
            raise ValueError("Situational modifier reason cannot be empty.")

    def as_roll_modifier(self) -> RollModifier | None:
        if self.modifier == 0:
            return None
        return RollModifier(
            self.label,
            self.modifier,
            RollModifierType.SITUATIONAL,
            stacking_key=f"exploration_situational:{self.source.value}:{self.label.strip().lower()}",
        )

    def as_payload(self) -> dict[str, object]:
        return {
            "label": self.label,
            "modifier": self.modifier,
            "source": self.source.value,
            "reason": self.reason,
            "roll_mode": self.roll_mode.value,
        }


@dataclass(frozen=True, slots=True)
class ImprovisedToolUse:
    label: str
    source: ExplorationSituationalModifierSource
    source_detail: str
    source_id: str | None = None
    effect_modifier: int = 1
    risk: str = ""
    reason: str = ""

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("Improvised tool label cannot be empty.")
        if not self.source_detail.strip():
            raise ValueError("Improvised tool source_detail cannot be empty.")
        if self.source_id is not None and not self.source_id.strip():
            raise ValueError("Improvised tool source_id cannot be empty.")
        if not -2 <= int(self.effect_modifier) <= 2:
            raise ValueError("Improvised tool effect modifier must be between -2 and +2.")
        if self.effect_modifier == 0:
            raise ValueError("Improvised tool must have a non-zero effect modifier.")
        if not self.reason.strip():
            raise ValueError("Improvised tool reason cannot be empty.")

    def as_roll_modifier(self) -> RollModifier:
        return RollModifier(
            self.label,
            self.effect_modifier,
            RollModifierType.SITUATIONAL,
            stacking_key=f"exploration_improvised_tool:{self.source.value}:{self.label.strip().lower()}",
        )

    def as_payload(self) -> dict[str, object]:
        return {
            "label": self.label,
            "source": self.source.value,
            "source_detail": self.source_detail,
            "source_id": self.source_id,
            "effect_modifier": self.effect_modifier,
            "risk": self.risk,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class PartyCheckResult:
    rolls: tuple[tuple[Actor, D20RollResult], ...]
    winner: Actor
    winning_roll: D20RollResult
    dc: int
    success: bool


@dataclass(frozen=True, slots=True)
class ExplorationCheckPlan:
    participants: CheckParticipants
    aggregation: CheckAggregation
    consequence_targets: tuple[ConsequenceTarget, ...]
    ability: str
    dc: int
    skill: str | None = None
    tool: str | None = None
    tool_label: str = ""
    lead_actor_id: str | None = None
    helper_actor_id: str | None = None
    selected_actor_ids: tuple[str, ...] = ()
    reason_for_players: str = ""
    roll_mode: RollMode = RollMode.NORMAL
    situational_modifiers: tuple[ExplorationSituationalModifier, ...] = ()
    improvised_tool: ImprovisedToolUse | None = None
    roll_modifiers_by_actor_id: tuple[tuple[str, tuple[RollModifier, ...]], ...] = ()
    option_bonus_payloads: tuple[dict[str, object], ...] = ()
    resource_payload: dict[str, object] | None = None
    mechanic_payload: dict[str, object] | None = None

    def as_payload(self) -> dict[str, object]:
        return {
            "participants": self.participants.value,
            "aggregation": self.aggregation.value,
            "consequence_targets": [target.value for target in self.consequence_targets],
            "lead_actor_id": self.lead_actor_id,
            "helper_actor_id": self.helper_actor_id,
            "selected_actor_ids": list(self.selected_actor_ids),
            "ability": self.ability,
            "skill": self.skill,
            "tool": self.tool,
            "tool_label": self.tool_label,
            "dc": self.dc,
            "reason_for_players": self.reason_for_players,
            "roll_mode": self.roll_mode.value,
            "situational_modifiers": [modifier.as_payload() for modifier in self.situational_modifiers],
            "improvised_tool": self.improvised_tool.as_payload() if self.improvised_tool else None,
            "roll_modifiers_by_actor_id": [
                {"actor_id": actor_id, "modifiers": [_roll_modifier_payload(modifier) for modifier in modifiers]}
                for actor_id, modifiers in self.roll_modifiers_by_actor_id
            ],
            "option_bonuses": list(self.option_bonus_payloads),
            "resource": self.resource_payload,
            "mechanic": self.mechanic_payload,
        }


@dataclass(frozen=True, slots=True)
class ExplorationCheckResult:
    plan: ExplorationCheckPlan
    rolls: tuple[tuple[Actor, D20RollResult], ...]
    success: bool
    selected_actor: Actor
    selected_roll: D20RollResult
    successful_actors: tuple[Actor, ...]
    failed_actors: tuple[Actor, ...]
    consequence_actors: tuple[Actor, ...]
    progress_total: int = 0

    def as_payload(self) -> dict[str, object]:
        return {
            "plan": self.plan.as_payload(),
            "success": self.success,
            "selected_actor_id": str(self.selected_actor.id),
            "selected_total": self.selected_roll.total,
            "successful_actor_ids": [str(actor.id) for actor in self.successful_actors],
            "failed_actor_ids": [str(actor.id) for actor in self.failed_actors],
            "consequence_actor_ids": [str(actor.id) for actor in self.consequence_actors],
            "progress_total": self.progress_total,
            "rolls": [
                {
                    "actor_id": str(actor.id),
                    "natural_roll": roll.natural_roll,
                    "total": roll.total,
                    "modifier_total": roll.breakdown.modifier_total,
                    "active_modifiers": [_roll_modifier_payload(modifier) for modifier in roll.breakdown.active_modifiers],
                    "ignored_modifiers": [_roll_modifier_payload(modifier) for modifier in roll.breakdown.ignored_modifiers],
                }
                for actor, roll in self.rolls
            ],
        }


@dataclass(frozen=True, slots=True)
class ItemBreakageRisk:
    chance_percent: int
    trigger: str = "critical_failure"

    def __post_init__(self) -> None:
        if not 0 <= self.chance_percent <= 100:
            raise ValueError("Item breakage chance must be between 0 and 100.")


@dataclass(frozen=True, slots=True)
class ExplorationOptionBonus:
    source_type: str
    source_id: str
    label: str
    modifier: int = 0
    spell_level: int = 0
    consume: bool = False
    breakage_risk: ItemBreakageRisk | None = None

    def __post_init__(self) -> None:
        if self.spell_level < 0:
            raise ValueError("Exploration spell bonus level cannot be negative.")

    def as_roll_modifier(self) -> RollModifier | None:
        if self.modifier == 0:
            return None
        modifier_type = RollModifierType.ITEM if self.source_type == "item" else RollModifierType.SITUATIONAL
        return RollModifier(
            self.label,
            self.modifier,
            modifier_type,
            stacking_key=f"exploration_bonus:{self.source_type}:{self.source_id}",
        )

    def as_payload(self) -> dict[str, object]:
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "label": self.label,
            "modifier": self.modifier,
            "spell_level": self.spell_level,
            "consume": self.consume,
            "breakage_risk": (
                {
                    "chance_percent": self.breakage_risk.chance_percent,
                    "trigger": self.breakage_risk.trigger,
                }
                if self.breakage_risk is not None
                else None
            ),
        }


class ExplorationHazardTrigger(StrEnum):
    FAILURE = "failure"
    CRITICAL_FAILURE = "critical_failure"


@dataclass(frozen=True, slots=True)
class ExplorationHazardDamage:
    damage_type: str
    fixed: int | None = None
    die_sides: int | None = None
    modifier: int = 0

    def __post_init__(self) -> None:
        if self.fixed is None and self.die_sides is None:
            raise ValueError("Exploration hazard damage requires fixed damage or one die.")
        if self.fixed is not None and self.die_sides is not None:
            raise ValueError("Exploration hazard damage cannot define both fixed and dice.")
        if self.fixed is not None and self.fixed < 0:
            raise ValueError("Exploration hazard fixed damage cannot be negative.")
        if self.die_sides is not None and self.die_sides < 2:
            raise ValueError("Exploration hazard damage die must have at least two sides.")

    def as_payload(self) -> dict[str, object]:
        return {
            "damage_type": self.damage_type,
            "fixed": self.fixed,
            "dice": f"1d{self.die_sides}" if self.die_sides is not None else None,
            "modifier": self.modifier,
        }


@dataclass(frozen=True, slots=True)
class ExplorationHazard:
    id: str
    label: str
    trigger: ExplorationHazardTrigger
    saving_throw: SavingThrowRequest
    damage: ExplorationHazardDamage
    narration: str = ""
    success_message: str = ""
    failure_message: str = ""
    success_effects: tuple[dict[str, object], ...] = ()
    failure_effects: tuple[dict[str, object], ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.label.strip():
            raise ValueError("Exploration hazard id and label cannot be empty.")

    def as_payload(self) -> dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "trigger": self.trigger.value,
            "saving_throw": self.saving_throw.as_payload(),
            "damage": self.damage.as_payload(),
            "narration": self.narration,
            "success_message": self.success_message,
            "failure_message": self.failure_message,
            "success_effects": list(self.success_effects),
            "failure_effects": list(self.failure_effects),
        }


class ExplorationTrapStatus(StrEnum):
    HIDDEN = "hidden"
    REVEALED = "revealed"
    DISARMED = "disarmed"
    BYPASSED = "bypassed"
    TRIGGERED = "triggered"


class ExplorationTrapAction(StrEnum):
    DISARM = "disarm"
    BYPASS = "bypass"
    TRIGGER = "trigger"


@dataclass(frozen=True, slots=True)
class ExplorationTrap:
    id: str
    zone_id: str
    name: str
    revealed_description: str
    detection_observation_id: str
    hazard: ExplorationHazard
    activation_challenge_id: str | None = None
    disarm_check: SceneAbilityCheck | None = None
    bypass_check: SceneAbilityCheck | None = None
    required_item_id: str | None = None
    disarm_intent_examples: tuple[str, ...] = ()
    bypass_intent_examples: tuple[str, ...] = ()
    trigger_intent_examples: tuple[str, ...] = ()
    disarm_success_message: str = "Pułapka została rozbrojona."
    bypass_success_message: str = "Drużyna bezpiecznie omija pułapkę."

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.zone_id.strip() or not self.name.strip():
            raise ValueError("Exploration trap id, zone_id and name cannot be empty.")
        if not self.revealed_description.strip() or not self.detection_observation_id.strip():
            raise ValueError(f"Exploration trap {self.id} requires reveal text and detection observation.")


@dataclass(frozen=True, slots=True)
class ExplorationTrapState:
    trap_id: str
    status: ExplorationTrapStatus = ExplorationTrapStatus.HIDDEN

    def __post_init__(self) -> None:
        if not self.trap_id.strip():
            raise ValueError("Exploration trap state id cannot be empty.")

@dataclass(frozen=True, slots=True)
class SearchResult:
    state: ExplorationState
    party_check: PartyCheckResult
    revealed_points: tuple[ExplorationPoint, ...]
    message: str


@dataclass(frozen=True, slots=True)
class ExplorationChallengeOption:
    id: str
    label: str
    ability_check: SceneAbilityCheck
    progress_on_success: int
    progress_on_failure: int
    color: tuple[int, int, int]
    description: str = ""
    success_message: str = ""
    failure_message: str = ""
    critical_failure_message: str = ""
    tags: tuple[str, ...] = ()
    unlocks_if_flag: str | None = None
    unlocks_if_resource_id: str | None = None
    success_noise: int = 0
    failure_noise: int = 0
    critical_failure_noise: int = 0
    quiet_success_margin: int | None = None
    quiet_on_natural_20: bool = False
    success_complication: str | None = None
    failure_complication: str | None = None
    critical_failure_complication: str | None = None
    check_participants: CheckParticipants | None = None
    check_aggregation: CheckAggregation | None = None
    consequence_targets: tuple[ConsequenceTarget, ...] = ()
    requires_item_ids: tuple[str, ...] = ()
    requires_spell_ids: tuple[str, ...] = ()
    requires_ability_scores: tuple[tuple[str, int], ...] = ()
    bonuses: tuple[ExplorationOptionBonus, ...] = ()
    mechanic_id: str | None = None
    roll_mode: RollMode = RollMode.NORMAL
    situational_modifiers: tuple[ExplorationSituationalModifier, ...] = ()
    improvised_tool: ImprovisedToolUse | None = None
    hazards: tuple[ExplorationHazard, ...] = ()


@dataclass(frozen=True, slots=True)
class ExplorationChallenge:
    id: str
    zone_id: str
    name: str
    progress_required: int
    completed_flag: str
    options: tuple[ExplorationChallengeOption, ...]
    reveals_on_complete: tuple[str, ...] = ()
    llm_context: LlmContext = LlmContext()
    llm_policy: LlmChallengePolicy = LlmChallengePolicy()


@dataclass(frozen=True, slots=True)
class ExplorationChallengeAttempt:
    challenge_id: str
    option_id: str
    approach_label: str
    approach_tags: tuple[str, ...]
    resource_id: str | None
    natural_roll: int
    total: int
    success: bool
    critical_failure: bool
    progress_added: int
    noise_added: int
    complications_added: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExplorationChallengeState:
    challenge_id: str
    current_progress: int = 0
    noise: int = 0
    complications: tuple[str, ...] = ()
    completed: bool = False
    attempts: tuple[ExplorationChallengeAttempt, ...] = ()


@dataclass(frozen=True, slots=True)
class ExplorationResource:
    id: str
    label: str
    bonus_tags: tuple[str, ...]
    modifier: int = 0
    advantage: bool = False
    mitigates_complications: tuple[str, ...] = ()
    mitigates_noise: int = 0
    unlocks_flags: tuple[str, ...] = ()
    consume_on_use: bool = False
    properties: tuple[str, ...] = ()
    portable: bool = True

    def as_roll_modifier(self) -> RollModifier | None:
        if self.modifier == 0:
            return None
        return RollModifier(
            self.label,
            self.modifier,
            RollModifierType.ITEM,
            stacking_key=f"exploration_resource:{self.id}",
        )


class CraftingComponentDisposition(StrEnum):
    CONSUMED = "consumed"
    RESERVED = "reserved"


class TemporaryItemScope(StrEnum):
    INTERACTION = "interaction"
    SCENE = "scene"
    SCENARIO = "scenario"


@dataclass(frozen=True, slots=True)
class CraftingComponentUse:
    source_id: str
    quantity: int
    disposition: CraftingComponentDisposition

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("Crafting component source_id cannot be empty.")
        if self.quantity < 1:
            raise ValueError("Crafting component quantity must be positive.")


@dataclass(frozen=True, slots=True)
class TemporaryItem:
    id: str
    template_id: str | None
    label: str
    description: str
    bonus_tags: tuple[str, ...]
    modifier: int
    advantage: bool
    uses_remaining: int
    created_in_zone_id: str
    source_materials: tuple[str, ...] = ()
    risk: str = ""
    purpose_id: str | None = None
    component_uses: tuple[CraftingComponentUse, ...] = ()
    scope: TemporaryItemScope = TemporaryItemScope.SCENARIO
    time_cost_minutes: int = 0
    dismantled: bool = False

    @property
    def available(self) -> bool:
        return self.uses_remaining > 0 and not self.dismantled

    def as_resource(self) -> ExplorationResource:
        return ExplorationResource(
            id=self.id,
            label=self.label,
            bonus_tags=self.bonus_tags,
            modifier=self.modifier,
            advantage=self.advantage,
        )


class EncounterEdgeType(StrEnum):
    INITIATIVE_ADVANTAGE = "initiative_advantage"


@dataclass(frozen=True, slots=True)
class EncounterEdge:
    id: str
    edge_type: EncounterEdgeType
    label: str
    beneficiary_actor_id: str
    encounter_trigger_id: str
    source_observation_id: str
    source_fact_id: str
    consumed: bool = False

    def __post_init__(self) -> None:
        required = {
            "id": self.id,
            "label": self.label,
            "beneficiary_actor_id": self.beneficiary_actor_id,
            "encounter_trigger_id": self.encounter_trigger_id,
            "source_observation_id": self.source_observation_id,
            "source_fact_id": self.source_fact_id,
        }
        for field_name, value in required.items():
            if not value.strip():
                raise ValueError(f"Encounter edge {field_name} cannot be empty.")


@dataclass(frozen=True, slots=True)
class ChallengeResult:
    state: ExplorationState
    challenge: ExplorationChallenge
    option: ExplorationChallengeOption
    roll: D20RollResult
    success: bool
    critical_failure: bool
    progress_added: int
    noise_added: int
    complications_added: tuple[str, ...]
    completed: bool
    message: str
    resource_used: ExplorationResource | None = None


@dataclass(frozen=True, slots=True)
class SceneSourceDiscovery:
    """Player knowledge that a concrete source was found in a scene."""

    source_id: str
    zone_id: str
    requested_as: str = ""
    purpose: str = ""
    matched_properties: tuple[str, ...] = ()
    semantic_substitution: bool = False

    def __post_init__(self) -> None:
        if not self.source_id.strip() or not self.zone_id.strip():
            raise ValueError("Scene source discovery ids cannot be empty.")
        if len(self.matched_properties) != len(set(self.matched_properties)):
            raise ValueError("Scene source discovery properties cannot contain duplicates.")


@dataclass(frozen=True, slots=True)
class SceneSourceCollection:
    """Persistent transfer of a concrete source out of its exploration location."""

    source_id: str
    zone_id: str
    quantity: int
    destination: str
    label: str
    owner_actor_id: str | None = None

    def __post_init__(self) -> None:
        if not self.source_id.strip() or not self.zone_id.strip():
            raise ValueError("Collected scene source ids cannot be empty.")
        if self.quantity < 1:
            raise ValueError("Collected scene source quantity must be positive.")
        if not self.destination.strip() or not self.label.strip():
            raise ValueError("Collected scene source destination and label cannot be empty.")


@dataclass(frozen=True, slots=True)
class FixtureRuntimeState:
    zone_id: str
    fixture_id: str
    condition: str
    unavailable: bool = False
    detached: bool = False
    destroyed: bool = False
    released_item_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.zone_id.strip() or not self.fixture_id.strip() or not self.condition.strip():
            raise ValueError("Fixture runtime state ids and condition cannot be empty.")
        if len(self.released_item_ids) != len(set(self.released_item_ids)):
            raise ValueError("Fixture runtime released item ids cannot contain duplicates.")


@dataclass(frozen=True, slots=True)
class ExplorationState:
    zones: tuple[ExplorationZone, ...]
    points: tuple[ExplorationPoint, ...]
    party_position: PartyPosition
    flags: SceneFlags = SceneFlags()
    exhausted_search_zones: tuple[str, ...] = ()
    challenges: tuple[ExplorationChallenge, ...] = ()
    challenge_states: tuple[ExplorationChallengeState, ...] = ()
    resources: tuple[ExplorationResource, ...] = ()
    inventory_resource_ids: tuple[str, ...] = ()
    elapsed_minutes: int = 0
    short_rest_counts: tuple[tuple[str, int], ...] = ()
    temporary_items: tuple[TemporaryItem, ...] = ()
    encounter_edges: tuple[EncounterEdge, ...] = ()
    source_discoveries: tuple[SceneSourceDiscovery, ...] = ()
    source_collections: tuple[SceneSourceCollection, ...] = ()
    fixture_states: tuple[FixtureRuntimeState, ...] = ()
    condition_states: tuple[ConditionState, ...] = ()
    traps: tuple[ExplorationTrap, ...] = ()
    trap_states: tuple[ExplorationTrapState, ...] = ()
    npc_states: tuple[NpcRuntimeState, ...] = ()

    def __post_init__(self) -> None:
        known_npcs = {
            point.npc_interaction.id: point.npc_interaction
            for point in self.points
            if point.npc_interaction is not None
        }
        if not self.npc_states and known_npcs:
            object.__setattr__(
                self,
                "npc_states",
                tuple(
                    NpcRuntimeState(
                        npc_id=npc.id,
                        attitude=npc.initial_attitude,
                        physical_state=npc.initial_physical_state or npc.current_state,
                        emotional_state=npc.initial_emotional_state,
                    )
                    for npc in known_npcs.values()
                ),
            )
        npc_ids = tuple(state.npc_id for state in self.npc_states)
        if len(npc_ids) != len(set(npc_ids)):
            raise ValueError("Exploration NPC runtime state ids must be unique.")
        if set(npc_ids) - set(known_npcs):
            raise ValueError("Exploration state contains an unknown NPC runtime state.")


def add_exploration_condition(
    state: ExplorationState,
    actor_id: str,
    condition: CombatCondition,
) -> ExplorationState:
    return replace(
        state,
        condition_states=add_condition(state.condition_states, actor_id, condition),
    )


def remove_exploration_condition(
    state: ExplorationState,
    actor_id: str,
    condition: CombatCondition,
) -> ExplorationState:
    return replace(
        state,
        condition_states=remove_condition(state.condition_states, actor_id, condition),
    )


def grant_encounter_edge(state: ExplorationState, edge: EncounterEdge) -> ExplorationState:
    """Add an encounter edge once, keeping repeated observation attempts idempotent."""

    remaining = tuple(item for item in state.encounter_edges if item.id != edge.id)
    return replace(state, encounter_edges=(*remaining, edge))


def available_encounter_edges(
    state: ExplorationState,
    encounter_trigger_id: str,
) -> tuple[EncounterEdge, ...]:
    return tuple(
        edge
        for edge in state.encounter_edges
        if edge.encounter_trigger_id == encounter_trigger_id and not edge.consumed
    )


def consume_encounter_edge(state: ExplorationState, edge_id: str) -> ExplorationState:
    return replace(
        state,
        encounter_edges=tuple(
            replace(edge, consumed=True) if edge.id == edge_id else edge
            for edge in state.encounter_edges
        ),
    )


def visible_exploration_zones(zones: tuple[ExplorationZone, ...]) -> tuple[ExplorationZone, ...]:
    return tuple(zone for zone in zones if zone.visibility == SetupVisibility.VISIBLE and zone.positions)


def available_exploration_zones(state: ExplorationState) -> tuple[ExplorationZone, ...]:
    return tuple(zone for zone in visible_exploration_zones(state.zones) if zone_is_available(state, zone))


def zone_is_available(state: ExplorationState, zone: ExplorationZone) -> bool:
    if zone.available_if_flag is None:
        return True
    return scene_flag(state.flags, zone.available_if_flag) == zone.available_if_value


def challenge_for_zone(state: ExplorationState, zone_id: str) -> ExplorationChallenge | None:
    for challenge in state.challenges:
        if challenge.zone_id == zone_id:
            return challenge
    return None


def challenge_state_for(state: ExplorationState, challenge_id: str) -> ExplorationChallengeState:
    for challenge_state in state.challenge_states:
        if challenge_state.challenge_id == challenge_id:
            return challenge_state
    return ExplorationChallengeState(challenge_id)


def available_challenge_options(
    state: ExplorationState,
    challenge: ExplorationChallenge,
) -> tuple[ExplorationChallengeOption, ...]:
    if challenge_state_for(state, challenge.id).completed:
        return ()
    result: list[ExplorationChallengeOption] = []
    for option in challenge.options:
        llm_unlocked = scene_flag(state.flags, f"llm_unlocked_option:{option.id}", False)
        if option.unlocks_if_flag is not None and not scene_flag(state.flags, option.unlocks_if_flag, False) and not llm_unlocked:
            continue
        if (
            option.unlocks_if_resource_id is not None
            and option.unlocks_if_resource_id not in state.inventory_resource_ids
            and not llm_unlocked
        ):
            continue
        result.append(option)
    return tuple(result)


def available_challenge_options_for_actors(
    state: ExplorationState,
    challenge: ExplorationChallenge,
    actors: tuple[Actor, ...],
) -> tuple[ExplorationChallengeOption, ...]:
    return tuple(
        option
        for option in available_challenge_options(state, challenge)
        if not challenge_option_requires_actor(option) or actors_matching_challenge_option(actors, option)
    )


def challenge_option_requires_actor(option: ExplorationChallengeOption) -> bool:
    return bool(option.requires_item_ids or option.requires_spell_ids or option.requires_ability_scores)


def actors_matching_challenge_option(
    actors: tuple[Actor, ...],
    option: ExplorationChallengeOption,
) -> tuple[Actor, ...]:
    return tuple(actor for actor in actors if actor_meets_challenge_option_requirements(actor, option))


def actor_meets_challenge_option_requirements(actor: Actor, option: ExplorationChallengeOption) -> bool:
    inventory_ids = {item.id for item in actor.inventory if item.available}
    if any(item_id not in inventory_ids for item_id in option.requires_item_ids):
        return False
    if any(not _actor_can_use_exploration_spell(actor, option, spell_id) for spell_id in option.requires_spell_ids):
        return False
    for ability, minimum in option.requires_ability_scores:
        if getattr(actor.ability_scores, ability, 0) < minimum:
            return False
    return True


def active_option_bonuses_for_actor(actor: Actor, option: ExplorationChallengeOption) -> tuple[ExplorationOptionBonus, ...]:
    inventory_ids = {item.id for item in actor.inventory if item.available}
    spell_ids = set(actor.spell_ids)
    result: list[ExplorationOptionBonus] = []
    for bonus in option.bonuses:
        if bonus.source_type == "item" and bonus.source_id in inventory_ids:
            result.append(bonus)
        elif (
            bonus.source_type == "spell"
            and bonus.source_id in spell_ids
            and _actor_has_prepared_spell_for_bonus(actor, bonus)
            and _actor_has_spell_slot_for_bonus(actor, bonus)
        ):
            result.append(bonus)
    return tuple(result)


def option_roll_modifiers_for_actor(actor: Actor, option: ExplorationChallengeOption) -> tuple[RollModifier, ...]:
    return tuple(
        modifier
        for bonus in active_option_bonuses_for_actor(actor, option)
        for modifier in (bonus.as_roll_modifier(),)
        if modifier is not None
    )


def _actor_can_use_exploration_spell(actor: Actor, option: ExplorationChallengeOption, spell_id: str) -> bool:
    if spell_id not in set(actor.spell_ids):
        return False
    matching_bonuses = tuple(bonus for bonus in option.bonuses if bonus.source_type == "spell" and bonus.source_id == spell_id)
    return all(
        _actor_has_prepared_spell_for_bonus(actor, bonus)
        and _actor_has_spell_slot_for_bonus(actor, bonus)
        for bonus in matching_bonuses
    )


def _actor_has_prepared_spell_for_bonus(actor: Actor, bonus: ExplorationOptionBonus) -> bool:
    casting_kind = "cantrip" if bonus.spell_level <= 0 else "leveled"
    return spell_is_prepared(
        actor.spell_preparation,
        bonus.source_id,
        casting_kind=casting_kind,
    )


def _actor_has_spell_slot_for_bonus(actor: Actor, bonus: ExplorationOptionBonus) -> bool:
    if bonus.spell_level <= 0:
        return True
    return any(slot.level == bonus.spell_level and slot.remaining > 0 for slot in actor.spell_slots)


def matching_resources(
    state: ExplorationState,
    option: ExplorationChallengeOption,
) -> tuple[ExplorationResource, ...]:
    option_tags = set(option.tags)
    owned = set(state.inventory_resource_ids)
    persistent = tuple(
        resource
        for resource in state.resources
        if resource.id in owned
        and (option_tags.intersection(resource.bonus_tags) or resource.id == option.unlocks_if_resource_id)
    )
    collected_source_ids = {item.source_id for item in state.source_collections}
    temporary = tuple(
        item.as_resource()
        for item in state.temporary_items
        if item.available
        and f"temporary:{item.id}" not in collected_source_ids
        and option_tags.intersection(item.bonus_tags)
    )
    return (*persistent, *temporary)


def create_temporary_item(
    state: ExplorationState,
    template: TemporaryItemTemplate,
    *,
    zone_id: str,
    source_materials: tuple[str, ...],
) -> tuple[ExplorationState, TemporaryItem]:
    if template.uses < 1:
        raise ValueError("Temporary item template must provide at least one use.")
    if zone_id not in {zone.id for zone in state.zones}:
        raise ValueError(f"Unknown exploration zone for temporary item: {zone_id}.")
    if not source_materials:
        raise ValueError("Temporary item requires at least one source material.")
    unsupported_materials = set(source_materials) - set(template.allowed_materials)
    if unsupported_materials:
        raise ValueError(
            "Temporary item template does not allow materials: "
            + ", ".join(sorted(unsupported_materials))
            + "."
        )
    if any(existing.template_id == template.id for existing in state.temporary_items):
        raise ValueError(f"Temporary item was already created in this scenario: {template.id}.")
    item = TemporaryItem(
        id=f"temporary:{template.id}",
        template_id=template.id,
        label=template.label,
        description=template.description,
        bonus_tags=template.bonus_tags,
        modifier=template.modifier,
        advantage=template.advantage,
        uses_remaining=template.uses,
        created_in_zone_id=zone_id,
        source_materials=source_materials,
        risk=template.risk,
    )
    return replace(state, temporary_items=(*state.temporary_items, item)), item


def use_temporary_item(state: ExplorationState, item_id: str) -> tuple[ExplorationState, TemporaryItem]:
    item = next((candidate for candidate in state.temporary_items if candidate.id == item_id), None)
    if item is None:
        raise ValueError(f"Unknown temporary item: {item_id}.")
    if not item.available:
        raise ValueError(f"Temporary item has no uses remaining: {item_id}.")
    updated = replace(item, uses_remaining=item.uses_remaining - 1)
    items = tuple(updated if candidate.id == item_id else candidate for candidate in state.temporary_items)
    return replace(state, temporary_items=items), updated


def grant_resource(state: ExplorationState, resource_id: str) -> ExplorationState:
    if resource_id in state.inventory_resource_ids:
        return state
    resource = next((candidate for candidate in state.resources if candidate.id == resource_id), None)
    if resource is None:
        raise ValueError(f"Unknown exploration resource: {resource_id}.")
    flags = state.flags
    for flag in resource.unlocks_flags:
        flags = set_scene_flag(flags, flag, True)
    return replace(state, flags=flags, inventory_resource_ids=tuple(sorted((*state.inventory_resource_ids, resource_id))))


def remove_resource(state: ExplorationState, resource_id: str) -> ExplorationState:
    resource = next((candidate for candidate in state.resources if candidate.id == resource_id), None)
    if resource is None:
        raise ValueError(f"Unknown exploration resource: {resource_id}.")
    if resource_id not in state.inventory_resource_ids:
        return state
    return replace(
        state,
        inventory_resource_ids=tuple(
            owned_resource_id
            for owned_resource_id in state.inventory_resource_ids
            if owned_resource_id != resource_id
        ),
    )


def reveal_exploration_points(
    state: ExplorationState,
    point_ids: tuple[str, ...],
) -> tuple[ExplorationState, tuple[ExplorationPoint, ...]]:
    requested = set(point_ids)
    if not requested:
        return state, ()
    unknown = requested - {point.id for point in state.points}
    if unknown:
        raise ValueError(f"Unknown exploration points: {', '.join(sorted(unknown))}.")
    revealed: list[ExplorationPoint] = []
    points: list[ExplorationPoint] = []
    for point in state.points:
        if point.id in requested and point.visibility != SetupVisibility.VISIBLE:
            updated = replace(point, visibility=SetupVisibility.VISIBLE)
            points.append(updated)
            revealed.append(updated)
        else:
            points.append(point)
    return replace(state, points=tuple(points)), tuple(revealed)


def resolve_challenge_option(
    state: ExplorationState,
    challenge: ExplorationChallenge,
    option: ExplorationChallengeOption,
    roll: D20RollResult,
    resource: ExplorationResource | None = None,
    negative_effect_reduction: int = 0,
    progress_boost_on_success: int = 0,
) -> ChallengeResult:
    if option not in available_challenge_options(state, challenge):
        raise ValueError(f"Challenge option {option.id} is not available.")
    current = challenge_state_for(state, challenge.id)
    if current.completed:
        raise ValueError(f"Challenge {challenge.id} is already completed.")
    check = resolve_ability_check(roll, option.ability_check.dc)
    success = check.success
    critical_failure = roll.is_natural_1 and not success
    raw_progress_added = option.progress_on_success + max(0, progress_boost_on_success) if success else option.progress_on_failure
    progress_added = min(challenge.progress_required - current.current_progress, raw_progress_added)
    progress = min(challenge.progress_required, current.current_progress + progress_added)
    completed = progress >= challenge.progress_required
    noise_added = _challenge_noise(option, roll, success, critical_failure)
    complications_added = _challenge_complications(option, success, critical_failure)
    if resource is not None:
        noise_added = max(0, noise_added - resource.mitigates_noise)
        mitigated = set(resource.mitigates_complications)
        complications_added = tuple(complication for complication in complications_added if complication not in mitigated)
    if negative_effect_reduction:
        noise_added = max(0, noise_added - negative_effect_reduction)

    complications = tuple(dict.fromkeys((*current.complications, *complications_added)))
    flags = state.flags
    if completed:
        flags = set_scene_flag(flags, challenge.completed_flag, True)
    if resource is not None:
        for flag in resource.unlocks_flags:
            flags = set_scene_flag(flags, flag, True)
    updated = ExplorationChallengeState(
        challenge_id=challenge.id,
        current_progress=progress,
        noise=current.noise + noise_added,
        complications=complications,
        completed=completed,
        attempts=(
            *current.attempts,
            ExplorationChallengeAttempt(
                challenge_id=challenge.id,
                option_id=option.id,
                approach_label=option.label,
                approach_tags=option.tags,
                resource_id=resource.id if resource is not None else None,
                natural_roll=roll.natural_roll,
                total=roll.total,
                success=success,
                critical_failure=critical_failure,
                progress_added=progress_added,
                noise_added=noise_added,
                complications_added=complications_added,
            ),
        ),
    )
    new_state = replace(state, flags=flags, challenge_states=_replace_challenge_state(state, updated))
    message = _challenge_result_message(challenge, option, roll, success, critical_failure, progress_added, updated, resource)
    return ChallengeResult(
        state=new_state,
        challenge=challenge,
        option=option,
        roll=roll,
        success=success,
        critical_failure=critical_failure,
        progress_added=progress_added,
        noise_added=noise_added,
        complications_added=complications_added,
        completed=completed,
        message=message,
        resource_used=resource,
    )


def _replace_challenge_state(
    state: ExplorationState,
    updated: ExplorationChallengeState,
) -> tuple[ExplorationChallengeState, ...]:
    replaced = False
    result: list[ExplorationChallengeState] = []
    for challenge_state in state.challenge_states:
        if challenge_state.challenge_id == updated.challenge_id:
            result.append(updated)
            replaced = True
        else:
            result.append(challenge_state)
    if not replaced:
        result.append(updated)
    return tuple(sorted(result, key=lambda item: item.challenge_id))


def _challenge_noise(
    option: ExplorationChallengeOption,
    roll: D20RollResult,
    success: bool,
    critical_failure: bool,
) -> int:
    if success:
        if option.quiet_on_natural_20 and roll.is_natural_20:
            return 0
        if option.quiet_success_margin is not None and roll.total >= option.ability_check.dc + option.quiet_success_margin:
            return 0
        return max(0, option.success_noise)
    if critical_failure and option.critical_failure_noise:
        return max(0, option.critical_failure_noise)
    return max(0, option.failure_noise)


def _challenge_complications(
    option: ExplorationChallengeOption,
    success: bool,
    critical_failure: bool,
) -> tuple[str, ...]:
    if success:
        return (option.success_complication,) if option.success_complication else ()
    if critical_failure and option.critical_failure_complication:
        return (option.critical_failure_complication,)
    return (option.failure_complication,) if option.failure_complication else ()


def _challenge_result_message(
    challenge: ExplorationChallenge,
    option: ExplorationChallengeOption,
    roll: D20RollResult,
    success: bool,
    critical_failure: bool,
    progress_added: int,
    updated: ExplorationChallengeState,
    resource: ExplorationResource | None,
) -> str:
    if critical_failure and option.critical_failure_message:
        base = option.critical_failure_message
    elif success:
        base = option.success_message or "Podejście działa."
    else:
        base = option.failure_message or "Podejście nie wychodzi czysto, ale sytuacja idzie naprzód."
    resource_text = f" Użyty zasób: {resource.label}." if resource is not None else ""
    noise_text = f" Hałas: {updated.noise}." if updated.noise else " Bez dodatkowego hałasu."
    complications_text = f" Komplikacje: {', '.join(updated.complications)}." if updated.complications else ""
    completed_text = " Wyzwanie zakończone." if updated.completed else ""
    return (
        f"{base}{resource_text} Wynik testu: {roll.total}. "
        f"Dodany postęp: {progress_added}. Postęp {challenge.name}: "
        f"{updated.current_progress}/{challenge.progress_required}.{noise_text}{complications_text}{completed_text}"
    )


def visible_exploration_points(points: tuple[ExplorationPoint, ...]) -> tuple[ExplorationPoint, ...]:
    return tuple(point for point in points if point.visibility == SetupVisibility.VISIBLE and point.positions)


def zone_for_position(zones: tuple[ExplorationZone, ...], position: Coordinate) -> ExplorationZone | None:
    for zone in zones:
        if position in zone.positions:
            return zone
    return None


def set_party_zone(state: ExplorationState, zone: ExplorationZone) -> ExplorationState:
    return replace(state, party_position=PartyPosition(zone.id, zone.marker_position))


def resolve_exploration_check(
    plan: ExplorationCheckPlan,
    inputs: tuple[PartyCheckInput, ...],
) -> ExplorationCheckResult:
    if not inputs:
        raise ValueError("Party check requires at least one roll.")
    rolls = tuple(
        (item.actor, resolve_d20_roll(D20RollInput(item.request, item.natural_roll, item.natural_roll_2)))
        for item in inputs
    )
    passed = tuple((actor, roll) for actor, roll in rolls if resolve_ability_check(roll, plan.dc).success)
    failed = tuple((actor, roll) for actor, roll in rolls if not resolve_ability_check(roll, plan.dc).success)
    if plan.aggregation in {CheckAggregation.HIGHEST, CheckAggregation.ANY_SUCCESS, CheckAggregation.SUM_PROGRESS}:
        selected_actor, selected_roll = max(rolls, key=lambda item: (item[1].total, item[1].natural_roll, item[0].name))
    elif plan.aggregation == CheckAggregation.LOWEST:
        selected_actor, selected_roll = min(rolls, key=lambda item: (item[1].total, item[1].natural_roll, item[0].name))
    else:
        lead_id = plan.lead_actor_id
        lead_entry = next(((actor, roll) for actor, roll in rolls if str(actor.id) == lead_id), None)
        if lead_entry is None:
            lead_entry = rolls[0]
        selected_actor, selected_roll = lead_entry

    if plan.aggregation == CheckAggregation.HIGHEST:
        success = resolve_ability_check(selected_roll, plan.dc).success
    elif plan.aggregation == CheckAggregation.LOWEST:
        success = resolve_ability_check(selected_roll, plan.dc).success
    elif plan.aggregation == CheckAggregation.MAJORITY:
        success = len(passed) >= ((len(rolls) + 1) // 2)
    elif plan.aggregation == CheckAggregation.ALL_MUST_SUCCEED:
        success = len(failed) == 0
    elif plan.aggregation == CheckAggregation.ANY_SUCCESS:
        success = len(passed) > 0
    elif plan.aggregation == CheckAggregation.SUM_PROGRESS:
        success = len(passed) > 0
    else:
        success = resolve_ability_check(selected_roll, plan.dc).success

    successful_actors = tuple(actor for actor, _roll in passed)
    failed_actors = tuple(actor for actor, _roll in failed)
    consequence_actors = _consequence_actors(plan, rolls, failed_actors)
    return ExplorationCheckResult(
        plan=plan,
        rolls=rolls,
        success=success,
        selected_actor=selected_actor,
        selected_roll=selected_roll,
        successful_actors=successful_actors,
        failed_actors=failed_actors,
        consequence_actors=consequence_actors,
        progress_total=len(passed) if plan.aggregation == CheckAggregation.SUM_PROGRESS else 0,
    )


def _consequence_actors(
    plan: ExplorationCheckPlan,
    rolls: tuple[tuple[Actor, D20RollResult], ...],
    failed_actors: tuple[Actor, ...],
) -> tuple[Actor, ...]:
    actors_by_id = {str(actor.id): actor for actor, _roll in rolls}
    result: list[Actor] = []
    for target in plan.consequence_targets:
        if target == ConsequenceTarget.LEAD_ACTOR and plan.lead_actor_id in actors_by_id:
            result.append(actors_by_id[str(plan.lead_actor_id)])
        elif target == ConsequenceTarget.HELPER_ACTOR and plan.helper_actor_id in actors_by_id:
            result.append(actors_by_id[str(plan.helper_actor_id)])
        elif target == ConsequenceTarget.FAILED_ACTORS:
            result.extend(failed_actors)
        elif target == ConsequenceTarget.WHOLE_PARTY:
            result.extend(actor for actor, _roll in rolls)
    unique: dict[str, Actor] = {}
    for actor in result:
        unique.setdefault(str(actor.id), actor)
    return tuple(unique.values())


def resolve_party_check(inputs: tuple[PartyCheckInput, ...], dc: int) -> PartyCheckResult:
    plan = ExplorationCheckPlan(
        participants=CheckParticipants.WHOLE_PARTY,
        aggregation=CheckAggregation.HIGHEST,
        consequence_targets=(ConsequenceTarget.SCENE,),
        ability="wisdom",
        dc=dc,
    )
    result = resolve_exploration_check(plan, inputs)
    return PartyCheckResult(result.rolls, result.selected_actor, result.selected_roll, dc, result.success)


def _roll_modifier_payload(modifier: RollModifier) -> dict[str, object]:
    return {
        "label": modifier.label,
        "value": modifier.value,
        "type": modifier.modifier_type.value,
        "stacking_key": modifier.stacking_key,
    }


def resolve_zone_search(
    state: ExplorationState,
    zone: ExplorationZone,
    inputs: tuple[PartyCheckInput, ...],
) -> SearchResult:
    if zone.id in state.exhausted_search_zones:
        raise ValueError(f"Zone {zone.id} has already been searched.")
    if zone.search_dc is None:
        raise ValueError(f"Zone {zone.id} has no search configured.")
    party_check = resolve_party_check(inputs, zone.search_dc)
    exhausted = tuple(sorted((*state.exhausted_search_zones, zone.id)))
    flags = state.flags
    revealed: tuple[ExplorationPoint, ...] = ()
    points = state.points
    if party_check.success:
        if zone.search_success_flag:
            flags = set_scene_flag(flags, zone.search_success_flag, True)
        revealed_ids = set(zone.search_reveals)
        points = tuple(
            replace(point, visibility=SetupVisibility.VISIBLE) if point.id in revealed_ids else point
            for point in state.points
        )
        revealed = tuple(point for point in points if point.id in revealed_ids)
        if revealed:
            message = f"Sukces. {party_check.winner.name} osiąga wynik {party_check.winning_roll.total}. Odkrywacie ukryty element w strefie: {zone.name}."
        else:
            message = f"Sukces. {party_check.winner.name} osiąga wynik {party_check.winning_roll.total}. Uważnie sprawdzacie strefę: {zone.name}."
    else:
        if zone.search_failure_flag:
            flags = set_scene_flag(flags, zone.search_failure_flag, True)
        message = f"Porażka. Najwyższy wynik to {party_check.winning_roll.total}. Nie znajdujecie nic nowego w strefie: {zone.name}."
    return SearchResult(replace(state, points=points, flags=flags, exhausted_search_zones=exhausted), party_check, revealed, message)


def dim_color(color: tuple[int, int, int], factor: float = 0.3) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(round(component * factor)))) for component in color)


def exploration_setup_feedback(
    positions: tuple[Coordinate, ...],
    color: tuple[int, int, int],
    anchor_position: Coordinate | None = None,
) -> LedFeedback:
    if not positions:
        return LedFeedback()
    anchor = anchor_position if anchor_position in positions else None
    area_positions = tuple(position for position in positions if position != anchor)
    frames: list[LedFrame] = []
    if area_positions:
        frames.append(LedFrame(area_positions, dim_color(color), LedRole.DESTINATION))
    if anchor is not None:
        frames.append(LedFrame((anchor,), color, LedRole.DESTINATION))
    if anchor is None:
        frames.append(LedFrame(positions, dim_color(color), LedRole.DESTINATION))
    return LedFeedback(tuple(frames))


def exploration_zone_feedback(state: ExplorationState) -> LedFeedback:
    frames: list[LedFrame] = []
    for zone in available_exploration_zones(state):
        frames.append(LedFrame((zone.marker_position,), zone.color, LedRole.DESTINATION))
    for point in visible_exploration_points(state.points):
        frames.append(LedFrame(point.positions, point.color, LedRole.DESTINATION))
    return LedFeedback(tuple(frames))


def party_position_feedback(state: ExplorationState) -> LedFeedback:
    current = next((zone for zone in state.zones if zone.id == state.party_position.zone_id), None)
    if current is None:
        return LedFeedback()
    return LedFeedback((LedFrame((current.marker_position,), LedColor.ACTIVE_ACTOR, LedRole.ACTIVE_ACTOR),))


def look_around_feedback(zone: ExplorationZone) -> LedFeedback:
    area_positions = tuple(position for position in zone.positions if position != zone.marker_position)
    frames: list[LedFrame] = []
    if area_positions:
        frames.append(LedFrame(area_positions, dim_color(zone.color), LedRole.DESTINATION))
    frames.append(LedFrame((zone.marker_position,), zone.color, LedRole.DESTINATION))
    return LedFeedback(tuple(frames))
