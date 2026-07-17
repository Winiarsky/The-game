from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UiSessionView:
    """Transport-neutral top-level contract returned by ``/api/state``."""

    scenario: dict[str, object]
    session_log: dict[str, object]
    snapshot: dict[str, object]
    flow: dict[str, object]
    spell_preparation: dict[str, object] | None
    short_rest: dict[str, object] | None
    current_zone: dict[str, object]
    available_zones: list[dict[str, object]]
    visible_environment: list[dict[str, object]]
    travel_options: list[dict[str, object]]
    visible_points: list[dict[str, object]]
    current_zone_points: list[dict[str, object]]
    active_challenge: dict[str, object] | None
    active_point: dict[str, object] | None
    resources: list[dict[str, object]]
    discovered_sources: list[dict[str, object]]
    actors: list[dict[str, object]]
    active_effects: list[dict[str, object]]
    scene_status: list[dict[str, object]]
    flags: list[dict[str, object]]
    messages: list[dict[str, object]]
    conversation: dict[str, object]
    pending: dict[str, object] | None
    pending_npc_transition: dict[str, object] | None
    selected_lead_actor_id: str
    selected_helper_actor_id: str | None
    allowed_mechanics: list[dict[str, object]]
    pending_encounter: dict[str, object] | None
    exploration_setup: dict[str, object] | None
    encounter_setup: dict[str, object] | None
    encounter_stealth: dict[str, object] | None
    encounter_initiative: dict[str, object] | None
    combat: dict[str, object] | None
    board: dict[str, object]
    required_rolls: list[dict[str, object]]

    def as_payload(self) -> dict[str, object]:
        return {
            "scenario": self.scenario,
            "session_log": self.session_log,
            "snapshot": self.snapshot,
            "flow": self.flow,
            "spell_preparation": self.spell_preparation,
            "short_rest": self.short_rest,
            "current_zone": self.current_zone,
            "available_zones": self.available_zones,
            "visible_environment": self.visible_environment,
            "travel_options": self.travel_options,
            "visible_points": self.visible_points,
            "current_zone_points": self.current_zone_points,
            "active_challenge": self.active_challenge,
            "active_point": self.active_point,
            "resources": self.resources,
            "discovered_sources": self.discovered_sources,
            "actors": self.actors,
            "active_effects": self.active_effects,
            "scene_status": self.scene_status,
            "flags": self.flags,
            "messages": self.messages,
            "conversation": self.conversation,
            "pending": self.pending,
            "pending_npc_transition": self.pending_npc_transition,
            "selected_lead_actor_id": self.selected_lead_actor_id,
            "selected_helper_actor_id": self.selected_helper_actor_id,
            "allowed_mechanics": self.allowed_mechanics,
            "pending_encounter": self.pending_encounter,
            "exploration_setup": self.exploration_setup,
            "encounter_setup": self.encounter_setup,
            "encounter_stealth": self.encounter_stealth,
            "encounter_initiative": self.encounter_initiative,
            "combat": self.combat,
            "board": self.board,
            "required_rolls": self.required_rolls,
        }
