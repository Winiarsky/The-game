from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping

from dnd_board_game.actors import (
    AbilityScores,
    Actor,
    ActorId,
    ActorResourcePool,
    Faction,
    HitDicePool,
    PreparableSpell,
    RecoveryPeriod,
    SpellPreparationProfile,
)
from dnd_board_game.combat import (
    ActionUse,
    CombatState,
    InitiativeEntry,
    InitiativeOrder,
    TurnActionState,
)
from dnd_board_game.combat.session import CombatStatus
from dnd_board_game.combat.spells import SpellSlotState
from dnd_board_game.combat.scene import SceneFlags
from dnd_board_game.combat.setup import SetupVisibility
from dnd_board_game.exploration import (
    ExplorationChallengeAttempt,
    ExplorationChallengeState,
    ExplorationState,
    PartyPosition,
    PendingEncounter,
    TemporaryItem,
)
from dnd_board_game.inventory import InventoryItem
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
)
from dnd_board_game.world import Coordinate
from dnd_board_game.ui.conversation import InteractionConversationEntry


SNAPSHOT_SCHEMA = "dnd_board_game.session"
SNAPSHOT_SCHEMA_VERSION = 1


class SnapshotValidationError(ValueError):
    """Raised when a save snapshot cannot be safely restored."""


@dataclass(frozen=True, slots=True)
class SessionSnapshot:
    scenario_id: str
    ui_stage: str
    actors: tuple[Actor, ...]
    exploration_state: ExplorationState
    active_effects: tuple[ActiveEffect, ...] = ()
    pending_encounter: PendingEncounter | None = None
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
            "combat": _combat_payload(self.combat_state),
            "resolved_encounter_trigger_ids": list(self.resolved_encounter_trigger_ids),
            "selected_attack_source_ids": dict(self.selected_attack_source_ids),
            "selected_healing_source_ids": dict(self.selected_healing_source_ids),
            "conversation_entries": [entry.as_payload() for entry in self.conversation_entries],
        }

    @classmethod
    def from_dict(cls, raw: object, *, base_state: ExplorationState) -> SessionSnapshot:
        data = _mapping(raw, "snapshot")
        if data.get("schema") != SNAPSHOT_SCHEMA:
            raise SnapshotValidationError("Nieznany format zapisu gry.")
        version = _integer(data.get("schema_version"), "schema_version")
        if version != SNAPSHOT_SCHEMA_VERSION:
            raise SnapshotValidationError(
                f"Nieobsługiwana wersja zapisu: {version}; oczekiwana: {SNAPSHOT_SCHEMA_VERSION}."
            )
        ui = _mapping(data.get("ui"), "ui")
        actors = tuple(_actor_from_payload(item) for item in _sequence(data.get("actors"), "actors"))
        _require_unique((str(actor.id) for actor in actors), "actor id")
        state = _exploration_from_payload(base_state, data.get("exploration"))
        effects = tuple(_effect_from_payload(item) for item in _sequence(data.get("active_effects", []), "active_effects"))
        pending = _pending_encounter_from_payload(data.get("pending_encounter"))
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
            ui_stage=_string(ui.get("stage"), "ui.stage"),
            actors=actors,
            exploration_state=state,
            active_effects=effects,
            pending_encounter=pending,
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
        "temp_hp": actor.temp_hp, "max_hp": actor.max_hp, "speed_feet": actor.speed_feet,
        "position": _coordinate_payload(actor.position), "faction": actor.faction.value,
        "ability_scores": {name: getattr(actor.ability_scores, name) for name in _ABILITY_NAMES},
        "spell_slots": [{"level": slot.level, "remaining": slot.remaining, "maximum": slot.maximum} for slot in actor.spell_slots],
        "spell_save_dc": actor.spell_save_dc, "spell_ids": list(actor.spell_ids),
        "inventory": [
            {"id": item.id, "name": item.name, "kind": item.kind, "quantity": item.quantity,
             "equipped": item.equipped, "source_ref": item.source_ref, "broken": item.broken}
            for item in actor.inventory
        ],
        "spell_preparation": None if prep is None else {
            "source_label": prep.source_label, "preparation_limit": prep.preparation_limit,
            "available_spells": [{"id": spell.id, "label": spell.label, "level": spell.level} for spell in prep.available_spells],
            "prepared_spell_ids": list(prep.prepared_spell_ids),
            "always_prepared_spell_ids": list(prep.always_prepared_spell_ids), "confirmed": prep.confirmed,
        },
        "hit_dice": [{"die_sides": pool.die_sides, "remaining": pool.remaining, "maximum": pool.maximum} for pool in actor.hit_dice],
        "resource_pools": [
            {"id": pool.id, "label": pool.label, "current": pool.current, "maximum": pool.maximum, "recovery": pool.recovery.value}
            for pool in actor.resource_pools
        ],
    }


def _actor_from_payload(raw: object) -> Actor:
    data = _mapping(raw, "actor")
    abilities = _mapping(data.get("ability_scores"), "actor.ability_scores")
    prep_raw = data.get("spell_preparation")
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
    return Actor(
        id=ActorId(_string(data.get("id"), "actor.id")), name=_string(data.get("name"), "actor.name"),
        ac=_integer(data.get("ac"), "actor.ac"), hp=_integer(data.get("hp"), "actor.hp"),
        temp_hp=_integer(data.get("temp_hp"), "actor.temp_hp"), max_hp=_integer(data.get("max_hp"), "actor.max_hp"),
        speed_feet=_integer(data.get("speed_feet"), "actor.speed_feet"), position=_coordinate(data.get("position"), "actor.position"),
        faction=_enum(Faction, data.get("faction"), "actor.faction"),
        ability_scores=AbilityScores(**{name: _integer(abilities.get(name), f"ability_scores.{name}") for name in _ABILITY_NAMES}),
        spell_slots=tuple(SpellSlotState(_integer(slot.get("level"), "slot.level"), _integer(slot.get("remaining"), "slot.remaining"), _integer(slot.get("maximum"), "slot.maximum")) for value in _sequence(data.get("spell_slots", []), "spell_slots") for slot in (_mapping(value, "slot"),)),
        spell_save_dc=_integer(data.get("spell_save_dc"), "actor.spell_save_dc"),
        inventory=tuple(InventoryItem(id=_string(item.get("id"), "item.id"), name=_string(item.get("name"), "item.name"), kind=_string(item.get("kind"), "item.kind"), quantity=_integer(item.get("quantity"), "item.quantity"), equipped=_boolean(item.get("equipped"), "item.equipped"), source_ref=_optional_string(item.get("source_ref"), "item.source_ref"), broken=_boolean(item.get("broken"), "item.broken")) for value in _sequence(data.get("inventory", []), "inventory") for item in (_mapping(value, "item"),)),
        spell_ids=_string_tuple(data.get("spell_ids", []), "actor.spell_ids"), spell_preparation=prep,
        hit_dice=tuple(HitDicePool(_integer(pool.get("die_sides"), "hit_die.die_sides"), _integer(pool.get("remaining"), "hit_die.remaining"), _integer(pool.get("maximum"), "hit_die.maximum")) for value in _sequence(data.get("hit_dice", []), "hit_dice") for pool in (_mapping(value, "hit_die"),)),
        resource_pools=tuple(ActorResourcePool(id=_string(pool.get("id"), "resource.id"), label=_string(pool.get("label"), "resource.label"), current=_integer(pool.get("current"), "resource.current"), maximum=_integer(pool.get("maximum"), "resource.maximum"), recovery=_enum(RecoveryPeriod, pool.get("recovery"), "resource.recovery")) for value in _sequence(data.get("resource_pools", []), "resource_pools") for pool in (_mapping(value, "resource"),)),
    )


def _exploration_payload(state: ExplorationState) -> dict[str, object]:
    return {
        "party_position": {"zone_id": state.party_position.zone_id, "marker_position": _coordinate_payload(state.party_position.marker_position)},
        "flags": [{"key": key, "value": _json_value(value, "flag.value")} for key, value in state.flags.values],
        "point_visibility": [{"id": point.id, "visibility": point.visibility.value} for point in state.points],
        "exhausted_search_zones": list(state.exhausted_search_zones),
        "challenge_states": [
            {"challenge_id": item.challenge_id, "current_progress": item.current_progress, "noise": item.noise,
             "complications": list(item.complications), "completed": item.completed,
             "attempts": [_attempt_payload(attempt) for attempt in item.attempts]}
            for item in state.challenge_states
        ],
        "inventory_resource_ids": list(state.inventory_resource_ids), "elapsed_minutes": state.elapsed_minutes,
        "short_rest_counts": [{"policy_id": key, "count": value} for key, value in state.short_rest_counts],
        "temporary_items": [
            {
                "id": item.id, "template_id": item.template_id, "label": item.label,
                "description": item.description, "bonus_tags": list(item.bonus_tags),
                "modifier": item.modifier, "advantage": item.advantage,
                "uses_remaining": item.uses_remaining, "created_in_zone_id": item.created_in_zone_id,
                "source_materials": list(item.source_materials), "risk": item.risk,
            }
            for item in state.temporary_items
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
    short_counts = tuple(
        (_string(item.get("policy_id"), "short_rest.policy_id"), _integer(item.get("count"), "short_rest.count"))
        for raw_item in _sequence(data.get("short_rest_counts", []), "short_rest_counts")
        for item in (_mapping(raw_item, "short_rest_count"),)
    )
    temporary_items = tuple(
        TemporaryItem(
            id=_string(item.get("id"), "temporary_item.id"),
            template_id=_string(item.get("template_id"), "temporary_item.template_id"),
            label=_string(item.get("label"), "temporary_item.label"),
            description=_string(item.get("description"), "temporary_item.description"),
            bonus_tags=_string_tuple(item.get("bonus_tags", []), "temporary_item.bonus_tags"),
            modifier=_integer(item.get("modifier"), "temporary_item.modifier"),
            advantage=_boolean(item.get("advantage"), "temporary_item.advantage"),
            uses_remaining=_integer(item.get("uses_remaining"), "temporary_item.uses_remaining"),
            created_in_zone_id=_string(item.get("created_in_zone_id"), "temporary_item.created_in_zone_id"),
            source_materials=_string_tuple(item.get("source_materials", []), "temporary_item.source_materials"),
            risk=_string(item.get("risk"), "temporary_item.risk"),
        )
        for raw_item in _sequence(data.get("temporary_items", []), "temporary_items")
        for item in (_mapping(raw_item, "temporary_item"),)
    )
    if any(item.created_in_zone_id not in {zone.id for zone in base.zones} for item in temporary_items):
        raise SnapshotValidationError("Zapis zawiera przedmiot tymczasowy z nieznanej lokacji.")
    return replace(
        base, party_position=PartyPosition(zone_id, _optional_coordinate(party.get("marker_position"), "party_position.marker_position")),
        flags=SceneFlags(tuple(flags)), points=tuple(replace(point, visibility=visibility[point.id]) for point in base.points),
        exhausted_search_zones=_string_tuple(data.get("exhausted_search_zones", []), "exhausted_search_zones"),
        challenge_states=challenge_states, inventory_resource_ids=resources,
        elapsed_minutes=_integer(data.get("elapsed_minutes"), "elapsed_minutes"), short_rest_counts=short_counts,
        temporary_items=temporary_items,
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
    )


def _combat_payload(state: CombatState | None) -> dict[str, object] | None:
    if state is None:
        return None
    return {
        "actors": [_actor_payload(actor) for actor in state.actors],
        "initiative": {
            "current_index": state.initiative_order.current_index, "round_number": state.initiative_order.round_number,
            "entries": [{"actor_id": str(entry.actor.id), "natural_roll": entry.roll.natural_roll, "natural_rolls": list(entry.roll.natural_rolls), "total": entry.roll.total, "mode": entry.roll.mode.value, "dexterity_modifier": entry.dexterity_modifier, "stable_order": entry.stable_order} for entry in state.initiative_order.entries],
        },
        "turn_action": {"action_use": state.turn_action.action_use.value, "bonus_action_use": state.turn_action.bonus_action_use.value, "reaction_available": state.turn_action.reaction_available, "movement_used_feet": state.turn_action.movement_used_feet, "extra_movement_feet": state.turn_action.extra_movement_feet},
        "status": state.status.value, "winner": state.winner.value if state.winner else None,
        "spent_reaction_actor_ids": sorted(str(item) for item in state.spent_reaction_actor_ids),
    }


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
    return CombatState(
        actors, InitiativeOrder(tuple(entries), current_index, _integer(initiative.get("round_number"), "initiative.round_number")),
        TurnActionState(_enum(ActionUse, turn.get("action_use"), "turn_action.action_use"), _enum(ActionUse, turn.get("bonus_action_use"), "turn_action.bonus_action_use"), _boolean(turn.get("reaction_available"), "turn_action.reaction_available"), _integer(turn.get("movement_used_feet"), "turn_action.movement_used_feet"), _integer(turn.get("extra_movement_feet"), "turn_action.extra_movement_feet")),
        _enum(CombatStatus, data.get("status"), "combat.status"), _optional_enum(Faction, data.get("winner"), "combat.winner"),
        frozenset(ActorId(item) for item in _string_tuple(data.get("spent_reaction_actor_ids", []), "spent_reaction_actor_ids")),
    )


def _pending_encounter_payload(value: PendingEncounter | None) -> dict[str, object] | None:
    if value is None:
        return None
    return {"trigger_id": value.trigger_id, "name": value.name, "description": value.description, "encounter_scenario": value.encounter_scenario, "reason": value.reason}


def _pending_encounter_from_payload(raw: object) -> PendingEncounter | None:
    if raw is None:
        return None
    data = _mapping(raw, "pending_encounter")
    return PendingEncounter(*(_string(data.get(name), f"pending_encounter.{name}", allow_empty=name in {"description", "reason"}) for name in ("trigger_id", "name", "description", "encounter_scenario", "reason")))


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
