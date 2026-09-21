"""Read-only presentation of engine combat payloads for the shared laptop screen.

This projection never evaluates legality or changes a turn, target or resource.
In particular, a target snapshot is resolved against the current actor roster.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from dnd_board_game.combat.conditions import ConditionState, condition_definition
from dnd_board_game.combat.spells import grid_distance_feet
from dnd_board_game.world import Coordinate

_INTERNAL_EFFECTS = frozenset({
    "mana_series_source", "shared_offensive_used", "rage_duration",
    "rage_activity", "mana_ordinary_movement",
})


def _actor_effects(
    actor: Mapping[str, Any], actors: Mapping[str, Mapping[str, Any]],
    combat: Mapping[str, Any], conditions: Sequence[ConditionState],
) -> list[dict[str, Any]]:
    """Keep source/duration metadata and real, already-resolved aura membership."""
    effects: list[dict[str, Any]] = []
    labels: set[str] = set()
    for effect in actor.get("effects", ()):
        if effect.get("kind") in _INTERNAL_EFFECTS:
            continue
        source_id = str(effect.get("source_actor_id") or "")
        label = str(effect.get("label") or effect.get("kind") or "")
        effects.append({
            "id": effect.get("id"), "label": label,
            "body": effect.get("value_label") or "",
            "expires": effect.get("expires") or "",
            "source_name": actors.get(source_id, {}).get("name", ""),
        })
        labels.add(label)
    concentration = actor.get("concentration")
    if concentration:
        effects.append({
            "id": "concentration", "label": concentration.get("label", ""),
            "body": "", "expires": concentration.get("expires", ""),
            "source_name": actor.get("name", ""), "concentration": True,
        })
    for condition in conditions:
        if condition.actor_id != str(actor["id"]):
            continue
        definition = condition_definition(condition.condition)
        source = actors.get(str(condition.source_actor_id), {})
        expires_actor = actors.get(str(condition.expiration_actor_id), {})
        effects.append({
            "id": "condition:" + condition.condition.value,
            "label": definition.label, "body": definition.description,
            "source_name": source.get("name") or condition.source_label,
            "source_label": condition.source_label,
            "duration": condition.duration.value,
            "expiration_actor": expires_actor.get("name", ""),
            "expiration_count": condition.expiration_event_count,
            "save_ability": condition.save_ability, "save_dc": condition.save_dc,
            "save_timing": condition.save_timing.value if condition.save_timing else None,
        })
        labels.add(definition.label)
    for chip in actor.get("status_chips", ()):
        label = str(chip.get("label") or "")
        if not label or label in labels or any(label.startswith(previous + ": ") for previous in labels):
            continue
        # Turn resources remain in the actor's compact resource line.
        if label.startswith(("Akcja ", "Ataki ", "Bonus ", "Reakcja ", "Ruch ", "Darmowa interakcja ")):
            continue
        effects.append({"id": "status:" + label, "label": label,
                        "body": chip.get("title", ""), "tone": chip.get("tone", "neutral")})
        labels.add(label)
    for aura in combat.get("auras", ()):
        own = str(aura.get("source_actor_id")) == str(actor["id"])
        receives = str(actor["id"]) in {str(item) for item in aura.get("affected_actor_ids", ())}
        if not own and not receives:
            continue
        source_effect = next((item for item in combat.get("active_effects", ())
                              if item.get("id") == aura.get("id")), {})
        effects.append({
            "id": "aura:" + str(aura.get("id", "")), "label": aura.get("label", ""),
            "source_name": aura.get("source_actor_name", ""),
            "expires": source_effect.get("expires", ""),
            "aura": dict(aura), "aura_source": own, "aura_receives": receives,
        })
    return effects


def tabletop_combat_payload(
    combat: Mapping[str, Any], initiative_order: Sequence[Mapping[str, Any]] = (),
    *, conditions: Sequence[ConditionState] = (),
) -> dict[str, Any]:
    """Build the vertical roster and enrich a selected target from live payloads."""
    actors = {str(actor["id"]): dict(actor) for actor in combat.get("actors", ())}
    current = combat.get("current_actor") or {}
    current_id = str(current.get("id", ""))
    if current_id in actors:
        actors[current_id] = {**actors[current_id], **current,
                              "portrait_url": actors[current_id].get("portrait_url") or current.get("portrait_url")}
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in [*initiative_order, *actors.values()]:
        actor_id = str(entry.get("actor_id") or entry.get("id") or "")
        if actor_id in seen or actor_id not in actors:
            continue
        seen.add(actor_id)
        actor = actors[actor_id]
        entries.append({**actor, "initiative": entry.get("total"),
                        "active": actor_id == current_id,
                        "details": _actor_effects(actor, actors, combat, conditions)})

    pending = combat.get("pending_player_attack") or {}
    feature = combat.get("class_feature_targeting") or {}
    target_ref = pending.get("target") or feature.get("selected_target") or {}
    target_id = str(target_ref.get("id", ""))
    target = next((entry for entry in entries if entry["id"] == target_id), None)
    # Never fall back to a stale pending target removed from the current roster.
    target_view: dict[str, Any] | None = None
    if target:
        attacker = actors.get(str((pending.get("attacker") or current).get("id")), current)
        distance = None
        if attacker.get("position") is not None and target.get("position") is not None:
            distance = grid_distance_feet(Coordinate(*attacker["position"]), Coordinate(*target["position"]))
        target_view = {"actor_id": target_id, "distance_feet": distance}
    return {"actors": entries, "active_actor_id": current_id, "target": target_view}
