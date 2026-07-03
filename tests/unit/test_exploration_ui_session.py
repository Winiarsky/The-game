from dnd_board_game.llm import (
    GmClassifierProposal,
    GmDeclarationAnalysis,
    GmDeclarationAnalysisType,
    NpcInteractionProposal,
)
from dnd_board_game.ui.exploration_app import ExplorationUiSession


class FakeGmClient:
    model = "fake-gm"

    def __init__(self, proposal):
        self.proposal = proposal
        self.requests = []

    def analyze(self, request):
        return GmDeclarationAnalysis(
            analysis_type=GmDeclarationAnalysisType.PLAUSIBLE,
            player_message="",
            normalized_intent=request.player_action,
            reason="test",
            confidence=1.0,
        )

    def classify(self, request):
        self.requests.append(request)
        return self.proposal


class FakeNpcClient:
    model = "fake-npc"

    def __init__(self, proposal):
        self.proposal = proposal
        self.requests = []

    def interact_npc(self, request):
        self.requests.append(request)
        return self.proposal


def _challenge_proposal(**overrides):
    data = {
        "intent_type": "challenge_attempt",
        "target_challenge_id": "closed_gate",
        "approach_label": "Wyważenie bramy",
        "approach_tags": ["heavy_force", "noise"],
        "ability": "strength",
        "skill": "athletics",
        "difficulty_tier": "medium",
        "difficulty_reason": "Stara brama może ustąpić pod mocnym naporem.",
        "dc": 15,
        "progress_on_success": 3,
        "progress_on_failure": 1,
        "used_resource_ids": [],
        "check_participants": "single_actor",
        "check_aggregation": "lead_result",
        "consequence_targets": ["lead_actor", "scene"],
        "consequences": [{"trigger": "failure", "type": "add_noise", "value": 1}],
        "player_narration": "Napieracie na skrzydła bramy.",
    }
    data.update(overrides)
    return GmClassifierProposal.model_validate(data)


def test_exploration_ui_session_resolves_gate_challenge():
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(_challenge_proposal()),
    )

    state = session.submit_action("Wyważamy bramę.")
    assert state["pending"]["stage"] == "decision"
    assert state["active_challenge"]["current_progress"] == 0

    state = session.decide("accept")
    assert state["pending"]["stage"] == "roll"
    assert state["required_rolls"] == [{"actor_id": "hero", "actor_name": "Bohater"}]

    state = session.resolve_rolls({"hero": 16})

    assert state["pending"] is None
    assert state["active_challenge"] is None
    assert state["travel_options"][0]["id"] == "courtyard"
    assert any(message["title"] == "Nowy punkt odkryty" for message in state["messages"])


def test_exploration_ui_session_rejects_pending_interpretation():
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(_challenge_proposal()),
    )

    session.submit_action("Wyważamy bramę.")
    state = session.decide("reject")

    assert state["pending"] is None
    assert any("Odrzucono interpretację" in message["body"] for message in state["messages"])


def test_exploration_ui_session_debug_npc_sets_flags_without_roll():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "social",
            "player_narration": "Mówicie spokojnie i trzymacie ręce widocznie.",
            "npc_response": "Zwiadowca oddycha wolniej.",
            "requires_roll": False,
            "flag_changes_on_success": [{"key": "scout_calmed", "value": True}],
        }
    )
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        npc_client=FakeNpcClient(proposal),
        debug_point_id="wounded_scout",
    )

    state = session.submit_action("Uspokajamy zwiadowcę.")
    assert state["pending"]["kind"] == "npc"

    state = session.decide("accept")

    assert state["pending"] is None
    assert {"key": "scout_calmed", "value": True} in state["flags"]


def test_exploration_ui_session_reset_restores_initial_state():
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(_challenge_proposal()),
    )
    session.submit_action("Wyważamy bramę.")
    session.decide("accept")
    session.resolve_rolls({"hero": 16})

    session.reset()
    state = session.state_payload()

    assert state["active_challenge"]["current_progress"] == 0
    assert state["flags"] == []
