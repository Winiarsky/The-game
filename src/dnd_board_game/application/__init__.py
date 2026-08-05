"""Application services coordinating deterministic domain operations."""

from .combat_movement_flow import (
    CombatMovementFlowService,
    CombatMovementPreview,
    CombatMovementSubmission,
)
from .long_casting_flow import (
    LongCastActionSpec,
    LongCastingFlowService,
    LongCastingTransition,
)
from .summoning_flow import (
    PendingSummon,
    SummonActionSpec,
    SummoningFlowService,
    SummoningTransition,
    remove_orphaned_summons,
)
from .magic_movement_flow import (
    MagicMovementActionSpec,
    MagicMovementFlowService,
    MagicMovementTransition,
    PendingMagicMovement,
)
from .spell_debuff_flow import (
    PendingSpellDebuff,
    SpellDebuffActionSpec,
    SpellDebuffFlowService,
    SpellDebuffTransition,
)
from .spell_dispel_flow import (
    PendingDispelCheck,
    PendingSpellDispel,
    SpellDispelActionSpec,
    SpellDispelFlowService,
    SpellDispelTransition,
)
from .player_multi_target_spell_flow import (
    MultiTargetDamageSpellTransition,
    PendingMultiTargetDamageSpell,
    PlayerMultiTargetSpellFlowService,
    ProjectileAllocation,
)
from .combat_reaction_flow import (
    ClassFeatureReactionFlowService,
    CombatReactionFlowService,
    CombatReactionResolution,
    CounterspellReactionFlowService,
    CounterspellReactionResolution,
    CuttingWordsReactionResolution,
    DeflectMissilesReactionResolution,
    DeflectedMissileReturnResolution,
    DefensiveSpellReactionFlowService,
    DefensiveSpellReactionResolution,
    PlayerReactionAttackResolution,
    PlayerReactionDamageResolution,
    PlayerReactionFlowService,
    ReadyAttackTrigger,
)
from .combat_scene_interaction_flow import (
    CombatApproachInteractionPlan,
    CombatSceneEffectExpiration,
    CombatSceneInteractionFlowService,
    CombatSceneInteractionTransition,
    PendingCombatInteraction,
)
from .combat_turn_action_flow import (
    CombatTurnActionFlowService,
    CombatTurnActionTransition,
    HelpPreparation,
    PendingCombatSkillCheck,
    ReadyPreparation,
)
from .combat_turn_finalization import (
    CombatTurnFinalizationService,
    CombatTurnFinalizationTransition,
    EnemyTurnCommitTransition,
    ExpiredCombatEffects,
)
from .combat_stabilization_flow import (
    CombatStabilizationResult,
    StabilizationMethod,
    legal_stabilization_targets,
    resolve_combat_stabilization,
)
from .combat_shove_flow import (
    CombatShoveFlowService,
    PendingShove,
    ShoveMode,
    ShoveResolution,
    automatic_defender_roll,
    forced_push_destination,
    shove_push_destination,
)
from .combat_grapple_flow import (
    CombatGrappleFlowService,
    GrappleMode,
    GrappleResolution,
    PendingGrapple,
    automatic_grapple_opponent_roll,
)
from .combat_item_action_flow import (
    CombatItemActionResolution,
    TargetedItemActionSpec,
    resolve_targeted_item_action,
    targeted_item_action_is_legal,
)
from .exploration_flow import (
    CancelPreviewTransition,
    EncounterDetection,
    ExplorationFlowService,
    ExplorationFlowStage,
    FinishInteractionTransition,
    LocationTransition,
    PointSelection,
    SetupStepTransition,
    StartSessionTransition,
)
from .exploration_interaction_flow import (
    ExplorationGoalRoute,
    ExplorationInteractionFlowService,
)
from .exploration_goal_execution import (
    ExplorationGoalExecutionPlan,
    ExplorationGoalExecutionPlanner,
    ProceduralSourceExecution,
)
from .npc_goal_execution import (
    NpcGoalExecutionPlan,
    NpcGoalExecutionPlanner,
    NpcGoalRoute,
)
from .exploration_hazard_flow import (
    ExplorationHazardResolution,
    apply_exploration_hazard_outcome,
    resolve_exploration_hazard,
)
from .encounter_opening_flow import resolve_encounter_opening
from .precombat_stealth_flow import (
    PrecombatStealthResolution,
    hidden_states_from_precombat_attempts,
    precombat_stealth_is_available,
    precombat_stealth_modifier,
    resolve_precombat_stealth,
)
from .player_combat_action_flow import (
    CombatSourceSelectionTransition,
    PendingPlayerAttack,
    PlayerAttackTransition,
    PlayerCombatActionFlowService,
)
from .player_combat_resource_flow import (
    CombatResourceTransition,
    PendingConcentrationAction,
    PendingConcentrationCheck,
    PlayerCombatResourceFlowService,
    concentration_effects_for_actor,
)
from .player_area_healing_flow import (
    PendingAreaSpell,
    PendingPlayerHealing,
    PlayerAreaHealingFlowService,
    PlayerAreaSpellTransition,
    PlayerHealingTransition,
)
from .spell_preparation_flow import SpellPreparationFlowService, SpellPreparationTransition
from .ritual_casting_flow import (
    RitualCastingFlowService,
    RitualCastingResult,
    ritual_casting_minutes,
)
from .exploration_spell_casting_flow import (
    ExplorationSpellCastResult,
    ExplorationSpellCastingFlowService,
)
from .exploration_action_sources import (
    ExplorationActionSource,
    ExplorationActionSourceKind,
    action_sources_for_goal,
    resource_for_action_source,
    selected_action_source,
)
from .short_rest_flow import (
    PendingShortRest,
    ShortRestCompletionTransition,
    ShortRestFlowService,
    ShortRestHitDieTransition,
    short_rest_count,
)
from .long_rest_flow import LongRestFlowService, LongRestTransition, rest_policy_count
from .scenario_continuation_flow import (
    ScenarioContinuationFlowService,
    ScenarioContinuationOutcomeResolution,
    ScenarioContinuationPlan,
    merge_handoff_actor,
)
from .enemy_turn_flow import (
    EnemySavingThrowTransition,
    EnemyTurnFlowService,
    EnemyTurnIntentTransition,
    EnemyTurnResolutionTransition,
    EnemyTurnTransitionKind,
    PendingEnemySavingThrow,
)
from .effect_boundary_flow import (
    ConditionBoundaryTransition,
    expire_exploration_conditions,
    reconcile_conditions_after_encounter,
)

__all__ = [
    "CancelPreviewTransition",
    "ConditionBoundaryTransition",
    "CombatMovementFlowService",
    "CombatMovementPreview",
    "CombatMovementSubmission",
    "LongRestFlowService",
    "LongRestTransition",
    "CombatReactionFlowService",
    "CombatReactionResolution",
    "ClassFeatureReactionFlowService",
    "CounterspellReactionFlowService",
    "CounterspellReactionResolution",
    "CuttingWordsReactionResolution",
    "DeflectMissilesReactionResolution",
    "DeflectedMissileReturnResolution",
    "DefensiveSpellReactionFlowService",
    "DefensiveSpellReactionResolution",
    "CombatApproachInteractionPlan",
    "CombatSceneEffectExpiration",
    "CombatSceneInteractionFlowService",
    "CombatSceneInteractionTransition",
    "CombatStabilizationResult",
    "CombatShoveFlowService",
    "CombatGrappleFlowService",
    "CombatItemActionResolution",
    "CombatResourceTransition",
    "CombatTurnActionFlowService",
    "CombatTurnActionTransition",
    "CombatTurnFinalizationService",
    "CombatTurnFinalizationTransition",
    "EnemyTurnCommitTransition",
    "ExpiredCombatEffects",
    "HelpPreparation",
    "PendingCombatSkillCheck",
    "PendingShove",
    "PendingGrapple",
    "PlayerReactionAttackResolution",
    "PlayerReactionDamageResolution",
    "PlayerReactionFlowService",
    "ReadyAttackTrigger",
    "ReadyPreparation",
    "rest_policy_count",
    "StabilizationMethod",
    "ShoveMode",
    "ShoveResolution",
    "GrappleMode",
    "GrappleResolution",
    "TargetedItemActionSpec",
    "automatic_defender_roll",
    "forced_push_destination",
    "shove_push_destination",
    "automatic_grapple_opponent_roll",
    "EncounterDetection",
    "resolve_encounter_opening",
    "PrecombatStealthResolution",
    "hidden_states_from_precombat_attempts",
    "precombat_stealth_is_available",
    "precombat_stealth_modifier",
    "resolve_precombat_stealth",
    "EnemyTurnFlowService",
    "EnemySavingThrowTransition",
    "EnemyTurnIntentTransition",
    "EnemyTurnResolutionTransition",
    "EnemyTurnTransitionKind",
    "expire_exploration_conditions",
    "PendingEnemySavingThrow",
    "ExplorationFlowService",
    "ExplorationFlowStage",
    "ExplorationGoalRoute",
    "ExplorationInteractionFlowService",
    "ExplorationHazardResolution",
    "FinishInteractionTransition",
    "LocationTransition",
    "LongCastActionSpec",
    "LongCastingFlowService",
    "LongCastingTransition",
    "PendingSummon",
    "SummonActionSpec",
    "SummoningFlowService",
    "SummoningTransition",
    "remove_orphaned_summons",
    "MagicMovementActionSpec",
    "MagicMovementFlowService",
    "MagicMovementTransition",
    "PendingMagicMovement",
    "PendingSpellDebuff",
    "SpellDebuffActionSpec",
    "SpellDebuffFlowService",
    "SpellDebuffTransition",
    "PendingDispelCheck",
    "PendingSpellDispel",
    "SpellDispelActionSpec",
    "SpellDispelFlowService",
    "SpellDispelTransition",
    "MultiTargetDamageSpellTransition",
    "PendingMultiTargetDamageSpell",
    "PlayerMultiTargetSpellFlowService",
    "ProjectileAllocation",
    "CombatSourceSelectionTransition",
    "PendingPlayerAttack",
    "PendingAreaSpell",
    "PendingCombatInteraction",
    "PendingConcentrationAction",
    "PendingConcentrationCheck",
    "PendingPlayerHealing",
    "PendingShortRest",
    "PointSelection",
    "PlayerAttackTransition",
    "PlayerAreaHealingFlowService",
    "PlayerAreaSpellTransition",
    "PlayerCombatActionFlowService",
    "PlayerCombatResourceFlowService",
    "PlayerHealingTransition",
    "SetupStepTransition",
    "StartSessionTransition",
    "SpellPreparationFlowService",
    "SpellPreparationTransition",
    "ExplorationSpellCastResult",
    "ExplorationSpellCastingFlowService",
    "ExplorationActionSource",
    "ExplorationActionSourceKind",
    "action_sources_for_goal",
    "resource_for_action_source",
    "selected_action_source",
    "ShortRestCompletionTransition",
    "ShortRestFlowService",
    "ShortRestHitDieTransition",
    "ScenarioContinuationFlowService",
    "ScenarioContinuationOutcomeResolution",
    "ScenarioContinuationPlan",
    "merge_handoff_actor",
    "concentration_effects_for_actor",
    "short_rest_count",
    "legal_stabilization_targets",
    "resolve_combat_stabilization",
    "resolve_exploration_hazard",
    "apply_exploration_hazard_outcome",
    "resolve_targeted_item_action",
    "reconcile_conditions_after_encounter",
    "targeted_item_action_is_legal",
]
