from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from dnd_board_game.actors import Actor, spell_is_prepared
from dnd_board_game.combat import SceneAbilityCheck, SceneFlags, SetupVisibility, scene_flag, set_scene_flag
from dnd_board_game.hardware import LedColor, LedFeedback, LedFrame, LedRole
from dnd_board_game.rules import (
    D20RollInput,
    D20RollRequest,
    D20RollResult,
    RollMode,
    RollModifier,
    RollModifierType,
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


@dataclass(frozen=True, slots=True)
class EncounterOutcome:
    title: str
    body: str
    effects: tuple[dict[str, object], ...] = ()
    next_instruction: str = ""


@dataclass(frozen=True, slots=True)
class LlmContext:
    summary: str = ""
    available_materials: tuple[str, ...] = ()
    forbidden_assumptions: tuple[str, ...] = ()
    reasonable_approaches: tuple[str, ...] = ()
    impossible_approaches: tuple[str, ...] = ()
    risk_notes: tuple[str, ...] = ()

    def as_payload(self) -> dict[str, object]:
        return {
            "summary": self.summary,
            "available_materials": list(self.available_materials),
            "forbidden_assumptions": list(self.forbidden_assumptions),
            "reasonable_approaches": list(self.reasonable_approaches),
            "impossible_approaches": list(self.impossible_approaches),
            "risk_notes": list(self.risk_notes),
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
    outcome_on_victory: EncounterOutcome | None = None
    outcome_on_defeat: EncounterOutcome | None = None


@dataclass(frozen=True, slots=True)
class PendingEncounter:
    trigger_id: str
    name: str
    description: str
    encounter_scenario: str
    reason: str


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


@dataclass(frozen=True, slots=True)
class NpcIntentPermission:
    intent: str
    status: str
    notes: str = ""
    unlock_if_flags: tuple[str, ...] = ()
    limits: dict[str, object] | None = None
    consequences: dict[str, object] | None = None
    reveals: tuple[str, ...] = ()

    def as_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "status": self.status,
            "notes": self.notes,
            "unlock_if_flags": list(self.unlock_if_flags),
            "reveals": list(self.reveals),
        }
        if self.limits:
            payload["limits"] = self.limits
        if self.consequences:
            payload["consequences"] = self.consequences
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
    name: str
    public_description: str
    gm_context: str = ""
    personality: str = ""
    current_state: str = ""
    dialogue_intro: str = ""
    capabilities: tuple[str, ...] = ()
    locked_information: tuple[NpcLockedInformation, ...] = ()
    policy: NpcInteractionPolicy = NpcInteractionPolicy()

    def as_payload(self) -> dict[str, object]:
        return {
            "name": self.name,
            "public_description": self.public_description,
            "gm_context": self.gm_context,
            "personality": self.personality,
            "current_state": self.current_state,
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
    effect_modifier: int = 1
    risk: str = ""
    reason: str = ""

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("Improvised tool label cannot be empty.")
        if not self.source_detail.strip():
            raise ValueError("Improvised tool source_detail cannot be empty.")
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

    def as_roll_modifier(self) -> RollModifier | None:
        if self.modifier == 0:
            return None
        return RollModifier(
            self.label,
            self.modifier,
            RollModifierType.ITEM,
            stacking_key=f"exploration_resource:{self.id}",
        )


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
    return tuple(
        resource
        for resource in state.resources
        if resource.id in owned
        and (option_tags.intersection(resource.bonus_tags) or resource.id == option.unlocks_if_resource_id)
    )


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
