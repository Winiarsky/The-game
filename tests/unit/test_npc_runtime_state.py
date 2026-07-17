from dataclasses import replace

from dnd_board_game.combat import set_scene_flag
from dnd_board_game.exploration import (
    ExplorationPoint,
    ExplorationState,
    NpcAttitude,
    NpcInteraction,
    NpcAttemptPolicy,
    NpcStateUpdate,
    PartyPosition,
    npc_runtime_state_for,
    plan_npc_attempt,
    resolve_npc_runtime_interaction,
)
from dnd_board_game.world import Coordinate


def _state() -> ExplorationState:
    npc = NpcInteraction(
        id="scout",
        name="Scout",
        public_description="A wounded scout.",
        initial_attitude=NpcAttitude.INDIFFERENT,
        initial_physical_state="Wounded",
        initial_emotional_state="Afraid",
    )
    point = ExplorationPoint(
        id="scout_point",
        name="Scout",
        zone_id="courtyard",
        positions=(Coordinate(1, 1),),
        color=(1, 2, 3),
        npc_interaction=npc,
    )
    return ExplorationState((), (point,), PartyPosition("courtyard"))


def test_exploration_state_initializes_runtime_state_from_npc_content() -> None:
    state = _state()

    npc = npc_runtime_state_for(state, "scout")

    assert npc is not None
    assert npc.attitude == NpcAttitude.INDIFFERENT
    assert npc.physical_state == "Wounded"
    assert npc.emotional_state == "Afraid"


def test_npc_interaction_updates_state_and_persists_unique_history() -> None:
    first = resolve_npc_runtime_interaction(
        _state(),
        npc_id="scout",
        intent="medical",
        success=True,
        summary="The wound is dressed.",
        update=NpcStateUpdate(
            attitude=NpcAttitude.FRIENDLY,
            physical_state="Stabilized",
            emotional_state="Grateful",
        ),
        revealed_information_ids=("tower_hint",),
        attempt_id="medical",
    )
    second = resolve_npc_runtime_interaction(
        first.state,
        npc_id="scout",
        intent="medical",
        success=False,
        summary="The second examination reveals nothing.",
        revealed_information_ids=("tower_hint",),
        attempt_id="medical",
    )

    npc = second.npc_after
    assert npc.attitude == NpcAttitude.FRIENDLY
    assert npc.physical_state == "Stabilized"
    assert npc.revealed_information_ids == ("tower_hint",)
    assert npc.used_attempt_ids == ("medical",)
    assert [event.sequence for event in npc.relationship_events] == [1, 2]
    assert [event.outcome for event in npc.relationship_events] == ["success", "failure"]
    assert [event.attempt_id for event in npc.relationship_events] == ["medical", "medical"]


def test_npc_attempt_requires_changed_context_and_then_exhausts_limit() -> None:
    policy = NpcAttemptPolicy(
        attempt_id="build_trust",
        max_attempts=2,
        retry_requires_any_flags=("scout_helped",),
        retry_locked_message="Najpierw pomóż zwiadowcy.",
        exhausted_message="Zwiadowca nie zmieni już zdania.",
    )
    initial = plan_npc_attempt(_state(), npc_id="scout", policy=policy)
    assert initial.available is True
    assert initial.attempts_used == 0
    assert initial.attempts_remaining == 2

    first = resolve_npc_runtime_interaction(
        _state(),
        npc_id="scout",
        intent="social",
        success=False,
        summary="Zwiadowca nie ufa drużynie.",
        attempt_id="build_trust",
    )
    locked = plan_npc_attempt(first.state, npc_id="scout", policy=policy)
    assert locked.available is False
    assert locked.blocked_reason == "Najpierw pomóż zwiadowcy."
    assert locked.attempts_used == 1

    helped_state = replace(
        first.state,
        flags=set_scene_flag(first.state.flags, "scout_helped", True),
    )
    retry = plan_npc_attempt(helped_state, npc_id="scout", policy=policy)
    assert retry.available is True
    assert retry.is_retry is True
    assert retry.attempts_remaining == 1

    second = resolve_npc_runtime_interaction(
        helped_state,
        npc_id="scout",
        intent="social",
        success=False,
        summary="Zwiadowca podjął ostateczną decyzję.",
        attempt_id="build_trust",
    )
    exhausted = plan_npc_attempt(second.state, npc_id="scout", policy=policy)
    assert exhausted.available is False
    assert exhausted.blocked_reason == "Zwiadowca nie zmieni już zdania."
    assert exhausted.attempts_remaining == 0
