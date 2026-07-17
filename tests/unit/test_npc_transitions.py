from dataclasses import replace

import pytest

from dnd_board_game.combat import SceneFlags, scene_flag, set_scene_flag
from dnd_board_game.exploration import (
    ExplorationState,
    NpcSceneTransition,
    NpcTransitionReaction,
    NpcTransitionResultType,
    NpcTransitionVariant,
    PartyPosition,
    plan_npc_transition,
    resolve_npc_transition_reaction,
)


def _transition() -> NpcSceneTransition:
    calm = NpcTransitionReaction(
        "calm",
        "Calm down",
        "Stop the alarm.",
        NpcTransitionResultType.RESUME_DIALOGUE,
        "The NPC lowers their voice.",
        effects=({"type": "set_flag", "parameters": {"key": "alarm", "value": False}},),
    )
    fight = NpcTransitionReaction(
        "fight",
        "Hold ground",
        "Start combat.",
        NpcTransitionResultType.START_ENCOUNTER,
        "Enemies arrive.",
        encounter_trigger_id="alarm_encounter",
    )
    return NpcSceneTransition(
        "npc_escalation",
        "scout",
        (
            NpcTransitionVariant(
                "secured",
                "Secured area",
                "Nobody answers the alarm.",
                (calm,),
                required_flags=("secured",),
            ),
            NpcTransitionVariant("danger", "Danger", "Enemies may answer.", (calm, fight)),
        ),
    )


def test_npc_transition_selects_first_matching_variant_and_applies_only_reaction_effects() -> None:
    base = ExplorationState((), (), PartyPosition("yard"), SceneFlags())
    secured = replace(base, flags=set_scene_flag(base.flags, "secured", True))

    secured_plan = plan_npc_transition(
        (_transition(),), transition_id="npc_escalation", state=secured,
        resolved_encounter_trigger_ids=set(),
    )
    danger_plan = plan_npc_transition(
        (_transition(),), transition_id="npc_escalation", state=base,
        resolved_encounter_trigger_ids=set(),
    )
    assert secured_plan.variant.id == "secured"
    assert danger_plan.variant.id == "danger"

    alarmed = replace(base, flags=set_scene_flag(base.flags, "alarm", True))
    resolution = resolve_npc_transition_reaction(alarmed, danger_plan, "calm")
    assert scene_flag(resolution.state.flags, "alarm", True) is False
    assert resolution.reaction.result_type == NpcTransitionResultType.RESUME_DIALOGUE


def test_npc_transition_rejects_unknown_reaction() -> None:
    state = ExplorationState((), (), PartyPosition("yard"), SceneFlags())
    plan = plan_npc_transition(
        (_transition(),), transition_id="npc_escalation", state=state,
        resolved_encounter_trigger_ids=set(),
    )
    with pytest.raises(ValueError, match="has no reaction"):
        resolve_npc_transition_reaction(state, plan, "run")
