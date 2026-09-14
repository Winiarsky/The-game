from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping

from dnd_board_game.actors import (
    AbilityScores,
    Actor,
    ActorAura,
    ActorTrigger,
    ActorId,
    ActorSenseProfile,
    AuraEffectKind,
    AuraTarget,
    TriggerEffectKind,
    TriggerEventType,
    ActorResourcePool,
    DeathSaveState,
    CreatureSize,
    DamageAffinityProfile,
    Faction,
    FeatureGrant,
    FeatureSourceKind,
    HitDicePool,
    PreparableSpell,
    ProficiencyProfile,
    RecoveryPeriod,
    ResourceRechargeRule,
    SpellPreparationProfile,
    WildShapeState,
)
from dnd_board_game.combat import (
    ActionUse,
    AmmunitionExpenditure,
    BattlefieldLoot,
    CombatState,
    CombatCondition,
    ConditionSaveTiming,
    ConditionState,
    DroppedWeapon,
    EnemyAiRuntimeState,
    EnemyOutcome,
    HiddenState,
    InitiativeEntry,
    InitiativeOrder,
    LongCastState,
    SummonDefinition,
    SummonedCreatureState,
    TurnActionState,
    DamageType,
)
from dnd_board_game.combat.session import CombatStatus
from dnd_board_game.combat.spells import SpellSlotState
from dnd_board_game.combat.scene import SceneFlags
from dnd_board_game.combat.setup import SetupVisibility
from dnd_board_game.core import MigrationError, MigrationRegistry
from dnd_board_game.exploration import (
    CraftingComponentDisposition,
    CraftingComponentUse,
    EncounterEdge,
    EncounterEdgeType,
    EncounterOpeningOutcome,
    EncounterOpeningResolution,
    ExplorationChallengeAttempt,
    ExplorationChallengeState,
    ExplorationHiddenActorState,
    ExplorationState,
    ExplorationTrapState,
    ExplorationTrapStatus,
    NpcAttitude,
    NpcInteractionStatus,
    NpcRelationshipEvent,
    NpcRuntimeState,
    SceneSourceDiscovery,
    SceneSourceCollection,
    FixtureRuntimeState,
    PartyPosition,
    PendingEncounter,
    PendingNpcTransition,
    PrecombatStealthAttempt,
    TemporaryItem,
    TemporaryItemScope,
    TimedMagicEffect,
)
from dnd_board_game.inventory import (
    ArmorCategory,
    ActiveLight,
    BundleEntry,
    CheckModifier,
    CheckModifierMode,
    ContainerCapacity,
    GearCategory,
    HandSlot,
    InventoryItem,
    ItemChargeRecovery,
    LootBundle,
    MagicItemEffect,
    MagicItemEffectKind,
    LightShape,
    LightSource,
    ObjectDurability,
    SpellcastingFocusKind,
    WeaponCategory,
    WeaponProperty,
    MerchantState,
    inventory_item_payload,
    validate_attunement_limit,
)
from dnd_board_game.inventory.economy import CurrencyWallet
from dnd_board_game.rules import (
    ActiveEffect,
    AdditionalEffectExpiration,
    D20RollResult,
    EffectDuration,
    EffectSource,
    EffectSourceType,
    EffectStackingPolicy,
    RollMode,
    RollModifierBreakdown,
    SpellAccessKind,
    SpellAccessProfile,
    SpellCastingTime,
    SpellComponents,
    SpellDefinition,
    SpellDuration,
    SpellDurationKind,
    SpellExplorationEffect,
    SpellExplorationEffectKind,
    SpellMaterial,
    SpellRange,
    SpellRangeKind,
    SpellSchool,
    SpellScaling,
)
from dnd_board_game.world import Coordinate
from dnd_board_game.ui.conversation import InteractionConversationEntry
from dnd_board_game.scenarios.content_contract import (
    RULESET_DND_5E_2014,
    SCENARIO_SCHEMA,
)


SNAPSHOT_SCHEMA = "dnd_board_game.session"
SNAPSHOT_SCHEMA_VERSION = 33


def _migrate_snapshot_v1_to_v2(data: dict[str, Any]) -> dict[str, Any]:
    migrated = dict(data)
    migrated["schema_version"] = 2
    migrated["content"] = {
        "scenario_schema": SCENARIO_SCHEMA,
        "scenario_schema_version": 1,
        "ruleset_id": RULESET_DND_5E_2014,
        "source_pack_ids": ["project_original"],
    }
    return migrated


def _migrate_snapshot_v2_to_v3(data: dict[str, Any]) -> dict[str, Any]:
    migrated = dict(data)
    migrated["schema_version"] = 3

    def actor_payload_v3(raw: object) -> object:
        if not isinstance(raw, dict):
            return raw
        actor = dict(raw)
        actor.setdefault("currency", {"cp": 0, "sp": 0, "ep": 0, "gp": 0, "pp": 0})
        inventory: list[object] = []
        for raw_item in actor.get("inventory", []):
            if not isinstance(raw_item, dict):
                inventory.append(raw_item)
                continue
            item = dict(raw_item)
            item.setdefault("value_cp", 0)
            item.setdefault("weight_lb", 0.0)
            inventory.append(item)
        actor["inventory"] = inventory
        return actor

    migrated["actors"] = [actor_payload_v3(actor) for actor in migrated.get("actors", [])]
    combat = migrated.get("combat")
    if isinstance(combat, dict):
        combat_v3 = dict(combat)
        combat_v3["actors"] = [actor_payload_v3(actor) for actor in combat.get("actors", [])]
        migrated["combat"] = combat_v3
    return migrated


def _migrate_snapshot_v3_to_v4(data: dict[str, Any]) -> dict[str, Any]:
    migrated = dict(data)
    migrated["schema_version"] = 4

    def actor_payload_v4(raw: object) -> object:
        if not isinstance(raw, dict):
            return raw
        actor = dict(raw)
        inventory: list[object] = []
        for raw_item in actor.get("inventory", []):
            if not isinstance(raw_item, dict):
                inventory.append(raw_item)
                continue
            item = dict(raw_item)
            item.setdefault("ammunition_type", None)
            inventory.append(item)
        actor["inventory"] = inventory
        return actor

    migrated["actors"] = [actor_payload_v4(actor) for actor in migrated.get("actors", [])]
    combat = migrated.get("combat")
    if isinstance(combat, dict):
        combat_v4 = dict(combat)
        combat_v4["actors"] = [actor_payload_v4(actor) for actor in combat.get("actors", [])]
        migrated["combat"] = combat_v4
    return migrated


def _migrate_snapshot_v4_to_v5(data: dict[str, Any]) -> dict[str, Any]:
    migrated = dict(data)
    migrated["schema_version"] = 5
    combat = migrated.get("combat")
    if isinstance(combat, dict):
        combat_v5 = dict(combat)
        combat_v5.setdefault("ammunition_expenditures", [])
        combat_v5.setdefault("battlefield_loot", [])
        migrated["combat"] = combat_v5
    return migrated


def _migrate_snapshot_v5_to_v6(data: dict[str, Any]) -> dict[str, Any]:
    migrated = dict(data)
    migrated["schema_version"] = 6
    # Merchant state did not exist in v5. Its absence intentionally means that
    # the current scenario content supplies the initial merchant state.
    return migrated


def _migrate_snapshot_v6_to_v7(data: dict[str, Any]) -> dict[str, Any]:
    migrated = dict(data)
    migrated["schema_version"] = 7
    # Body-armor fields are optional. Items from v6 retain their prior behavior.
    return migrated


def _migrate_snapshot_v7_to_v8(data: dict[str, Any]) -> dict[str, Any]:
    migrated = dict(data)
    migrated["schema_version"] = 8
    # Charge fields are optional. Items from v7 remain ordinary consumables.
    return migrated


def _migrate_snapshot_v8_to_v9(data: dict[str, Any]) -> dict[str, Any]:
    migrated = dict(data)
    migrated["schema_version"] = 9
    # Attunement is opt-in. Existing items retain their previous availability.
    return migrated


def _migrate_snapshot_v9_to_v10(data: dict[str, Any]) -> dict[str, Any]:
    migrated = dict(data)
    migrated["schema_version"] = 10
    return migrated


def _migrate_snapshot_v10_to_v11(data: dict[str, Any]) -> dict[str, Any]:
    migrated = dict(data)
    migrated["schema_version"] = 11
    return migrated


def _migrate_snapshot_v11_to_v12(data: dict[str, Any]) -> dict[str, Any]:
    migrated = dict(data)
    migrated["schema_version"] = 12
    # Mundane-gear metadata is optional; v11 items retain their prior behavior.
    return migrated


def _migrate_snapshot_v12_to_v13(data: dict[str, Any]) -> dict[str, Any]:
    migrated = dict(data)
    migrated["schema_version"] = 13
    # Spell definitions are restored from scenario content for a fresh session;
    # old saves safely retain empty optional runtime metadata.
    return migrated


def _migrate_snapshot_v13_to_v14(data: dict[str, Any]) -> dict[str, Any]:
    migrated = dict(data)
    migrated["schema_version"] = 14
    # Spell scaling and ritual metadata are optional additions to SpellDefinition.
    return migrated


def _migrate_snapshot_v14_to_v15(data: dict[str, Any]) -> dict[str, Any]:
    migrated = dict(data)
    migrated["schema_version"] = 15
    exploration = dict(_mapping(migrated.get("exploration"), "exploration"))
    exploration.setdefault("magic_effects", [])
    migrated["exploration"] = exploration
    return migrated


def _migrate_snapshot_v15_to_v16(data: dict[str, Any]) -> dict[str, Any]:
    migrated = dict(data)
    migrated["schema_version"] = 16
    combat = migrated.get("combat")
    if combat is not None:
        combat_data = dict(_mapping(combat, "combat"))
        combat_data.setdefault("long_casts", [])
        migrated["combat"] = combat_data
    return migrated


def _migrate_snapshot_v16_to_v17(data: dict[str, Any]) -> dict[str, Any]:
    migrated = dict(data)
    migrated["schema_version"] = 17
    combat = migrated.get("combat")
    if combat is not None:
        combat_data = dict(_mapping(combat, "combat"))
        combat_data.setdefault("summoned_creatures", [])
        migrated["combat"] = combat_data
    return migrated


def _migrate_snapshot_v17_to_v18(data: dict[str, Any]) -> dict[str, Any]:
    migrated = dict(data)
    migrated["schema_version"] = 18
    migrated["active_effects"] = [
        (
            {**effect, "spell_level": effect.get("spell_level")}
            if isinstance(effect, dict)
            else effect
        )
        for effect in migrated.get("active_effects", [])
    ]
    exploration = migrated.get("exploration")
    if isinstance(exploration, dict):
        exploration_v18 = dict(exploration)
        exploration_v18["condition_states"] = [
            (
                {
                    **condition,
                    "source_spell_id": condition.get("source_spell_id"),
                    "source_spell_level": condition.get("source_spell_level"),
                }
                if isinstance(condition, dict)
                else condition
            )
            for condition in exploration.get("condition_states", [])
        ]
        migrated["exploration"] = exploration_v18
    combat = migrated.get("combat")
    if isinstance(combat, dict):
        combat_v18 = dict(combat)
        combat_v18["condition_states"] = [
            (
                {
                    **condition,
                    "source_spell_id": condition.get("source_spell_id"),
                    "source_spell_level": condition.get("source_spell_level"),
                }
                if isinstance(condition, dict)
                else condition
            )
            for condition in combat.get("condition_states", [])
        ]
        migrated["combat"] = combat_v18
    return migrated


def _migrate_snapshot_v18_to_v19(data: dict[str, Any]) -> dict[str, Any]:
    migrated = dict(data)
    migrated["schema_version"] = 19

    def actor_payload_v19(raw: object) -> object:
        if not isinstance(raw, dict):
            return raw
        actor = dict(raw)
        actor.setdefault("level", 1)
        return actor

    migrated["actors"] = [
        actor_payload_v19(actor) for actor in migrated.get("actors", [])
    ]
    combat = migrated.get("combat")
    if isinstance(combat, dict):
        combat_v19 = dict(combat)
        combat_v19["actors"] = [
            actor_payload_v19(actor) for actor in combat.get("actors", [])
        ]
        migrated["combat"] = combat_v19
    return migrated


def _migrate_snapshot_v19_to_v20(data: dict[str, Any]) -> dict[str, Any]:
    migrated = dict(data)
    migrated["schema_version"] = 20

    def actor_payload_v20(raw: object) -> object:
        if not isinstance(raw, dict):
            return raw
        actor = dict(raw)
        actor.setdefault(
            "senses",
            {
                "darkvision_feet": 0,
                "blindsight_feet": 0,
                "tremorsense_feet": 0,
                "truesight_feet": 0,
            },
        )
        return actor

    migrated["actors"] = [
        actor_payload_v20(actor) for actor in migrated.get("actors", [])
    ]
    combat = migrated.get("combat")
    if isinstance(combat, dict):
        combat_v20 = dict(combat)
        combat_v20["actors"] = [
            actor_payload_v20(actor) for actor in combat.get("actors", [])
        ]
        migrated["combat"] = combat_v20
    return migrated


def _migrate_snapshot_v20_to_v21(data: dict[str, Any]) -> dict[str, Any]:
    migrated = dict(data)
    migrated["schema_version"] = 21
    exploration = migrated.get("exploration")
    if isinstance(exploration, dict):
        exploration_v21 = dict(exploration)
        exploration_v21.setdefault("hidden_actor_states", [])
        migrated["exploration"] = exploration_v21
    return migrated


def _migrate_snapshot_v21_to_v22(data: dict[str, Any]) -> dict[str, Any]:
    migrated = dict(data)
    migrated["schema_version"] = 22
    exploration = migrated.get("exploration")
    if isinstance(exploration, dict):
        exploration_v22 = dict(exploration)
        fixture_states = []
        for raw in exploration.get("fixture_states", []):
            if not isinstance(raw, dict):
                fixture_states.append(raw)
                continue
            fixture_state = dict(raw)
            fixture_state.setdefault("opened", False)
            fixture_state.setdefault("locked", False)
            fixture_state.setdefault("looted", False)
            fixture_state.setdefault("current_hit_points", None)
            fixture_states.append(fixture_state)
        exploration_v22["fixture_states"] = fixture_states
        migrated["exploration"] = exploration_v22
    return migrated


def _migrate_snapshot_v22_to_v23(data: dict[str, Any]) -> dict[str, Any]:
    migrated = dict(data)
    migrated["schema_version"] = 23

    def actor_payload_v23(raw: object) -> object:
        if not isinstance(raw, dict):
            return raw
        actor = dict(raw)
        actor.setdefault("exhaustion_level", 0)
        return actor

    migrated["actors"] = [
        actor_payload_v23(actor) for actor in migrated.get("actors", [])
    ]
    combat = migrated.get("combat")
    if isinstance(combat, dict):
        combat_v23 = dict(combat)
        combat_v23["actors"] = [
            actor_payload_v23(actor) for actor in combat.get("actors", [])
        ]
        migrated["combat"] = combat_v23
    return migrated


def _migrate_snapshot_v23_to_v24(data: dict[str, Any]) -> dict[str, Any]:
    migrated = dict(data)
    migrated["schema_version"] = 24

    def actor_payload_v24(raw: object) -> object:
        if not isinstance(raw, dict):
            return raw
        actor = dict(raw)
        actor.setdefault("experience_points", 0)
        return actor

    migrated["actors"] = [
        actor_payload_v24(actor) for actor in migrated.get("actors", [])
    ]
    combat = migrated.get("combat")
    if isinstance(combat, dict):
        combat_v24 = dict(combat)
        combat_v24["actors"] = [
            actor_payload_v24(actor) for actor in combat.get("actors", [])
        ]
        migrated["combat"] = combat_v24
    return migrated


def _migrate_snapshot_v24_to_v25(data: dict[str, Any]) -> dict[str, Any]:
    """Spell access gained an optional source-specific casting ability."""
    migrated = dict(data)
    migrated["schema_version"] = 25
    return migrated


def _migrate_snapshot_v25_to_v26(data: dict[str, Any]) -> dict[str, Any]:
    """Spell slots gained an explicit long- or short-rest recovery period."""
    migrated = dict(data)
    migrated["schema_version"] = 26
    return migrated


def _migrate_snapshot_v26_to_v27(data: dict[str, Any]) -> dict[str, Any]:
    """Actors gained a creature type; old actors retain the humanoid default."""
    migrated = dict(data)
    migrated["schema_version"] = 27
    return migrated


def _migrate_snapshot_v27_to_v28(data: dict[str, Any]) -> dict[str, Any]:
    """Spell access can map innate spells to their once-per-rest resources."""
    migrated = dict(data)
    migrated["schema_version"] = 28
    return migrated


def _migrate_snapshot_v28_to_v29(data: dict[str, Any]) -> dict[str, Any]:
    """Actors can persist an active Wild Shape form and their normal statistics."""
    migrated = dict(data)
    migrated["schema_version"] = 29
    return migrated


def _migrate_snapshot_v29_to_v30(data: dict[str, Any]) -> dict[str, Any]:
    """Timed conditions can survive more than one matching expiration event."""
    migrated = dict(data)
    migrated["schema_version"] = 30
    return migrated


def _migrate_snapshot_v30_to_v31(data: dict[str, Any]) -> dict[str, Any]:
    """Persist turn spell restrictions and magical-darkness sight."""
    migrated = dict(data)
    migrated["schema_version"] = 31
    return migrated


def _migrate_snapshot_v31_to_v32(data: dict[str, Any]) -> dict[str, Any]:
    """Active effects gained optional spell-aura geometry and use counters."""
    migrated = dict(data)
    migrated["schema_version"] = 32
    return migrated


def _migrate_snapshot_v32_to_v33(data: dict[str, Any]) -> dict[str, Any]:
    """Exploration gained a persistent shared post-combat loot pool."""

    migrated = dict(data)
    migrated["schema_version"] = 33
    exploration = migrated.get("exploration")
    if isinstance(exploration, dict):
        exploration_v33 = dict(exploration)
        exploration_v33.setdefault(
            "party_loot",
            {
                "id": "party_stash",
                "label": "Łup drużyny",
                "items": [],
                "currency": {"cp": 0, "sp": 0, "ep": 0, "gp": 0, "pp": 0},
            },
        )
        migrated["exploration"] = exploration_v33
    return migrated


_SNAPSHOT_MIGRATIONS = MigrationRegistry(
    schema=SNAPSHOT_SCHEMA,
    current_version=SNAPSHOT_SCHEMA_VERSION,
)
_SNAPSHOT_MIGRATIONS.register(1, _migrate_snapshot_v1_to_v2)
_SNAPSHOT_MIGRATIONS.register(2, _migrate_snapshot_v2_to_v3)
_SNAPSHOT_MIGRATIONS.register(3, _migrate_snapshot_v3_to_v4)
_SNAPSHOT_MIGRATIONS.register(4, _migrate_snapshot_v4_to_v5)
_SNAPSHOT_MIGRATIONS.register(5, _migrate_snapshot_v5_to_v6)
_SNAPSHOT_MIGRATIONS.register(6, _migrate_snapshot_v6_to_v7)
_SNAPSHOT_MIGRATIONS.register(7, _migrate_snapshot_v7_to_v8)
_SNAPSHOT_MIGRATIONS.register(8, _migrate_snapshot_v8_to_v9)
_SNAPSHOT_MIGRATIONS.register(9, _migrate_snapshot_v9_to_v10)
_SNAPSHOT_MIGRATIONS.register(10, _migrate_snapshot_v10_to_v11)
_SNAPSHOT_MIGRATIONS.register(11, _migrate_snapshot_v11_to_v12)
_SNAPSHOT_MIGRATIONS.register(12, _migrate_snapshot_v12_to_v13)
_SNAPSHOT_MIGRATIONS.register(13, _migrate_snapshot_v13_to_v14)
_SNAPSHOT_MIGRATIONS.register(14, _migrate_snapshot_v14_to_v15)
_SNAPSHOT_MIGRATIONS.register(15, _migrate_snapshot_v15_to_v16)
_SNAPSHOT_MIGRATIONS.register(16, _migrate_snapshot_v16_to_v17)
_SNAPSHOT_MIGRATIONS.register(17, _migrate_snapshot_v17_to_v18)
_SNAPSHOT_MIGRATIONS.register(18, _migrate_snapshot_v18_to_v19)
_SNAPSHOT_MIGRATIONS.register(19, _migrate_snapshot_v19_to_v20)
_SNAPSHOT_MIGRATIONS.register(20, _migrate_snapshot_v20_to_v21)
_SNAPSHOT_MIGRATIONS.register(21, _migrate_snapshot_v21_to_v22)
_SNAPSHOT_MIGRATIONS.register(22, _migrate_snapshot_v22_to_v23)
_SNAPSHOT_MIGRATIONS.register(23, _migrate_snapshot_v23_to_v24)
_SNAPSHOT_MIGRATIONS.register(24, _migrate_snapshot_v24_to_v25)
_SNAPSHOT_MIGRATIONS.register(25, _migrate_snapshot_v25_to_v26)
_SNAPSHOT_MIGRATIONS.register(26, _migrate_snapshot_v26_to_v27)
_SNAPSHOT_MIGRATIONS.register(27, _migrate_snapshot_v27_to_v28)
_SNAPSHOT_MIGRATIONS.register(28, _migrate_snapshot_v28_to_v29)
_SNAPSHOT_MIGRATIONS.register(29, _migrate_snapshot_v29_to_v30)
_SNAPSHOT_MIGRATIONS.register(30, _migrate_snapshot_v30_to_v31)
_SNAPSHOT_MIGRATIONS.register(31, _migrate_snapshot_v31_to_v32)
_SNAPSHOT_MIGRATIONS.register(32, _migrate_snapshot_v32_to_v33)


class SnapshotValidationError(ValueError):
    """Raised when a save snapshot cannot be safely restored."""


@dataclass(frozen=True, slots=True)
class SessionSnapshot:
    scenario_id: str
    scenario_schema: str
    scenario_schema_version: int
    ruleset_id: str
    source_pack_ids: tuple[str, ...]
    ui_stage: str
    actors: tuple[Actor, ...]
    exploration_state: ExplorationState
    active_effects: tuple[ActiveEffect, ...] = ()
    pending_encounter: PendingEncounter | None = None
    pending_npc_transition: PendingNpcTransition | None = None
    combat_state: CombatState | None = None
    resolved_encounter_trigger_ids: tuple[str, ...] = ()
    selected_attack_source_ids: tuple[tuple[str, str], ...] = ()
    selected_healing_source_ids: tuple[tuple[str, str], ...] = ()
    selected_lead_actor_id: str = ""
    selected_helper_actor_id: str | None = None
    active_point_id: str = ""
    preview_zone_id: str = ""
    interaction_result: Mapping[str, object] | None = None
    conversation_entries: tuple[InteractionConversationEntry, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": SNAPSHOT_SCHEMA,
            "schema_version": SNAPSHOT_SCHEMA_VERSION,
            "scenario_id": self.scenario_id,
            "content": {
                "scenario_schema": self.scenario_schema,
                "scenario_schema_version": self.scenario_schema_version,
                "ruleset_id": self.ruleset_id,
                "source_pack_ids": list(self.source_pack_ids),
            },
            "ui": {
                "stage": self.ui_stage,
                "selected_lead_actor_id": self.selected_lead_actor_id,
                "selected_helper_actor_id": self.selected_helper_actor_id,
                "active_point_id": self.active_point_id,
                "preview_zone_id": self.preview_zone_id,
                "interaction_result": _json_value(self.interaction_result, "ui.interaction_result"),
            },
            "actors": [_actor_payload(actor) for actor in self.actors],
            "exploration": _exploration_payload(self.exploration_state),
            "active_effects": [_effect_payload(effect) for effect in self.active_effects],
            "pending_encounter": _pending_encounter_payload(self.pending_encounter),
            "pending_npc_transition": (
                None
                if self.pending_npc_transition is None
                else {
                    "transition_id": self.pending_npc_transition.transition_id,
                    "variant_id": self.pending_npc_transition.variant_id,
                    "npc_id": self.pending_npc_transition.npc_id,
                }
            ),
            "combat": _combat_payload(self.combat_state),
            "resolved_encounter_trigger_ids": list(self.resolved_encounter_trigger_ids),
            "selected_attack_source_ids": dict(self.selected_attack_source_ids),
            "selected_healing_source_ids": dict(self.selected_healing_source_ids),
            "conversation_entries": [entry.as_payload() for entry in self.conversation_entries],
        }

    @classmethod
    def from_dict(cls, raw: object, *, base_state: ExplorationState) -> SessionSnapshot:
        try:
            data = _SNAPSHOT_MIGRATIONS.migrate(raw)
        except MigrationError as exc:
            raise SnapshotValidationError(
                f"Nieobsługiwana wersja lub format zapisu: {exc}"
            ) from exc
        content = _mapping(data.get("content"), "content")
        ui = _mapping(data.get("ui"), "ui")
        actors = tuple(_actor_from_payload(item) for item in _sequence(data.get("actors"), "actors"))
        _require_unique((str(actor.id) for actor in actors), "actor id")
        state = _exploration_from_payload(base_state, data.get("exploration"))
        effects = tuple(_effect_from_payload(item) for item in _sequence(data.get("active_effects", []), "active_effects"))
        pending = _pending_encounter_from_payload(data.get("pending_encounter"))
        pending_npc_raw = data.get("pending_npc_transition")
        pending_npc = None
        if pending_npc_raw is not None:
            item = _mapping(pending_npc_raw, "pending_npc_transition")
            pending_npc = PendingNpcTransition(
                transition_id=_string(item.get("transition_id"), "pending_npc_transition.transition_id"),
                variant_id=_string(item.get("variant_id"), "pending_npc_transition.variant_id"),
                npc_id=_string(item.get("npc_id"), "pending_npc_transition.npc_id"),
            )
        combat = _combat_from_payload(data.get("combat"))
        interaction = ui.get("interaction_result")
        if interaction is not None:
            interaction = _mapping(interaction, "ui.interaction_result")
            _assert_json_value(interaction, "ui.interaction_result")
        conversation_entries = tuple(
            _conversation_entry_from_payload(item)
            for item in _sequence(data.get("conversation_entries", []), "conversation_entries")
        )
        known_interaction_ids = {
            *(f"challenge:{challenge.id}" for challenge in base_state.challenges),
            *(f"point:{point.id}" for point in base_state.points),
            *(f"zone:{zone.id}" for zone in base_state.zones),
        }
        unknown_interaction_ids = {
            entry.interaction_id for entry in conversation_entries
            if entry.interaction_id not in known_interaction_ids
        }
        if unknown_interaction_ids:
            raise SnapshotValidationError(
                "Zapis zawiera rozmowy dla nieznanych interakcji: "
                + ", ".join(sorted(unknown_interaction_ids))
                + "."
            )
        return cls(
            scenario_id=_string(data.get("scenario_id"), "scenario_id"),
            scenario_schema=_string(
                content.get("scenario_schema"),
                "content.scenario_schema",
            ),
            scenario_schema_version=_integer(
                content.get("scenario_schema_version"),
                "content.scenario_schema_version",
            ),
            ruleset_id=_string(content.get("ruleset_id"), "content.ruleset_id"),
            source_pack_ids=_string_tuple(
                content.get("source_pack_ids"),
                "content.source_pack_ids",
            ),
            ui_stage=_string(ui.get("stage"), "ui.stage"),
            actors=actors,
            exploration_state=state,
            active_effects=effects,
            pending_encounter=pending,
            pending_npc_transition=pending_npc,
            combat_state=combat,
            resolved_encounter_trigger_ids=_string_tuple(data.get("resolved_encounter_trigger_ids", []), "resolved_encounter_trigger_ids"),
            selected_attack_source_ids=_string_map(data.get("selected_attack_source_ids", {}), "selected_attack_source_ids"),
            selected_healing_source_ids=_string_map(data.get("selected_healing_source_ids", {}), "selected_healing_source_ids"),
            selected_lead_actor_id=_string(ui.get("selected_lead_actor_id", ""), "ui.selected_lead_actor_id", allow_empty=True),
            selected_helper_actor_id=_optional_string(ui.get("selected_helper_actor_id"), "ui.selected_helper_actor_id"),
            active_point_id=_string(ui.get("active_point_id", ""), "ui.active_point_id", allow_empty=True),
            preview_zone_id=_string(ui.get("preview_zone_id", ""), "ui.preview_zone_id", allow_empty=True),
            interaction_result=interaction,
            conversation_entries=conversation_entries,
        )


def _conversation_entry_from_payload(raw: object) -> InteractionConversationEntry:
    data = _mapping(raw, "conversation_entry")
    role = _string(data.get("role"), "conversation_entry.role")
    if role not in {"player", "gm"}:
        raise SnapshotValidationError(f"Nieznana rola rozmowy: {role}.")
    return InteractionConversationEntry(
        interaction_id=_string(data.get("interaction_id"), "conversation_entry.interaction_id"),
        role=role,
        title=_string(data.get("title"), "conversation_entry.title"),
        body=_string(data.get("body"), "conversation_entry.body"),
        outcome=_string(data.get("outcome", ""), "conversation_entry.outcome", allow_empty=True),
        grounded_fact_ids=_string_tuple(
            data.get("grounded_fact_ids", []),
            "conversation_entry.grounded_fact_ids",
        ),
        hint_level=_integer(data.get("hint_level", 0), "conversation_entry.hint_level"),
    )


def write_snapshot(path: str | Path, snapshot: SessionSnapshot) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(f"{target.suffix}.tmp")
    temporary.write_text(
        json.dumps(snapshot.as_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(target)


def read_snapshot(path: str | Path, *, base_state: ExplorationState) -> SessionSnapshot:
    target = Path(path)
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SnapshotValidationError("Nie znaleziono zapisu dla tego scenariusza.") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise SnapshotValidationError(f"Nie można odczytać zapisu gry: {exc}.") from exc
    return SessionSnapshot.from_dict(raw, base_state=base_state)


def _actor_payload(actor: Actor) -> dict[str, object]:
    prep = actor.spell_preparation
    return {
        "id": str(actor.id), "name": actor.name, "ac": actor.ac, "hp": actor.hp,
        "portrait": actor.portrait,
        "creature_type": actor.creature_type,
        "wild_shape": (
            {
                "form_id": actor.wild_shape.form_id,
                "form_name": actor.wild_shape.form_name,
                "original_ac": actor.wild_shape.original_ac,
                "original_hp": actor.wild_shape.original_hp,
                "original_max_hp": actor.wild_shape.original_max_hp,
                "original_speed_feet": actor.wild_shape.original_speed_feet,
                "original_ability_scores": {
                    name: getattr(actor.wild_shape.original_ability_scores, name)
                    for name in _ABILITY_NAMES
                },
                "original_size": actor.wild_shape.original_size.value,
                "original_senses": actor.wild_shape.original_senses.as_payload(),
                "original_damage_affinities": {
                    "resistances": [
                        value.value
                        for value in actor.wild_shape.original_damage_affinities.resistances
                    ],
                    "immunities": [
                        value.value
                        for value in actor.wild_shape.original_damage_affinities.immunities
                    ],
                    "vulnerabilities": [
                        value.value
                        for value in actor.wild_shape.original_damage_affinities.vulnerabilities
                    ],
                },
                "original_creature_type": actor.wild_shape.original_creature_type,
                "remaining_minutes": actor.wild_shape.remaining_minutes,
            }
            if actor.wild_shape is not None
            else None
        ),
        "temp_hp": actor.temp_hp, "max_hp": actor.max_hp, "speed_feet": actor.speed_feet,
        "position": _coordinate_payload(actor.position), "faction": actor.faction.value,
        "size": actor.size.value,
        "damage_affinities": {
            "resistances": [value.value for value in actor.damage_affinities.resistances],
            "immunities": [value.value for value in actor.damage_affinities.immunities],
            "vulnerabilities": [value.value for value in actor.damage_affinities.vulnerabilities],
        },
        "uses_death_saves": actor.uses_death_saves,
        "level": actor.level,
        "experience_points": actor.experience_points,
        "exhaustion_level": actor.exhaustion_level,
        "attacks_per_action": actor.attacks_per_action,
        "condition_immunities": list(actor.condition_immunities),
        "auras": [
            {
                "id": aura.id,
                "label": aura.label,
                "radius_feet": aura.radius_feet,
                "target": aura.target.value,
                "effect_kind": aura.effect_kind.value,
                "value": aura.value,
            }
            for aura in actor.auras
        ],
        "triggers": [
            {
                "id": trigger.id,
                "label": trigger.label,
                "event_type": trigger.event_type.value,
                "effect_kind": trigger.effect_kind.value,
                "value": trigger.value,
            }
            for trigger in actor.triggers
        ],
        "features": [
            {
                "feature_id": feature.feature_id,
                "label": feature.label,
                "description": feature.description,
                "source_kind": feature.source_kind.value,
                "source_ref": feature.source_ref,
                "resource_ids": list(feature.resource_ids),
                "action_ids": list(feature.action_ids),
                "trigger_ids": list(feature.trigger_ids),
                "aura_ids": list(feature.aura_ids),
            }
            for feature in actor.features
        ],
        "death_saves": {
            "successes": actor.death_saves.successes,
            "failures": actor.death_saves.failures,
            "stable": actor.death_saves.stable,
            "dead": actor.death_saves.dead,
        },
        "ability_scores": {name: getattr(actor.ability_scores, name) for name in _ABILITY_NAMES},
        "proficiency_bonus": actor.proficiency_bonus,
        "proficiencies": {
            "saving_throws": list(actor.proficiencies.saving_throws),
            "skills": list(actor.proficiencies.skills),
            "expertise": list(actor.proficiencies.expertise),
            "weapons": list(actor.proficiencies.weapons),
            "armor": list(actor.proficiencies.armor),
            "tools": list(actor.proficiencies.tools),
        },
        "spell_slots": [
            {
                "level": slot.level,
                "remaining": slot.remaining,
                "maximum": slot.maximum,
                "recovery": slot.recovery,
                "temporary": slot.temporary,
            }
            for slot in actor.spell_slots
        ],
        "spell_save_dc": actor.spell_save_dc, "spell_ids": list(actor.spell_ids),
        "spells": [_spell_definition_payload(spell) for spell in actor.spells],
        "spell_access": [
            {
                "kind": profile.kind.value,
                "spell_ids": list(profile.spell_ids),
                "allowed_focus_kinds": list(profile.allowed_focus_kinds),
                "casting_ability": profile.casting_ability,
                "resource_ids_by_spell": {
                    spell_id: resource_id
                    for spell_id, resource_id in profile.resource_ids_by_spell
                },
            }
            for profile in actor.spell_access
        ],
        "currency": actor.currency.as_payload(),
        "inventory": [inventory_item_payload(item) for item in actor.inventory],
        "active_light": (
            None
            if actor.active_light is None
            else {
                "source_item_id": actor.active_light.source_item_id,
                "source_name": actor.active_light.source_name,
                "bright_distance_feet": actor.active_light.bright_distance_feet,
                "dim_additional_feet": actor.active_light.dim_additional_feet,
                "remaining_minutes": actor.active_light.remaining_minutes,
                "shape": actor.active_light.shape.value,
                "hooded_dim_distance_feet": actor.active_light.hooded_dim_distance_feet,
                "hood_lowered": actor.active_light.hood_lowered,
            }
        ),
        "senses": actor.senses.as_payload(),
        "spell_preparation": None if prep is None else {
            "source_label": prep.source_label, "preparation_limit": prep.preparation_limit,
            "available_spells": [{"id": spell.id, "label": spell.label, "level": spell.level} for spell in prep.available_spells],
            "prepared_spell_ids": list(prep.prepared_spell_ids),
            "always_prepared_spell_ids": list(prep.always_prepared_spell_ids), "confirmed": prep.confirmed,
        },
        "hit_dice": [{"die_sides": pool.die_sides, "remaining": pool.remaining, "maximum": pool.maximum} for pool in actor.hit_dice],
        "resource_pools": [
            {
                "id": pool.id,
                "label": pool.label,
                "current": pool.current,
                "maximum": pool.maximum,
                "recovery": pool.recovery.value,
                "recharge": (
                    None
                    if pool.recharge is None
                    else {
                        "die_sides": pool.recharge.die_sides,
                        "minimum_roll": pool.recharge.minimum_roll,
                    }
                ),
            }
            for pool in actor.resource_pools
        ],
    }


def _resource_pool_from_payload(raw: object) -> ActorResourcePool:
    pool = _mapping(raw, "resource")
    recharge_raw = pool.get("recharge")
    recharge = None
    if recharge_raw is not None:
        item = _mapping(recharge_raw, "resource.recharge")
        recharge = ResourceRechargeRule(
            die_sides=_integer(item.get("die_sides", 6), "resource.recharge.die_sides"),
            minimum_roll=_integer(
                item.get("minimum_roll"),
                "resource.recharge.minimum_roll",
            ),
        )
    return ActorResourcePool(
        id=_string(pool.get("id"), "resource.id"),
        label=_string(pool.get("label"), "resource.label"),
        current=_integer(pool.get("current"), "resource.current"),
        maximum=_integer(pool.get("maximum"), "resource.maximum"),
        recovery=_enum(RecoveryPeriod, pool.get("recovery"), "resource.recovery"),
        recharge=recharge,
    )


def _spell_definition_payload(spell: SpellDefinition) -> dict[str, object]:
    return {
        "id": spell.id,
        "name": spell.name,
        "level": spell.level,
        "school": spell.school.value,
        "casting_time": spell.casting_time.value,
        "range": {"kind": spell.range.kind.value, "feet": spell.range.feet},
        "components": {
            "verbal": spell.components.verbal,
            "somatic": spell.components.somatic,
            "materials": [
                {
                    "item_id": material.item_id,
                    "label": material.label,
                    "minimum_value_cp": material.minimum_value_cp,
                    "consumed": material.consumed,
                    "quantity": material.quantity,
                }
                for material in spell.components.materials
            ],
        },
        "duration": {"kind": spell.duration.kind.value, "amount": spell.duration.amount},
        "concentration": spell.concentration,
        "ritual": spell.ritual,
        "effect_kind": spell.effect_kind,
        "scaling": (
            None
            if spell.scaling is None
            else {
                "damage_dice_per_slot_level": spell.scaling.damage_dice_per_slot_level,
                "healing_dice_per_slot_level": spell.scaling.healing_dice_per_slot_level,
                "targets_per_slot_level": spell.scaling.targets_per_slot_level,
                "cantrip_damage_dice_per_tier": spell.scaling.cantrip_damage_dice_per_tier,
            }
        ),
        "exploration_effect": (
            None
            if spell.exploration_effect is None
            else {
                "kind": spell.exploration_effect.kind.value,
                "flag_key": spell.exploration_effect.flag_key,
                "flag_value": spell.exploration_effect.flag_value,
            }
        ),
        "exploration_tags": list(spell.exploration_tags),
        "exploration_target_tags": list(spell.exploration_target_tags),
        "exploration_consequence_tags": list(spell.exploration_consequence_tags),
    }


def _spell_definition_from_payload(raw: object) -> SpellDefinition:
    data = _mapping(raw, "actor.spell")
    range_data = _mapping(data.get("range"), "actor.spell.range")
    components = _mapping(data.get("components"), "actor.spell.components")
    duration = _mapping(data.get("duration"), "actor.spell.duration")
    scaling_raw = data.get("scaling")
    scaling = None
    if scaling_raw is not None:
        scaling_data = _mapping(scaling_raw, "actor.spell.scaling")
        scaling = SpellScaling(
            damage_dice_per_slot_level=_integer(
                scaling_data.get("damage_dice_per_slot_level", 0),
                "actor.spell.scaling.damage_dice_per_slot_level",
            ),
            healing_dice_per_slot_level=_integer(
                scaling_data.get("healing_dice_per_slot_level", 0),
                "actor.spell.scaling.healing_dice_per_slot_level",
            ),
            targets_per_slot_level=_integer(
                scaling_data.get("targets_per_slot_level", 0),
                "actor.spell.scaling.targets_per_slot_level",
            ),
            cantrip_damage_dice_per_tier=_integer(
                scaling_data.get("cantrip_damage_dice_per_tier", 0),
                "actor.spell.scaling.cantrip_damage_dice_per_tier",
            ),
        )
    exploration_effect_raw = data.get("exploration_effect")
    exploration_effect = None
    if exploration_effect_raw is not None:
        exploration_effect_data = _mapping(
            exploration_effect_raw,
            "actor.spell.exploration_effect",
        )
        exploration_effect = SpellExplorationEffect(
            kind=_enum(
                SpellExplorationEffectKind,
                exploration_effect_data.get("kind"),
                "actor.spell.exploration_effect.kind",
            ),
            flag_key=_string(
                exploration_effect_data.get("flag_key"),
                "actor.spell.exploration_effect.flag_key",
            ),
            flag_value=exploration_effect_data.get("flag_value", True),
        )
    return SpellDefinition(
        id=_string(data.get("id"), "actor.spell.id"),
        name=_string(data.get("name"), "actor.spell.name"),
        level=_integer(data.get("level"), "actor.spell.level"),
        school=_enum(SpellSchool, data.get("school"), "actor.spell.school"),
        casting_time=_enum(
            SpellCastingTime,
            data.get("casting_time"),
            "actor.spell.casting_time",
        ),
        range=SpellRange(
            _enum(SpellRangeKind, range_data.get("kind"), "actor.spell.range.kind"),
            _integer(range_data.get("feet", 0), "actor.spell.range.feet"),
        ),
        components=SpellComponents(
            verbal=_boolean(components.get("verbal", False), "actor.spell.components.verbal"),
            somatic=_boolean(components.get("somatic", False), "actor.spell.components.somatic"),
            materials=tuple(
                SpellMaterial(
                    item_id=_string(material.get("item_id"), "actor.spell.material.item_id"),
                    label=_string(material.get("label"), "actor.spell.material.label"),
                    minimum_value_cp=_integer(
                        material.get("minimum_value_cp", 0),
                        "actor.spell.material.minimum_value_cp",
                    ),
                    consumed=_boolean(
                        material.get("consumed", False),
                        "actor.spell.material.consumed",
                    ),
                    quantity=_integer(
                        material.get("quantity", 1),
                        "actor.spell.material.quantity",
                    ),
                )
                for raw_material in _sequence(
                    components.get("materials", []),
                    "actor.spell.components.materials",
                )
                for material in (_mapping(raw_material, "actor.spell.material"),)
            ),
        ),
        duration=SpellDuration(
            _enum(SpellDurationKind, duration.get("kind"), "actor.spell.duration.kind"),
            _integer(duration.get("amount", 1), "actor.spell.duration.amount"),
        ),
        concentration=_boolean(data.get("concentration", False), "actor.spell.concentration"),
        ritual=_boolean(data.get("ritual", False), "actor.spell.ritual"),
        effect_kind=_string(data.get("effect_kind"), "actor.spell.effect_kind"),
        scaling=scaling,
        exploration_effect=exploration_effect,
        exploration_tags=tuple(
            _string(value, "actor.spell.exploration_tags")
            for value in _sequence(
                data.get("exploration_tags", []),
                "actor.spell.exploration_tags",
            )
        ),
        exploration_target_tags=tuple(
            _string(value, "actor.spell.exploration_target_tags")
            for value in _sequence(
                data.get("exploration_target_tags", []),
                "actor.spell.exploration_target_tags",
            )
        ),
        exploration_consequence_tags=tuple(
            _string(value, "actor.spell.exploration_consequence_tags")
            for value in _sequence(
                data.get("exploration_consequence_tags", []),
                "actor.spell.exploration_consequence_tags",
            )
        ),
    )


def _actor_from_payload(raw: object) -> Actor:
    data = _mapping(raw, "actor")
    abilities = _mapping(data.get("ability_scores"), "actor.ability_scores")
    prep_raw = data.get("spell_preparation")
    death_raw = _mapping(data.get("death_saves", {}), "actor.death_saves")
    proficiency_raw = _mapping(data.get("proficiencies", {}), "actor.proficiencies")
    affinities_raw = _mapping(data.get("damage_affinities", {}), "actor.damage_affinities")
    senses_raw = _mapping(data.get("senses", {}), "actor.senses")
    wild_shape_raw = data.get("wild_shape")
    wild_shape = None
    if wild_shape_raw is not None:
        shape = _mapping(wild_shape_raw, "actor.wild_shape")
        original_abilities = _mapping(
            shape.get("original_ability_scores"),
            "actor.wild_shape.original_ability_scores",
        )
        original_senses = _mapping(
            shape.get("original_senses", {}),
            "actor.wild_shape.original_senses",
        )
        original_affinities = _mapping(
            shape.get("original_damage_affinities", {}),
            "actor.wild_shape.original_damage_affinities",
        )
        wild_shape = WildShapeState(
            form_id=_string(shape.get("form_id"), "actor.wild_shape.form_id"),
            form_name=_string(shape.get("form_name"), "actor.wild_shape.form_name"),
            original_ac=_integer(shape.get("original_ac"), "actor.wild_shape.original_ac"),
            original_hp=_integer(shape.get("original_hp"), "actor.wild_shape.original_hp"),
            original_max_hp=_integer(
                shape.get("original_max_hp"),
                "actor.wild_shape.original_max_hp",
            ),
            original_speed_feet=_integer(
                shape.get("original_speed_feet"),
                "actor.wild_shape.original_speed_feet",
            ),
            original_ability_scores=AbilityScores(
                **{
                    name: _integer(
                        original_abilities.get(name),
                        f"actor.wild_shape.original_ability_scores.{name}",
                    )
                    for name in _ABILITY_NAMES
                }
            ),
            original_size=_enum(
                CreatureSize,
                shape.get("original_size"),
                "actor.wild_shape.original_size",
            ),
            original_senses=ActorSenseProfile(
                darkvision_feet=_integer(
                    original_senses.get("darkvision_feet", 0),
                    "actor.wild_shape.original_senses.darkvision_feet",
                ),
                blindsight_feet=_integer(
                    original_senses.get("blindsight_feet", 0),
                    "actor.wild_shape.original_senses.blindsight_feet",
                ),
                tremorsense_feet=_integer(
                    original_senses.get("tremorsense_feet", 0),
                    "actor.wild_shape.original_senses.tremorsense_feet",
                ),
                truesight_feet=_integer(
                    original_senses.get("truesight_feet", 0),
                    "actor.wild_shape.original_senses.truesight_feet",
                ),
                magical_darkness_vision_feet=_integer(
                    original_senses.get("magical_darkness_vision_feet", 0),
                    "actor.wild_shape.original_senses.magical_darkness_vision_feet",
                ),
            ),
            original_damage_affinities=DamageAffinityProfile(
                resistances=tuple(
                    _enum(DamageType, value, "wild_shape.resistance")
                    for value in _sequence(
                        original_affinities.get("resistances", []),
                        "wild_shape.resistances",
                    )
                ),
                immunities=tuple(
                    _enum(DamageType, value, "wild_shape.immunity")
                    for value in _sequence(
                        original_affinities.get("immunities", []),
                        "wild_shape.immunities",
                    )
                ),
                vulnerabilities=tuple(
                    _enum(DamageType, value, "wild_shape.vulnerability")
                    for value in _sequence(
                        original_affinities.get("vulnerabilities", []),
                        "wild_shape.vulnerabilities",
                    )
                ),
            ),
            original_creature_type=_string(
                shape.get("original_creature_type"),
                "actor.wild_shape.original_creature_type",
            ),
            remaining_minutes=_integer(
                shape.get("remaining_minutes"),
                "actor.wild_shape.remaining_minutes",
            ),
        )
    prep = None
    if prep_raw is not None:
        item = _mapping(prep_raw, "actor.spell_preparation")
        prep = SpellPreparationProfile(
            source_label=_string(item.get("source_label"), "spell_preparation.source_label"),
            preparation_limit=_integer(item.get("preparation_limit"), "spell_preparation.preparation_limit"),
            available_spells=tuple(
                PreparableSpell(_string(spell.get("id"), "spell.id"), _string(spell.get("label"), "spell.label"), _integer(spell.get("level"), "spell.level"))
                for value in _sequence(item.get("available_spells"), "spell_preparation.available_spells")
                for spell in (_mapping(value, "spell"),)
            ),
            prepared_spell_ids=_string_tuple(item.get("prepared_spell_ids", []), "prepared_spell_ids"),
            always_prepared_spell_ids=_string_tuple(item.get("always_prepared_spell_ids", []), "always_prepared_spell_ids"),
            confirmed=_boolean(item.get("confirmed"), "spell_preparation.confirmed"),
        )
    inventory = tuple(
        _inventory_item_from_payload(value, "actor.inventory")
        for value in _sequence(data.get("inventory", []), "actor.inventory")
    )
    active_light_raw = data.get("active_light")
    active_light = None
    if active_light_raw is not None:
        light = _mapping(active_light_raw, "actor.active_light")
        active_light = ActiveLight(
            source_item_id=_string(light.get("source_item_id"), "actor.active_light.source_item_id"),
            source_name=_string(light.get("source_name"), "actor.active_light.source_name"),
            bright_distance_feet=_integer(light.get("bright_distance_feet"), "actor.active_light.bright_distance_feet"),
            dim_additional_feet=_integer(light.get("dim_additional_feet"), "actor.active_light.dim_additional_feet"),
            remaining_minutes=_integer(light.get("remaining_minutes"), "actor.active_light.remaining_minutes"),
            shape=_enum(LightShape, light.get("shape"), "actor.active_light.shape"),
            hooded_dim_distance_feet=_optional_integer(light.get("hooded_dim_distance_feet"), "actor.active_light.hooded_dim_distance_feet"),
            hood_lowered=_boolean(light.get("hood_lowered", False), "actor.active_light.hood_lowered"),
        )
    validate_attunement_limit(inventory)
    return Actor(
        id=ActorId(_string(data.get("id"), "actor.id")), name=_string(data.get("name"), "actor.name"),
        portrait=_string(data.get("portrait", ""), "actor.portrait", allow_empty=True),
        creature_type=_string(
            data.get("creature_type", "humanoid"),
            "actor.creature_type",
        ),
        wild_shape=wild_shape,
        ac=_integer(data.get("ac"), "actor.ac"), hp=_integer(data.get("hp"), "actor.hp"),
        temp_hp=_integer(data.get("temp_hp"), "actor.temp_hp"), max_hp=_integer(data.get("max_hp"), "actor.max_hp"),
        speed_feet=_integer(data.get("speed_feet"), "actor.speed_feet"), position=_coordinate(data.get("position"), "actor.position"),
        faction=_enum(Faction, data.get("faction"), "actor.faction"),
        size=_enum(CreatureSize, data.get("size", CreatureSize.MEDIUM.value), "actor.size"),
        ability_scores=AbilityScores(**{name: _integer(abilities.get(name), f"ability_scores.{name}") for name in _ABILITY_NAMES}),
        spell_slots=tuple(
            SpellSlotState(
                _integer(slot.get("level"), "slot.level"),
                _integer(slot.get("remaining"), "slot.remaining"),
                _integer(slot.get("maximum"), "slot.maximum"),
                str(slot.get("recovery", "long_rest")),
                bool(slot.get("temporary", False)),
            )
            for value in _sequence(data.get("spell_slots", []), "spell_slots")
            for slot in (_mapping(value, "slot"),)
        ),
        spell_save_dc=_integer(data.get("spell_save_dc"), "actor.spell_save_dc"),
        currency=_currency_from_payload(data.get("currency", {})),
        inventory=inventory,
        active_light=active_light,
        senses=ActorSenseProfile(
            darkvision_feet=_integer(
                senses_raw.get("darkvision_feet", 0),
                "actor.senses.darkvision_feet",
            ),
            blindsight_feet=_integer(
                senses_raw.get("blindsight_feet", 0),
                "actor.senses.blindsight_feet",
            ),
            tremorsense_feet=_integer(
                senses_raw.get("tremorsense_feet", 0),
                "actor.senses.tremorsense_feet",
            ),
            truesight_feet=_integer(
                senses_raw.get("truesight_feet", 0),
                "actor.senses.truesight_feet",
            ),
            magical_darkness_vision_feet=_integer(
                senses_raw.get("magical_darkness_vision_feet", 0),
                "actor.senses.magical_darkness_vision_feet",
            ),
        ),
        spell_ids=_string_tuple(data.get("spell_ids", []), "actor.spell_ids"), spell_preparation=prep,
        spells=tuple(
            _spell_definition_from_payload(value)
            for value in _sequence(data.get("spells", []), "actor.spells")
        ),
        spell_access=tuple(
            SpellAccessProfile(
                kind=_enum(
                    SpellAccessKind,
                    profile.get("kind"),
                    "actor.spell_access.kind",
                ),
                spell_ids=_string_tuple(
                    profile.get("spell_ids", []),
                    "actor.spell_access.spell_ids",
                ),
                allowed_focus_kinds=_string_tuple(
                    profile.get("allowed_focus_kinds", []),
                    "actor.spell_access.allowed_focus_kinds",
                ),
                casting_ability=(
                    str(profile["casting_ability"])
                    if profile.get("casting_ability") is not None
                    else None
                ),
                resource_ids_by_spell=tuple(
                    (str(spell_id), str(resource_id))
                    for spell_id, resource_id in _mapping(
                        profile.get("resource_ids_by_spell", {}),
                        "actor.spell_access.resource_ids_by_spell",
                    ).items()
                ),
            )
            for raw_profile in _sequence(
                data.get("spell_access", []),
                "actor.spell_access",
            )
            for profile in (_mapping(raw_profile, "actor.spell_access"),)
        ),
        hit_dice=tuple(HitDicePool(_integer(pool.get("die_sides"), "hit_die.die_sides"), _integer(pool.get("remaining"), "hit_die.remaining"), _integer(pool.get("maximum"), "hit_die.maximum")) for value in _sequence(data.get("hit_dice", []), "hit_dice") for pool in (_mapping(value, "hit_die"),)),
        resource_pools=tuple(_resource_pool_from_payload(value) for value in _sequence(data.get("resource_pools", []), "resource_pools")),
        level=_integer(data.get("level", 1), "actor.level"),
        experience_points=_integer(
            data.get("experience_points", 0),
            "actor.experience_points",
        ),
        exhaustion_level=_integer(
            data.get("exhaustion_level", 0),
            "actor.exhaustion_level",
        ),
        proficiency_bonus=_integer(data.get("proficiency_bonus", 2), "actor.proficiency_bonus"),
        proficiencies=ProficiencyProfile(
            saving_throws=_string_tuple(
                proficiency_raw.get("saving_throws", []),
                "actor.proficiencies.saving_throws",
            ),
            skills=_string_tuple(
                proficiency_raw.get("skills", data.get("skill_proficiencies", [])),
                "actor.proficiencies.skills",
            ),
            expertise=_string_tuple(
                proficiency_raw.get("expertise", data.get("skill_expertise", [])),
                "actor.proficiencies.expertise",
            ),
            weapons=_string_tuple(proficiency_raw.get("weapons", []), "actor.proficiencies.weapons"),
            armor=_string_tuple(proficiency_raw.get("armor", []), "actor.proficiencies.armor"),
            tools=_string_tuple(proficiency_raw.get("tools", []), "actor.proficiencies.tools"),
        ),
        uses_death_saves=_boolean(data.get("uses_death_saves", False), "actor.uses_death_saves"),
        death_saves=DeathSaveState(
            successes=_integer(death_raw.get("successes", 0), "death_saves.successes"),
            failures=_integer(death_raw.get("failures", 0), "death_saves.failures"),
            stable=_boolean(death_raw.get("stable", False), "death_saves.stable"),
            dead=_boolean(death_raw.get("dead", False), "death_saves.dead"),
        ),
        damage_affinities=DamageAffinityProfile(
            resistances=tuple(
                _enum(DamageType, value, "damage_affinities.resistances")
                for value in _sequence(affinities_raw.get("resistances", []), "damage_affinities.resistances")
            ),
            immunities=tuple(
                _enum(DamageType, value, "damage_affinities.immunities")
                for value in _sequence(affinities_raw.get("immunities", []), "damage_affinities.immunities")
            ),
            vulnerabilities=tuple(
                _enum(DamageType, value, "damage_affinities.vulnerabilities")
                for value in _sequence(affinities_raw.get("vulnerabilities", []), "damage_affinities.vulnerabilities")
            ),
        ),
        attacks_per_action=_integer(data.get("attacks_per_action", 1), "actor.attacks_per_action"),
        condition_immunities=_string_tuple(
            data.get("condition_immunities", []),
            "actor.condition_immunities",
        ),
        auras=tuple(
            ActorAura(
                id=_string(aura.get("id"), "actor.aura.id"),
                label=_string(aura.get("label"), "actor.aura.label"),
                radius_feet=_integer(aura.get("radius_feet"), "actor.aura.radius_feet"),
                target=_enum(AuraTarget, aura.get("target"), "actor.aura.target"),
                effect_kind=_enum(
                    AuraEffectKind,
                    aura.get("effect_kind"),
                    "actor.aura.effect_kind",
                ),
                value=_integer(aura.get("value"), "actor.aura.value"),
            )
            for raw_aura in _sequence(data.get("auras", []), "actor.auras")
            for aura in (_mapping(raw_aura, "actor.aura"),)
        ),
        triggers=tuple(
            ActorTrigger(
                id=_string(trigger.get("id"), "actor.trigger.id"),
                label=_string(trigger.get("label"), "actor.trigger.label"),
                event_type=_enum(
                    TriggerEventType,
                    trigger.get("event_type"),
                    "actor.trigger.event_type",
                ),
                effect_kind=_enum(
                    TriggerEffectKind,
                    trigger.get("effect_kind"),
                    "actor.trigger.effect_kind",
                ),
                value=_integer(trigger.get("value"), "actor.trigger.value"),
            )
            for raw_trigger in _sequence(data.get("triggers", []), "actor.triggers")
            for trigger in (_mapping(raw_trigger, "actor.trigger"),)
        ),
        features=tuple(
            FeatureGrant(
                feature_id=_string(feature.get("feature_id"), "actor.feature.feature_id"),
                label=_string(feature.get("label"), "actor.feature.label"),
                description=_string(
                    feature.get("description", ""),
                    "actor.feature.description",
                    allow_empty=True,
                ),
                source_kind=_enum(
                    FeatureSourceKind,
                    feature.get("source_kind"),
                    "actor.feature.source_kind",
                ),
                source_ref=_string(feature.get("source_ref"), "actor.feature.source_ref"),
                resource_ids=_string_tuple(feature.get("resource_ids", []), "actor.feature.resource_ids"),
                action_ids=_string_tuple(feature.get("action_ids", []), "actor.feature.action_ids"),
                trigger_ids=_string_tuple(feature.get("trigger_ids", []), "actor.feature.trigger_ids"),
                aura_ids=_string_tuple(feature.get("aura_ids", []), "actor.feature.aura_ids"),
            )
            for raw_feature in _sequence(data.get("features", []), "actor.features")
            for feature in (_mapping(raw_feature, "actor.feature"),)
        ),
    )


def _exploration_payload(state: ExplorationState) -> dict[str, object]:
    return {
        "party_position": {"zone_id": state.party_position.zone_id, "marker_position": _coordinate_payload(state.party_position.marker_position)},
        "flags": [{"key": key, "value": _json_value(value, "flag.value")} for key, value in state.flags.values],
        "point_visibility": [{"id": point.id, "visibility": point.visibility.value} for point in state.points],
        "point_positions": [
            {
                "id": point.id,
                "positions": [_coordinate_payload(position) for position in point.positions],
            }
            for point in state.points
        ],
        "exhausted_search_zones": list(state.exhausted_search_zones),
        "party_loot": {
            "id": state.party_loot.id,
            "label": state.party_loot.label,
            "items": [
                inventory_item_payload(item) for item in state.party_loot.items
            ],
            "currency": state.party_loot.currency.as_payload(),
        },
        "challenge_states": [
            {"challenge_id": item.challenge_id, "current_progress": item.current_progress, "noise": item.noise,
             "complications": list(item.complications), "completed": item.completed,
             "attempts": [_attempt_payload(attempt) for attempt in item.attempts]}
            for item in state.challenge_states
        ],
        "inventory_resource_ids": list(state.inventory_resource_ids), "elapsed_minutes": state.elapsed_minutes,
        "magic_effects": [
            {
                "id": effect.id,
                "actor_id": effect.actor_id,
                "spell_id": effect.spell_id,
                "label": effect.label,
                "flag_key": effect.flag_key,
                "flag_value": _json_value(effect.flag_value, "magic_effect.flag_value"),
                "started_at_minute": effect.started_at_minute,
                "expires_at_minute": effect.expires_at_minute,
            }
            for effect in state.magic_effects
        ],
        "short_rest_counts": [{"policy_id": key, "count": value} for key, value in state.short_rest_counts],
        "temporary_items": [
            {
                "id": item.id, "template_id": item.template_id, "label": item.label,
                "description": item.description, "bonus_tags": list(item.bonus_tags),
                "modifier": item.modifier, "advantage": item.advantage,
                "uses_remaining": item.uses_remaining, "created_in_zone_id": item.created_in_zone_id,
                "source_materials": list(item.source_materials), "risk": item.risk,
                "purpose_id": item.purpose_id,
                "component_uses": [
                    {
                        "source_id": component.source_id,
                        "quantity": component.quantity,
                        "disposition": component.disposition.value,
                    }
                    for component in item.component_uses
                ],
                "scope": item.scope.value,
                "time_cost_minutes": item.time_cost_minutes,
                "dismantled": item.dismantled,
            }
            for item in state.temporary_items
        ],
        "encounter_edges": [
            {
                "id": edge.id,
                "type": edge.edge_type.value,
                "label": edge.label,
                "beneficiary_actor_id": edge.beneficiary_actor_id,
                "encounter_trigger_id": edge.encounter_trigger_id,
                "source_observation_id": edge.source_observation_id,
                "source_fact_id": edge.source_fact_id,
                "consumed": edge.consumed,
            }
            for edge in state.encounter_edges
        ],
        "source_discoveries": [
            {
                "source_id": item.source_id,
                "zone_id": item.zone_id,
                "requested_as": item.requested_as,
                "purpose": item.purpose,
                "matched_properties": list(item.matched_properties),
                "semantic_substitution": item.semantic_substitution,
            }
            for item in state.source_discoveries
        ],
        "source_collections": [
            {
                "source_id": item.source_id,
                "zone_id": item.zone_id,
                "quantity": item.quantity,
                "destination": item.destination,
                "label": item.label,
                "owner_actor_id": item.owner_actor_id,
            }
            for item in state.source_collections
        ],
        "fixture_states": [
            {
                "zone_id": item.zone_id,
                "fixture_id": item.fixture_id,
                "condition": item.condition,
                "unavailable": item.unavailable,
                "detached": item.detached,
                "destroyed": item.destroyed,
                "opened": item.opened,
                "locked": item.locked,
                "looted": item.looted,
                "current_hit_points": item.current_hit_points,
                "released_item_ids": list(item.released_item_ids),
            }
            for item in state.fixture_states
        ],
        "condition_states": [
            {
                "actor_id": item.actor_id,
                "condition": item.condition.value,
                "source_actor_id": item.source_actor_id,
                "source_label": item.source_label,
                "duration": item.duration.value,
                "expiration_actor_id": item.expiration_actor_id,
                "save_ability": item.save_ability,
                "save_dc": item.save_dc,
                "save_timing": item.save_timing.value if item.save_timing is not None else None,
                "source_spell_id": item.source_spell_id,
                "source_spell_level": item.source_spell_level,
                "expiration_event_count": item.expiration_event_count,
            }
            for item in state.condition_states
        ],
        "trap_states": [
            {"trap_id": item.trap_id, "status": item.status.value}
            for item in state.trap_states
        ],
        "hidden_actor_states": [
            {
                "actor_id": item.actor_id,
                "zone_id": item.zone_id,
                "natural_roll": item.natural_roll,
                "stealth_total": item.stealth_total,
            }
            for item in state.hidden_actor_states
        ],
        "npc_states": [item.as_payload() for item in state.npc_states],
        "merchants": [
            {
                "id": merchant.id,
                "name": merchant.name,
                "buyback_percent": merchant.buyback_percent,
                "currency": merchant.currency.as_payload(),
                "inventory": [
                    inventory_item_payload(item)
                    for item in merchant.inventory
                ],
            }
            for merchant in state.merchants
        ],
    }


def _exploration_from_payload(base: ExplorationState, raw: object) -> ExplorationState:
    data = _mapping(raw, "exploration")
    party = _mapping(data.get("party_position"), "exploration.party_position")
    zone_id = _string(party.get("zone_id"), "party_position.zone_id")
    if zone_id not in {zone.id for zone in base.zones}:
        raise SnapshotValidationError(f"Zapis odwołuje się do nieznanej lokacji: {zone_id}.")
    visibility = {}
    for raw_item in _sequence(data.get("point_visibility"), "point_visibility"):
        item = _mapping(raw_item, "point_visibility item")
        visibility[_string(item.get("id"), "point.id")] = _enum(SetupVisibility, item.get("visibility"), "point.visibility")
    known_points = {point.id for point in base.points}
    if set(visibility) != known_points:
        raise SnapshotValidationError("Lista punktów zapisu nie odpowiada aktualnej wersji scenariusza.")
    point_positions = {point.id: point.positions for point in base.points}
    if "point_positions" in data:
        point_positions = {}
        for raw_item in _sequence(data.get("point_positions"), "point_positions"):
            item = _mapping(raw_item, "point_positions item")
            point_id = _string(item.get("id"), "point_positions.id")
            positions = tuple(
                _coordinate(raw_position, f"point_positions.{point_id}.position")
                for raw_position in _sequence(
                    item.get("positions", []),
                    f"point_positions.{point_id}.positions",
                )
            )
            if not positions:
                raise SnapshotValidationError("Punkt eksploracji musi zachować co najmniej jedną pozycję.")
            point_positions[point_id] = positions
        if set(point_positions) != known_points:
            raise SnapshotValidationError(
                "Lista pozycji punktów zapisu nie odpowiada aktualnej wersji scenariusza."
            )
    flags = []
    for raw_item in _sequence(data.get("flags", []), "flags"):
        item = _mapping(raw_item, "flag")
        value = item.get("value")
        _assert_json_value(value, "flag.value")
        flags.append((_string(item.get("key"), "flag.key"), value))
    challenge_states = tuple(_challenge_state_from_payload(item) for item in _sequence(data.get("challenge_states", []), "challenge_states"))
    unknown_challenges = {item.challenge_id for item in challenge_states} - {item.id for item in base.challenges}
    if unknown_challenges:
        raise SnapshotValidationError(f"Zapis zawiera nieznane wyzwania: {', '.join(sorted(unknown_challenges))}.")
    resources = _string_tuple(data.get("inventory_resource_ids", []), "inventory_resource_ids")
    if set(resources) - {item.id for item in base.resources}:
        raise SnapshotValidationError("Zapis zawiera nieznane zasoby scenariusza.")
    party_loot_raw = _mapping(
        data.get(
            "party_loot",
            {
                "id": "party_stash",
                "label": "Łup drużyny",
                "items": [],
                "currency": {},
            },
        ),
        "exploration.party_loot",
    )
    party_loot = LootBundle(
        id=_string(party_loot_raw.get("id"), "exploration.party_loot.id"),
        label=_string(
            party_loot_raw.get("label"),
            "exploration.party_loot.label",
        ),
        items=tuple(
            _inventory_item_from_payload(
                item,
                "exploration.party_loot.item",
            )
            for item in _sequence(
                party_loot_raw.get("items", []),
                "exploration.party_loot.items",
            )
        ),
        currency=_currency_from_payload(party_loot_raw.get("currency", {})),
    )
    short_counts = tuple(
        (_string(item.get("policy_id"), "short_rest.policy_id"), _integer(item.get("count"), "short_rest.count"))
        for raw_item in _sequence(data.get("short_rest_counts", []), "short_rest_counts")
        for item in (_mapping(raw_item, "short_rest_count"),)
    )
    magic_effects = tuple(
        TimedMagicEffect(
            id=_string(item.get("id"), "magic_effect.id"),
            actor_id=_string(item.get("actor_id"), "magic_effect.actor_id"),
            spell_id=_string(item.get("spell_id"), "magic_effect.spell_id"),
            label=_string(item.get("label"), "magic_effect.label"),
            flag_key=_string(item.get("flag_key"), "magic_effect.flag_key"),
            flag_value=item.get("flag_value", True),
            started_at_minute=_integer(
                item.get("started_at_minute"),
                "magic_effect.started_at_minute",
            ),
            expires_at_minute=_optional_integer(
                item.get("expires_at_minute"),
                "magic_effect.expires_at_minute",
            ),
        )
        for raw_item in _sequence(
            data.get("magic_effects", []),
            "magic_effects",
        )
        for item in (_mapping(raw_item, "magic_effect"),)
    )
    temporary_items = tuple(
        TemporaryItem(
            id=_string(item.get("id"), "temporary_item.id"),
            template_id=_optional_string(item.get("template_id"), "temporary_item.template_id"),
            label=_string(item.get("label"), "temporary_item.label"),
            description=_string(item.get("description"), "temporary_item.description"),
            bonus_tags=_string_tuple(item.get("bonus_tags", []), "temporary_item.bonus_tags"),
            modifier=_integer(item.get("modifier"), "temporary_item.modifier"),
            advantage=_boolean(item.get("advantage"), "temporary_item.advantage"),
            uses_remaining=_integer(item.get("uses_remaining"), "temporary_item.uses_remaining"),
            created_in_zone_id=_string(item.get("created_in_zone_id"), "temporary_item.created_in_zone_id"),
            source_materials=_string_tuple(item.get("source_materials", []), "temporary_item.source_materials"),
            risk=_string(item.get("risk", ""), "temporary_item.risk", allow_empty=True),
            purpose_id=_optional_string(item.get("purpose_id"), "temporary_item.purpose_id"),
            component_uses=tuple(
                CraftingComponentUse(
                    source_id=_string(component.get("source_id"), "crafting_component.source_id"),
                    quantity=_integer(component.get("quantity"), "crafting_component.quantity"),
                    disposition=_enum(
                        CraftingComponentDisposition,
                        component.get("disposition"),
                        "crafting_component.disposition",
                    ),
                )
                for raw_component in _sequence(item.get("component_uses", []), "temporary_item.component_uses")
                for component in (_mapping(raw_component, "crafting_component"),)
            ),
            scope=_enum(
                TemporaryItemScope,
                item.get("scope", TemporaryItemScope.SCENARIO.value),
                "temporary_item.scope",
            ),
            time_cost_minutes=_integer(item.get("time_cost_minutes", 0), "temporary_item.time_cost_minutes"),
            dismantled=_boolean(item.get("dismantled", False), "temporary_item.dismantled"),
        )
        for raw_item in _sequence(data.get("temporary_items", []), "temporary_items")
        for item in (_mapping(raw_item, "temporary_item"),)
    )
    if any(item.created_in_zone_id not in {zone.id for zone in base.zones} for item in temporary_items):
        raise SnapshotValidationError("Zapis zawiera przedmiot tymczasowy z nieznanej lokacji.")
    encounter_edges = tuple(
        EncounterEdge(
            id=_string(item.get("id"), "encounter_edge.id"),
            edge_type=_enum(EncounterEdgeType, item.get("type"), "encounter_edge.type"),
            label=_string(item.get("label"), "encounter_edge.label"),
            beneficiary_actor_id=_string(
                item.get("beneficiary_actor_id"),
                "encounter_edge.beneficiary_actor_id",
            ),
            encounter_trigger_id=_string(
                item.get("encounter_trigger_id"),
                "encounter_edge.encounter_trigger_id",
            ),
            source_observation_id=_string(
                item.get("source_observation_id"),
                "encounter_edge.source_observation_id",
            ),
            source_fact_id=_string(item.get("source_fact_id"), "encounter_edge.source_fact_id"),
            consumed=_boolean(item.get("consumed", False), "encounter_edge.consumed"),
        )
        for raw_item in _sequence(data.get("encounter_edges", []), "encounter_edges")
        for item in (_mapping(raw_item, "encounter_edge"),)
    )
    source_discoveries = tuple(
        SceneSourceDiscovery(
            source_id=_string(item.get("source_id"), "source_discovery.source_id"),
            zone_id=_string(item.get("zone_id"), "source_discovery.zone_id"),
            requested_as=_string(
                item.get("requested_as", ""),
                "source_discovery.requested_as",
                allow_empty=True,
            ),
            purpose=_string(
                item.get("purpose", ""),
                "source_discovery.purpose",
                allow_empty=True,
            ),
            matched_properties=_string_tuple(
                item.get("matched_properties", []),
                "source_discovery.matched_properties",
            ),
            semantic_substitution=_boolean(
                item.get("semantic_substitution", False),
                "source_discovery.semantic_substitution",
            ),
        )
        for raw_item in _sequence(data.get("source_discoveries", []), "source_discoveries")
        for item in (_mapping(raw_item, "source_discovery"),)
    )
    known_zone_ids = {zone.id for zone in base.zones}
    if any(item.zone_id not in known_zone_ids for item in source_discoveries):
        raise SnapshotValidationError("Zapis zawiera znaleziony element z nieznanej lokacji.")
    if len({item.source_id for item in source_discoveries}) != len(source_discoveries):
        raise SnapshotValidationError("Zapis zawiera powtórzone znalezione elementy sceny.")
    source_collections = tuple(
        SceneSourceCollection(
            source_id=_string(item.get("source_id"), "source_collection.source_id"),
            zone_id=_string(item.get("zone_id"), "source_collection.zone_id"),
            quantity=_integer(item.get("quantity"), "source_collection.quantity"),
            destination=_string(item.get("destination"), "source_collection.destination"),
            label=_string(item.get("label"), "source_collection.label"),
            owner_actor_id=_optional_string(
                item.get("owner_actor_id"),
                "source_collection.owner_actor_id",
            ),
        )
        for raw_item in _sequence(data.get("source_collections", []), "source_collections")
        for item in (_mapping(raw_item, "source_collection"),)
    )
    if any(item.zone_id not in known_zone_ids for item in source_collections):
        raise SnapshotValidationError("Zapis zawiera zabrany element z nieznanej lokacji.")
    collection_keys = tuple(
        (item.source_id, item.destination, item.owner_actor_id)
        for item in source_collections
    )
    if len(collection_keys) != len(set(collection_keys)):
        raise SnapshotValidationError("Zapis zawiera powtórzone wpisy zabranych elementów.")
    fixture_states = tuple(
        FixtureRuntimeState(
            zone_id=_string(item.get("zone_id"), "fixture_state.zone_id"),
            fixture_id=_string(item.get("fixture_id"), "fixture_state.fixture_id"),
            condition=_string(item.get("condition"), "fixture_state.condition"),
            unavailable=_boolean(item.get("unavailable", False), "fixture_state.unavailable"),
            detached=_boolean(item.get("detached", False), "fixture_state.detached"),
            destroyed=_boolean(item.get("destroyed", False), "fixture_state.destroyed"),
            opened=_boolean(item.get("opened", False), "fixture_state.opened"),
            locked=_boolean(item.get("locked", False), "fixture_state.locked"),
            looted=_boolean(item.get("looted", False), "fixture_state.looted"),
            current_hit_points=(
                _integer(
                    item.get("current_hit_points"),
                    "fixture_state.current_hit_points",
                )
                if item.get("current_hit_points") is not None
                else None
            ),
            released_item_ids=_string_tuple(
                item.get("released_item_ids", []),
                "fixture_state.released_item_ids",
            ),
        )
        for raw_item in _sequence(data.get("fixture_states", []), "fixture_states")
        for item in (_mapping(raw_item, "fixture_state"),)
    )
    fixture_ids_by_zone = {
        zone.id: {fixture.id for fixture in zone.fixtures}
        for zone in base.zones
    }
    for fixture_state in fixture_states:
        if fixture_state.fixture_id not in fixture_ids_by_zone.get(fixture_state.zone_id, set()):
            raise SnapshotValidationError("Zapis zawiera stan nieznanego fixture'a.")
    fixture_state_keys = tuple((item.zone_id, item.fixture_id) for item in fixture_states)
    if len(fixture_state_keys) != len(set(fixture_state_keys)):
        raise SnapshotValidationError("Zapis zawiera powtórzony stan fixture'a.")
    condition_states = tuple(
        ConditionState(
            actor_id=_string(item.get("actor_id"), "exploration.condition.actor_id"),
            condition=_enum(
                CombatCondition,
                item.get("condition"),
                "exploration.condition.condition",
            ),
            source_actor_id=_optional_string(
                item.get("source_actor_id"),
                "exploration.condition.source_actor_id",
            ),
            source_label=_string(
                item.get("source_label", ""),
                "exploration.condition.source_label",
                allow_empty=True,
            ),
            duration=_enum(
                EffectDuration,
                item.get("duration", EffectDuration.PERMANENT.value),
                "exploration.condition.duration",
            ),
            expiration_actor_id=_optional_string(
                item.get("expiration_actor_id"),
                "exploration.condition.expiration_actor_id",
            ),
            save_ability=_optional_string(
                item.get("save_ability"),
                "exploration.condition.save_ability",
            ),
            save_dc=_optional_integer(item.get("save_dc"), "exploration.condition.save_dc"),
            save_timing=_optional_enum(
                ConditionSaveTiming,
                item.get("save_timing"),
                "exploration.condition.save_timing",
            ),
            source_spell_id=_optional_string(
                item.get("source_spell_id"),
                "exploration.condition.source_spell_id",
            ),
            source_spell_level=_optional_integer(
                item.get("source_spell_level"),
                "exploration.condition.source_spell_level",
            ),
            expiration_event_count=_integer(
                item.get("expiration_event_count", 1),
                "exploration.condition.expiration_event_count",
            ),
        )
        for raw_item in _sequence(data.get("condition_states", []), "condition_states")
        for item in (_mapping(raw_item, "condition_state"),)
    )
    trap_states = tuple(
        ExplorationTrapState(
            trap_id=_string(item.get("trap_id"), "exploration.trap_state.trap_id"),
            status=_enum(
                ExplorationTrapStatus,
                item.get("status"),
                "exploration.trap_state.status",
            ),
        )
        for raw_item in _sequence(data.get("trap_states", []), "trap_states")
        for item in (_mapping(raw_item, "trap_state"),)
    )
    unknown_trap_ids = {item.trap_id for item in trap_states} - {item.id for item in base.traps}
    if unknown_trap_ids:
        raise SnapshotValidationError("Zapis zawiera stan nieznanej pułapki.")
    if len({item.trap_id for item in trap_states}) != len(trap_states):
        raise SnapshotValidationError("Zapis zawiera powtórzony stan pułapki.")
    hidden_actor_states = tuple(
        ExplorationHiddenActorState(
            actor_id=_string(
                item.get("actor_id"),
                "exploration.hidden_actor_state.actor_id",
            ),
            zone_id=_string(
                item.get("zone_id"),
                "exploration.hidden_actor_state.zone_id",
            ),
            natural_roll=_integer(
                item.get("natural_roll"),
                "exploration.hidden_actor_state.natural_roll",
            ),
            stealth_total=_integer(
                item.get("stealth_total"),
                "exploration.hidden_actor_state.stealth_total",
            ),
        )
        for raw_item in _sequence(
            data.get("hidden_actor_states", []),
            "hidden_actor_states",
        )
        for item in (_mapping(raw_item, "hidden_actor_state"),)
    )
    if any(item.zone_id not in {zone.id for zone in base.zones} for item in hidden_actor_states):
        raise SnapshotValidationError("Zapis zawiera ukrycie w nieznanej lokacji.")
    if len({item.actor_id for item in hidden_actor_states}) != len(hidden_actor_states):
        raise SnapshotValidationError("Zapis zawiera powtórzony stan ukrycia aktora.")
    npc_states = base.npc_states
    if "npc_states" in data:
        npc_states = tuple(
            NpcRuntimeState(
                npc_id=_string(item.get("npc_id"), "exploration.npc_state.npc_id"),
                attitude=_enum(
                    NpcAttitude,
                    item.get("attitude"),
                    "exploration.npc_state.attitude",
                ),
                physical_state=_string(
                    item.get("physical_state", ""),
                    "exploration.npc_state.physical_state",
                    allow_empty=True,
                ),
                emotional_state=_string(
                    item.get("emotional_state", ""),
                    "exploration.npc_state.emotional_state",
                    allow_empty=True,
                ),
                interaction_status=_enum(
                    NpcInteractionStatus,
                    item.get("interaction_status", NpcInteractionStatus.ACTIVE.value),
                    "exploration.npc_state.interaction_status",
                ),
                closure_reason=_string(
                    item.get("closure_reason", ""),
                    "exploration.npc_state.closure_reason",
                    allow_empty=True,
                ),
                revealed_information_ids=_string_tuple(
                    item.get("revealed_information_ids", []),
                    "exploration.npc_state.revealed_information_ids",
                ),
                used_attempt_ids=_string_tuple(
                    item.get("used_attempt_ids", []),
                    "exploration.npc_state.used_attempt_ids",
                ),
                used_feature_ids=_string_tuple(
                    item.get("used_feature_ids", []),
                    "exploration.npc_state.used_feature_ids",
                ),
                relationship_events=tuple(
                    NpcRelationshipEvent(
                        sequence=_integer(event.get("sequence"), "npc_relationship_event.sequence"),
                        intent=_string(event.get("intent"), "npc_relationship_event.intent"),
                        outcome=_string(event.get("outcome"), "npc_relationship_event.outcome"),
                        summary=_string(event.get("summary"), "npc_relationship_event.summary"),
                        attempt_id=_optional_string(
                            event.get("attempt_id"),
                            "npc_relationship_event.attempt_id",
                        ),
                        actor_id=_optional_string(
                            event.get("actor_id"),
                            "npc_relationship_event.actor_id",
                        ),
                        critical_failure=bool(event.get("critical_failure", False)),
                    )
                    for raw_event in _sequence(
                        item.get("relationship_events", []),
                        "exploration.npc_state.relationship_events",
                    )
                    for event in (_mapping(raw_event, "npc_relationship_event"),)
                ),
            )
            for raw_item in _sequence(data.get("npc_states", []), "npc_states")
            for item in (_mapping(raw_item, "npc_state"),)
        )
        known_npcs = {
            point.npc_interaction.id: point.npc_interaction
            for point in base.points
            if point.npc_interaction is not None
        }
        if {item.npc_id for item in npc_states} != set(known_npcs):
            raise SnapshotValidationError("Lista stanów NPC nie odpowiada aktualnej wersji scenariusza.")
        for npc_state in npc_states:
            known_information_ids = {
                info.id for info in known_npcs[npc_state.npc_id].locked_information
            }
            if set(npc_state.revealed_information_ids) - known_information_ids:
                raise SnapshotValidationError("Zapis zawiera nieznaną informację NPC.")
    merchants = base.merchants
    if "merchants" in data:
        merchants = tuple(
            MerchantState(
                id=_string(item.get("id"), "exploration.merchant.id"),
                name=_string(item.get("name"), "exploration.merchant.name"),
                buyback_percent=_integer(
                    item.get("buyback_percent"),
                    "exploration.merchant.buyback_percent",
                ),
                currency=_currency_from_payload(item.get("currency", {})),
                inventory=tuple(
                    _inventory_item_from_payload(
                        raw_inventory_item,
                        "exploration.merchant.inventory.item",
                    )
                    for raw_inventory_item in _sequence(
                        item.get("inventory", []),
                        "exploration.merchant.inventory",
                    )
                ),
            )
            for raw_item in _sequence(data.get("merchants", []), "merchants")
            for item in (_mapping(raw_item, "merchant"),)
        )
        if {merchant.id for merchant in merchants} != {
            merchant.id for merchant in base.merchants
        }:
            raise SnapshotValidationError(
                "Lista sprzedawców nie odpowiada aktualnej wersji scenariusza."
            )
    return replace(
        base, party_position=PartyPosition(zone_id, _optional_coordinate(party.get("marker_position"), "party_position.marker_position")),
        flags=SceneFlags(tuple(flags)),
        points=tuple(
            replace(
                point,
                visibility=visibility[point.id],
                positions=point_positions[point.id],
            )
            for point in base.points
        ),
        exhausted_search_zones=_string_tuple(data.get("exhausted_search_zones", []), "exhausted_search_zones"),
        challenge_states=challenge_states, inventory_resource_ids=resources,
        elapsed_minutes=_integer(data.get("elapsed_minutes"), "elapsed_minutes"), short_rest_counts=short_counts,
        temporary_items=temporary_items,
        encounter_edges=encounter_edges,
        source_discoveries=source_discoveries,
        source_collections=source_collections,
        fixture_states=fixture_states,
        condition_states=condition_states,
        trap_states=trap_states,
        hidden_actor_states=hidden_actor_states,
        npc_states=npc_states,
        merchants=merchants,
        magic_effects=magic_effects,
        party_loot=party_loot,
    )


def _attempt_payload(item: ExplorationChallengeAttempt) -> dict[str, object]:
    return {name: getattr(item, name) for name in (
        "challenge_id", "option_id", "approach_label", "approach_tags", "resource_id", "natural_roll", "total",
        "success", "critical_failure", "progress_added", "noise_added", "complications_added",
    )} | {"approach_tags": list(item.approach_tags), "complications_added": list(item.complications_added)}


def _challenge_state_from_payload(raw: object) -> ExplorationChallengeState:
    data = _mapping(raw, "challenge_state")
    attempts = []
    for raw_attempt in _sequence(data.get("attempts", []), "attempts"):
        item = _mapping(raw_attempt, "attempt")
        attempts.append(ExplorationChallengeAttempt(
            challenge_id=_string(item.get("challenge_id"), "attempt.challenge_id"), option_id=_string(item.get("option_id"), "attempt.option_id"),
            approach_label=_string(item.get("approach_label"), "attempt.approach_label"), approach_tags=_string_tuple(item.get("approach_tags", []), "attempt.approach_tags"),
            resource_id=_optional_string(item.get("resource_id"), "attempt.resource_id"), natural_roll=_integer(item.get("natural_roll"), "attempt.natural_roll"),
            total=_integer(item.get("total"), "attempt.total"), success=_boolean(item.get("success"), "attempt.success"), critical_failure=_boolean(item.get("critical_failure"), "attempt.critical_failure"),
            progress_added=_integer(item.get("progress_added"), "attempt.progress_added"), noise_added=_integer(item.get("noise_added"), "attempt.noise_added"),
            complications_added=_string_tuple(item.get("complications_added", []), "attempt.complications_added"),
        ))
    return ExplorationChallengeState(
        challenge_id=_string(data.get("challenge_id"), "challenge_state.challenge_id"), current_progress=_integer(data.get("current_progress"), "challenge_state.current_progress"),
        noise=_integer(data.get("noise"), "challenge_state.noise"), complications=_string_tuple(data.get("complications", []), "challenge_state.complications"),
        completed=_boolean(data.get("completed"), "challenge_state.completed"), attempts=tuple(attempts),
    )


def _effect_payload(effect: ActiveEffect) -> dict[str, object]:
    assert effect.source is not None and effect.duration is not None
    return {
        "id": effect.id, "actor_id": effect.actor_id, "kind": effect.kind, "label": effect.label,
        "object_id": effect.object_id, "value": effect.value, "anchor_position": _coordinate_payload(effect.anchor_position),
        "base_ac": effect.base_ac, "source_actor_id": effect.source_actor_id, "target_actor_id": effect.target_actor_id,
        "source": {"type": effect.source.source_type.value, "id": effect.source.id, "label": effect.source.label},
        "duration": effect.duration.value, "stacking": effect.stacking.value, "stacking_key": effect.stacking_key,
        "expiration_actor_id": effect.expiration_actor_id,
        "additional_expirations": [{"duration": item.duration.value, "actor_id": item.actor_id, "target_actor_id": item.target_actor_id} for item in effect.additional_expirations],
        "spell_level": effect.spell_level,
        "radius_feet": effect.radius_feet,
        "die_sides": effect.die_sides,
        "modifier": effect.modifier,
        "uses_maximum": effect.uses_maximum,
        "remaining_rounds": effect.remaining_rounds,
        "excluded_positions": [
            _coordinate_payload(position) for position in effect.excluded_positions
        ],
    }


def _effect_from_payload(raw: object) -> ActiveEffect:
    data = _mapping(raw, "effect")
    source = _mapping(data.get("source"), "effect.source")
    return ActiveEffect(
        id=_string(data.get("id"), "effect.id"), actor_id=_string(data.get("actor_id"), "effect.actor_id"),
        kind=_string(data.get("kind"), "effect.kind"), label=_string(data.get("label"), "effect.label", allow_empty=True),
        object_id=_string(data.get("object_id"), "effect.object_id", allow_empty=True), value=_integer(data.get("value"), "effect.value"),
        anchor_position=_optional_coordinate(data.get("anchor_position"), "effect.anchor_position"), base_ac=_optional_integer(data.get("base_ac"), "effect.base_ac"),
        source_actor_id=_optional_string(data.get("source_actor_id"), "effect.source_actor_id"), target_actor_id=_optional_string(data.get("target_actor_id"), "effect.target_actor_id"),
        source=EffectSource(_enum(EffectSourceType, source.get("type"), "effect.source.type"), _string(source.get("id"), "effect.source.id"), _string(source.get("label", ""), "effect.source.label", allow_empty=True)),
        duration=_enum(EffectDuration, data.get("duration"), "effect.duration"), stacking=_enum(EffectStackingPolicy, data.get("stacking"), "effect.stacking"),
        stacking_key=_string(data.get("stacking_key"), "effect.stacking_key"), expiration_actor_id=_optional_string(data.get("expiration_actor_id"), "effect.expiration_actor_id"),
        additional_expirations=tuple(AdditionalEffectExpiration(_enum(EffectDuration, item.get("duration"), "expiration.duration"), _optional_string(item.get("actor_id"), "expiration.actor_id"), _optional_string(item.get("target_actor_id"), "expiration.target_actor_id")) for value in _sequence(data.get("additional_expirations", []), "additional_expirations") for item in (_mapping(value, "expiration"),)),
        spell_level=_optional_integer(data.get("spell_level"), "effect.spell_level"),
        radius_feet=_integer(data.get("radius_feet", 0), "effect.radius_feet"),
        die_sides=_integer(data.get("die_sides", 0), "effect.die_sides"),
        modifier=_integer(data.get("modifier", 0), "effect.modifier"),
        uses_maximum=_integer(data.get("uses_maximum", 0), "effect.uses_maximum"),
        remaining_rounds=_optional_integer(data.get("remaining_rounds"), "effect.remaining_rounds"),
        excluded_positions=tuple(
            _coordinate(value, "effect.excluded_positions[]")
            for value in _sequence(
                data.get("excluded_positions", []),
                "effect.excluded_positions",
            )
        ),
    )


def _inventory_item_from_payload(raw: object, path: str) -> InventoryItem:
    item = _mapping(raw, path)
    return InventoryItem(
        id=_string(item.get("id"), f"{path}.id"),
        name=_string(item.get("name"), f"{path}.name"),
        kind=_string(item.get("kind"), f"{path}.kind"),
        quantity=_integer(item.get("quantity"), f"{path}.quantity"),
        equipped=_boolean(item.get("equipped"), f"{path}.equipped"),
        source_ref=_optional_string(item.get("source_ref"), f"{path}.source_ref"),
        broken=_boolean(item.get("broken"), f"{path}.broken"),
        description=_string(
            item.get("description", ""),
            f"{path}.description",
            allow_empty=True,
        ),
        properties=_string_tuple(item.get("properties", []), f"{path}.properties"),
        portable=_boolean(item.get("portable", True), f"{path}.portable"),
        hands_required=_integer(item.get("hands_required", 0), f"{path}.hands_required"),
        held_in=tuple(
            _enum(HandSlot, slot, f"{path}.held_in")
            for slot in _sequence(item.get("held_in", []), f"{path}.held_in")
        ),
        light_weapon=_boolean(item.get("light_weapon", False), f"{path}.light_weapon"),
        versatile_damage_dice=_optional_string(
            item.get("versatile_damage_dice"),
            f"{path}.versatile_damage_dice",
        ),
        armor_class_bonus=_integer(
            item.get("armor_class_bonus", 0),
            f"{path}.armor_class_bonus",
        ),
        armor_proficiency=_optional_string(
            item.get("armor_proficiency"),
            f"{path}.armor_proficiency",
        ),
        armor_category=(
            _enum(
                ArmorCategory,
                item.get("armor_category"),
                f"{path}.armor_category",
            )
            if item.get("armor_category") is not None
            else None
        ),
        armor_base_ac=_optional_integer(
            item.get("armor_base_ac"),
            f"{path}.armor_base_ac",
        ),
        armor_dexterity_cap=_optional_integer(
            item.get("armor_dexterity_cap"),
            f"{path}.armor_dexterity_cap",
        ),
        armor_strength_requirement=_optional_integer(
            item.get("armor_strength_requirement"),
            f"{path}.armor_strength_requirement",
        ),
        stealth_disadvantage=_boolean(
            item.get("stealth_disadvantage", False),
            f"{path}.stealth_disadvantage",
        ),
        charges_maximum=_optional_integer(
            item.get("charges_maximum"),
            f"{path}.charges_maximum",
        ),
        charges_current=_optional_integer(
            item.get("charges_current"),
            f"{path}.charges_current",
        ),
        charges_recovery=_enum(
            ItemChargeRecovery,
            item.get("charges_recovery", ItemChargeRecovery.NEVER.value),
            f"{path}.charges_recovery",
        ),
        charges_recovery_dice=_optional_string(
            item.get("charges_recovery_dice"),
            f"{path}.charges_recovery_dice",
        ),
        charges_recovery_modifier=_integer(
            item.get("charges_recovery_modifier", 0),
            f"{path}.charges_recovery_modifier",
        ),
        requires_attunement=_boolean(
            item.get("requires_attunement", False),
            f"{path}.requires_attunement",
        ),
        attuned=_boolean(
            item.get("attuned", False),
            f"{path}.attuned",
        ),
        magic_effects=_magic_item_effects(
            item.get("magic_effects", []),
            f"{path}.magic_effects",
        ),
        weapon_category=_optional_enum(
            WeaponCategory,
            item.get("weapon_category"),
            f"{path}.weapon_category",
        ),
        weapon_properties=tuple(
            _enum(WeaponProperty, value, f"{path}.weapon_properties")
            for value in _sequence(
                item.get("weapon_properties", []),
                f"{path}.weapon_properties",
            )
        ),
        ammunition_type=_optional_string(
            item.get("ammunition_type"),
            f"{path}.ammunition_type",
        ),
        gear_category=_optional_enum(
            GearCategory,
            item.get("gear_category"),
            f"{path}.gear_category",
        ),
        stackable=_boolean(item.get("stackable", True), f"{path}.stackable"),
        tool_proficiency_id=_optional_string(
            item.get("tool_proficiency_id"),
            f"{path}.tool_proficiency_id",
        ),
        spellcasting_focus_kind=_optional_enum(
            SpellcastingFocusKind,
            item.get("spellcasting_focus_kind"),
            f"{path}.spellcasting_focus_kind",
        ),
        container_capacity=_container_capacity_from_payload(
            item.get("container_capacity"),
            f"{path}.container_capacity",
        ),
        light_source=_light_source_from_payload(
            item.get("light_source"),
            f"{path}.light_source",
        ),
        check_modifiers=_check_modifiers_from_payload(
            item.get("check_modifiers", []),
            f"{path}.check_modifiers",
        ),
        durability=_durability_from_payload(
            item.get("durability"),
            f"{path}.durability",
        ),
        bundle_contents=tuple(
            BundleEntry(
                item_id=_string(
                    entry.get("item_id"),
                    f"{path}.bundle_contents[{index}].item_id",
                ),
                quantity=_integer(
                    entry.get("quantity", 1),
                    f"{path}.bundle_contents[{index}].quantity",
                ),
            )
            for index, raw_entry in enumerate(
                _sequence(item.get("bundle_contents", []), f"{path}.bundle_contents")
            )
            for entry in (
                _mapping(raw_entry, f"{path}.bundle_contents[{index}]"),
            )
        ),
        value_cp=_integer(item.get("value_cp", 0), f"{path}.value_cp"),
        weight_lb=_number(item.get("weight_lb", 0), f"{path}.weight_lb"),
    )


def _container_capacity_from_payload(
    raw: object,
    path: str,
) -> ContainerCapacity | None:
    if raw is None:
        return None
    data = _mapping(raw, path)
    return ContainerCapacity(
        maximum_weight_lb=(
            _number(data.get("maximum_weight_lb"), f"{path}.maximum_weight_lb")
            if data.get("maximum_weight_lb") is not None
            else None
        ),
        volume_cubic_feet=(
            _number(data.get("volume_cubic_feet"), f"{path}.volume_cubic_feet")
            if data.get("volume_cubic_feet") is not None
            else None
        ),
        liquid_pints=(
            _number(data.get("liquid_pints"), f"{path}.liquid_pints")
            if data.get("liquid_pints") is not None
            else None
        ),
        ammunition_type=_optional_string(
            data.get("ammunition_type"),
            f"{path}.ammunition_type",
        ),
        ammunition_count=_optional_integer(
            data.get("ammunition_count"),
            f"{path}.ammunition_count",
        ),
        sheet_count=_optional_integer(
            data.get("sheet_count"),
            f"{path}.sheet_count",
        ),
    )


def _light_source_from_payload(raw: object, path: str) -> LightSource | None:
    if raw is None:
        return None
    data = _mapping(raw, path)
    return LightSource(
        bright_distance_feet=_integer(
            data.get("bright_distance_feet"),
            f"{path}.bright_distance_feet",
        ),
        dim_additional_feet=_integer(
            data.get("dim_additional_feet"),
            f"{path}.dim_additional_feet",
        ),
        duration_minutes=_integer(
            data.get("duration_minutes"),
            f"{path}.duration_minutes",
        ),
        shape=_enum(
            LightShape,
            data.get("shape", LightShape.RADIUS.value),
            f"{path}.shape",
        ),
        fuel_item_id=_optional_string(
            data.get("fuel_item_id"),
            f"{path}.fuel_item_id",
        ),
        hooded_dim_distance_feet=_optional_integer(
            data.get("hooded_dim_distance_feet"),
            f"{path}.hooded_dim_distance_feet",
        ),
    )


def _check_modifiers_from_payload(
    raw: object,
    path: str,
) -> tuple[CheckModifier, ...]:
    return tuple(
        CheckModifier(
            id=_string(data.get("id"), f"{path}[{index}].id"),
            label=_string(data.get("label"), f"{path}[{index}].label"),
            context=_string(data.get("context"), f"{path}[{index}].context"),
            mode=_enum(
                CheckModifierMode,
                data.get("mode"),
                f"{path}[{index}].mode",
            ),
            value=_integer(data.get("value", 0), f"{path}[{index}].value"),
            ability=_optional_string(data.get("ability"), f"{path}[{index}].ability"),
            skill=_optional_string(data.get("skill"), f"{path}[{index}].skill"),
        )
        for index, entry in enumerate(_sequence(raw, path))
        for data in (_mapping(entry, f"{path}[{index}]"),)
    )


def _durability_from_payload(raw: object, path: str) -> ObjectDurability | None:
    if raw is None:
        return None
    data = _mapping(raw, path)
    return ObjectDurability(
        hit_points=_optional_integer(data.get("hit_points"), f"{path}.hit_points"),
        break_strength_dc=_optional_integer(
            data.get("break_strength_dc"),
            f"{path}.break_strength_dc",
        ),
        escape_dexterity_dc=_optional_integer(
            data.get("escape_dexterity_dc"),
            f"{path}.escape_dexterity_dc",
        ),
        pick_lock_dc=_optional_integer(
            data.get("pick_lock_dc"),
            f"{path}.pick_lock_dc",
        ),
    )


def _magic_item_effects(data: Any, path: str) -> tuple[MagicItemEffect, ...]:
    entries = _sequence(data, path)
    effects: list[MagicItemEffect] = []
    for index, raw in enumerate(entries):
        effect_path = f"{path}[{index}]"
        effect = _mapping(raw, effect_path)
        effects.append(
            MagicItemEffect(
                id=_string(effect.get("id"), f"{effect_path}.id"),
                kind=_enum(
                    MagicItemEffectKind,
                    effect.get("kind"),
                    f"{effect_path}.kind",
                ),
                value=_integer(effect.get("value"), f"{effect_path}.value"),
                requires_equipped=_boolean(
                    effect.get("requires_equipped", True),
                    f"{effect_path}.requires_equipped",
                ),
            )
        )
    return tuple(effects)


def _combat_payload(state: CombatState | None) -> dict[str, object] | None:
    if state is None:
        return None
    return {
        "shared_mana": state.shared_mana.as_payload() if state.shared_mana else None,
        "actors": [_actor_payload(actor) for actor in state.actors],
        "initiative": {
            "current_index": state.initiative_order.current_index, "round_number": state.initiative_order.round_number,
            "entries": [{"actor_id": str(entry.actor.id), "natural_roll": entry.roll.natural_roll, "natural_rolls": list(entry.roll.natural_rolls), "total": entry.roll.total, "mode": entry.roll.mode.value, "dexterity_modifier": entry.dexterity_modifier, "stable_order": entry.stable_order} for entry in state.initiative_order.entries],
        },
        "turn_action": {"shared_speed_halved": state.turn_action.shared_speed_halved, "shared_bonus_actions_used": state.turn_action.shared_bonus_actions_used, "action_use": state.turn_action.action_use.value, "bonus_action_use": state.turn_action.bonus_action_use.value, "reaction_available": state.turn_action.reaction_available, "movement_used_feet": state.turn_action.movement_used_feet, "extra_movement_feet": state.turn_action.extra_movement_feet, "object_interaction_available": state.turn_action.object_interaction_available, "two_weapon_trigger_item_id": state.turn_action.two_weapon_trigger_item_id, "attack_action_active": state.turn_action.attack_action_active, "attacks_used": state.turn_action.attacks_used, "attacks_maximum": state.turn_action.attacks_maximum, "bonus_attacks_remaining": state.turn_action.bonus_attacks_remaining, "bonus_attack_source_id": state.turn_action.bonus_attack_source_id, "bonus_action_spell_cast": state.turn_action.bonus_action_spell_cast, "leveled_action_spell_cast": state.turn_action.leveled_action_spell_cast, "movement_action_used": state.turn_action.movement_action_used, "weapon_change_available": state.turn_action.weapon_change_available},
        "status": state.status.value, "winner": state.winner.value if state.winner else None,
        "enemy_ai": {
            "profile_id": state.enemy_ai.profile_id,
            "encounter_seed": state.enemy_ai.encounter_seed,
            "starting_morale": state.enemy_ai.starting_morale,
            "morale": state.enemy_ai.morale,
            "used_morale_events": list(state.enemy_ai.used_morale_events),
            "previous_targets": [list(item) for item in state.enemy_ai.previous_targets],
            "decision_counts": [list(item) for item in state.enemy_ai.decision_counts],
            "outcomes": [
                {
                    "actor_id": outcome.actor_id,
                    "actor_name": outcome.actor_name,
                    "outcome": outcome.outcome,
                    "round_number": outcome.round_number,
                }
                for outcome in state.enemy_ai.outcomes
            ],
        },
        "spent_reaction_actor_ids": sorted(str(item) for item in state.spent_reaction_actor_ids),
        "damage_received_by_actor": [list(item) for item in state.damage_received_by_actor],
        "ammunition_expenditures": [
            {
                "shooter_actor_id": str(entry.shooter_actor_id),
                "shooter_faction": entry.shooter_faction.value,
                "ammunition_type": entry.ammunition_type,
                "quantity": entry.quantity,
                "item": inventory_item_payload(entry.item),
            }
            for entry in state.ammunition_expenditures
        ],
        "battlefield_loot": [
            {
                "id": ground.id,
                "position": _coordinate_payload(ground.position),
                "bundle": {
                    "id": ground.bundle.id,
                    "label": ground.bundle.label,
                    "items": [
                        inventory_item_payload(item)
                        for item in ground.bundle.items
                    ],
                    "currency": ground.bundle.currency.as_payload(),
                },
            }
            for ground in state.battlefield_loot
        ],
        "long_casts": [
            {
                "caster_id": str(cast.caster_id),
                "spell_id": cast.spell_id,
                "label": cast.label,
                "cast_level": cast.cast_level,
                "required_actions": cast.required_actions,
                "completed_actions": cast.completed_actions,
                "started_round": cast.started_round,
                "last_progress_round": cast.last_progress_round,
            }
            for cast in state.long_casts
        ],
        "summoned_creatures": [
            {
                "actor_id": str(summon.actor_id),
                "owner_actor_id": str(summon.owner_actor_id),
                "spell_id": summon.spell_id,
                "concentration_effect_id": summon.concentration_effect_id,
                "definition": _summon_definition_payload(summon.definition),
            }
            for summon in state.summoned_creatures
        ],
        "dropped_weapons": [
            {
                "id": dropped.id,
                "source_actor_id": str(dropped.source_actor_id),
                "position": _coordinate_payload(dropped.position),
                "dropped_round": dropped.dropped_round,
                "weapon": inventory_item_payload(dropped.weapon),
            }
            for dropped in state.dropped_weapons
        ],
        "hidden_states": [
            {
                "actor_id": hidden.actor_id,
                "stealth_total": hidden.stealth_total,
                "hidden_from_actor_ids": list(hidden.hidden_from_actor_ids),
                "observer_perception_totals": [
                    [actor_id, total]
                    for actor_id, total in hidden.observer_perception_totals
                ],
            }
            for hidden in state.hidden_states
        ],
        "condition_states": [
            {
                "actor_id": condition.actor_id,
                "condition": condition.condition.value,
                "source_actor_id": condition.source_actor_id,
                "source_label": condition.source_label,
                "duration": condition.duration.value,
                "expiration_actor_id": condition.expiration_actor_id,
                "save_ability": condition.save_ability,
                "save_dc": condition.save_dc,
                "save_timing": condition.save_timing.value if condition.save_timing is not None else None,
                "source_spell_id": condition.source_spell_id,
                "source_spell_level": condition.source_spell_level,
                "expiration_event_count": condition.expiration_event_count,
            }
            for condition in state.condition_states
        ],
    }


def _summon_definition_payload(
    definition: SummonDefinition,
) -> dict[str, object]:
    return {
        "id": definition.id,
        "name": definition.name,
        "size": definition.size.value,
        "ac": definition.ac,
        "hp": definition.hp,
        "speed_feet": definition.speed_feet,
        "ability_scores": {
            name: getattr(definition.ability_scores, name)
            for name in _ABILITY_NAMES
        },
        "attack": {
            "id": definition.attack_id,
            "name": definition.attack_name,
            "bonus": definition.attack_bonus,
            "range_feet": definition.attack_range_feet,
            "damage_fixed": definition.attack_damage_fixed,
            "damage_type": definition.attack_damage_type.value,
        },
    }


def _summoned_creature_from_payload(
    raw: object,
    actors_by_id: Mapping[str, Actor],
) -> SummonedCreatureState:
    data = _mapping(raw, "combat.summoned_creature")
    definition_data = _mapping(
        data.get("definition"),
        "combat.summoned_creature.definition",
    )
    abilities = _mapping(
        definition_data.get("ability_scores"),
        "combat.summoned_creature.definition.ability_scores",
    )
    attack = _mapping(
        definition_data.get("attack"),
        "combat.summoned_creature.definition.attack",
    )
    actor_id = _string(data.get("actor_id"), "summoned_creature.actor_id")
    owner_actor_id = _string(
        data.get("owner_actor_id"),
        "summoned_creature.owner_actor_id",
    )
    if actor_id not in actors_by_id:
        raise SnapshotValidationError(
            f"Przywołanie odwołuje się do nieznanego aktora: {actor_id}."
        )
    if owner_actor_id not in actors_by_id:
        raise SnapshotValidationError(
            f"Przywołanie ma nieznanego właściciela: {owner_actor_id}."
        )
    definition = SummonDefinition(
        id=_string(definition_data.get("id"), "summon.definition.id"),
        name=_string(definition_data.get("name"), "summon.definition.name"),
        size=_enum(
            CreatureSize,
            definition_data.get("size"),
            "summon.definition.size",
        ),
        ac=_integer(definition_data.get("ac"), "summon.definition.ac"),
        hp=_integer(definition_data.get("hp"), "summon.definition.hp"),
        speed_feet=_integer(
            definition_data.get("speed_feet"),
            "summon.definition.speed_feet",
        ),
        ability_scores=AbilityScores(
            **{
                name: _integer(
                    abilities.get(name),
                    f"summon.definition.ability_scores.{name}",
                )
                for name in _ABILITY_NAMES
            }
        ),
        attack_id=_string(attack.get("id"), "summon.definition.attack.id"),
        attack_name=_string(
            attack.get("name"),
            "summon.definition.attack.name",
        ),
        attack_bonus=_integer(
            attack.get("bonus"),
            "summon.definition.attack.bonus",
        ),
        attack_range_feet=_integer(
            attack.get("range_feet"),
            "summon.definition.attack.range_feet",
        ),
        attack_damage_fixed=_integer(
            attack.get("damage_fixed"),
            "summon.definition.attack.damage_fixed",
        ),
        attack_damage_type=_enum(
            DamageType,
            attack.get("damage_type"),
            "summon.definition.attack.damage_type",
        ),
    )
    return SummonedCreatureState(
        actor_id=ActorId(actor_id),
        owner_actor_id=ActorId(owner_actor_id),
        spell_id=_string(data.get("spell_id"), "summoned_creature.spell_id"),
        definition=definition,
        concentration_effect_id=_string(
            data.get("concentration_effect_id"),
            "summoned_creature.concentration_effect_id",
        ),
    )


def _combat_from_payload(raw: object) -> CombatState | None:
    if raw is None:
        return None
    data = _mapping(raw, "combat")
    actors = tuple(_actor_from_payload(item) for item in _sequence(data.get("actors"), "combat.actors"))
    by_id = {str(actor.id): actor for actor in actors}
    _require_unique(by_id, "combat actor id")
    initiative = _mapping(data.get("initiative"), "combat.initiative")
    entries = []
    for raw_entry in _sequence(initiative.get("entries"), "initiative.entries"):
        item = _mapping(raw_entry, "initiative.entry")
        actor_id = _string(item.get("actor_id"), "initiative.actor_id")
        if actor_id not in by_id:
            raise SnapshotValidationError(f"Inicjatywa odwołuje się do nieznanego aktora: {actor_id}.")
        natural = _integer(item.get("natural_roll"), "initiative.natural_roll")
        total = _integer(item.get("total"), "initiative.total")
        entries.append(InitiativeEntry(
            by_id[actor_id],
            D20RollResult(natural, tuple(_integer(value, "initiative.natural_rolls") for value in _sequence(item.get("natural_rolls"), "initiative.natural_rolls")), RollModifierBreakdown(modifier_total=total - natural), total, _enum(RollMode, item.get("mode"), "initiative.mode"), natural == 20, natural == 1),
            _integer(item.get("dexterity_modifier"), "initiative.dexterity_modifier"), _integer(item.get("stable_order"), "initiative.stable_order"),
        ))
    current_index = _integer(initiative.get("current_index"), "initiative.current_index")
    if not entries or not 0 <= current_index < len(entries):
        raise SnapshotValidationError("Zapis zawiera nieprawidłowy indeks inicjatywy.")
    turn = _mapping(data.get("turn_action"), "combat.turn_action")
    enemy_ai_raw = _mapping(data.get("enemy_ai", {}), "combat.enemy_ai")
    from dnd_board_game.rules.shared_mana import SharedMana
    mana_raw = data.get("shared_mana")
    return CombatState(
        shared_mana=SharedMana.from_payload(_mapping(mana_raw, "combat.shared_mana")) if mana_raw is not None else None,
        actors=actors,
        initiative_order=InitiativeOrder(
            tuple(entries), current_index, _integer(initiative.get("round_number"), "initiative.round_number")
        ),
        turn_action=TurnActionState(
            _enum(ActionUse, turn.get("action_use"), "turn_action.action_use"),
            _enum(ActionUse, turn.get("bonus_action_use"), "turn_action.bonus_action_use"),
            _boolean(turn.get("reaction_available"), "turn_action.reaction_available"),
            _integer(turn.get("movement_used_feet"), "turn_action.movement_used_feet"),
            _integer(turn.get("extra_movement_feet"), "turn_action.extra_movement_feet"),
            _boolean(turn.get("object_interaction_available", True), "turn_action.object_interaction_available"),
            _optional_string(turn.get("two_weapon_trigger_item_id"), "turn_action.two_weapon_trigger_item_id"),
            _boolean(turn.get("attack_action_active", False), "turn_action.attack_action_active"),
            _integer(turn.get("attacks_used", 0), "turn_action.attacks_used"),
            _integer(turn.get("attacks_maximum", 0), "turn_action.attacks_maximum"),
            _integer(
                turn.get("bonus_attacks_remaining", 0),
                "turn_action.bonus_attacks_remaining",
            ),
            _string(
                turn.get("bonus_attack_source_id", ""),
                "turn_action.bonus_attack_source_id",
                allow_empty=True,
            ),
            _boolean(
                turn.get("bonus_action_spell_cast", False),
                "turn_action.bonus_action_spell_cast",
            ),
            _boolean(
                turn.get("leveled_action_spell_cast", False),
                "turn_action.leveled_action_spell_cast",
            ),
            _boolean(
                turn.get("movement_action_used", False),
                "turn_action.movement_action_used",
            ),
            _boolean(
                turn.get("weapon_change_available", True),
                "turn_action.weapon_change_available",
            ),
            _boolean(turn.get("shared_speed_halved", False), "turn_action.shared_speed_halved"),
            _integer(turn.get("shared_bonus_actions_used", 0), "turn_action.shared_bonus_actions_used"),
        ),
        status=_enum(CombatStatus, data.get("status"), "combat.status"),
        winner=_optional_enum(Faction, data.get("winner"), "combat.winner"),
        spent_reaction_actor_ids=frozenset(
            ActorId(item) for item in _string_tuple(data.get("spent_reaction_actor_ids", []), "spent_reaction_actor_ids")
        ),
        long_casts=tuple(
            LongCastState(
                caster_id=ActorId(
                    _string(item.get("caster_id"), "long_cast.caster_id")
                ),
                spell_id=_string(item.get("spell_id"), "long_cast.spell_id"),
                label=_string(item.get("label"), "long_cast.label"),
                cast_level=_integer(
                    item.get("cast_level"),
                    "long_cast.cast_level",
                ),
                required_actions=_integer(
                    item.get("required_actions"),
                    "long_cast.required_actions",
                ),
                completed_actions=_integer(
                    item.get("completed_actions"),
                    "long_cast.completed_actions",
                ),
                started_round=_integer(
                    item.get("started_round"),
                    "long_cast.started_round",
                ),
                last_progress_round=_integer(
                    item.get("last_progress_round"),
                    "long_cast.last_progress_round",
                ),
            )
            for raw_item in _sequence(
                data.get("long_casts", []),
                "combat.long_casts",
            )
            for item in (_mapping(raw_item, "combat.long_cast"),)
        ),
        summoned_creatures=tuple(
            _summoned_creature_from_payload(raw_item, by_id)
            for raw_item in _sequence(
                data.get("summoned_creatures", []),
                "combat.summoned_creatures",
            )
        ),
        enemy_ai=EnemyAiRuntimeState(
            profile_id=_string(
                enemy_ai_raw.get("profile_id", ""),
                "combat.enemy_ai.profile_id",
                allow_empty=True,
            ),
            encounter_seed=_integer(
                enemy_ai_raw.get("encounter_seed", 7),
                "combat.enemy_ai.encounter_seed",
            ),
            starting_morale=_integer(
                enemy_ai_raw.get("starting_morale", 0),
                "combat.enemy_ai.starting_morale",
            ),
            morale=_integer(
                enemy_ai_raw.get("morale", 0),
                "combat.enemy_ai.morale",
            ),
            used_morale_events=_string_tuple(
                enemy_ai_raw.get("used_morale_events", []),
                "combat.enemy_ai.used_morale_events",
            ),
            previous_targets=tuple(
                (
                    _string(item[0], "combat.enemy_ai.previous_target.actor_id"),
                    _string(item[1], "combat.enemy_ai.previous_target.target_id"),
                )
                for item in _sequence(
                    enemy_ai_raw.get("previous_targets", []),
                    "combat.enemy_ai.previous_targets",
                )
                if isinstance(item, list | tuple) and len(item) == 2
            ),
            decision_counts=tuple(
                (
                    _string(item[0], "combat.enemy_ai.decision_count.actor_id"),
                    _integer(item[1], "combat.enemy_ai.decision_count.value"),
                )
                for item in _sequence(
                    enemy_ai_raw.get("decision_counts", []),
                    "combat.enemy_ai.decision_counts",
                )
                if isinstance(item, list | tuple) and len(item) == 2
            ),
            outcomes=tuple(
                EnemyOutcome(
                    actor_id=_string(item.get("actor_id"), "combat.enemy_ai.outcome.actor_id"),
                    actor_name=_string(item.get("actor_name"), "combat.enemy_ai.outcome.actor_name"),
                    outcome=_string(item.get("outcome"), "combat.enemy_ai.outcome.outcome"),
                    round_number=_integer(item.get("round_number"), "combat.enemy_ai.outcome.round_number"),
                )
                for raw_item in _sequence(
                    enemy_ai_raw.get("outcomes", []),
                    "combat.enemy_ai.outcomes",
                )
                for item in (_mapping(raw_item, "combat.enemy_ai.outcome"),)
            ),
        ),
        damage_received_by_actor=tuple(
            (
                _string(item[0], "combat.damage_received.actor_id"),
                _integer(item[1], "combat.damage_received.amount"),
            )
            for item in _sequence(
                data.get("damage_received_by_actor", []),
                "combat.damage_received_by_actor",
            )
            if isinstance(item, list | tuple) and len(item) == 2
        ),
        ammunition_expenditures=tuple(
            AmmunitionExpenditure(
                shooter_actor_id=ActorId(
                    _string(
                        item.get("shooter_actor_id"),
                        "ammunition_expenditure.shooter_actor_id",
                    )
                ),
                shooter_faction=_enum(
                    Faction,
                    item.get("shooter_faction"),
                    "ammunition_expenditure.shooter_faction",
                ),
                ammunition_type=_string(
                    item.get("ammunition_type"),
                    "ammunition_expenditure.ammunition_type",
                ),
                item=_inventory_item_from_payload(
                    item.get("item"),
                    "ammunition_expenditure.item",
                ),
                quantity=_integer(
                    item.get("quantity"),
                    "ammunition_expenditure.quantity",
                ),
            )
            for raw_item in _sequence(
                data.get("ammunition_expenditures", []),
                "combat.ammunition_expenditures",
            )
            for item in (_mapping(raw_item, "ammunition_expenditure"),)
        ),
        battlefield_loot=tuple(
            BattlefieldLoot(
                id=_string(item.get("id"), "battlefield_loot.id"),
                position=_coordinate(
                    item.get("position"),
                    "battlefield_loot.position",
                ),
                bundle=LootBundle(
                    id=_string(bundle.get("id"), "battlefield_loot.bundle.id"),
                    label=_string(
                        bundle.get("label"),
                        "battlefield_loot.bundle.label",
                    ),
                    items=tuple(
                        _inventory_item_from_payload(
                            raw_bundle_item,
                            "battlefield_loot.bundle.item",
                        )
                        for raw_bundle_item in _sequence(
                            bundle.get("items", []),
                            "battlefield_loot.bundle.items",
                        )
                    ),
                    currency=_currency_from_payload(bundle.get("currency", {})),
                ),
            )
            for raw_item in _sequence(
                data.get("battlefield_loot", []),
                "combat.battlefield_loot",
            )
            for item in (_mapping(raw_item, "battlefield_loot"),)
            for bundle in (_mapping(item.get("bundle"), "battlefield_loot.bundle"),)
        ),
        dropped_weapons=tuple(
            DroppedWeapon(
                id=_string(item.get("id"), "dropped_weapon.id"),
                source_actor_id=ActorId(_string(item.get("source_actor_id"), "dropped_weapon.source_actor_id")),
                weapon=_inventory_item_from_payload(
                    weapon,
                    "dropped_weapon.weapon",
                ),
                position=_coordinate(item.get("position"), "dropped_weapon.position"),
                dropped_round=_integer(item.get("dropped_round"), "dropped_weapon.dropped_round"),
            )
            for raw_item in _sequence(data.get("dropped_weapons", []), "combat.dropped_weapons")
            for item in (_mapping(raw_item, "dropped_weapon"),)
            for weapon in (_mapping(item.get("weapon"), "dropped_weapon.weapon"),)
        ),
        hidden_states=tuple(
            HiddenState(
                actor_id=_string(item.get("actor_id"), "hidden_state.actor_id"),
                stealth_total=_integer(item.get("stealth_total"), "hidden_state.stealth_total"),
                hidden_from_actor_ids=_string_tuple(
                    item.get("hidden_from_actor_ids", []),
                    "hidden_state.hidden_from_actor_ids",
                ),
                observer_perception_totals=tuple(
                    (
                        _string(pair[0], "hidden_state.observer_perception_totals.actor_id"),
                        _integer(pair[1], "hidden_state.observer_perception_totals.total"),
                    )
                    for pair in _sequence(
                        item.get("observer_perception_totals", []),
                        "hidden_state.observer_perception_totals",
                    )
                    if isinstance(pair, (list, tuple)) and len(pair) == 2
                ),
            )
            for raw_item in _sequence(data.get("hidden_states", []), "combat.hidden_states")
            for item in (_mapping(raw_item, "hidden_state"),)
        ),
        condition_states=tuple(
            ConditionState(
                actor_id=_string(item.get("actor_id"), "condition_state.actor_id"),
                condition=_enum(
                    CombatCondition,
                    item.get("condition"),
                    "condition_state.condition",
                ),
                source_actor_id=(
                    _string(item.get("source_actor_id"), "condition_state.source_actor_id")
                    if item.get("source_actor_id") is not None
                    else None
                ),
                source_label=_string(
                    item.get("source_label", ""),
                    "condition_state.source_label",
                    allow_empty=True,
                ),
                duration=_enum(
                    EffectDuration,
                    item.get("duration", EffectDuration.PERMANENT.value),
                    "condition_state.duration",
                ),
                expiration_actor_id=_optional_string(
                    item.get("expiration_actor_id"),
                    "condition_state.expiration_actor_id",
                ),
                save_ability=_optional_string(item.get("save_ability"), "condition_state.save_ability"),
                save_dc=_optional_integer(item.get("save_dc"), "condition_state.save_dc"),
                save_timing=_optional_enum(
                    ConditionSaveTiming,
                    item.get("save_timing"),
                    "condition_state.save_timing",
                ),
                source_spell_id=_optional_string(
                    item.get("source_spell_id"),
                    "condition_state.source_spell_id",
                ),
                source_spell_level=_optional_integer(
                    item.get("source_spell_level"),
                    "condition_state.source_spell_level",
                ),
                expiration_event_count=_integer(
                    item.get("expiration_event_count", 1),
                    "condition_state.expiration_event_count",
                ),
            )
            for raw_item in _sequence(data.get("condition_states", []), "combat.condition_states")
            for item in (_mapping(raw_item, "condition_state"),)
        ),
    )


def _pending_encounter_payload(value: PendingEncounter | None) -> dict[str, object] | None:
    if value is None:
        return None
    opening = value.opening_resolution
    return {
        "trigger_id": value.trigger_id,
        "name": value.name,
        "description": value.description,
        "encounter_scenario": value.encounter_scenario,
        "reason": value.reason,
        "opening_resolution": (
            {
                "rule_id": opening.rule_id,
                "outcome": opening.outcome.value,
                "title": opening.title,
                "narration": opening.narration,
                "noise": opening.noise,
                "completion_tags": list(opening.completion_tags),
            }
            if opening is not None
            else None
        ),
        "precombat_stealth_completed": value.precombat_stealth_completed,
        "precombat_stealth_attempts": [
            {
                "actor_id": attempt.actor_id,
                "natural_roll": attempt.natural_roll,
                "total": attempt.total,
                "hidden_from_actor_ids": list(attempt.hidden_from_actor_ids),
                "detected_by_actor_ids": list(attempt.detected_by_actor_ids),
            }
            for attempt in value.precombat_stealth_attempts
        ],
    }


def _pending_encounter_from_payload(raw: object) -> PendingEncounter | None:
    if raw is None:
        return None
    data = _mapping(raw, "pending_encounter")
    opening_raw = data.get("opening_resolution")
    opening = None
    if opening_raw is not None:
        item = _mapping(opening_raw, "pending_encounter.opening_resolution")
        opening = EncounterOpeningResolution(
            rule_id=_string(item.get("rule_id"), "opening_resolution.rule_id"),
            outcome=_enum(EncounterOpeningOutcome, item.get("outcome"), "opening_resolution.outcome"),
            title=_string(item.get("title"), "opening_resolution.title"),
            narration=_string(item.get("narration"), "opening_resolution.narration"),
            noise=_integer(item.get("noise"), "opening_resolution.noise"),
            completion_tags=_string_tuple(item.get("completion_tags", []), "opening_resolution.completion_tags"),
        )
    return PendingEncounter(
        trigger_id=_string(data.get("trigger_id"), "pending_encounter.trigger_id"),
        name=_string(data.get("name"), "pending_encounter.name"),
        description=_string(data.get("description"), "pending_encounter.description", allow_empty=True),
        encounter_scenario=_string(data.get("encounter_scenario"), "pending_encounter.encounter_scenario"),
        reason=_string(data.get("reason"), "pending_encounter.reason", allow_empty=True),
        opening_resolution=opening,
        precombat_stealth_completed=_boolean(
            data.get("precombat_stealth_completed", False),
            "pending_encounter.precombat_stealth_completed",
        ),
        precombat_stealth_attempts=tuple(
            PrecombatStealthAttempt(
                actor_id=_string(item.get("actor_id"), "precombat_stealth.actor_id"),
                natural_roll=_integer(item.get("natural_roll"), "precombat_stealth.natural_roll"),
                total=_integer(item.get("total"), "precombat_stealth.total"),
                hidden_from_actor_ids=_string_tuple(
                    item.get("hidden_from_actor_ids", []),
                    "precombat_stealth.hidden_from_actor_ids",
                ),
                detected_by_actor_ids=_string_tuple(
                    item.get("detected_by_actor_ids", []),
                    "precombat_stealth.detected_by_actor_ids",
                ),
            )
            for raw_attempt in _sequence(
                data.get("precombat_stealth_attempts", []),
                "pending_encounter.precombat_stealth_attempts",
            )
            for item in (_mapping(raw_attempt, "precombat_stealth"),)
        ),
    )


_ABILITY_NAMES = ("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma")


def _mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SnapshotValidationError(f"Pole {field} musi być obiektem.")
    return value


def _sequence(value: object, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise SnapshotValidationError(f"Pole {field} musi być listą.")
    return value


def _string(value: object, field: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise SnapshotValidationError(f"Pole {field} musi być {'napisem' if allow_empty else 'niepustym napisem'}.")
    return value


def _optional_string(value: object, field: str) -> str | None:
    return None if value is None else _string(value, field)


def _integer(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SnapshotValidationError(f"Pole {field} musi być liczbą całkowitą.")
    return value


def _optional_integer(value: object, field: str) -> int | None:
    return None if value is None else _integer(value, field)


def _number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise SnapshotValidationError(f"Pole {field} musi być liczbą.")
    return float(value)


def _currency_from_payload(value: object) -> CurrencyWallet:
    data = _mapping(value, "actor.currency")
    return CurrencyWallet(
        cp=_integer(data.get("cp", 0), "actor.currency.cp"),
        sp=_integer(data.get("sp", 0), "actor.currency.sp"),
        ep=_integer(data.get("ep", 0), "actor.currency.ep"),
        gp=_integer(data.get("gp", 0), "actor.currency.gp"),
        pp=_integer(data.get("pp", 0), "actor.currency.pp"),
    )


def _boolean(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise SnapshotValidationError(f"Pole {field} musi być wartością logiczną.")
    return value


def _enum(enum_type, value: object, field: str):
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        raise SnapshotValidationError(f"Pole {field} ma nieznaną wartość: {value!r}.") from exc


def _optional_enum(enum_type, value: object, field: str):
    return None if value is None else _enum(enum_type, value, field)


def _string_tuple(value: object, field: str) -> tuple[str, ...]:
    result = tuple(_string(item, field) for item in _sequence(value, field))
    _require_unique(result, field)
    return result


def _string_map(value: object, field: str) -> tuple[tuple[str, str], ...]:
    data = _mapping(value, field)
    return tuple(sorted((_string(key, f"{field}.key"), _string(item, f"{field}.value")) for key, item in data.items()))


def _coordinate_payload(value: Coordinate | None) -> list[int] | None:
    return None if value is None else [value.col, value.row]


def _coordinate(value: object, field: str) -> Coordinate:
    items = _sequence(value, field)
    if len(items) != 2:
        raise SnapshotValidationError(f"Pole {field} musi zawierać dwie współrzędne.")
    return Coordinate(_integer(items[0], field), _integer(items[1], field))


def _optional_coordinate(value: object, field: str) -> Coordinate | None:
    return None if value is None else _coordinate(value, field)


def _require_unique(values, label: str) -> None:
    items = tuple(values)
    if len(items) != len(set(items)):
        raise SnapshotValidationError(f"Wartości {label} muszą być unikalne.")


def _assert_json_value(value: object, field: str) -> None:
    try:
        json.dumps(value)
    except (TypeError, ValueError) as exc:
        raise SnapshotValidationError(f"Pole {field} nie jest poprawną wartością JSON.") from exc


def _json_value(value: object, field: str) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_json_value(item, field) for item in value]
    if isinstance(value, Mapping):
        return {
            _string(key, f"{field}.key"): _json_value(item, field)
            for key, item in value.items()
        }
    raise SnapshotValidationError(f"Pole {field} nie jest poprawną wartością JSON.")
