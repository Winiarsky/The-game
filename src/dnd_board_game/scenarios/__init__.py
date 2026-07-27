"""Scenario loading for encounter and exploration scenes."""

from .content_contract import (
    RULESET_DND_5E_2014,
    SCENARIO_SCHEMA,
    SCENARIO_SCHEMA_VERSION,
    ContentHeader,
    SourcePack,
    load_source_pack_registry,
    migrate_scenario_payload,
    validate_stable_id,
)
from .content_audit import (
    AuditSeverity,
    ContentAuditEntry,
    ContentAuditIssue,
    ContentAuditReport,
    audit_content,
)
from .loader import (
    LoadedExploration,
    LoadedEncounter,
    LoadedScenario,
    ScenarioActorDefinition,
    ScenarioAttackDefinition,
    ScenarioDefinition,
    ScenarioEnvironmentDefinition,
    ScenarioObjectiveDefinition,
    build_exploration_from_scenario,
    build_encounter_from_scenario,
    load_scenario,
)

__all__ = [
    "AuditSeverity",
    "ContentAuditEntry",
    "ContentAuditIssue",
    "ContentAuditReport",
    "ContentHeader",
    "LoadedEncounter",
    "LoadedExploration",
    "LoadedScenario",
    "RULESET_DND_5E_2014",
    "SCENARIO_SCHEMA",
    "SCENARIO_SCHEMA_VERSION",
    "ScenarioActorDefinition",
    "ScenarioAttackDefinition",
    "ScenarioDefinition",
    "ScenarioEnvironmentDefinition",
    "ScenarioObjectiveDefinition",
    "SourcePack",
    "build_encounter_from_scenario",
    "build_exploration_from_scenario",
    "audit_content",
    "load_scenario",
    "load_source_pack_registry",
    "migrate_scenario_payload",
    "validate_stable_id",
]
