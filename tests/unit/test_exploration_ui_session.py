import random
from dataclasses import replace

import pytest

from dnd_board_game.actors import (
    ActorTrigger,
    CreatureSize,
    DamageAffinityProfile,
    DeathSaveState,
    Faction,
    TriggerEffectKind,
    TriggerEventType,
)
from dnd_board_game.actions import PlayerIntentHint
from dnd_board_game.combat import (
    AttackKind,
    CombatCondition,
    ConditionSaveTiming,
    ConditionState,
    EnemyAutoTurnResult,
    HiddenState,
    current_actor,
    replace_actor,
    scene_flag,
    set_scene_flag,
)
from dnd_board_game.combat.damage import DamageComponentInput, DamageType, apply_damage_result, resolve_damage
from dnd_board_game.exploration import (
    CraftingComponentSelection,
    CraftingDraft,
    ExplorationChallengeState,
    add_exploration_condition,
    ExplorationTrapStatus,
    trap_state_for,
    build_crafting_source_registry,
    craft_temporary_item,
)
from dnd_board_game.hardware import LedColor
from dnd_board_game.inventory import HandSlot, InventoryItem
from dnd_board_game.llm import (
    GmClassifierProposal,
    GmDeclarationAnalysis,
    GmDeclarationAnalysisType,
    NpcInteractionProposal,
)
from dnd_board_game.rules import (
    ActiveEffect,
    EffectDuration,
    EffectSource,
    EffectSourceType,
    RollMode,
)
from dnd_board_game.ui.exploration_app import (
    ExplorationUiSession,
    PendingInteraction,
    PendingKind,
    PendingStage,
    PendingEnemyOpportunityAttack,
    UiFlowStage,
    create_app,
)
from dnd_board_game.world import Coordinate, find_path


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


class FakeSemanticSourceGmClient(FakeGmClient):
    def __init__(
        self,
        proposal,
        *,
        requested_name="kij",
        required_properties=("long",),
        preferred_properties=("rigid",),
    ):
        super().__init__(proposal)
        self.requested_name = requested_name
        self.required_properties = required_properties
        self.preferred_properties = preferred_properties

    def analyze(self, request):
        return GmDeclarationAnalysis.model_validate(
            {
                "analysis_type": "plausible",
                "action_flow": "challenge_attempt",
                "normalized_intent": request.player_action,
                "reason": "test ogólnego dopasowania funkcjonalnego",
                "confidence": 1.0,
                "source_query": {
                    "purpose": "dosięgnięcie rygla przez szczelinę",
                    "requested_name": self.requested_name,
                    "required_properties": list(self.required_properties),
                    "preferred_properties": list(self.preferred_properties),
                },
            }
        )


class FakeUseSourceGmClient(FakeGmClient):
    def __init__(self, proposal, source_id):
        super().__init__(proposal)
        self.source_id = source_id
        self.analysis_requests = []

    def analyze(self, request):
        self.analysis_requests.append(request)
        return GmDeclarationAnalysis.model_validate(
            {
                "analysis_type": "plausible",
                "action_flow": "challenge_attempt",
                "normalized_intent": request.player_action,
                "reason": "test jawnego użycia źródła",
                "confidence": 1.0,
                "use_source_id": self.source_id,
            }
        )


class FakeFixtureActionGmClient(FakeGmClient):
    def __init__(self, proposal, source_id, operation):
        super().__init__(proposal)
        self.source_id = source_id
        self.operation = operation

    def analyze(self, request):
        return GmDeclarationAnalysis.model_validate(
            {
                "analysis_type": "plausible",
                "action_flow": "challenge_attempt",
                "normalized_intent": request.player_action,
                "reason": "test trwałej operacji na fixture",
                "confidence": 1.0,
                "action_target_source_id": self.source_id,
                "fixture_operation": self.operation,
            }
        )


class FakeNpcClient:
    model = "fake-npc"

    def __init__(self, proposal):
        self.proposal = proposal
        self.requests = []

    def interact_npc(self, request):
        self.requests.append(request)
        return self.proposal


class FakeQuestionGmClient:
    model = "fake-question-gm"

    def __init__(self):
        self.requests = []

    def analyze(self, request):
        self.requests.append(request)
        return GmDeclarationAnalysis(
            analysis_type=GmDeclarationAnalysisType.PLAYER_QUESTION,
            player_message="W pobliżu leżą kamienie, ale żaden nie wygląda na wystarczająco duży, by sam zastąpić taran.",
            reason="Odpowiedź oparta na available_materials bez tworzenia nowego zasobu.",
            confidence=1.0,
            response_kind="observation",
            grounded_fact_ids=("source:zone:gate:item:gate_loose_stones",),
        )

    def classify(self, request):  # noqa: ARG002
        raise AssertionError("Pytanie gracza nie powinno trafiać do klasyfikatora mechaniki.")


class FakeHintGmClient:
    model = "fake-hint-gm"

    def __init__(self):
        self.requests = []

    def analyze(self, request):
        self.requests.append(request)
        level = request.to_prompt_payload()["conversation_policy"]["next_hint_level"]
        fact_id = (
            "fact:gate.climb_is_dangerous"
            if level == 2
            else "fact:gate.force_possible"
        )
        return GmDeclarationAnalysis.model_validate(
            {
                "analysis_type": "player_question",
                "player_message": f"Podpowiedź poziomu {level} oparta na aktualnej scenie.",
                "reason": "test progresji podpowiedzi",
                "confidence": 1.0,
                "response_kind": "strong_hint" if level == 3 else "gentle_hint",
                "grounded_fact_ids": [fact_id],
                "hint_level": level,
            }
        )

    def classify(self, request):  # noqa: ARG002
        raise AssertionError("Prośba o podpowiedź nie powinna trafiać do klasyfikatora mechaniki.")


class FakeMismatchedQuestionGmClient:
    model = "fake-mismatched-question-gm"

    def analyze(self, request):  # noqa: ARG002
        return GmDeclarationAnalysis.model_validate(
            {
                "analysis_type": "player_question",
                "player_message": "Tak, ale wyważanie jest głośne.",
                "response_kind": "observation",
                "grounded_fact_ids": ["fact:gate.force_is_loud"],
                "hint_level": 0,
            }
        )

    def classify(self, request):  # noqa: ARG002
        raise AssertionError("Pytanie gracza nie powinno trafiać do klasyfikatora mechaniki.")


class FakeObservationGmClient:
    model = "fake-observation-gm"

    def __init__(self):
        self.requests = []

    def analyze(self, request):
        self.requests.append(request)
        return GmDeclarationAnalysis.model_validate(
            {
                "analysis_type": "player_question",
                "player_message": "Przez szczelinę widzisz dwa gobliny, ale dokładne rozpoznanie wymaga testu.",
                "response_kind": "requires_check",
                "requires_check": True,
                "suggested_followup": "Przyglądam się przez szczelinę i szukam ruchu.",
                "observation_id": "look_through_gate_gap",
            }
        )

    def classify(self, request):  # noqa: ARG002
        raise AssertionError("Stopniowana obserwacja nie powinna trafiać do klasyfikatora wyzwania.")


class FakeInvalidFactGmClient:
    model = "fake-invalid-fact-gm"

    def analyze(self, request):  # noqa: ARG002
        return GmDeclarationAnalysis.model_validate(
            {
                "analysis_type": "plausible",
                "action_flow": "challenge_attempt",
                "player_message": "",
                "normalized_intent": "Używam działa laserowego.",
                "reason": "test",
                "confidence": 1.0,
                "assumed_new_facts": ["działo laserowe"],
            }
        )

    def classify(self, request):  # noqa: ARG002
        raise AssertionError("Nieugruntowana deklaracja nie powinna trafić do klasyfikatora mechaniki.")


class FakeBoardConnection:
    def __init__(self, clicks=None):
        self.led_calls = []
        self.clicks = list(clicks or [])
        self.reset_calls = []

    def set_leds(self, positions, rgb_color):
        self.led_calls.append((positions, rgb_color))

    def leds_off(self):
        self.led_calls.append(("off", None))

    def scan_board(self, acceptable_responses=None, *, timeout_s=None):  # noqa: ARG002
        if not self.clicks:
            return None
        click = self.clicks.pop(0)
        if acceptable_responses and click not in acceptable_responses:
            return None
        return click

    def reset_connection(self):
        self.reset_calls.append("reset_connection")


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


def _start_combat_from_scout_alarm(session: ExplorationUiSession):
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.state = replace(session.state, flags=set_scene_flag(session.state.flags, "scout_panicked", True))
    session.state_payload()
    session.start_encounter_setup()
    while session.encounter_setup_flow is not None and not session.encounter_setup_flow.completed:
        if session.encounter_setup_flow.is_player_start_step:
            while session.encounter_setup_flow.is_player_start_step:
                position = session.encounter_setup_flow.remaining_player_start_positions()[0]
                session.assign_encounter_player_start_position(position)
            continue
        session.confirm_encounter_setup_step()
    session.start_encounter_initiative()
    session.submit_encounter_initiative_roll(20)
    session.submit_encounter_initiative_roll(19)
    session.submit_encounter_initiative_roll(18)
    assert session.combat_state is not None
    return session.combat_state


def _start_gate_skirmish(session: ExplorationUiSession):
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    flags = set_scene_flag(session.state.flags, "gate_passed", True)
    flags = set_scene_flag(flags, "gate_goblins_spotted", True)
    session.state = replace(
        session.state,
        flags=flags,
        challenge_states=(
            *tuple(item for item in session.state.challenge_states if item.challenge_id != "closed_gate"),
            ExplorationChallengeState(challenge_id="closed_gate", noise=3),
        ),
    )
    session.state_payload()
    session.resolve_encounter_opening()
    session.start_encounter_setup()
    while session.encounter_setup_flow is not None and not session.encounter_setup_flow.completed:
        if session.encounter_setup_flow.is_player_start_step:
            while session.encounter_setup_flow.is_player_start_step:
                position = session.encounter_setup_flow.remaining_player_start_positions()[0]
                session.assign_encounter_player_start_position(position)
            continue
        session.confirm_encounter_setup_step()
    session.start_encounter_initiative()
    session.submit_encounter_initiative_roll(20)
    session.submit_encounter_initiative_roll(19)
    session.submit_encounter_initiative_roll(18)
    assert session.combat_state is not None
    return session.combat_state


def _prepare_enemy_opportunity_preview(session: ExplorationUiSession):
    assert session.combat_state is not None
    while session.combat_state.initiative_order.current_actor.faction != Faction.ENEMY:
        session.finish_combat_turn()
    assert session.combat_state is not None
    enemy = session.combat_state.initiative_order.current_actor
    hero = next(actor for actor in session.combat_state.actors if actor.faction == Faction.ALLY)
    session.combat_state = replace_actor(session.combat_state, replace(enemy, position=Coordinate(8, 7)))
    session.combat_state = replace_actor(session.combat_state, replace(hero, position=Coordinate(7, 7)))
    enemy = session.combat_state.initiative_order.current_actor
    moved_enemy = replace(enemy, position=Coordinate(9, 7))
    path = find_path(session.encounter_setup_flow.encounter.board, enemy, session.combat_state.actors, moved_enemy.position)
    moved_state = replace_actor(session.combat_state, moved_enemy)
    session.pending_enemy_turn_result = EnemyAutoTurnResult(
        state=moved_state,
        enemy=enemy,
        target=None,
        message=f"{enemy.name} rusza się na {moved_enemy.position.as_tuple()}.",
        movement_path=path,
        moved_enemy=moved_enemy,
    )
    session.pending_enemy_opportunity_attack = PendingEnemyOpportunityAttack(
        target_id=str(enemy.id),
        threat_actor_ids=(str(hero.id),),
    )
    return hero, enemy


def _prepare_ready_attack_trigger(session: ExplorationUiSession, trigger: str = "enemy_moves"):
    assert session.combat_state is not None
    readied_actor = session.combat_state.initiative_order.current_actor
    target = next(actor for actor in session.combat_state.actors if str(actor.id) == "goblin_b")
    session.combat_state = replace_actor(session.combat_state, replace(readied_actor, position=Coordinate(8, 7)))
    session.combat_state = replace_actor(session.combat_state, replace(target, position=Coordinate(10, 7)))
    readied_actor = session.combat_state.initiative_order.current_actor
    target = next(actor for actor in session.combat_state.actors if actor.id == target.id)
    session.confirm_combat_ready(trigger=trigger)
    moved_target = replace(target, position=Coordinate(9, 7))
    path = find_path(session.encounter_setup_flow.encounter.board, target, session.combat_state.actors, moved_target.position)
    result_state = replace_actor(session.combat_state, moved_target)
    result = EnemyAutoTurnResult(
        state=result_state,
        enemy=target,
        target=None,
        message=f"{target.name} rusza się na {moved_target.position.as_tuple()}.",
        movement_path=path,
        moved_enemy=moved_target,
    )
    pending = session._pending_ready_attack_for_enemy_result(result)
    assert pending is not None
    session.pending_enemy_turn_result = result
    session.pending_ready_attack = pending
    return readied_actor, target


def test_exploration_ui_session_resolves_gate_challenge():
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(_challenge_proposal()),
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    state = session.submit_action("Wyważamy bramę.")
    assert state["pending"]["stage"] == "decision"
    assert state["active_challenge"]["current_progress"] == 0
    assert state["conversation"]["entries"][-1]["title"] == "Narracja MG"
    assert state["conversation"]["entries"][-1]["body"] == "Napieracie na skrzydła bramy."
    assert "Test:" not in state["conversation"]["entries"][-1]["body"]
    assert state["pending"]["option"]["ability"] == "strength"
    assert state["pending"]["option"]["dc"] == 15

    state = session.decide("accept")
    assert state["pending"]["stage"] == "roll"
    roll = state["required_rolls"][0]
    assert {key: roll[key] for key in ("actor_id", "actor_name", "die_sides", "label")} == {
        "actor_id": "hero",
        "actor_name": "Bohater",
        "die_sides": 20,
        "label": "d20",
    }

    state = session.resolve_rolls({"hero": 16})

    assert state["pending"]["stage"] == "hazard_save"
    assert state["pending"]["trap"]["id"] == "gate_alarm_wire"
    state = session.resolve_rolls({"hero": 20})

    assert state["pending"] is None
    assert state["active_challenge"] is None
    assert state["flow"]["stage"] == "interaction_result"
    assert state["exploration_setup"] is None


def test_exploration_hazard_waits_for_manual_save_after_critical_failure() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    challenge = next(item for item in session.state.challenges if item.id == "closed_gate")
    option = next(item for item in challenge.options if item.id == "vault_gate")
    session.pending = PendingInteraction(
        kind=PendingKind.CHALLENGE,
        stage=PendingStage.DECISION,
        challenge=challenge,
        option=option,
    )
    hp_before = next(actor for actor in session.exploration.actors if str(actor.id) == "hero").hp

    session.decide("accept", lead_actor_id="hero")
    hazard_pending = session.resolve_rolls({"hero": 1})

    assert hazard_pending["pending"]["stage"] == "hazard_save"
    assert hazard_pending["pending"]["hazard"]["id"] == "fall_from_gate"
    assert hazard_pending["required_rolls"][0]["actor_id"] == "hero"
    assert hazard_pending["required_rolls"][0]["modifier_total"] == 2
    assert next(actor for actor in session.exploration.actors if str(actor.id) == "hero").hp == hp_before

    resolved = session.resolve_rolls({"hero": 20})

    hero = next(actor for actor in session.exploration.actors if str(actor.id) == "hero")
    assert resolved["pending"] is None
    assert hero.hp < hp_before
    assert next(actor for actor in resolved["actors"] if actor["id"] == "hero")["conditions"] == []
    assert any(message["title"] == "Wynik zagrożenia" for message in resolved["messages"])


def test_failed_hazard_save_adds_visible_recoverable_prone_condition() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    challenge = next(item for item in session.state.challenges if item.id == "closed_gate")
    option = next(item for item in challenge.options if item.id == "vault_gate")
    session.pending = PendingInteraction(
        kind=PendingKind.CHALLENGE,
        stage=PendingStage.DECISION,
        challenge=challenge,
        option=option,
    )

    session.decide("accept", lead_actor_id="hero")
    session.resolve_rolls({"hero": 1})
    failed = session.resolve_rolls({"hero": 1})

    hero_payload = next(actor for actor in failed["actors"] if actor["id"] == "hero")
    assert hero_payload["conditions"] == [
        {"id": "prone", "label": "Powalony", "recoverable": True},
    ]
    assert any(item["label"] == "Stan: Bohater" for item in failed["scene_status"])

    recovered = session.recover_exploration_condition(actor_id="hero", condition="prone")

    hero_payload = next(actor for actor in recovered["actors"] if actor["id"] == "hero")
    assert hero_payload["conditions"] == []
    assert recovered["messages"][-1]["title"] == "Powrót na nogi"


def test_exploration_condition_is_carried_into_encounter() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    session.state = add_exploration_condition(
        session.state,
        "hero",
        CombatCondition.PRONE,
    )

    _start_combat_from_scout_alarm(session)

    assert session.combat_state is not None
    assert ConditionState("hero", CombatCondition.PRONE) in session.combat_state.condition_states


def test_chat_detects_and_disarms_authored_trap() -> None:
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(_challenge_proposal()),
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    proposed = session.submit_action("/szukaj szukam pułapek przy bramie")

    assert proposed["pending"]["kind"] == "observation"
    assert proposed["pending"]["observation"]["id"] == "search_gate_traps"
    session.decide("accept", lead_actor_id="rogue")
    detected = session.resolve_rolls({"rogue": 20})
    assert trap_state_for(session.state, "gate_alarm_wire").status == ExplorationTrapStatus.REVEALED
    assert any(item["label"].startswith("Pułapka:") for item in detected["scene_status"])

    preview = session.submit_action("/akcja rozbrajam linkę alarmową")
    assert preview["pending"]["kind"] == "trap"
    assert preview["pending"]["trap"]["action"] == "disarm"
    session.decide("accept")
    resolved = session.resolve_rolls({"rogue": 20})

    assert resolved["pending"] is None
    assert trap_state_for(session.state, "gate_alarm_wire").status == ExplorationTrapStatus.DISARMED


def test_failed_trap_disarm_queues_save_and_adds_alarm_noise() -> None:
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(_challenge_proposal()),
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.submit_action("/szukaj szukam pułapek przy bramie")
    session.decide("accept", lead_actor_id="rogue")
    session.resolve_rolls({"rogue": 20})
    session.submit_action("/akcja rozbrajam linkę alarmową")
    session.decide("accept")

    triggered = session.resolve_rolls({"rogue": 1})

    assert triggered["pending"]["stage"] == "hazard_save"
    assert triggered["pending"]["hazard"]["id"] == "gate_alarm_wire_trigger"
    assert trap_state_for(session.state, "gate_alarm_wire").status == ExplorationTrapStatus.TRIGGERED

    resolved = session.resolve_rolls({"rogue": 1})

    assert resolved["pending"] is None
    assert next(
        item for item in session.state.challenge_states if item.challenge_id == "closed_gate"
    ).noise == 3
    assert scene_flag(session.state.flags, "gate_alarm_triggered") is True


def test_hidden_trap_triggers_when_gate_is_completed() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    challenge = next(item for item in session.state.challenges if item.id == "closed_gate")
    option = next(item for item in challenge.options if item.id == "force_gate")
    session.pending = PendingInteraction(
        kind=PendingKind.CHALLENGE,
        stage=PendingStage.DECISION,
        challenge=challenge,
        option=option,
    )

    session.decide("accept", lead_actor_id="hero")
    triggered = session.resolve_rolls({"hero": 20})

    assert triggered["pending"]["kind"] == "trap"
    assert triggered["pending"]["stage"] == "hazard_save"
    assert trap_state_for(session.state, "gate_alarm_wire").status == ExplorationTrapStatus.TRIGGERED


def test_exploration_ui_session_answers_grounded_player_question_without_roll(tmp_path):
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeQuestionGmClient(),
        session_id="question_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    state = session.submit_action("Czy jest tu jakiś duży kamień, którego możemy użyć?")

    assert state["pending"] is None
    assert state["required_rolls"] == []
    assert state["messages"][-2]["title"] == "Gracze"
    assert state["messages"][-1] == {
        "title": "Odpowiedź MG",
        "body": "W pobliżu leżą kamienie, ale żaden nie wygląda na wystarczająco duży, by sam zastąpić taran.",
    }
    assert [entry.role for entry in session.declaration_thread] == ["player", "gm"]
    events = [__import__("json").loads(line) for line in session.observer.path.read_text(encoding="utf-8").splitlines()]
    assert any(event["event_type"] == "ui_gm_question_answered" for event in events)


def test_slash_question_strips_command_and_passes_explicit_intent_hint(tmp_path):
    client = FakeQuestionGmClient()
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=client,
        session_id="slash_question_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    state = session.submit_action("/pytaj czy te kamienie są ciężkie?")

    assert client.requests[0].player_action == "czy te kamienie są ciężkie?"
    assert client.requests[0].player_intent_hint == PlayerIntentHint.QUESTION
    assert state["conversation"]["entries"][-2]["body"] == "/pytaj czy te kamienie są ciężkie?"
    assert state["messages"][-1]["title"] == "Odpowiedź MG"


def test_slash_search_answers_visible_scene_source_without_crafting_or_roll(tmp_path):
    client = FakeGmClient(_challenge_proposal())
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=client,
        session_id="visible_source_lookup_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    state = session.submit_action("/szukaj chcę znaleźć jakąś deskę")

    assert state["pending"] is None
    assert state["messages"][-1]["title"] == "Odpowiedź MG"
    assert "Drewniana deska (4 szt.)" in state["messages"][-1]["body"]
    assert state["discovered_sources"][0]["label"] == "Drewniana deska"
    assert state["discovered_sources"][0]["inventory"] is False
    assert {item["label"] for item in state["discovered_sources"][0]["properties"]} >= {
        "długie",
        "sztywne",
    }
    assert all(resource["id"] != "zone:gate:item:gate_rotten_planks" for resource in state["resources"])
    assert client.requests == []
    events = [__import__("json").loads(line) for line in session.observer.path.read_text(encoding="utf-8").splitlines()]
    event = next(item for item in events if item["event_type"] == "ui_scene_source_lookup_answered")
    assert event["payload"]["source_ids"] == ["zone:gate:item:gate_rotten_planks"]


def test_followup_action_receives_previously_found_scene_source_as_context(tmp_path):
    client = FakeGmClient(_challenge_proposal())
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=client,
        session_id="found_source_followup_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.submit_action("/szukaj szukam deski")

    state = session.submit_action("/akcja używam jej jako dźwigni przy bramie")

    assert state["pending"]["kind"] == "challenge"
    grounded = client.requests[0].to_prompt_payload()["player_grounded_sources"]
    assert "zone:gate:item:gate_rotten_planks" in {item["id"] for item in grounded}


def test_use_command_resolves_found_scene_source_and_previews_its_properties(tmp_path):
    source_id = "zone:gate:item:gate_rotten_planks"
    proposal = _challenge_proposal(
        selected_mechanic="improvised_tool_check",
        approach_label="Podniesienie rygla deską",
        approach_tags=["lever", "quiet"],
        ability="dexterity",
        skill="sleight_of_hand",
        used_resource_ids=[],
        improvised_tool={
            "label": "Drewniana deska",
            "source": "interaction_object",
            "source_detail": "Znaleziona drewniana deska",
            "source_id": source_id,
            "effect_modifier": -1,
            "risk": "Spróchniała deska może pęknąć.",
            "reason": "Deska jest długa i sztywna, ale w złym stanie.",
        },
    )
    client = FakeUseSourceGmClient(proposal, source_id)
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=client,
        session_id="use_found_source_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.submit_action("/szukaj szukam deski")

    state = session.submit_action("/uzyj używam jej, żeby podnieść rygiel")

    assert state["pending"]["kind"] == "challenge"
    assert state["pending"]["source_use"]["id"] == source_id
    assert state["pending"]["source_use"]["remains_in_scene"] is True
    assert {item["label"] for item in state["pending"]["source_use"]["properties"]} >= {
        "długie",
        "sztywne",
    }
    assert state["pending"]["option"]["improvised_tool"]["source_id"] == source_id
    assert client.requests[0].selected_use_source_id == source_id


def test_use_command_rejects_unknown_source_before_calling_llm(tmp_path):
    client = FakeUseSourceGmClient(_challenge_proposal(), "missing")
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=client,
        session_id="use_unknown_source_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    state = session.submit_action("/uzyj używam kryształowego klucza")

    assert state["pending"] is None
    assert state["messages"][-1]["title"] == "Deklaracja wymaga korekty"
    assert "/szukaj" in state["messages"][-1]["body"]
    assert client.analysis_requests == []
    assert client.requests == []


def test_take_command_previews_and_collects_selected_scene_quantity(tmp_path):
    client = FakeGmClient(_challenge_proposal())
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=client,
        session_id="take_scene_item_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    preview = session.submit_action("/wez drewnianą deskę")

    assert preview["pending"]["kind"] == "collection"
    assert preview["pending"]["collection"]["source_id"] == "zone:gate:item:gate_rotten_planks"
    assert preview["pending"]["collection"]["available_quantity"] == 4
    assert preview["pending"]["collection"]["destination"] == "actor_inventory"
    assert client.requests == []

    accepted = session.decide("accept", lead_actor_id="rogue", quantity=2)

    assert accepted["pending"] is None
    rogue = next(actor for actor in accepted["actors"] if actor["id"] == "rogue")
    planks = next(item for item in rogue["inventory"] if item["name"] == "Drewniana deska")
    assert planks["quantity"] == 2
    assert accepted["discovered_sources"][0]["quantity"] == 2
    assert accepted["discovered_sources"][0]["collections"] == [
        {"quantity": 2, "destination": "actor_inventory", "owner_actor_id": "rogue"}
    ]
    assert accepted["messages"][-1]["title"] == "Zabrano przedmiot"


def test_take_command_rejects_attached_fixture_without_calling_llm(tmp_path):
    client = FakeGmClient(_challenge_proposal())
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=client,
        session_id="take_fixture_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    state = session.submit_action("/wez skorodowane zawiasy")

    assert state["pending"] is None
    assert state["messages"][-1]["title"] == "Nie można zabrać elementu"
    assert "Najpierw odłącz" in state["messages"][-1]["body"]
    assert client.requests == []


def test_action_command_persists_fixture_change_and_reveals_yield_items(tmp_path):
    source_id = "zone:gate:fixture:gate_corroded_hinges"
    proposal = _challenge_proposal(
        approach_label="Oderwanie skorodowanych zawiasów",
        approach_tags=["rusted_hinge", "lever"],
        ability="dexterity",
        skill="acrobatics",
        difficulty_tier="hard",
        difficulty_reason="Wartości LLM zostaną zastąpione polityką fixture'a.",
        dc=18,
        progress_on_success=1,
        progress_on_failure=1,
        consequences=[],
        player_narration="Bohater próbuje oderwać skorodowane zawiasy od bramy.",
    )
    client = FakeFixtureActionGmClient(proposal, source_id, "detach")
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=client,
        session_id="fixture_action_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    preview = session.submit_action("/akcja odrywam skorodowane zawiasy od bramy")

    assert preview["pending"]["fixture_action"]["source_id"] == source_id
    assert preview["pending"]["fixture_action"]["operation"] == "detach"
    assert preview["pending"]["option"]["dc"] == 12
    assert preview["pending"]["option"]["progress_on_success"] == 2
    assert client.requests[0].selected_fixture_source_id == source_id
    with pytest.raises(ValueError, match="wynikają z contentu"):
        session.update_pending_challenge_decision({"dc": 5})

    session.decide("accept", lead_actor_id="hero")
    resolved = session.resolve_rolls({"hero": 20})

    assert session.state.fixture_states[0].condition == "detached"
    assert session.state.fixture_states[0].detached is True
    metal = next(item for item in resolved["discovered_sources"] if item["label"] == "Metalowy element")
    assert metal["quantity"] == 2
    registry = build_crafting_source_registry(session.state, session.exploration.actors)
    assert registry.source_by_id(source_id).usable is False
    assert resolved["messages"][-1]["title"] == "Zmiana obiektu"
    assert "corroded → detached" in resolved["messages"][-1]["body"]


def test_mixed_search_and_direct_use_routes_to_improvised_action_not_observation(tmp_path):
    proposal = _challenge_proposal(
        selected_mechanic="improvised_tool_check",
        approach_label="Sięgnięcie do rygla deską",
        approach_tags=["lever", "quiet"],
        ability="dexterity",
        skill="sleight_of_hand",
        player_narration="Bohater wsuwają długą deskę przez szczelinę i próbuje unieść rygiel.",
        improvised_tool={
            "label": "Długa deska",
            "source": "interaction_object",
            "source_detail": "Drewniana deska leżąca przy bramie",
            "effect_modifier": -1,
            "risk": "Spróchniałe drewno może pęknąć.",
            "reason": "Widoczna długa deska może posłużyć jako prowizoryczny wysięgnik.",
        },
    )
    client = FakeSemanticSourceGmClient(proposal)
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=client,
        session_id="direct_source_use_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    state = session.submit_action(
        "/szukaj szukam cienkiej spróchniałej deski i staram się zdjąć rygiel przez szparę"
    )

    assert state["pending"]["kind"] == "source_selection"
    assert state["pending"]["source_selection"]["candidates"][0]["label"] == "Drewniana deska"
    assert state["discovered_sources"] == []

    accepted = session.decide(
        "accept",
        source_id="zone:gate:item:gate_rotten_planks",
    )

    assert accepted["pending"] is None
    assert accepted["discovered_sources"][0]["label"] == "Drewniana deska"
    assert accepted["discovered_sources"][0]["inventory"] is False
    assert all(resource["id"] != "zone:gate:item:gate_rotten_planks" for resource in accepted["resources"])
    assert client.requests == []


def test_semantic_source_query_answers_naturally_when_scene_has_no_match(tmp_path):
    client = FakeSemanticSourceGmClient(
        _challenge_proposal(),
        required_properties=("container", "metallic"),
        preferred_properties=(),
    )
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=client,
        session_id="functional_source_no_match_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    state = session.submit_action("/szukaj szukam metalowego pojemnika na wodę")

    assert state["pending"] is None
    assert state["messages"][-1]["title"] == "Odpowiedź MG"
    assert "nie ma teraz elementu" in state["messages"][-1]["body"]
    assert client.requests == []


def test_functional_stick_wording_is_grounded_to_visible_plank_for_direct_use(tmp_path):
    proposal = _challenge_proposal(
        selected_mechanic="improvised_tool_check",
        approach_label="Manipulowanie ryglem prowizorycznym wysięgnikiem",
        approach_tags=["lever", "quiet"],
        ability="dexterity",
        skill="sleight_of_hand",
        player_narration="Bohater używa długiej deski jak kija i próbuje dosięgnąć rygla.",
        improvised_tool={
            "label": "Deska jako wysięgnik",
            "source": "interaction_object",
            "source_detail": "Drewniana deska leżąca przy bramie",
            "effect_modifier": -1,
            "risk": "Spróchniała deska może się złamać.",
            "reason": "Długa i sztywna deska może pełnić funkcję kija.",
        },
    )
    client = FakeSemanticSourceGmClient(proposal)
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=client,
        session_id="functional_source_property_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    state = session.submit_action("szukam jakiegoś kija, którym mógłbym zdjąć rygiel przez szparę")

    assert state["pending"]["kind"] == "source_selection"
    assert state["pending"]["source_selection"]["requested_name"] == "kij"
    assert state["pending"]["source_selection"]["candidates"][0]["label"] == "Drewniana deska"
    assert client.requests == []


def test_slash_help_is_answered_locally_without_calling_gm(tmp_path):
    client = FakeQuestionGmClient()
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=client,
        session_id="slash_help_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    state = session.submit_action("/pomoc")

    assert client.requests == []
    assert state["messages"][-1]["title"] == "Dostępne komendy"
    assert "/zbuduj" in state["messages"][-1]["body"]


def test_graded_gate_observation_reveals_only_information_tiers_reached(tmp_path):
    client = FakeObservationGmClient()
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=client,
        session_id="graded_observation_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    proposed = session.submit_action("/pytaj chcę zajrzeć przez szczelinę i sprawdzić, czy ktoś stoi za bramą")

    assert proposed["pending"]["kind"] == "observation"
    assert proposed["pending"]["observation"]["thresholds"] == [10, 15, 20]
    assert "goblin" not in proposed["messages"][-1]["body"].lower()

    rolling = session.decide("accept", lead_actor_id="hero")
    assert rolling["pending"]["stage"] == "roll"
    resolved = session.resolve_rolls({"hero": 16})

    assert resolved["pending"] is None
    assert scene_flag(session.state.flags, "courtyard_activity_suspected", False) is True
    assert scene_flag(session.state.flags, "gate_goblins_spotted", False) is True
    assert scene_flag(session.state.flags, "gate_goblins_positions_known", False) is False
    assert resolved["messages"][-1]["title"] == "Wynik rozpoznania"
    assert "dwie niewielkie" in resolved["messages"][-1]["body"]
    assert resolved["active_challenge"]["current_progress"] == 0


def test_action_through_gap_routes_to_authored_observation_before_generic_classifier(tmp_path):
    client = FakeObservationGmClient()
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=client,
        session_id="observation_action_routing_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    state = session.submit_action(
        "/akcja najpierw chcę spróbować zerknąć przez szparę w deskach, "
        "czy nikt tam nie stoi i co w ogóle widać, robię to cicho"
    )

    assert state["pending"]["kind"] == "observation"
    assert state["pending"]["observation"]["id"] == "look_through_gate_gap"
    assert state["pending"]["observation"]["thresholds"] == [10, 15, 20]
    assert client.requests == []
    assert not any("dc_policy" in message["body"] for message in state["messages"])


def test_exact_gate_reconnaissance_grants_and_consumes_initiative_advantage(tmp_path):
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeObservationGmClient(),
        session_id="reconnaissance_initiative_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.submit_action("/pytaj zaglądam przez szczelinę i obserwuję gobliny")
    session.decide("accept", lead_actor_id="hero")
    session.resolve_rolls({"hero": 20})

    edge = session.state.encounter_edges[0]
    assert edge.beneficiary_actor_id == "hero"
    assert edge.encounter_trigger_id == "gate_open_skirmish"
    assert edge.consumed is False
    assert {
        "label": "Przewaga na inicjatywę",
        "value": "Bohater — Rozpoznane pozycje goblinów",
    } in session.state_payload()["scene_status"]

    session.state = replace(
        session.state,
        flags=set_scene_flag(session.state.flags, "gate_passed", True),
    )
    session.state_payload()
    opening = session.resolve_encounter_opening()
    assert opening["pending_encounter"]["opening"]["outcome"] == "party_surprises_enemies"
    session.start_encounter_setup()
    while session.encounter_setup_flow is not None and not session.encounter_setup_flow.completed:
        if session.encounter_setup_flow.is_player_start_step:
            session.assign_encounter_player_start_position(
                session.encounter_setup_flow.remaining_player_start_positions()[0]
            )
        else:
            session.confirm_encounter_setup_step()

    session.finish_precombat_stealth()
    state = session.start_encounter_initiative()

    assert state["encounter_initiative"]["current_prompt"]["actor_id"] == "hero"
    assert state["encounter_initiative"]["current_prompt"]["roll_mode"] == "advantage"
    assert state["encounter_initiative"]["current_prompt"]["requires_second_roll"] is True
    assert state["encounter_initiative"]["current_prompt"]["encounter_edge"]["label"] == (
        "Rozpoznane pozycje goblinów"
    )

    state = session.submit_encounter_initiative_roll(4, 17)

    assert state["encounter_initiative"]["entries"][0]["natural_roll"] == 17
    assert session.state.encounter_edges[0].consumed is True

    while session.combat_state is None:
        session.submit_encounter_initiative_roll(10)
    for actor in tuple(session.combat_state.actors):
        if actor.faction == Faction.ENEMY:
            session.combat_state = replace_actor(session.combat_state, replace(actor, hp=0))

    resolved = session.resolve_active_combat()

    assert any(point["id"] == "wounded_scout" for point in resolved["visible_points"])


def test_quiet_gate_opening_gives_enemies_initiative_disadvantage(tmp_path):
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        session_id="quiet_gate_surprise_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.state = replace(
        session.state,
        flags=set_scene_flag(session.state.flags, "gate_passed", True),
    )
    session.state_payload()

    opening = session.resolve_encounter_opening()
    assert opening["pending_encounter"]["opening"]["outcome"] == "party_surprises_enemies"

    session.start_encounter_setup()
    while session.encounter_setup_flow is not None and not session.encounter_setup_flow.completed:
        if session.encounter_setup_flow.is_player_start_step:
            session.assign_encounter_player_start_position(
                session.encounter_setup_flow.remaining_player_start_positions()[0]
            )
        else:
            session.confirm_encounter_setup_step()
    session.finish_precombat_stealth()
    session.start_encounter_initiative()
    for roll in (20, 19, 18):
        session.submit_encounter_initiative_roll(roll)

    state = session.state_payload()
    enemy_entries = [
        entry
        for entry in state["encounter_initiative"]["order"]
        if entry["actor_id"] in {"goblin_a", "goblin_b"}
    ]
    assert len(enemy_entries) == 2
    assert all(entry["roll_mode"] == "disadvantage" for entry in enemy_entries)
    assert all(len(entry["natural_rolls"]) == 2 for entry in enemy_entries)


def test_precombat_stealth_roll_becomes_per_observer_hidden_state_in_combat(tmp_path):
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        session_id="precombat_stealth_bridge_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.state = replace(
        session.state,
        flags=set_scene_flag(session.state.flags, "gate_passed", True),
    )
    session.state_payload()
    session.resolve_encounter_opening()
    session.start_encounter_setup()
    while session.encounter_setup_flow is not None and not session.encounter_setup_flow.completed:
        if session.encounter_setup_flow.is_player_start_step:
            session.assign_encounter_player_start_position(
                session.encounter_setup_flow.remaining_player_start_positions()[0]
            )
        else:
            session.confirm_encounter_setup_step()

    before = session.state_payload()["encounter_stealth"]
    rogue = next(actor for actor in before["actors"] if actor["actor_id"] == "rogue")
    assert rogue["modifier"] == 7
    assert rogue["can_attempt"] is True

    rolled = session.submit_precombat_stealth_roll(actor_id="rogue", natural_roll=15)
    rogue_result = next(
        actor for actor in rolled["encounter_stealth"]["actors"] if actor["actor_id"] == "rogue"
    )["result"]
    assert rogue_result["total"] == 22
    assert {item["actor_id"] for item in rogue_result["hidden_from"]} == {"goblin_a", "goblin_b"}

    session.finish_precombat_stealth()
    session.start_encounter_initiative()
    for roll in (20, 19, 18):
        session.submit_encounter_initiative_roll(roll)

    assert session.combat_state is not None
    assert session.combat_state.hidden_states == (
        HiddenState("rogue", 22, ("goblin_a", "goblin_b")),
    )


def test_enemy_ambush_gives_party_initiative_disadvantage(tmp_path):
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        session_id="gate_party_disadvantage_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.state = replace(
        session.state,
        flags=set_scene_flag(session.state.flags, "gate_passed", True),
        challenge_states=(ExplorationChallengeState(challenge_id="closed_gate", noise=3),),
    )
    session.state_payload()
    opening = session.resolve_encounter_opening()
    assert opening["pending_encounter"]["opening"]["outcome"] == "enemies_surprise_party"

    session.start_encounter_setup()
    while session.encounter_setup_flow is not None and not session.encounter_setup_flow.completed:
        if session.encounter_setup_flow.is_player_start_step:
            session.assign_encounter_player_start_position(
                session.encounter_setup_flow.remaining_player_start_positions()[0]
            )
        else:
            session.confirm_encounter_setup_step()

    state = session.start_encounter_initiative()

    assert state["encounter_initiative"]["current_prompt"]["roll_mode"] == "disadvantage"
    assert state["encounter_initiative"]["current_prompt"]["requires_second_roll"] is True


def test_conversation_is_scoped_to_interaction_and_reused_as_gm_context(tmp_path):
    client = FakeQuestionGmClient()
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=client,
        session_id="conversation_scope_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    session.submit_action("Czy możemy zbudować z tych desek taran?")
    second = session.submit_action("Czy taki taran będzie głośny?")

    assert second["conversation"]["interaction_id"] == "challenge:closed_gate"
    assert [entry["role"] for entry in second["conversation"]["entries"]] == ["player", "gm", "player", "gm"]
    assert [entry.role for entry in client.requests[1].declaration_thread] == ["player", "gm"]
    session.active_point_id = "wounded_scout"
    assert session.state_payload()["conversation"] == {
        "interaction_id": "point:wounded_scout",
        "entries": [],
    }
    session.active_point_id = ""
    assert len(session.state_payload()["conversation"]["entries"]) == 4


def test_snapshot_restores_interaction_conversation(tmp_path):
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeQuestionGmClient(),
        session_id="conversation_snapshot_test",
        observation_dir=tmp_path / "observations",
        save_dir=tmp_path / "saves",
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.submit_action("Czy możemy zbudować taran?")
    expected = session.state_payload()["conversation"]
    session.save_snapshot()
    session.conversation_entries = []

    restored = session.load_snapshot()

    assert restored["conversation"] == expected


def test_conversational_gm_progresses_hints_and_persists_their_context(tmp_path):
    client = FakeHintGmClient()
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=client,
        session_id="progressive_hint_test",
        observation_dir=tmp_path / "observations",
        save_dir=tmp_path / "saves",
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    first = session.submit_action("Potrzebujemy podpowiedzi.")
    second = session.submit_action("Możesz podpowiedzieć trochę więcej?")
    third = session.submit_action("Powiedz nam konkretne rozwiązanie wprost.")

    gm_entries = [entry for entry in third["conversation"]["entries"] if entry["role"] == "gm"]
    assert [entry["hint_level"] for entry in gm_entries] == [1, 2, 3]
    assert all(entry["grounded_fact_ids"] for entry in gm_entries)
    assert first["messages"][-1]["title"] == "Podpowiedź MG"
    assert second["pending"] is None
    assert third["required_rolls"] == []
    assert client.requests[1].declaration_thread[-1].hint_level == 1

    expected = third["conversation"]
    session.save_snapshot()
    session.conversation_entries = []
    restored = session.load_snapshot()

    assert restored["conversation"] == expected


def test_pytaj_can_naturally_return_a_grounded_approach_hint(tmp_path):
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeMismatchedQuestionGmClient(),
        session_id="unified_question_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    state = session.submit_action("/pytaj jaki jest stan bramy, można ją wyważyć?")

    assert state["pending"] is None
    assert state["messages"][-1]["title"] == "Podpowiedź MG"
    assert "hint_level" not in state["messages"][-1]["body"]
    assert state["messages"][-1]["body"] == "Tak, ale wyważanie jest głośne."
    assert state["conversation"]["entries"][-1]["hint_level"] == 1


def test_exploration_ui_session_turns_validation_error_into_visible_gm_message(tmp_path):
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeInvalidFactGmClient(),
        session_id="invalid_fact_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    state = session.submit_action("Używam działa laserowego.")

    assert state["pending"] is None
    assert state["messages"][-1]["title"] == "Deklaracja wymaga korekty"
    assert "działo laserowe" in state["messages"][-1]["body"]
    events = [__import__("json").loads(line) for line in session.observer.path.read_text(encoding="utf-8").splitlines()]
    assert any(event["event_type"] == "ui_gm_declaration_rejected" for event in events)


def test_exploration_ui_session_creates_and_uses_temporary_scene_item(tmp_path):
    preparation = _challenge_proposal(
        action_flow="preparation",
        requires_roll_now=False,
        selected_mechanic="preparation_effect",
        approach_label="Budowa prowizorycznego taranu",
        approach_tags=["heavy_force"],
        ability=None,
        skill=None,
        dc=None,
        difficulty_tier=None,
        progress_on_success=None,
        progress_on_failure=None,
        preparation_effect={
            "type": "create_temporary_item",
            "label": "Prowizoryczny taran",
            "target_tags": ["heavy_force"],
            "crafting_draft": {
                "label": "Prowizoryczny taran",
                "description": "Długa deska obciążona kamieniem.",
                "purpose_id": "heavy_force",
                "components": [
                    {"source_id": "zone:gate:item:gate_rotten_planks", "quantity": 1},
                    {"source_id": "zone:gate:item:gate_loose_stones", "quantity": 1},
                ],
            },
        },
    )
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(preparation),
        session_id="temporary_item_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    prepared = session.submit_action("/zbuduj taran do późniejszego użycia")

    assert prepared["pending"]["kind"] == "crafting"
    prepared = session.decide("accept")
    assert prepared["resources"][-1]["id"] == "temporary:crafted:1"
    assert prepared["resources"][-1]["uses_remaining"] == 2
    session.gm_client = FakeGmClient(
        _challenge_proposal(used_resource_ids=["temporary:crafted:1"])
    )
    session.submit_action("Uderzam przygotowanym taranem w bramę.")
    session.decide("accept")
    resolved = session.resolve_rolls({"hero": 16})

    temporary = next(item for item in session.state.temporary_items if item.id == "temporary:crafted:1")
    assert temporary.uses_remaining == 1
    assert any(message["title"] == "Użyto przedmiotu sceny" for message in resolved["messages"])
    events = [__import__("json").loads(line) for line in session.observer.path.read_text(encoding="utf-8").splitlines()]
    assert any(event["event_type"] == "ui_crafting_confirmed" for event in events)
    assert any(event["event_type"] == "ui_temporary_item_used" for event in events)


def test_exploration_ui_session_confirms_dynamic_crafting_before_spending_costs(tmp_path):
    preparation = _challenge_proposal(
        action_flow="preparation",
        requires_roll_now=False,
        selected_mechanic="preparation_effect",
        approach_label="Budowa prowizorycznego taranu",
        approach_tags=["heavy_force"],
        ability=None,
        skill=None,
        dc=None,
        difficulty_tier=None,
        progress_on_success=None,
        progress_on_failure=None,
        preparation_effect={
            "type": "create_temporary_item",
            "label": "Prowizoryczny taran",
            "target_tags": ["heavy_force"],
            "crafting_draft": {
                "label": "Prowizoryczny taran",
                "description": "Długa deska obciążona luźnym kamieniem.",
                "purpose_id": "heavy_force",
                "components": [
                    {"source_id": "zone:gate:item:gate_rotten_planks", "quantity": 1},
                    {"source_id": "zone:gate:item:gate_loose_stones", "quantity": 1},
                ],
            },
        },
    )
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(preparation),
        session_id="dynamic_crafting_confirmation_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    proposed = session.submit_action("Buduję taran z deski i kamienia.")

    assert proposed["pending"]["kind"] == "crafting"
    assert proposed["pending"]["crafting"]["requires_build_roll"] is False
    assert proposed["pending"]["crafting"]["time_cost_minutes"] == 10
    assert proposed["pending"]["crafting"]["uses"] == 2
    assert session.state.temporary_items == ()
    assert session.state.elapsed_minutes == 0

    crafted = session.decide("accept")

    assert crafted["pending"] is None
    assert session.state.elapsed_minutes == 10
    assert session.state.temporary_items[-1].purpose_id == "heavy_force"
    assert crafted["resources"][-1]["id"] == "temporary:crafted:1"
    assert crafted["resources"][-1]["component_uses"][0]["disposition"] == "consumed"
    assert "Budowa nie wymagała rzutu" in crafted["messages"][-1]["body"]
    events = [__import__("json").loads(line) for line in session.observer.path.read_text(encoding="utf-8").splitlines()]
    assert any(event["event_type"] == "ui_crafting_confirmed" for event in events)

    dismantled = session.dismantle_temporary_item("temporary:crafted:1")

    assert all(resource["id"] != "temporary:crafted:1" for resource in dismantled["resources"])
    assert session.state.temporary_items[-1].dismantled is True
    events = [__import__("json").loads(line) for line in session.observer.path.read_text(encoding="utf-8").splitlines()]
    assert any(event["event_type"] == "ui_crafting_dismantled" for event in events)


def test_exploration_ui_session_can_reject_dynamic_crafting_without_state_change(tmp_path):
    preparation = _challenge_proposal(
        action_flow="preparation",
        requires_roll_now=False,
        selected_mechanic="preparation_effect",
        approach_label="Budowa prowizorycznej dźwigni",
        approach_tags=["lever"],
        ability=None,
        skill=None,
        dc=None,
        difficulty_tier=None,
        progress_on_success=None,
        progress_on_failure=None,
        preparation_effect={
            "type": "create_temporary_item",
            "label": "Prowizoryczna dźwignia",
            "target_tags": ["lever"],
            "crafting_draft": {
                "label": "Prowizoryczna dźwignia",
                "description": "Długa deska podparta klinem.",
                "purpose_id": "leverage",
                "components": [
                    {"source_id": "zone:gate:item:gate_rotten_planks", "quantity": 1},
                    {"source_id": "resource:wedge", "quantity": 1},
                ],
            },
        },
    )
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(preparation),
        session_id="dynamic_crafting_rejection_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.submit_action("Buduję dźwignię.")

    rejected = session.decide("reject")

    assert rejected["pending"] is None
    assert session.state.temporary_items == ()
    assert session.state.elapsed_minutes == 0


def test_invalid_crafting_requirements_are_explained_without_technical_property_ids(tmp_path):
    invalid_preparation = _challenge_proposal(
        action_flow="preparation",
        requires_roll_now=False,
        selected_mechanic="preparation_effect",
        approach_label="Budowa dźwigni z samej deski",
        approach_tags=["lever"],
        ability=None,
        skill=None,
        dc=None,
        difficulty_tier=None,
        progress_on_success=None,
        progress_on_failure=None,
        preparation_effect={
            "type": "create_temporary_item",
            "label": "Prowizoryczna dźwignia",
            "target_tags": ["lever"],
            "crafting_draft": {
                "label": "Prowizoryczna dźwignia",
                "description": "Próba zbudowania dźwigni z samej spróchniałej deski.",
                "purpose_id": "leverage",
                "auto_select_missing_components": False,
                "components": [
                    {"source_id": "zone:gate:item:gate_rotten_planks", "quantity": 1}
                ],
            },
        },
    )
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(invalid_preparation),
        session_id="natural_crafting_error_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    state = session.submit_action("/zbuduj robię dźwignię z samej deski")

    message = state["messages"][-1]["body"]
    assert "[prying, hard]" not in message
    assert "nadającego się do podważania" in message
    assert "użyć tego materiału bezpośrednio" in message


def test_exploration_ui_session_repairs_legacy_shaped_explicit_build_to_dynamic_crafting(tmp_path):
    proposal = _challenge_proposal(
        action_flow="preparation",
        requires_roll_now=False,
        selected_mechanic="preparation_effect",
        approach_label="Budowa prowizorycznego taranu",
        approach_tags=["heavy_force"],
        ability=None,
        skill=None,
        dc=None,
        difficulty_tier=None,
        progress_on_success=None,
        progress_on_failure=None,
        preparation_effect={
            "type": "create_temporary_item",
            "label": "Prowizoryczny taran",
            "target_tags": ["heavy_force"],
            "source_materials": ["stare deski", "metalowe okucia"],
        },
    )
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(proposal),
        session_id="temporary_item_grounding_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    state = session.submit_action("/zbuduj prowizoryczny taran")

    assert state["pending"]["kind"] == "crafting"
    assert state["pending"]["crafting"]["auto_selected_components"] is True
    state = session.decide("accept")
    assert state["resources"][-1]["id"] == "temporary:crafted:1"
    assert state["messages"][-1]["title"] == "Utworzono przedmiot sceny"
    events = [__import__("json").loads(line) for line in session.observer.path.read_text(encoding="utf-8").splitlines()]
    assert any(event["event_type"] == "ui_gm_proposal_grounded" for event in events)


def test_exploration_ui_session_expires_temporary_items_at_scenario_end(tmp_path):
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(_challenge_proposal()),
        session_id="temporary_item_expiration_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    draft = CraftingDraft(
        label="Prowizoryczny taran",
        description="Długa deska obciążona kamieniem.",
        purpose_id="heavy_force",
        components=(
            CraftingComponentSelection("zone:gate:item:gate_rotten_planks"),
            CraftingComponentSelection("zone:gate:item:gate_loose_stones"),
        ),
    )
    session.state, _item = craft_temporary_item(
        session.state,
        draft,
        build_crafting_source_registry(session.state, session.exploration.actors),
        session.exploration.crafting_policy,
    )

    completed = session.finish_scenario()

    assert session.state.temporary_items == ()
    assert not any(resource.get("temporary") for resource in completed["resources"])
    events = [__import__("json").loads(line) for line in session.observer.path.read_text(encoding="utf-8").splitlines()]
    event = next(item for item in events if item["event_type"] == "ui_scenario_completed")
    assert event["payload"]["expired_temporary_item_ids"] == ["temporary:crafted:1"]


def test_exploration_ui_session_can_correct_gm_decision_before_roll():
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(_challenge_proposal()),
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.submit_action("Wyważamy bramę z pomocą.")

    corrected = session.update_pending_challenge_decision(
        {
            "mechanic_id": "lead_with_help_check",
            "check_participants": "lead_with_help",
            "check_aggregation": "lead_result",
            "lead_actor_id": "rogue",
            "helper_actor_id": "hero",
            "ability": "dexterity",
            "skill": "acrobatics",
            "dc": 13,
        }
    )

    option = corrected["pending"]["option"]
    assert option["mechanic"]["id"] == "lead_with_help_check"
    assert option["check_participants"] == "lead_with_help"
    assert option["ability"] == "dexterity"
    assert option["skill"] == "acrobatics"
    assert option["dc"] == 13
    assert corrected["selected_lead_actor_id"] == "rogue"
    assert corrected["selected_helper_actor_id"] == "hero"

    accepted = session.decide("accept")

    assert [roll["actor_id"] for roll in accepted["required_rolls"]] == ["rogue", "hero"]
    assert all(roll["die_sides"] == 20 and roll["label"] == "d20" for roll in accepted["required_rolls"])
    plan = accepted["pending"]["check_plan"]
    assert plan["lead_actor_id"] == "rogue"
    assert plan["helper_actor_id"] == "hero"
    assert plan["mechanic"]["id"] == "lead_with_help_check"


def test_exploration_ui_session_rejects_same_lead_and_helper_for_correction():
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(_challenge_proposal()),
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.submit_action("Wyważamy bramę z pomocą.")

    with pytest.raises(ValueError, match="Pomocnik musi być inną postacią"):
        session.update_pending_challenge_decision(
            {
                "mechanic_id": "lead_with_help_check",
                "check_participants": "lead_with_help",
                "check_aggregation": "lead_result",
                "lead_actor_id": "hero",
                "helper_actor_id": "hero",
                "ability": "strength",
                "skill": "athletics",
                "dc": 15,
            }
        )


def test_exploration_ui_session_corrects_situational_modifier_and_disadvantage_roll():
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(_challenge_proposal()),
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.submit_action("W deszczu wspinam się po mokrej linie.")

    corrected = session.update_pending_challenge_decision(
        {
            "mechanic_id": "single_actor_check",
            "check_participants": "single_actor",
            "check_aggregation": "lead_result",
            "lead_actor_id": "hero",
            "ability": "strength",
            "skill": "athletics",
            "dc": 15,
            "roll_mode": "normal",
            "situational_modifiers": [
                {
                    "label": "Mokra lina",
                    "modifier": -1,
                    "source": "interaction_object",
                    "reason": "Opis obiektu wskazuje mokrą linę.",
                    "roll_mode": "disadvantage",
                }
            ],
        }
    )

    option = corrected["pending"]["option"]
    assert option["roll_mode"] == "disadvantage"
    assert option["situational_modifiers"][0]["modifier"] == -1

    accepted = session.decide("accept")

    roll = accepted["required_rolls"][0]
    assert roll["actor_id"] == "hero"
    assert roll["actor_name"] == "Bohater"
    assert roll["die_sides"] == 20
    assert roll["label"] == "d20"
    assert roll["roll_mode"] == "disadvantage"
    assert roll["requires_second_roll"] is True
    plan = accepted["pending"]["check_plan"]
    assert plan["roll_mode"] == "disadvantage"
    assert plan["situational_modifiers"][0]["label"] == "Mokra lina"

    resolved = session.resolve_rolls({"hero": {"natural_roll": 18, "natural_roll_2": 7}})

    assert resolved["pending"] is None
    assert session.pending is None


def test_exploration_ui_session_corrects_improvised_tool_before_roll():
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(_challenge_proposal()),
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.submit_action("Używam starej deski jak dźwigni.")

    corrected = session.update_pending_challenge_decision(
        {
            "mechanic_id": "improvised_tool_check",
            "check_participants": "single_actor",
            "check_aggregation": "lead_result",
            "lead_actor_id": "hero",
            "ability": "strength",
            "skill": "athletics",
            "dc": 15,
            "roll_mode": "normal",
            "situational_modifiers": [],
            "improvised_tool": {
                "label": "Stara deska",
                "source": "interaction_object",
                "source_detail": "rumowisko przy bramie",
                "effect_modifier": 1,
                "risk": "może pęknąć przy krytycznej porażce",
                "reason": "Opis sceny zawiera stare deski, które mogą działać jak prowizoryczna dźwignia.",
            },
        }
    )

    option = corrected["pending"]["option"]
    assert option["mechanic"]["id"] == "improvised_tool_check"
    assert option["improvised_tool"]["label"] == "Stara deska"
    assert option["improvised_tool"]["effect_modifier"] == 1

    accepted = session.decide("accept")

    plan = accepted["pending"]["check_plan"]
    assert plan["improvised_tool"]["label"] == "Stara deska"
    assert plan["mechanic"]["id"] == "improvised_tool_check"


def test_exploration_ui_session_applies_item_bonus_and_breaks_item_after_critical_failure():
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(_challenge_proposal()),
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    challenge = next(item for item in session.state.challenges if item.id == "closed_gate")
    option = next(item for item in challenge.options if item.id == "lockpick_gate")
    session.pending = PendingInteraction(
        kind=PendingKind.CHALLENGE,
        stage=PendingStage.DECISION,
        proposal=_challenge_proposal(),
        challenge=challenge,
        option=option,
    )

    accepted = session.decide("accept", lead_actor_id="hero")

    required = accepted["required_rolls"][0]
    assert required["actor_id"] == "rogue"
    assert required["actor_name"] == "Łotrzyca"
    assert required["modifier_total"] == 5
    assert [(item["label"], item["value"]) for item in required["active_modifiers"]] == [
        ("Zręczność", 3),
        ("Biegłość: Narzędzia złodziejskie", 2),
    ]
    plan = accepted["pending"]["check_plan"]
    assert plan["skill"] is None
    assert plan["tool"] == "thieves_tools"
    assert plan["tool_label"] == "Narzędzia złodziejskie"
    assert plan["option_bonuses"][0]["source_id"] == "thieves_tools"
    assert plan["option_bonuses"][0]["modifier"] == 0

    after_roll = session.resolve_rolls({"rogue": 1})

    assert after_roll["pending"]["stage"] == "breakage"
    assert after_roll["required_rolls"] == [{"actor_id": "rogue", "actor_name": "Łotrzyca", "die_sides": 100, "label": "k100 trwałości"}]
    assert after_roll["pending"]["breakage"]["chance_percent"] == 25

    after_breakage = session.resolve_rolls({"rogue": 12})

    assert after_breakage["pending"] is None
    rogue = next(actor for actor in after_breakage["actors"] if actor["id"] == "rogue")
    thieves_tools = next(item for item in rogue["inventory"] if item["id"] == "thieves_tools")
    assert thieves_tools["broken"] is True
    assert thieves_tools["available"] is False


def test_exploration_ui_session_consumes_leveled_spell_slot_for_exploration_bonus():
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(_challenge_proposal()),
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    challenge = next(item for item in session.state.challenges if item.id == "closed_gate")
    option = next(item for item in challenge.options if item.id == "reveal_bolt_with_flame")
    option = replace(
        option,
        requires_spell_ids=("healing_word",),
        bonuses=(
            replace(
                option.bonuses[0],
                source_id="healing_word",
                spell_level=1,
            ),
        ),
    )
    session.pending = PendingInteraction(
        kind=PendingKind.CHALLENGE,
        stage=PendingStage.DECISION,
        proposal=_challenge_proposal(),
        challenge=challenge,
        option=option,
    )

    accepted = session.decide("accept", lead_actor_id="hero")

    assert accepted["required_rolls"][0]["actor_id"] == "cleric"
    assert accepted["required_rolls"][0]["actor_name"] == "Kapłan"
    assert accepted["required_rolls"][0]["die_sides"] == 20
    assert accepted["pending"]["check_plan"]["option_bonuses"][0]["spell_level"] == 1

    resolved = session.resolve_rolls({"cleric": 12})

    cleric = next(actor for actor in resolved["actors"] if actor["id"] == "cleric")
    assert cleric["spell_slots"][0]["remaining"] == 1
    assert any(message["title"] == "Zużyty slot czaru" for message in resolved["messages"])


def test_exploration_ui_session_pending_encounter_waits_for_ui_setup_not_board_click():
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(_challenge_proposal()),
    )
    board = FakeBoardConnection()
    session.attach_board_connection(board, backend="simulator")
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    session.submit_action("Wyważamy bramę.")
    session.decide("accept")
    session.resolve_rolls({"hero": 16})
    session.finish_interaction_result()
    state = session.confirm_exploration_setup_step()

    assert state["pending_encounter"]["trigger_id"] == "gate_open_skirmish"
    assert state["board"]["message"] == "Encounter gotowy. Rozstrzygnij rozpoczęcie starcia w UI albo Enterem."
    assert board.led_calls[-1] == ("off", None)

    client = create_app(session).test_client()
    response = client.post("/api/board/scan", json={})

    assert response.status_code == 400
    assert "Encounter czeka na rozstrzygnięcie rozpoczęcia starcia" in response.get_json()["error"]


def test_exploration_ui_session_starts_with_map_setup_before_location_preview():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    session.confirm_spell_preparation(
        actor_id="cleric",
        spell_ids=("healing_word", "bless_attack_bonus"),
    )
    session.attach_board_connection(FakeBoardConnection(), backend="simulator")

    state = session.start_session()

    assert state["flow"]["stage"] == "party_setup"
    assert state["exploration_setup"]["current_step"]["label"] == "elementy mapy"
    assert state["exploration_setup"]["current_step"]["has_positions"] is False
    assert state["exploration_setup"]["current_step"]["color"] is None

    while session.exploration_setup_flow is not None:
        state = session.confirm_exploration_setup_step()

    assert state["flow"]["stage"] == "location_preview"
    assert state["exploration_setup"] is None


def test_exploration_ui_session_requires_spell_preparation_before_scenario_setup():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    board = FakeBoardConnection()

    initial = session.state_payload()

    assert initial["flow"]["stage"] == "spell_preparation"
    assert initial["spell_preparation"]["current_actor_id"] == "cleric"
    cleric = initial["spell_preparation"]["actors"][0]
    assert cleric["preparation_limit"] == 2
    assert cleric["selected_count"] == 2
    assert {spell["id"] for spell in cleric["spells"]} == {
        "radiant_line",
        "healing_word",
        "bless_attack_bonus",
    }

    session.attach_board_connection(board, backend="simulator")
    assert session.state_payload()["flow"]["stage"] == "spell_preparation"

    confirmed = session.confirm_spell_preparation(
        actor_id="cleric",
        spell_ids=("radiant_line", "healing_word"),
    )

    assert confirmed["flow"]["stage"] == "ready_to_start"
    assert confirmed["spell_preparation"]["complete"] is True
    events = [
        __import__("json").loads(line)
        for line in session.observer.path.read_text(encoding="utf-8").splitlines()
    ]
    assert any(record["event_type"] == "ui_spell_preparation_confirmed" for record in events)


def test_exploration_ui_session_completes_short_rest_and_spends_hit_die():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.exploration = replace(
        session.exploration,
        actors=tuple(
            replace(actor, hp=10) if str(actor.id) == "hero" else actor
            for actor in session.exploration.actors
        ),
    )

    preview = session.start_short_rest()

    assert preview["flow"]["stage"] == "short_rest"
    assert preview["short_rest"]["policy"]["safety"] == "contested"
    assert preview["short_rest"]["policy"]["duration_minutes"] == 60
    assert preview["short_rest"]["pending"]["completed"] is False

    completed = session.confirm_short_rest()

    assert completed["short_rest"]["pending"]["completed"] is True
    assert completed["short_rest"]["elapsed_minutes"] == 60
    assert completed["active_challenge"] is None
    assert next(item for item in completed["scene_status"] if item["label"] == "Hałas")["value"] == "niski (2)"
    hero_before_die = next(actor for actor in completed["actors"] if actor["id"] == "hero")
    assert hero_before_die["hp"] == 10

    healed = session.spend_short_rest_hit_die(
        actor_id="hero",
        die_sides=10,
        natural_roll=5,
    )
    hero = next(actor for actor in healed["actors"] if actor["id"] == "hero")

    assert hero["hp"] == 16
    assert hero["hit_dice"][0]["remaining"] == 1

    finished = session.finish_short_rest()

    assert finished["flow"]["stage"] == "location_active"
    assert finished["short_rest"]["available"] is False
    assert "wykorzystana" in finished["short_rest"]["unavailable_reason"]


def test_exploration_ui_session_can_cancel_short_rest_without_advancing_time():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    session.start_short_rest()
    cancelled = session.cancel_short_rest()

    assert cancelled["flow"]["stage"] == "location_active"
    assert cancelled["short_rest"]["elapsed_minutes"] == 0
    assert cancelled["short_rest"]["available"] is True


def test_exploration_ui_session_finishes_scenario_and_expires_daily_effects():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    daily = ActiveEffect(
        id="daily",
        actor_id="hero",
        kind="daily_blessing",
        label="Błogosławieństwo dnia",
        object_id="shrine",
        value=1,
        source=EffectSource(EffectSourceType.SCENE, "shrine", "Kapliczka"),
        duration=EffectDuration.UNTIL_SCENARIO_END,
    )
    permanent = ActiveEffect(
        id="permanent",
        actor_id="hero",
        kind="permanent_mark",
        label="Trwały znak",
        object_id="story",
        value=0,
        source=EffectSource(EffectSourceType.SCENE, "story", "Fabuła"),
        duration=EffectDuration.PERMANENT,
    )
    session.active_combat_effects = (daily, permanent)

    payload = session.finish_scenario()

    assert payload["flow"]["stage"] == "scenario_complete"
    assert [effect["id"] for effect in payload["active_effects"]] == ["permanent"]
    assert any(message["title"] == "Scenariusz zakończony" for message in payload["messages"])


def test_exploration_ui_session_rejects_pending_interpretation():
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(_challenge_proposal()),
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

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
            "effects_on_success": [
                {"type": "set_flag", "parameters": {"key": "scout_calmed", "value": True}},
            ],
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


def test_npc_request_receives_only_that_npc_interaction_history():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "social",
            "player_narration": "Zwiadowca obserwuje drużynę.",
            "npc_response": "Słucham was.",
            "requires_roll": False,
        }
    )
    client = FakeNpcClient(proposal)
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        npc_client=client,
        debug_point_id="wounded_scout",
    )

    session.submit_action("Pytamy zwiadowcę o bramę.")
    session.decide("accept")
    session.submit_action("Wracamy do wcześniejszego pytania.")

    assert len(client.requests) == 2
    assert client.requests[0].conversation_thread == ()
    assert [entry.role for entry in client.requests[1].conversation_thread] == ["player", "gm", "gm"]
    assert client.requests[1].conversation_thread[0].content == "Pytamy zwiadowcę o bramę."


def test_exploration_ui_session_npc_information_sets_flags_without_roll():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "medical",
            "player_narration": "Opatrujecie ranę zwiadowcy.",
            "npc_response": "Zwiadowca odzyskuje oddech i wskazuje ślady.",
            "requires_roll": False,
            "flag_changes_on_success": [{"key": "scout_stabilized", "value": True}],
            "revealed_information_ids": ["tower_hint"],
        }
    )
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        npc_client=FakeNpcClient(proposal),
        debug_point_id="wounded_scout",
    )

    session.submit_action("Opatrujemy zwiadowcę.")
    state = session.decide("accept")

    assert {"key": "scout_stabilized", "value": True} in state["flags"]
    assert {"key": "tower_hint_learned", "value": True} in state["flags"]
    assert any(message["title"] == "Informacja: Wskazówka o wieży" for message in state["messages"])


def test_exploration_ui_session_writes_debug_log_for_npc_effects(tmp_path):
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "social",
            "player_narration": "Mówicie spokojnie.",
            "npc_response": "Zwiadowca przestaje się szarpać.",
            "requires_roll": False,
            "effects_on_success": [
                {"type": "set_flag", "parameters": {"key": "scout_calmed", "value": True}},
            ],
        }
    )
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        npc_client=FakeNpcClient(proposal),
        debug_point_id="wounded_scout",
        session_id="ui_log_test",
        observation_dir=tmp_path,
    )

    session.submit_action("Uspokajamy zwiadowcę.")
    session.decide("accept")

    events = [__import__("json").loads(line) for line in session.observer.path.read_text(encoding="utf-8").splitlines()]
    event_types = [event["event_type"] for event in events]
    effect_event = next(event for event in events if event["event_type"] == "ui_effect_applied")

    assert event_types[:1] == ["ui_session_started"]
    assert "ui_action_submitted" in event_types
    assert "ui_npc_proposal_validated" in event_types
    assert effect_event["payload"]["source"] == "npc_proposal"
    assert effect_event["payload"]["effect"]["parameters"]["key"] == "scout_calmed"
    assert {"key": "scout_calmed", "value": True} in effect_event["payload"]["flags"]

    client = create_app(session).test_client()
    payload = client.get("/api/session-log").get_json()
    assert payload["session_id"] == "ui_log_test"
    assert payload["path"] == str(session.observer.path)
    assert any(event["event_type"] == "ui_effect_applied" for event in payload["events"])


def test_exploration_ui_session_applies_victory_outcome_after_combat():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.state = replace(session.state, flags=set_scene_flag(session.state.flags, "scout_panicked", True))

    state = session.state_payload()
    assert state["pending_encounter"]["trigger_id"] == "scout_panic_alarm"

    session.start_encounter_setup()
    while session.encounter_setup_flow is not None and not session.encounter_setup_flow.completed:
        if session.encounter_setup_flow.is_player_start_step:
            for position in session.encounter_setup_flow.current_step.positions[:2]:
                session.assign_encounter_player_start_position(position)
            continue
        session.confirm_encounter_setup_step()
    session.start_encounter_initiative()
    session.submit_encounter_initiative_roll(15)
    session.submit_encounter_initiative_roll(14)

    assert session.combat_state is not None
    for actor in tuple(session.combat_state.actors):
        if actor.faction == Faction.ENEMY:
            session.combat_state = replace_actor(session.combat_state, replace(actor, hp=0))

    state = session.resolve_active_combat()

    assert state["combat"] is None
    assert state["pending_encounter"] is None
    assert state["flow"]["stage"] == "interaction_result"
    assert {"key": "courtyard_cleared", "value": True} in state["flags"]
    assert any(point["id"] == "wounded_scout" for point in state["flow"]["interaction_result"]["revealed_points"])
    assert any(point["id"] == "wounded_scout" for point in state["visible_points"])

    state = session.finish_interaction_result()
    assert state["pending_encounter"] is None


def test_exploration_ui_session_player_attack_applies_damage_and_uses_action():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_combat_from_scout_alarm(session)

    state = session.state_payload()
    assert state["combat"]["current_actor"]["faction"] == "ally"
    assert state["combat"]["legal_targets"]
    assert state["combat"]["current_actor"]["max_hp"] >= state["combat"]["current_actor"]["hp"]
    assert "temp_hp" in state["combat"]["current_actor"]
    assert "defeated" in state["combat"]["current_actor"]
    assert state["combat"]["turn_action"]["bonus_action_use"] == "action_available"
    assert state["combat"]["turn_action"]["reaction_available"] is True
    target_id = state["combat"]["legal_targets"][0]["id"]

    state = session.submit_player_attack(
        target_id=target_id,
        natural_roll=20,
        natural_roll_2=20,
        damage=5,
    )

    damaged = next(actor for actor in state["combat"]["actors"] if actor["id"] == target_id)
    assert damaged["hp"] < 7
    assert damaged["max_hp"] >= damaged["hp"]
    assert damaged["defeated"] is False
    assert state["combat"]["turn_action"]["action_use"] == "action_used"
    assert any(message["title"] == "Atak" and "trafia krytycznie" in message["body"] for message in state["messages"])
    assert any(message["title"] == "Atak" and "HP" in message["body"] for message in state["messages"])


def test_exploration_ui_keeps_weapon_targets_visible_between_extra_attacks():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_combat_from_scout_alarm(session)
    assert session.combat_state is not None
    hero = current_actor(session.combat_state)
    session.combat_state = replace_actor(
        session.combat_state,
        replace(hero, attacks_per_action=2),
    )
    initial = session.state_payload()
    target_id = initial["combat"]["legal_targets"][0]["id"]

    after_first = session.submit_player_attack(
        target_id=target_id,
        natural_roll=20,
        natural_roll_2=20,
        damage=1,
    )

    assert after_first["combat"]["turn_action"]["attacks_remaining"] == 1
    assert after_first["combat"]["legal_targets"]
    assert any(
        option.action.value == "select_attack_source"
        for option in session._combat_context_options(
            current_actor(session.combat_state),
            current_actor(session.combat_state).position,
        )
    )

    after_second = session.submit_player_attack(
        target_id=target_id,
        natural_roll=20,
        natural_roll_2=20,
        damage=1,
    )

    assert after_second["combat"]["turn_action"]["attacks_remaining"] == 0


def test_exploration_ui_session_board_click_on_enemy_prompts_manual_attack_and_damage_rolls():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_combat_from_scout_alarm(session)
    state = session.state_payload()
    target = state["combat"]["legal_targets"][0]
    session.attach_board_connection(FakeBoardConnection(clicks=[tuple(target["position"])]), backend="simulator")

    selected = session.scan_board_selection()

    assert selected["combat"]["pending_player_attack"] is None
    attack_option = next(
        option
        for option in selected["combat"]["context_menu"]["options"]
        if option["action"] == "attack"
    )
    selected = session.confirm_combat_context_menu(attack_option["id"])

    assert selected["combat"]["pending_player_attack"]["stage"] == "confirm_attack"
    assert selected["combat"]["pending_player_attack"]["target"]["id"] == target["id"]
    assert selected["combat"]["pending_player_attack"]["target"]["ac"] == target["ac"]
    assert selected["combat"]["pending_player_attack"]["attack_modifier"] > 0
    assert selected["combat"]["pending_player_attack"]["active_modifiers"]
    assert "Rzuć 2d20 z utrudnieniem" in selected["combat"]["pending_player_attack"]["attack_instruction"]
    assert selected["combat"]["pending_player_attack"]["positioning"]["ranged_in_melee"] is True
    assert selected["combat"]["turn_action"]["action_use"] == "action_available"

    confirmed = session.confirm_player_attack_target()
    assert confirmed["combat"]["pending_player_attack"]["stage"] == "attack_roll"
    assert confirmed["combat"]["pending_player_attack"]["target"]["id"] == target["id"]
    assert confirmed["combat"]["turn_action"]["action_use"] == "action_available"

    attack_roll = session.submit_player_attack_roll(natural_roll=20, natural_roll_2=20)
    pending = attack_roll["combat"]["pending_player_attack"]
    assert pending["stage"] == "damage_roll"
    assert pending["hit"] is True
    assert pending["critical"] is True
    assert pending["target_ac"] == target["ac"]
    assert "Rzuć obrażenia" in pending["damage_instruction"]
    assert attack_roll["combat"]["turn_action"]["action_use"] == "action_used"

    state = session.submit_player_damage_roll(damage=5)

    damaged = next(actor for actor in state["combat"]["actors"] if actor["id"] == target["id"])
    assert damaged["hp"] < target["hp"]
    assert damaged["max_hp"] == target["max_hp"]
    assert state["combat"]["pending_player_attack"] is None
    assert state["combat"]["turn_action"]["action_use"] == "action_used"
    assert any(message["title"] == "Obrażenia" and "HP" in message["body"] for message in state["messages"])


def test_exploration_ui_session_player_damage_can_finish_combat_and_remove_target():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_combat_from_scout_alarm(session)
    state = session.state_payload()
    target = state["combat"]["legal_targets"][0]

    assert session.combat_state is not None
    for actor in tuple(session.combat_state.actors):
        if actor.faction == Faction.ENEMY and str(actor.id) != target["id"]:
            session.combat_state = replace_actor(session.combat_state, replace(actor, hp=0))

    state = session.submit_player_attack(
        target_id=target["id"],
        natural_roll=20,
        natural_roll_2=19,
        damage=999,
    )

    defeated = next(actor for actor in state["combat"]["actors"] if actor["id"] == target["id"])
    assert defeated["hp"] == 0
    assert defeated["defeated"] is True
    assert state["combat"]["status"] == "finished"
    assert state["combat"]["winner"] == "ally"
    assert state["combat"]["legal_targets"] == []
    assert any(message["title"] == "Atak" and "Cel zostaje pokonany" in message["body"] for message in state["messages"])


def test_player_attack_emits_hit_then_damage_taken_triggers() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_combat_from_scout_alarm(session)
    assert session.combat_state is not None
    attacker = current_actor(session.combat_state)
    target_id = session.state_payload()["combat"]["legal_targets"][0]["id"]
    target = next(actor for actor in session.combat_state.actors if str(actor.id) == target_id)
    hit_trigger = ActorTrigger(
        "hit_guard",
        "Osłona po trafieniu",
        TriggerEventType.ATTACK_HIT,
        TriggerEffectKind.GRANT_TEMP_HP,
        2,
    )
    damage_trigger = ActorTrigger(
        "damage_guard",
        "Osłona po obrażeniach",
        TriggerEventType.DAMAGE_TAKEN,
        TriggerEffectKind.GRANT_TEMP_HP,
        3,
    )
    session.combat_state = replace_actor(
        session.combat_state,
        replace(attacker, triggers=(hit_trigger,)),
    )
    session.combat_state = replace_actor(
        session.combat_state,
        replace(target, triggers=(damage_trigger,)),
    )

    state = session.submit_player_attack(
        target_id=target_id,
        natural_roll=20,
        natural_roll_2=20,
        damage=1,
    )

    actors = {actor["id"]: actor for actor in state["combat"]["actors"]}
    assert actors[str(attacker.id)]["temp_hp"] == 2
    assert actors[target_id]["temp_hp"] == 3
    activation_ids = [
        record["payload"]["trigger_id"]
        for record in (
            __import__("json").loads(line)
            for line in session.observer.path.read_text(encoding="utf-8").splitlines()
        )
        if record["event_type"] == "ui_actor_trigger_activated"
    ]
    assert activation_ids[-2:] == ["hit_guard", "damage_guard"]


def test_exploration_ui_session_board_scan_shows_feedback_once_before_waiting_for_click():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_combat_from_scout_alarm(session)
    state = session.state_payload()
    target = state["combat"]["legal_targets"][0]
    board = FakeBoardConnection(clicks=[tuple(target["position"])])
    session.attach_board_connection(board, backend="simulator")

    session.scan_board_selection()

    assert board.led_calls[0] == ("off", None)
    assert board.led_calls[1] != ("off", None)


def test_exploration_ui_session_player_movement_updates_position_and_remaining_speed():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_combat_from_scout_alarm(session)
    assert session.combat_state is not None
    for index, actor in enumerate(tuple(session.combat_state.actors)):
        if actor.faction == Faction.ENEMY:
            session.combat_state = replace_actor(session.combat_state, replace(actor, position=Coordinate(10, index)))

    state = session.state_payload()
    actor_id = state["combat"]["current_actor"]["id"]
    destination = next(tile for tile in state["combat"]["movement"]["destinations"] if tile["cost_feet"] == 5)

    state = session.submit_combat_movement(col=destination["col"], row=destination["row"])

    moved = next(actor for actor in state["combat"]["actors"] if actor["id"] == actor_id)
    assert moved["position"] == [destination["col"], destination["row"]]
    assert state["combat"]["movement"]["remaining_feet"] == 25
    assert any(message["title"] == "Ruch" for message in state["messages"])


def test_player_movement_emits_actor_moved_trigger_after_position_changes() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_combat_from_scout_alarm(session)
    assert session.combat_state is not None
    actor = current_actor(session.combat_state)
    trigger = ActorTrigger(
        "move_guard",
        "Osłona po ruchu",
        TriggerEventType.ACTOR_MOVED,
        TriggerEffectKind.GRANT_TEMP_HP,
        4,
    )
    session.combat_state = replace_actor(
        session.combat_state,
        replace(actor, triggers=(trigger,)),
    )
    for index, enemy in enumerate(tuple(session.combat_state.actors)):
        if enemy.faction == Faction.ENEMY:
            session.combat_state = replace_actor(
                session.combat_state,
                replace(enemy, position=Coordinate(10, index)),
            )
    destination = next(
        tile
        for tile in session.state_payload()["combat"]["movement"]["destinations"]
        if tile["cost_feet"] == 5
    )

    state = session.submit_combat_movement(
        col=destination["col"],
        row=destination["row"],
    )

    moved = next(item for item in state["combat"]["actors"] if item["id"] == str(actor.id))
    assert moved["temp_hp"] == 4
    assert moved["position"] == [destination["col"], destination["row"]]


def test_exploration_ui_session_board_movement_requires_second_click_confirmation():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_combat_from_scout_alarm(session)
    assert session.combat_state is not None
    for index, actor in enumerate(tuple(session.combat_state.actors)):
        if actor.faction == Faction.ENEMY:
            session.combat_state = replace_actor(session.combat_state, replace(actor, position=Coordinate(10, index)))
    state = session.state_payload()
    actor_id = state["combat"]["current_actor"]["id"]
    destination = next(tile for tile in state["combat"]["movement"]["destinations"] if tile["cost_feet"] == 5)
    clicked = (destination["col"], destination["row"])
    session.attach_board_connection(FakeBoardConnection(clicks=[clicked, clicked]), backend="simulator")

    preview = session.scan_board_selection()

    actor_after_preview = next(actor for actor in preview["combat"]["actors"] if actor["id"] == actor_id)
    assert actor_after_preview["position"] == state["combat"]["current_actor"]["position"]
    assert preview["combat"]["movement_preview"]["destination"] == [destination["col"], destination["row"]]

    moved = session.scan_board_selection()

    actor_after_move = next(actor for actor in moved["combat"]["actors"] if actor["id"] == actor_id)
    assert actor_after_move["position"] == [destination["col"], destination["row"]]
    assert moved["combat"]["movement_preview"] is None


def test_exploration_ui_session_dash_uses_action_and_extends_movement_pool():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)

    dashed = session.use_combat_dash()

    assert dashed["combat"]["turn_action"]["action_use"] == "action_used"
    assert dashed["combat"]["turn_action"]["extra_movement_feet"] == 30
    assert dashed["combat"]["movement"]["remaining_feet"] == 60
    assert dashed["combat"]["movement"]["extra_movement_feet"] == 30
    assert any(message["title"] == "Dash" and "dodatkowe 30 feet" in message["body"] for message in dashed["messages"])


def test_exploration_ui_session_can_select_attack_source_and_strength_potion_modifies_strength_attack():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    while str(session.combat_state.initiative_order.current_actor.id) != "hero":
        session.finish_combat_turn()

    state = session.state_payload()
    source_ids = {source["id"] for source in state["combat"]["available_attack_sources"]}
    assert {"longsword_slash", "crossbow_shot"} <= source_ids
    hero_payload = state["combat"]["current_actor"]
    assert {item["id"] for item in hero_payload["inventory"]} >= {"longsword", "crossbow", "strength_potion"}
    potion_action = next(action for action in state["combat"]["combat_actions"] if action["id"] == "drink_strength_potion")
    assert potion_action["source_item_id"] == "strength_potion"
    assert potion_action["source_item_quantity"] == 1
    assert potion_action["available"] is True
    longsword_payload = next(source for source in state["combat"]["available_attack_sources"] if source["id"] == "longsword_slash")
    crossbow_payload = next(source for source in state["combat"]["available_attack_sources"] if source["id"] == "crossbow_shot")
    assert longsword_payload["mechanic"]["type"] == "MeleeAttack"
    assert longsword_payload["attack_kind"] == "melee"
    assert longsword_payload["reach_feet"] == 5
    assert crossbow_payload["mechanic"]["type"] == "RangedAttack"
    assert crossbow_payload["attack_kind"] == "ranged"
    assert crossbow_payload["reach_feet"] is None

    selected = session.select_combat_attack_source("longsword_slash")
    assert selected["combat"]["selected_attack_source_id"] == "longsword_slash"

    boosted = session.use_combat_strength_potion("drink_strength_potion")
    assert boosted["combat"]["turn_action"]["action_use"] == "action_used"
    actor = next(candidate for candidate in boosted["combat"]["actors"] if candidate["id"] == "hero")
    assert any(effect["kind"] == "strength_potion" for effect in actor["effects"])
    strength_potion = next(item for item in actor["inventory"] if item["id"] == "strength_potion")
    assert strength_potion["quantity"] == 0
    spent_action = next(action for action in boosted["combat"]["combat_actions"] if action["id"] == "drink_strength_potion")
    assert spent_action["available"] is False

    hero = next(candidate for candidate in session.combat_state.actors if str(candidate.id) == "hero")
    base_source = next(source for source in session._attack_sources_for_actor(hero) if source.id == "longsword_slash")
    modified = session._effective_attack_source(hero, base_source)
    assert any(modifier.label == "Wypij napój siły" and modifier.value == 2 for modifier in modified.attack_roll_request.modifiers)
    assert modified.damage_modifier == base_source.damage_modifier + 2


def test_exploration_ui_session_crossbow_preview_shows_cart_half_cover() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    rogue = session.combat_state.initiative_order.current_actor
    assert str(rogue.id) == "rogue"
    goblin = next(actor for actor in session.combat_state.actors if str(actor.id) == "goblin_a")

    selected = session.select_player_attack_target_at_position(goblin.position)
    pending = selected["combat"]["pending_player_attack"]

    assert pending["source"]["attack_kind"] == "ranged"
    assert pending["positioning"] == {
        "cover_level": "half",
        "cover_bonus": 2,
        "cover_sources": ["Rozbity wóz"],
        "ranged_in_melee": False,
        "ranged_threat_actor_ids": [],
        "flanking": False,
        "flanking_ally_ids": [],
    }
    assert pending["target_ac"] == goblin.ac + 2


def test_exploration_ui_session_dexterity_save_preview_and_result_show_cover() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    while str(session.combat_state.initiative_order.current_actor.id) != "cleric":
        session.finish_combat_turn()
    goblin = next(
        actor for actor in session.combat_state.actors if str(actor.id) == "goblin_a"
    )

    session.select_combat_attack_source("sacred_flame")
    selected = session.select_player_attack_target_at_position(goblin.position)
    pending = selected["combat"]["pending_player_attack"]

    assert pending["positioning"]["cover_level"] == "half"
    assert pending["positioning"]["cover_bonus"] == 2
    assert pending["positioning"]["cover_sources"] == ["Rozbity wóz"]

    session.encounter_rng = random.Random(1)
    confirmed = session.confirm_player_attack_target()
    save = confirmed["combat"]["pending_player_attack"]["saving_throws"][0]

    assert any(
        component["label"] == "Połowa osłony" and component["value"] == 2
        for component in save["modifier_components"]
    )


def test_exploration_ui_session_crossbow_in_melee_requires_disadvantage_roll() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    rogue = session.combat_state.initiative_order.current_actor
    assert str(rogue.id) == "rogue"
    goblin = next(actor for actor in session.combat_state.actors if str(actor.id) == "goblin_b")
    session.combat_state = replace_actor(
        session.combat_state,
        replace(rogue, position=Coordinate(goblin.position.col - 1, goblin.position.row)),
    )

    session.select_player_attack_target_at_position(goblin.position)
    confirmed = session.confirm_player_attack_target()
    pending = confirmed["combat"]["pending_player_attack"]

    assert pending["attack_mode"] == "disadvantage"
    assert pending["positioning"]["ranged_in_melee"] is True
    assert pending["positioning"]["ranged_threat_actor_ids"] == ["goblin_b"]
    assert any(
        modifier["label"] == "Atak dystansowy w zwarciu"
        for modifier in pending["active_modifiers"]
    )


def test_exploration_ui_session_melee_flanking_is_visible_and_grants_advantage() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    hero = next(actor for actor in session.combat_state.actors if str(actor.id) == "hero")
    rogue = next(actor for actor in session.combat_state.actors if str(actor.id) == "rogue")
    cleric = next(actor for actor in session.combat_state.actors if str(actor.id) == "cleric")
    goblin = next(actor for actor in session.combat_state.actors if str(actor.id) == "goblin_a")
    current_index = next(
        index
        for index, entry in enumerate(session.combat_state.initiative_order.entries)
        if entry.actor.id == hero.id
    )
    session.combat_state = replace(
        session.combat_state,
        initiative_order=replace(
            session.combat_state.initiative_order,
            current_index=current_index,
        ),
    )
    session.combat_state = replace_actor(
        session.combat_state,
        replace(goblin, position=Coordinate(8, 6)),
    )
    session.combat_state = replace_actor(
        session.combat_state,
        replace(rogue, position=Coordinate(9, 6)),
    )
    session.combat_state = replace_actor(
        session.combat_state,
        replace(cleric, position=Coordinate(6, 6)),
    )
    session.selected_attack_source_ids["hero"] = "longsword_slash"

    session.select_player_attack_target_at_position(Coordinate(8, 6))
    confirmed = session.confirm_player_attack_target()
    pending = confirmed["combat"]["pending_player_attack"]

    assert pending["positioning"]["flanking"] is True
    assert pending["positioning"]["flanking_ally_ids"] == ["rogue"]
    assert pending["attack_mode"] == "advantage"
    assert any(
        modifier["label"] == "Flankowanie"
        for modifier in pending["active_modifiers"]
    )


def test_exploration_ui_session_hide_shows_roll_and_persists_observer_state() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    rogue = session.combat_state.initiative_order.current_actor
    assert str(rogue.id) == "rogue"
    session.combat_state = replace_actor(
        session.combat_state,
        replace(rogue, position=Coordinate(8, 4)),
    )

    started = session.start_combat_hide()
    pending = started["combat"]["pending_combat_skill_check"]

    assert pending["action"] == "hide"
    assert pending["modifier"] == 7
    assert "Końcowy modyfikator: +7" in pending["instruction"]
    assert started["combat"]["turn_action"]["action_use"] == "action_available"

    resolved = session.submit_combat_skill_check(natural_roll=15)
    rogue_payload = next(actor for actor in resolved["combat"]["actors"] if actor["id"] == "rogue")

    assert resolved["combat"]["pending_combat_skill_check"] is None
    assert resolved["combat"]["turn_action"]["action_use"] == "action_used"
    assert rogue_payload["hidden"]["stealth_total"] == 22
    assert set(rogue_payload["hidden"]["hidden_from_actor_ids"]) == {"goblin_a", "goblin_b"}


def test_exploration_ui_session_cleric_can_heal_wounded_ally():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    while str(session.combat_state.initiative_order.current_actor.id) != "cleric":
        session.finish_combat_turn()
    wounded = next(actor for actor in session.combat_state.actors if str(actor.id) == "hero")
    session.combat_state = replace_actor(session.combat_state, replace(wounded, hp=10))

    selected = session.select_combat_healing_source("healing_word")
    assert selected["combat"]["selected_healing_source_id"] == "healing_word"
    healing_payload = next(source for source in selected["combat"]["available_healing_sources"] if source["id"] == "healing_word")
    assert healing_payload["mechanic"]["type"] == "SpellHealing"
    assert healing_payload["casting_kind"] == "leveled"
    assert healing_payload["resource_label"] == "slot 1. poziomu"
    assert healing_payload["prepared"] is True
    assert any(target["id"] == "hero" for target in selected["combat"]["legal_healing_targets"])

    target_position = next(actor.position for actor in session.combat_state.actors if str(actor.id) == "hero")
    pending = session.select_player_healing_target_at_position(target_position)
    assert pending["combat"]["pending_player_healing"]["target"]["id"] == "hero"

    healed = session.submit_player_healing_roll(healing=6)
    hero = next(actor for actor in healed["combat"]["actors"] if actor["id"] == "hero")
    cleric = next(actor for actor in healed["combat"]["actors"] if actor["id"] == "cleric")
    assert hero["hp"] == 16
    assert cleric["spell_slots"][0]["remaining"] == 1
    assert healed["combat"]["turn_action"]["action_use"] == "action_used"
    assert any(message["title"] == "Leczenie" and "HP 10 -> 16" in message["body"] for message in healed["messages"])


def test_exploration_ui_session_cleric_concentration_spell_grants_attack_bonus():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    while str(session.combat_state.initiative_order.current_actor.id) != "cleric":
        session.finish_combat_turn()

    started = session.start_combat_concentration_action("bless_attack_bonus")
    pending = started["combat"]["pending_concentration_action"]
    assert pending["action"]["id"] == "bless_attack_bonus"
    assert pending["action"]["resource_label"] == "slot 1. poziomu"
    assert pending["action"]["concentration"] is True
    assert any(target["id"] == "hero" for target in pending["targets"])

    confirmed = session.confirm_combat_concentration_action(target_id="hero")
    hero = next(actor for actor in confirmed["combat"]["actors"] if actor["id"] == "hero")
    cleric = next(actor for actor in confirmed["combat"]["actors"] if actor["id"] == "cleric")

    assert confirmed["combat"]["pending_concentration_action"] is None
    assert confirmed["combat"]["turn_action"]["action_use"] == "action_used"
    assert cleric["spell_slots"][0]["remaining"] == 1
    assert cleric["concentration"]["kind"] == "concentration_attack_bonus"
    assert cleric["concentration"]["target_actor_id"] == "hero"
    assert any(effect["kind"] == "concentration_attack_bonus" and effect["value"] == 1 for effect in hero["effects"])

    hero_actor = next(actor for actor in session.combat_state.actors if str(actor.id) == "hero")
    source = next(source for source in session._attack_sources_for_actor(hero_actor) if source.id == "longsword_slash")
    modified = session._effective_attack_source(hero_actor, source)
    assert any(modifier.label == "Błogosławieństwo" and modifier.value == 1 for modifier in modified.attack_roll_request.modifiers)


def _cleric_casts_bless_on_hero(session: ExplorationUiSession) -> None:
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    while str(session.combat_state.initiative_order.current_actor.id) != "cleric":
        session.finish_combat_turn()
    session.start_combat_concentration_action("bless_attack_bonus")
    session.confirm_combat_concentration_action(target_id="hero")


def _apply_test_damage(session: ExplorationUiSession, actor_id: str, damage_amount: int) -> None:
    assert session.combat_state is not None
    actor = next(candidate for candidate in session.combat_state.actors if str(candidate.id) == actor_id)
    damage = resolve_damage((DamageComponentInput(damage_amount, DamageType.SLASHING, "test"),))
    applied = apply_damage_result(actor, damage)
    session.combat_state = replace_actor(session.combat_state, applied.actor_after)
    session._maybe_prompt_concentration_check(applied)


def test_exploration_ui_session_concentration_check_failure_removes_attack_bonus():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _cleric_casts_bless_on_hero(session)

    _apply_test_damage(session, "cleric", 12)
    payload = session.state_payload()
    pending = payload["combat"]["pending_concentration_check"]

    assert pending["actor"]["id"] == "cleric"
    assert pending["damage"] == 12
    assert pending["dc"] == 10
    assert pending["modifier"] == 2
    assert any(
        item["label"] == "Aura ochronnego relikwiarza"
        for item in pending["modifier_components"]
    )
    assert pending["effects"][0]["kind"] == "concentration_attack_bonus"

    resolved = session.submit_concentration_check(natural_roll=1)
    hero = next(actor for actor in resolved["combat"]["actors"] if actor["id"] == "hero")
    cleric = next(actor for actor in resolved["combat"]["actors"] if actor["id"] == "cleric")

    assert resolved["combat"]["pending_concentration_check"] is None
    assert hero["effects"] == []
    assert cleric["concentration"] is None

    hero_actor = next(actor for actor in session.combat_state.actors if str(actor.id) == "hero")
    source = next(source for source in session._attack_sources_for_actor(hero_actor) if source.id == "longsword_slash")
    modified = session._effective_attack_source(hero_actor, source)
    assert not any(modifier.label == "Błogosławieństwo" for modifier in modified.attack_roll_request.modifiers)


def test_exploration_ui_session_concentration_check_success_keeps_attack_bonus():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _cleric_casts_bless_on_hero(session)

    _apply_test_damage(session, "cleric", 12)
    resolved = session.submit_concentration_check(natural_roll=20)
    hero = next(actor for actor in resolved["combat"]["actors"] if actor["id"] == "hero")
    cleric = next(actor for actor in resolved["combat"]["actors"] if actor["id"] == "cleric")

    assert resolved["combat"]["pending_concentration_check"] is None
    assert cleric["concentration"]["kind"] == "concentration_attack_bonus"
    assert any(effect["kind"] == "concentration_attack_bonus" and effect["value"] == 1 for effect in hero["effects"])


def test_exploration_ui_session_cleric_area_spell_previews_line_and_consumes_slot():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    session.confirm_spell_preparation(
        actor_id="cleric",
        spell_ids=("radiant_line", "healing_word"),
    )
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    while str(session.combat_state.initiative_order.current_actor.id) != "cleric":
        session.finish_combat_turn()
    goblin = next(actor for actor in session.combat_state.actors if str(actor.id) == "goblin_b")
    session.combat_state = replace_actor(session.combat_state, replace(goblin, position=Coordinate(11, 6)))

    selected = session.select_combat_attack_source("radiant_line")

    assert selected["combat"]["selected_attack_source_id"] == "radiant_line"
    source_payload = next(source for source in selected["combat"]["available_attack_sources"] if source["id"] == "radiant_line")
    assert source_payload["mechanic"]["type"] == "AreaSpellAttack"
    assert source_payload["casting_kind"] == "leveled"
    assert source_payload["resource_label"] == "slot 1. poziomu"
    assert source_payload["area"] == {
        "shape": "line",
        "radius_feet": 0,
        "length_feet": 30,
        "width_feet": 5,
        "target_mode": "all_creatures",
    }
    cantrip_payload = next(source for source in selected["combat"]["available_attack_sources"] if source["id"] == "sacred_flame")
    assert cantrip_payload["casting_kind"] == "cantrip"
    assert cantrip_payload["resource_label"] == "cantrip"
    assert [10, 6] in selected["combat"]["legal_area_positions"]
    assert selected["combat"]["legal_targets"] == []

    pending = session.select_player_area_spell_at_position(Coordinate(10, 6))

    area_spell = pending["combat"]["pending_area_spell"]
    assert area_spell["source"]["id"] == "radiant_line"
    assert [11, 6] in area_spell["area_positions"]
    assert [target["id"] for target in area_spell["targets"]] == ["goblin_b"]

    confirmed = session.confirm_player_area_spell()
    cleric_after_confirm = next(actor for actor in confirmed["combat"]["actors"] if actor["id"] == "cleric")

    assert confirmed["combat"]["pending_area_spell"]["stage"] == "damage_roll"
    assert confirmed["combat"]["turn_action"]["action_use"] == "action_used"
    assert cleric_after_confirm["spell_slots"][0]["remaining"] == 1
    save = confirmed["combat"]["pending_area_spell"]["saving_throws"][0]
    assert save["actor_id"] == "goblin_b"
    assert save["ability"] == "dexterity"
    assert save["dc"] == 13
    assert save["success"] is True

    damaged = session.submit_player_area_spell_damage(damage=5)
    damaged_goblin = next(actor for actor in damaged["combat"]["actors"] if actor["id"] == "goblin_b")

    assert damaged["combat"]["pending_area_spell"] is None
    assert damaged_goblin["hp"] == 8
    assert any(message["title"] == "Obrażenia obszarowe" and "HP 10 -> 8" in message["body"] for message in damaged["messages"])


def test_exploration_ui_session_rejects_unprepared_leveled_spell():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    while str(session.combat_state.initiative_order.current_actor.id) != "cleric":
        session.finish_combat_turn()

    state = session.state_payload()
    radiant_line = next(
        source
        for source in state["combat"]["available_attack_sources"]
        if source["id"] == "radiant_line"
    )

    assert radiant_line["prepared"] is False
    assert radiant_line["available"] is False
    assert radiant_line["unavailable_reason"] == "Czar nie został przygotowany."
    with pytest.raises(ValueError, match="nie został przygotowany"):
        session.select_combat_attack_source("radiant_line")


def test_exploration_ui_session_sacred_flame_uses_enemy_save_instead_of_attack_roll():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    while str(session.combat_state.initiative_order.current_actor.id) != "cleric":
        session.finish_combat_turn()
    session.encounter_rng = random.Random(0)

    selected = session.select_combat_attack_source("sacred_flame")
    target_position = next(actor.position for actor in session.combat_state.actors if str(actor.id) == "goblin_b")
    pending = session.select_player_attack_target_at_position(target_position)

    assert pending["combat"]["pending_player_attack"]["source"]["save_ability"] == "dexterity"
    assert pending["combat"]["pending_player_attack"]["spell_save_dc"] == 13

    resolved = session.confirm_player_attack_target()
    goblin = next(actor for actor in resolved["combat"]["actors"] if actor["id"] == "goblin_b")

    assert resolved["combat"]["pending_player_attack"] is None
    assert resolved["combat"]["turn_action"]["action_use"] == "action_used"
    assert goblin["hp"] == 10
    assert any(message["title"] == "Czar" and "Sukces: brak obrażeń" in message["body"] for message in resolved["messages"])


def test_exploration_ui_session_dodge_adds_defensive_effect_until_next_turn():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    actor = session.combat_state.initiative_order.current_actor

    dodged = session.use_combat_dodge()
    actor_payload = next(candidate for candidate in dodged["combat"]["actors"] if candidate["id"] == str(actor.id))
    current_actor_payload = dodged["combat"]["current_actor"]
    enemy_actor = next(candidate for candidate in session.combat_state.actors if candidate.faction == Faction.ENEMY)
    source = session.encounter_setup_flow.encounter.attack_sources_by_actor[enemy_actor.id]
    modified_source = session._effective_attack_source(enemy_actor, source, actor)

    assert dodged["combat"]["turn_action"]["action_use"] == "action_used"
    assert actor_payload["effects"][0]["kind"] == "dodge_until_next_turn"
    assert actor_payload["effects"][0]["label"] == "Unik"
    assert actor_payload["effects"][0]["value_label"] == "ataki przeciwko aktorowi mają utrudnienie"
    assert actor_payload["effects"][0]["expires"] == "znika na początku następnej tury aktora"
    chip_labels = {chip["label"] for chip in current_actor_payload["status_chips"]}
    assert "Akcja zużyta" in chip_labels
    assert "Reakcja dostępna" in chip_labels
    assert "Unik: ataki przeciwko aktorowi mają utrudnienie" in chip_labels
    assert modified_source.attack_roll_request.mode == RollMode.DISADVANTAGE

    session.finish_combat_turn()
    assert any(effect.actor_id == str(actor.id) and effect.kind == "dodge_until_next_turn" for effect in session.active_combat_effects)
    while session.combat_state is not None and str(session.combat_state.initiative_order.current_actor.id) != str(actor.id):
        session.finish_combat_turn()

    assert not any(effect.actor_id == str(actor.id) and effect.kind == "dodge_until_next_turn" for effect in session.active_combat_effects)
    assert any(message.title == "Efekty" and "Unik" in message.body for message in session.messages)


def test_exploration_ui_session_disengage_adds_effect_until_turn_end():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    actor = session.combat_state.initiative_order.current_actor

    disengaged = session.use_combat_disengage()
    actor_payload = next(candidate for candidate in disengaged["combat"]["actors"] if candidate["id"] == str(actor.id))

    assert disengaged["combat"]["turn_action"]["action_use"] == "action_used"
    assert actor_payload["effects"][0]["kind"] == "disengage_until_turn_end"
    assert actor_payload["effects"][0]["label"] == "Odwrót"
    assert actor_payload["effects"][0]["value_label"] == "bezpieczne odejście"
    assert actor_payload["effects"][0]["expires"] == "znika na końcu tury"
    assert any(message["title"] == "Odwrót" and "bezpiecznie odejść" in message["body"] for message in disengaged["messages"])

    ended = session.finish_combat_turn()

    assert not any(effect.actor_id == str(actor.id) and effect.kind == "disengage_until_turn_end" for effect in session.active_combat_effects)
    assert not any(
        effect["kind"] == "disengage_until_turn_end"
        for candidate in ended["combat"]["actors"]
        for effect in candidate["effects"]
    )


def test_exploration_ui_session_movement_leaving_reach_requires_opportunity_confirmation():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    active_actor = session.combat_state.initiative_order.current_actor
    session.combat_state = replace_actor(session.combat_state, replace(active_actor, position=Coordinate(10, 7)))

    state = session.submit_combat_movement(col=9, row=7)

    actor = next(candidate for candidate in state["combat"]["actors"] if candidate["id"] == str(active_actor.id))
    assert actor["position"] == [10, 7]
    assert state["combat"]["pending_opportunity_movement"]["destination"] == [9, 7]
    assert [threat["id"] for threat in state["combat"]["pending_opportunity_movement"]["threats"]] == ["goblin_b"]
    assert any(message["title"] == "Atak okazyjny" for message in state["messages"])


def test_exploration_ui_session_confirming_opportunity_movement_resolves_reaction_then_moves():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    session.encounter_rng = random.Random(1)
    active_actor = session.combat_state.initiative_order.current_actor
    session.combat_state = replace_actor(session.combat_state, replace(active_actor, position=Coordinate(10, 7)))

    session.submit_combat_movement(col=9, row=7)
    state = session.confirm_opportunity_movement()

    actor = next(candidate for candidate in state["combat"]["actors"] if candidate["id"] == str(active_actor.id))
    assert actor["position"] == [9, 7]
    assert state["combat"]["pending_opportunity_movement"] is None
    assert any(message["title"] == "Atak okazyjny" and "Goblin przy rumowisku" in message["body"] for message in state["messages"])
    assert session.combat_state is not None
    assert str(next(iter(session.combat_state.spent_reaction_actor_ids))) == "goblin_b"


def test_exploration_ui_session_disengage_prevents_opportunity_movement_prompt():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    active_actor = session.combat_state.initiative_order.current_actor
    session.combat_state = replace_actor(session.combat_state, replace(active_actor, position=Coordinate(10, 7)))
    session.use_combat_disengage()

    state = session.submit_combat_movement(col=9, row=7)

    actor = next(candidate for candidate in state["combat"]["actors"] if candidate["id"] == str(active_actor.id))
    assert actor["position"] == [9, 7]
    assert state["combat"]["pending_opportunity_movement"] is None


def test_exploration_ui_session_help_grants_advantage_to_ally_attack_against_target():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    helper = session.combat_state.initiative_order.current_actor
    ally = next(actor for actor in session.combat_state.actors if actor.faction == Faction.ALLY and actor.id != helper.id)
    target = next(actor for actor in session.combat_state.actors if str(actor.id) == "goblin_b")
    session.combat_state = replace_actor(session.combat_state, replace(helper, position=Coordinate(10, 7)))
    session.combat_state = replace_actor(session.combat_state, replace(ally, position=Coordinate(10, 8)))
    session.combat_state = replace_actor(session.combat_state, replace(target, position=Coordinate(11, 7)))
    ally = next(actor for actor in session.combat_state.actors if actor.id == ally.id)
    target = next(actor for actor in session.combat_state.actors if actor.id == target.id)

    pending = session.start_combat_help()
    helped = session.confirm_combat_help(ally_id=str(ally.id), target_id=str(target.id))

    ally_payload = next(actor for actor in helped["combat"]["actors"] if actor["id"] == str(ally.id))
    assert pending["combat"]["pending_combat_help"]["helper"]["id"] == str(helper.id)
    assert helped["combat"]["turn_action"]["action_use"] == "action_used"
    assert ally_payload["effects"][0]["kind"] == "help_attack_advantage"
    assert ally_payload["effects"][0]["target_actor_id"] == str(target.id)

    session.finish_combat_turn()
    while session.combat_state is not None and str(session.combat_state.initiative_order.current_actor.id) != str(ally.id):
        session.finish_combat_turn()

    selected = session.select_player_attack_target_at_position(target.position)
    assert selected["combat"]["pending_player_attack"]["attack_mode"] == "advantage"

    session.confirm_player_attack_target()
    rolled = session.submit_player_attack_roll(natural_roll=10, natural_roll_2=15)

    assert not any(effect.kind == "help_attack_advantage" for effect in session.active_combat_effects)
    assert rolled["combat"]["pending_player_attack"] is not None
    assert rolled["combat"]["pending_player_attack"]["natural_rolls"] == [10, 15]
    assert rolled["combat"]["pending_player_attack"]["natural_roll"] == 15


def test_exploration_ui_session_ready_prepares_attack_and_can_trigger_on_enemy_movement():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)

    pending = session.start_combat_ready()
    readied_actor, target = _prepare_ready_attack_trigger(session, "enemy_moves")
    triggered = session.state_payload()

    assert pending["combat"]["pending_combat_ready"]["actor"]["id"] == str(readied_actor.id)
    assert triggered["combat"]["pending_ready_attack"]["stage"] == "choice"
    assert triggered["combat"]["pending_ready_attack"]["attacker"]["id"] == str(readied_actor.id)
    assert triggered["combat"]["pending_ready_attack"]["target"]["id"] == str(target.id)

    started = session.start_ready_attack()
    missed = session.submit_ready_attack_roll(natural_roll=1)

    assert started["combat"]["pending_ready_attack"]["stage"] == "attack_roll"
    assert missed["combat"]["pending_ready_attack"] is None
    assert missed["combat"]["enemy_turn_preview"]["kind"] == "movement"
    assert not any(effect.kind == "ready_attack" for effect in session.active_combat_effects)
    assert session.combat_state is not None
    assert readied_actor.id in session.pending_enemy_turn_result.state.spent_reaction_actor_ids


def test_exploration_ui_session_ready_attack_can_stop_enemy_turn():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)

    session.start_combat_ready()
    readied_actor, target = _prepare_ready_attack_trigger(session, "enemy_moves")
    session.start_ready_attack()
    rolled = session.submit_ready_attack_roll(natural_roll=20)
    stopped = session.submit_ready_damage_roll(damage=999)

    target_payload = next(actor for actor in stopped["combat"]["actors"] if actor["id"] == str(target.id))
    assert rolled["combat"]["pending_ready_attack"]["stage"] == "damage_roll"
    assert target_payload["defeated"] is True
    assert stopped["combat"]["pending_ready_attack"] is None
    assert stopped["combat"]["enemy_turn_preview"] is None
    assert any(
        message["title"] == "Ready" and "Tura przeciwnika zostaje przerwana" in message["body"]
        for message in stopped["messages"]
    )


def test_exploration_ui_session_hero_opportunity_attack_can_be_taken_during_enemy_movement():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    hero, enemy = _prepare_enemy_opportunity_preview(session)

    started = session.start_enemy_opportunity_attack()

    assert started["combat"]["pending_enemy_opportunity_attack"]["stage"] == "attack_roll"
    assert started["combat"]["pending_enemy_opportunity_attack"]["attacker"]["id"] == str(hero.id)
    assert started["combat"]["pending_enemy_opportunity_attack"]["target"]["id"] == str(enemy.id)

    missed = session.submit_enemy_opportunity_attack_roll(natural_roll=1)

    assert missed["combat"]["pending_enemy_opportunity_attack"] is None
    assert missed["combat"]["enemy_turn_preview"]["kind"] == "movement"
    assert session.combat_state is not None
    assert hero.id in session.pending_enemy_turn_result.state.spent_reaction_actor_ids


def test_exploration_ui_session_hero_opportunity_attack_can_stop_enemy_movement():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    hero, enemy = _prepare_enemy_opportunity_preview(session)

    session.start_enemy_opportunity_attack()
    rolled = session.submit_enemy_opportunity_attack_roll(natural_roll=20)
    stopped = session.submit_enemy_opportunity_damage_roll(damage=999)

    enemy_payload = next(actor for actor in stopped["combat"]["actors"] if actor["id"] == str(enemy.id))
    assert rolled["combat"]["pending_enemy_opportunity_attack"]["stage"] == "damage_roll"
    assert enemy_payload["defeated"] is True
    assert stopped["combat"]["pending_enemy_opportunity_attack"] is None
    assert stopped["combat"]["enemy_turn_preview"] is None
    assert any(
        message["title"] == "Atak okazyjny" and "Ruch przeciwnika zostaje przerwany" in message["body"]
        for message in stopped["messages"]
    )


def test_exploration_ui_session_cart_cover_uses_action_and_expires_after_movement():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)

    state = session.submit_combat_movement(col=7, row=7)
    actor_id = state["combat"]["current_actor"]["id"]
    base_ac = state["combat"]["current_actor"]["ac"]

    selected = session.select_board_position(Coordinate(7, 8))

    assert {option["id"] for option in selected["combat"]["context_menu"]["options"]} == {
        "move:7:8",
        "interact:broken_cart",
    }
    interaction = session.confirm_combat_context_menu("interact:broken_cart")
    assert interaction["combat"]["pending_combat_interaction"]["object_id"] == "broken_cart"
    assert {option["id"] for option in interaction["combat"]["pending_combat_interaction"]["options"]} == {
        "take_cover_cart",
        "climb_cart",
    }

    covered = session.confirm_combat_interaction("take_cover_cart")
    actor = next(candidate for candidate in covered["combat"]["actors"] if candidate["id"] == actor_id)

    assert covered["combat"]["turn_action"]["action_use"] == "action_used"
    assert actor["ac"] == base_ac + 2
    assert actor["effects"][0]["kind"] == "grant_ac_bonus_until_move"
    assert any(message["title"] == "Interakcja" and "AC +2" in message["body"] for message in covered["messages"])

    moved = session.submit_combat_movement(col=6, row=7)
    moved_actor = next(candidate for candidate in moved["combat"]["actors"] if candidate["id"] == actor_id)

    assert moved_actor["position"] == [6, 7]
    assert moved_actor["ac"] == base_ac
    assert moved_actor["effects"] == []


def test_exploration_ui_session_can_approach_and_then_open_remote_interaction() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)

    selected = session.select_board_position(Coordinate(7, 8))
    menu = selected["combat"]["context_menu"]
    approach = next(option for option in menu["options"] if option["id"] == "approach-interact:broken_cart")

    assert approach["movement_cost_feet"] > 0
    assert approach["destination"] != [7, 8]
    assert "następnie interakcja" in approach["description"]

    approached = session.confirm_combat_context_menu("approach-interact:broken_cart")
    actor = approached["combat"]["current_actor"]

    assert actor["position"] == approach["destination"]
    assert approached["combat"]["pending_combat_interaction"]["object_id"] == "broken_cart"
    assert approached["combat"]["turn_action"]["action_use"] == "action_available"


def test_exploration_ui_session_does_not_interact_when_opportunity_attack_stops_approach() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    hero = session.combat_state.initiative_order.current_actor
    enemy = next(actor for actor in session.combat_state.actors if actor.faction == Faction.ENEMY)
    session.combat_state = replace_actor(session.combat_state, replace(hero, position=Coordinate(5, 5), hp=1))
    session.combat_state = replace_actor(session.combat_state, replace(enemy, position=Coordinate(4, 5)))
    session.encounter_rng = type("MaxRng", (), {"randint": staticmethod(lambda low, high: high)})()

    selected = session.select_board_position(Coordinate(7, 8))
    pending = session.confirm_combat_context_menu("approach-interact:broken_cart")

    assert pending["combat"]["pending_opportunity_movement"] is not None

    stopped = session.confirm_opportunity_movement()
    stopped_hero = next(actor for actor in stopped["combat"]["actors"] if actor["id"] == str(hero.id))

    assert stopped_hero["position"] == [5, 5]
    assert stopped_hero["defeated"] is True
    assert stopped["combat"]["pending_combat_interaction"] is None
    assert session.pending_approach_interaction is None


def test_exploration_ui_session_approaches_and_picks_up_weapon_as_free_interaction() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    owner = next(
        actor
        for actor in session.combat_state.actors
        if actor.faction == Faction.ALLY
        and actor.id != session.combat_state.initiative_order.current_actor.id
        and any(item.kind == "weapon" and item.equipped for item in actor.inventory)
    )
    owner = replace(owner, position=Coordinate(8, 7))
    session.combat_state = replace_actor(session.combat_state, owner)
    session.combat_state = replace_actor(session.combat_state, replace(owner, hp=0, uses_death_saves=True))
    dropped = session.combat_state.dropped_weapons[0]

    selected = session.select_board_position(dropped.position)
    option_id = f"approach-pickup:{dropped.id}"
    pickup_option = next(option for option in selected["combat"]["context_menu"]["options"] if option["id"] == option_id)

    assert pickup_option["destination"] == [8, 7]
    assert "darmowa interakcja" in pickup_option["description"]

    picked_up = session.confirm_combat_context_menu(option_id)
    if picked_up["combat"]["pending_opportunity_movement"] is not None:
        session.encounter_rng = random.Random(1)
        picked_up = session.confirm_opportunity_movement()
    actor = picked_up["combat"]["current_actor"]

    assert actor["position"] == [8, 7]
    assert dropped.id not in [item["id"] for item in picked_up["combat"]["dropped_weapons"]]
    assert picked_up["combat"]["turn_action"]["object_interaction_available"] is False
    assert picked_up["combat"]["turn_action"]["action_use"] == "action_available"
    assert any(item["name"] == dropped.weapon.name and item["equipped"] is False for item in actor["inventory"])


def test_exploration_ui_session_self_menu_swaps_weapons_and_updates_attacks() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    actor = next(actor for actor in session.combat_state.actors if str(actor.id) == "hero")
    current_index = next(
        index
        for index, entry in enumerate(session.combat_state.initiative_order.entries)
        if entry.actor.id == actor.id
    )
    session.combat_state = replace(
        session.combat_state,
        initiative_order=replace(session.combat_state.initiative_order, current_index=current_index),
    )
    actor = replace(
        actor,
        inventory=tuple(
            replace(item, equipped=item.id == "longsword", held_in=())
            if item.kind == "weapon"
            else item
            for item in actor.inventory
        ),
    )
    session.combat_state = replace_actor(session.combat_state, actor)

    opened = session.select_board_position(actor.position)
    equip_option = next(
        option
        for option in opened["combat"]["context_menu"]["options"]
        if option["id"] == "equip-weapon:crossbow"
    )

    assert equip_option["label"] == "Zamień na: Kusza"
    assert "darmową interakcję i akcję" in equip_option["description"]

    equipped = session.confirm_combat_context_menu("equip-weapon:crossbow")
    inventory = {item["id"]: item for item in equipped["combat"]["current_actor"]["inventory"]}
    attacks = {source["id"]: source for source in equipped["combat"]["available_attack_sources"]}

    assert inventory["longsword"]["equipped"] is False
    assert inventory["crossbow"]["equipped"] is True
    assert equipped["combat"]["turn_action"]["object_interaction_available"] is False
    assert equipped["combat"]["turn_action"]["action_use"] == "action_used"
    assert equipped["combat"]["selected_attack_source_id"] == "crossbow_shot"
    assert attacks["crossbow_shot"]["available"] is True
    assert attacks["longsword_slash"]["available"] is False

    reopened = session.select_board_position(actor.position)
    option_ids = {option["id"] for option in reopened["combat"]["context_menu"]["options"]}
    assert "equip-weapon:longsword" not in option_ids


def test_exploration_ui_session_can_equip_weapon_originating_from_another_actor() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    cleric = next(actor for actor in session.combat_state.actors if str(actor.id) == "cleric")
    cleric = replace(
        cleric,
        inventory=(
            *cleric.inventory,
            InventoryItem(
                "crossbow_from_rogue",
                "Kusza Łotrzycy",
                "weapon",
                equipped=False,
                source_ref="crossbow",
            ),
        ),
    )
    session.combat_state = replace_actor(session.combat_state, cleric)
    current_index = next(
        index
        for index, entry in enumerate(session.combat_state.initiative_order.entries)
        if entry.actor.id == cleric.id
    )
    session.combat_state = replace(
        session.combat_state,
        initiative_order=replace(session.combat_state.initiative_order, current_index=current_index),
    )
    cleric = session.combat_state.initiative_order.current_actor

    opened = session.select_board_position(cleric.position)

    assert "equip-weapon:crossbow_from_rogue" in [
        option["id"] for option in opened["combat"]["context_menu"]["options"]
    ]

    equipped = session.confirm_combat_context_menu("equip-weapon:crossbow_from_rogue")
    crossbow = next(
        source for source in equipped["combat"]["available_attack_sources"] if source["id"] == "crossbow_shot"
    )

    assert crossbow["available"] is True
    assert equipped["combat"]["selected_attack_source_id"] == "crossbow_shot"


def test_exploration_ui_session_drops_equipped_weapon_without_spending_turn_resources() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    actor = session.combat_state.initiative_order.current_actor
    weapon = next(item for item in actor.inventory if item.kind == "weapon" and item.equipped)

    opened = session.select_board_position(actor.position)
    option_id = f"drop-weapon:{weapon.id}"
    assert option_id in [option["id"] for option in opened["combat"]["context_menu"]["options"]]

    dropped = session.confirm_combat_context_menu(option_id)
    dropped_inventory_item = next(
        item for item in dropped["combat"]["current_actor"]["inventory"] if item["id"] == weapon.id
    )

    assert dropped_inventory_item["equipped"] is False
    assert any(item["item_id"] == weapon.id for item in dropped["combat"]["dropped_weapons"])
    assert dropped["combat"]["turn_action"]["object_interaction_available"] is True
    assert dropped["combat"]["turn_action"]["action_use"] == "action_available"


def test_exploration_ui_session_stows_equipped_weapon_using_free_interaction() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    actor = session.combat_state.initiative_order.current_actor
    weapon = next(item for item in actor.inventory if item.kind == "weapon" and item.equipped)

    opened = session.select_board_position(actor.position)
    option_id = f"stow-weapon:{weapon.id}"
    option = next(
        candidate for candidate in opened["combat"]["context_menu"]["options"]
        if candidate["id"] == option_id
    )
    assert "darmową interakcję" in option["description"]

    stowed = session.confirm_combat_context_menu(option_id)
    item = next(
        candidate for candidate in stowed["combat"]["current_actor"]["inventory"]
        if candidate["id"] == weapon.id
    )
    assert item["equipped"] is False
    assert not any(candidate["item_id"] == weapon.id for candidate in stowed["combat"]["dropped_weapons"])
    assert stowed["combat"]["turn_action"]["object_interaction_available"] is False
    assert stowed["combat"]["turn_action"]["action_use"] == "action_available"


def test_exploration_ui_session_own_tile_opens_keyboard_driven_action_menu():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    actor = session.combat_state.initiative_order.current_actor

    opened = session.select_board_position(actor.position)

    menu = opened["combat"]["context_menu"]
    option_ids = [option["id"] for option in menu["options"]]
    assert menu["is_self_menu"] is True
    assert "basic:dash" in option_ids
    assert "basic:dodge" in option_ids
    assert "turn:end" in option_ids

    moved = session.move_combat_context_menu_selection(1)
    assert moved["combat"]["context_menu"]["selected_index"] == 1

    cancelled = session.cancel_combat_context_menu()
    assert cancelled["combat"]["context_menu"] is None


def test_exploration_ui_session_prone_and_stand_are_visible_self_actions():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    actor = session.combat_state.initiative_order.current_actor

    opened = session.select_board_position(actor.position)
    assert "basic:drop-prone" in {
        option["id"] for option in opened["combat"]["context_menu"]["options"]
    }

    prone = session.confirm_combat_context_menu("basic:drop-prone")
    assert prone["combat"]["current_actor"]["conditions"] == ["prone"]
    assert any(
        chip["label"] == "Powalony"
        for chip in prone["combat"]["current_actor"]["status_chips"]
    )
    assert prone["combat"]["turn_action"]["action_use"] == "action_available"

    reopened = session.select_board_position(actor.position)
    stand_option = next(
        option
        for option in reopened["combat"]["context_menu"]["options"]
        if option["id"] == "basic:stand-up"
    )
    assert "15 ft" in stand_option["description"]

    stood = session.confirm_combat_context_menu("basic:stand-up")
    assert stood["combat"]["current_actor"]["conditions"] == []
    assert stood["combat"]["turn_action"]["movement_used_feet"] == 15


def test_exploration_ui_session_shove_is_selected_from_enemy_field_and_applies_prone():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    hero = session.combat_state.initiative_order.current_actor
    goblin = next(actor for actor in session.combat_state.actors if actor.faction == Faction.ENEMY)
    session.combat_state = replace_actor(
        session.combat_state,
        replace(goblin, position=Coordinate(hero.position.col, hero.position.row + 1)),
    )
    goblin = next(actor for actor in session.combat_state.actors if actor.id == goblin.id)

    opened = session.select_board_position(goblin.position)
    option_ids = {option["id"] for option in opened["combat"]["context_menu"]["options"]}
    assert f"shove:prone:{goblin.id}" in option_ids
    attack_labels = {
        option["label"]
        for option in opened["combat"]["context_menu"]["options"]
        if option["category"] == "attack"
    }
    assert "Atak: Kusza" in attack_labels
    assert "Wyposaż i zaatakuj: Sztylet" not in attack_labels
    assert any(
        option["label"] == "Oblij lepką cieczą" and option["category"] == "item"
        for option in opened["combat"]["context_menu"]["options"]
    )

    pending = session.confirm_combat_context_menu(f"shove:prone:{goblin.id}")
    assert pending["combat"]["pending_combat_shove"]["target_id"] == str(goblin.id)
    assert pending["combat"]["pending_combat_shove"]["defender_check"]["label"] in {
        "Athletics",
        "Acrobatics",
    }

    session.encounter_rng.seed(1)
    resolved = session.submit_combat_shove(attacker_natural_roll=20)
    target = next(actor for actor in resolved["combat"]["actors"] if actor["id"] == str(goblin.id))
    assert target["conditions"] == ["prone"]
    assert resolved["combat"]["turn_action"]["action_use"] == "action_used"


def test_exploration_ui_session_grapple_is_selected_from_enemy_field_and_applied():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    hero = session.combat_state.initiative_order.current_actor
    goblin = next(actor for actor in session.combat_state.actors if actor.faction == Faction.ENEMY)
    session.combat_state = replace_actor(
        session.combat_state,
        replace(goblin, position=Coordinate(hero.position.col, hero.position.row + 1)),
    )
    goblin = next(actor for actor in session.combat_state.actors if actor.id == goblin.id)

    active = session.combat_state.initiative_order.current_actor
    two_handed = next(
        item
        for item in active.inventory
        if item.kind == "weapon" and item.equipped and item.hands_required == 2
    )
    blocked = session.select_board_position(goblin.position)
    hands = blocked["combat"]["current_actor"]["hands"]
    assert hands["main_hand"]["item_id"] == two_handed.id
    assert hands["off_hand"]["item_id"] == two_handed.id
    assert hands["free_hands"] == 0
    assert f"grapple:start:{goblin.id}" not in {
        option["id"] for option in blocked["combat"]["context_menu"]["options"]
    }
    session.cancel_combat_context_menu()
    session.select_board_position(active.position)
    session.confirm_combat_context_menu(f"drop-weapon:{two_handed.id}")

    opened = session.select_board_position(goblin.position)
    option_id = f"grapple:start:{goblin.id}"
    option = next(
        option
        for option in opened["combat"]["context_menu"]["options"]
        if option["id"] == option_id
    )
    assert option["category"] == "maneuver"

    pending = session.confirm_combat_context_menu(option_id)
    assert pending["combat"]["pending_combat_grapple"]["mode"] == "start"
    session.encounter_rng.seed(1)
    resolved = session.submit_combat_grapple(actor_natural_roll=20)

    target = next(actor for actor in resolved["combat"]["actors"] if actor["id"] == str(goblin.id))
    assert target["conditions"] == ["grappled"]
    assert any(chip["label"] == "Chwytany" for chip in target["status_chips"])
    assert resolved["combat"]["current_actor"]["hands"]["reserved_hands"] == 1
    assert resolved["combat"]["current_actor"]["hands"]["free_hands"] == 1
    assert resolved["combat"]["turn_action"]["action_use"] == "action_used"
    movement = resolved["combat"]["movement"]
    assert movement["base_speed_feet"] == 30
    assert movement["effective_speed_feet"] == 15
    assert movement["remaining_feet"] == 15
    assert movement["speed_reduction"] == "grappling"
    assert max(destination["cost_feet"] for destination in movement["destinations"]) <= 15

    destination = next(
        destination
        for destination in movement["destinations"]
        if destination["cost_feet"] == 5
    )
    preview = session.preview_combat_movement(
        col=destination["col"],
        row=destination["row"],
    )
    dragged = preview["combat"]["movement_preview"]["dragged_actor"]
    assert dragged["id"] == str(goblin.id)
    assert dragged["destination"] == [hero.position.col, hero.position.row]
    assert "przestaw" in session.board_message.lower()
    scan_target = session._current_board_scan_target()
    assert any(
        frame.color == LedColor.MENU_PINK
        and hero.position in frame.positions
        for frame in scan_target.feedback.frames
    )


def test_exploration_ui_session_explains_size_blocked_grapple_and_shove():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    actor = session.combat_state.initiative_order.current_actor
    enemy = next(
        candidate
        for candidate in session.combat_state.actors
        if candidate.faction == Faction.ENEMY
    )
    session.combat_state = replace_actor(
        session.combat_state,
        replace(
            enemy,
            size=CreatureSize.HUGE,
            damage_affinities=DamageAffinityProfile(
                resistances=(DamageType.FIRE,),
                immunities=(DamageType.POISON,),
                vulnerabilities=(DamageType.COLD,),
            ),
            position=Coordinate(actor.position.col, actor.position.row + 1),
        ),
    )
    enemy = next(
        candidate for candidate in session.combat_state.actors if candidate.id == enemy.id
    )

    opened = session.select_board_position(enemy.position)
    menu = opened["combat"]["context_menu"]
    option_ids = {option["id"] for option in menu["options"]}

    assert "Grapple i Shove są niedostępne" in menu["notice"]
    assert "ogromny" in menu["notice"]
    assert not any(option_id.startswith("grapple:start:") for option_id in option_ids)
    assert not any(option_id.startswith("shove:") for option_id in option_ids)
    target = next(item for item in opened["combat"]["actors"] if item["id"] == str(enemy.id))
    assert target["size"] == "huge"
    assert target["size_label"] == "ogromny"
    assert target["damage_affinities"] == {
        "resistances": [{"id": "fire", "label": "od ognia"}],
        "immunities": [{"id": "poison", "label": "od trucizny"}],
        "vulnerabilities": [{"id": "cold", "label": "od zimna"}],
    }


def test_exploration_ui_session_exposes_and_resolves_two_weapon_bonus_attack():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    encounter = session._active_encounter()
    assert encounter is not None
    actor = session.combat_state.initiative_order.current_actor
    crossbow = next(item for item in actor.inventory if item.id == "crossbow")
    dagger = next(item for item in actor.inventory if item.id == "dagger")
    actor = replace(
        actor,
        inventory=tuple(
            replace(
                item,
                hands_required=1,
                light_weapon=True,
                equipped=True,
                held_in=(HandSlot.MAIN_HAND,),
            )
            if item.id == crossbow.id
            else replace(item, equipped=True, held_in=(HandSlot.OFF_HAND,))
            if item.id == dagger.id
            else item
            for item in actor.inventory
        ),
    )
    session.combat_state = replace_actor(session.combat_state, actor)
    sources = encounter.attack_source_options_by_actor[actor.id]
    main_source = next(source for source in sources if source.source_item_id == "crossbow")
    off_source = next(source for source in sources if source.source_item_id == "dagger")
    encounter.attack_source_options_by_actor[actor.id] = tuple(
        replace(source, attack_kind=AttackKind.MELEE, range_feet=5)
        if source.id == main_source.id
        else source
        for source in sources
    )
    enemy = next(candidate for candidate in session.combat_state.actors if candidate.faction == Faction.ENEMY)
    session.combat_state = replace_actor(
        session.combat_state,
        replace(enemy, position=Coordinate(actor.position.col, actor.position.row + 1)),
    )
    enemy = next(candidate for candidate in session.combat_state.actors if candidate.id == enemy.id)

    session.selected_attack_source_ids[str(actor.id)] = main_source.id
    session.select_player_attack_target_at_position(enemy.position)
    session.confirm_player_attack_target()
    missed = session.submit_player_attack_roll(natural_roll=1)

    assert missed["combat"]["two_weapon"]["available"] is True
    assert missed["combat"]["two_weapon"]["source_ids"] == [off_source.id]
    option_id = f"two-weapon:{off_source.id}"
    option = next(
        option
        for option in session._combat_context_options(actor, enemy.position)
        if option.id == option_id
    )
    assert option.label == "Atak drugą bronią: Sztylet"

    selected = session.select_board_position(enemy.position)
    assert selected["combat"]["pending_player_attack"]["two_weapon_bonus"] is True
    confirmed = session.confirm_player_attack_target()
    assert "+ 3" not in confirmed["combat"]["pending_player_attack"]["damage_instruction"]
    hit = session.submit_player_attack_roll(natural_roll=20, natural_roll_2=19)

    assert hit["combat"]["turn_action"]["action_use"] == "action_used"
    assert hit["combat"]["turn_action"]["bonus_action_use"] == "action_used"
    assert "bez dodatniego modyfikatora cechy" in hit["combat"]["pending_player_attack"]["damage_instruction"]


def test_exploration_ui_session_offers_versatile_attack_when_second_hand_is_free():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    actor = session.combat_state.initiative_order.current_actor
    first_weapon = next(item for item in actor.inventory if item.kind == "weapon")
    actor = replace(
        actor,
        inventory=tuple(
            replace(
                item,
                id="longsword",
                source_ref="longsword",
                name="Miecz",
                hands_required=1,
                versatile_damage_dice="1d10",
                equipped=True,
                held_in=(HandSlot.MAIN_HAND,),
            )
            if item.id == first_weapon.id
            else replace(item, equipped=False, held_in=())
            if item.kind == "weapon"
            else item
            for item in actor.inventory
        ),
    )
    session.combat_state = replace_actor(session.combat_state, actor)
    enemy = next(
        candidate
        for candidate in session.combat_state.actors
        if candidate.faction == Faction.ENEMY
    )
    session.combat_state = replace_actor(
        session.combat_state,
        replace(enemy, position=Coordinate(actor.position.col, actor.position.row + 1)),
    )
    enemy = next(
        candidate for candidate in session.combat_state.actors if candidate.id == enemy.id
    )

    payload = session.state_payload()
    variants = {
        source["id"]: source
        for source in payload["combat"]["available_attack_sources"]
    }
    variant_id = "longsword_slash:two_handed"
    assert variants[variant_id]["damage_hint"].startswith("1d10")

    opened = session.select_board_position(enemy.position)
    option = next(
        option
        for option in opened["combat"]["context_menu"]["options"]
        if option["id"] == f"attack:{variant_id}"
    )
    assert option["label"] == "Atak: Miecz (oburącz)"

    selected = session.confirm_combat_context_menu(option["id"])
    assert selected["combat"]["pending_player_attack"]["source"]["id"] == variant_id
    confirmed = session.confirm_player_attack_target()
    assert "1d10" in confirmed["combat"]["pending_player_attack"]["damage_instruction"]


def test_exploration_ui_session_dons_shield_from_self_menu_and_updates_ac():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    actor = session.combat_state.initiative_order.current_actor
    shield = InventoryItem(
        "test_shield",
        "Tarcza testowa",
        "shield",
        equipped=False,
        hands_required=1,
        armor_class_bonus=2,
        armor_proficiency="shield",
    )
    actor = replace(
        actor,
        inventory=tuple(item for item in actor.inventory if item.kind != "shield") + (shield,),
        proficiencies=replace(
            actor.proficiencies,
            armor=tuple(dict.fromkeys((*actor.proficiencies.armor, "shield"))),
        ),
    )
    session.combat_state = replace_actor(session.combat_state, actor)

    opened = session.select_board_position(actor.position)
    option = next(
        option
        for option in opened["combat"]["context_menu"]["options"]
        if option["id"] == "don-shield:test_shield"
    )
    assert "+2 KP" in option["description"]

    equipped = session.confirm_combat_context_menu(option["id"])
    current = equipped["combat"]["current_actor"]
    equipped_shield = next(item for item in current["inventory"] if item["id"] == "test_shield")
    assert current["base_ac"] == actor.ac
    assert current["equipment_ac_bonus"] == 2
    assert current["ac"] == actor.ac + 2
    assert equipped_shield["equipped"] is True
    assert len(equipped_shield["held_in"]) == 1
    assert current["hands"]["free_hands"] <= 1
    assert equipped["combat"]["turn_action"]["action_use"] == "action_used"

def test_exploration_ui_session_grappled_hero_gets_escape_self_action():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    hero = session.combat_state.initiative_order.current_actor
    goblin = next(actor for actor in session.combat_state.actors if actor.faction == Faction.ENEMY)
    goblin = replace(goblin, position=Coordinate(hero.position.col, hero.position.row + 1))
    session.combat_state = replace_actor(session.combat_state, goblin)
    session.combat_state = replace(
        session.combat_state,
        condition_states=(
            ConditionState(str(hero.id), CombatCondition.GRAPPLED, str(goblin.id)),
        ),
    )

    opened = session.select_board_position(hero.position)
    escape_id = f"grapple:escape:{goblin.id}"
    assert escape_id in {
        option["id"] for option in opened["combat"]["context_menu"]["options"]
    }

    pending = session.confirm_combat_context_menu(escape_id)
    assert pending["combat"]["pending_combat_grapple"]["mode"] == "escape"
    session.encounter_rng.seed(1)
    escaped = session.submit_combat_grapple(actor_natural_roll=20)
    updated_hero = next(
        actor for actor in escaped["combat"]["actors"] if actor["id"] == str(hero.id)
    )
    assert updated_hero["conditions"] == []


def test_exploration_ui_session_targeted_inventory_action_is_contextual_and_consumed():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    hero = session.combat_state.initiative_order.current_actor
    goblin = next(actor for actor in session.combat_state.actors if actor.faction == Faction.ENEMY)
    session.combat_state = replace_actor(
        session.combat_state,
        replace(goblin, position=Coordinate(hero.position.col, hero.position.row + 1)),
    )
    goblin = next(actor for actor in session.combat_state.actors if actor.id == goblin.id)

    opened = session.select_board_position(goblin.position)
    item_option = next(
        option
        for option in opened["combat"]["context_menu"]["options"]
        if option["action"] == "targeted_item_action"
    )
    resolved = session.confirm_combat_context_menu(item_option["id"])

    updated_hero = next(actor for actor in resolved["combat"]["actors"] if actor["id"] == str(hero.id))
    sticky_flask = next(item for item in updated_hero["inventory"] if item["id"] == "sticky_flask")
    updated_goblin = next(actor for actor in resolved["combat"]["actors"] if actor["id"] == str(goblin.id))
    assert sticky_flask["quantity"] == 0
    assert updated_goblin["effects"] == []
    assert "restrained" in updated_goblin["conditions"]
    assert any(chip["label"] == "Unieruchomiony" for chip in updated_goblin["status_chips"])
    assert resolved["combat"]["turn_action"]["action_use"] == "action_used"


def test_combat_condition_save_is_visible_and_blocks_turn_end_until_resolved():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    hero = session.combat_state.initiative_order.current_actor
    poisoned = ConditionState(
        str(hero.id),
        CombatCondition.POISONED,
        source_label="Trucizna testowa",
        save_ability="constitution",
        save_dc=10,
        save_timing=ConditionSaveTiming.TURN_END,
    )
    session.combat_state = replace(
        session.combat_state,
        condition_states=(poisoned,),
    )

    payload = session.state_payload()["combat"]

    assert payload["condition_saves"][0]["condition"] == "poisoned"
    assert payload["condition_saves"][0]["roll_mode"] == "normal"
    with pytest.raises(ValueError, match="rzut obronny końca tury"):
        session.finish_combat_turn()

    resolved = session.submit_combat_condition_save(
        condition="poisoned",
        natural_roll=20,
    )

    assert resolved["combat"]["condition_saves"] == []
    assert "poisoned" not in resolved["combat"]["current_actor"]["conditions"]


def test_combat_payload_exposes_dynamic_aura_coverage():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    cleric = next(actor for actor in session.combat_state.actors if str(actor.id) == "cleric")
    hero = next(actor for actor in session.combat_state.actors if str(actor.id) == "hero")
    session.combat_state = replace(
        session.combat_state,
        actors=tuple(
            replace(actor, position=cleric.position)
            if actor.id == hero.id
            else actor
            for actor in session.combat_state.actors
        ),
    )

    payload = session.state_payload()["combat"]

    aura = next(item for item in payload["auras"] if item["id"] == "protective_reliquary")
    assert aura["effect_kind"] == "saving_throw_bonus"
    assert aura["value"] == 1
    assert "hero" in aura["affected_actor_ids"]

    session.combat_state = replace(
        session.combat_state,
        actors=tuple(replace(actor, hp=0) if actor.id == cleric.id else actor for actor in session.combat_state.actors),
    )
    assert session.state_payload()["combat"]["auras"] == []


def test_turn_start_trigger_is_visible_and_applied_in_combat_ui():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    entries = session.combat_state.initiative_order.entries
    guard_index = next(
        index for index, entry in enumerate(entries) if str(entry.actor.id) == "goblin_b"
    )
    previous_index = (guard_index - 1) % len(entries)
    session.combat_state = replace(
        session.combat_state,
        initiative_order=replace(
            session.combat_state.initiative_order,
            current_index=previous_index,
        ),
    )

    payload = session.finish_combat_turn()["combat"]

    assert payload["current_actor"]["id"] == "goblin_b"
    assert payload["current_actor"]["temp_hp"] == 2
    assert payload["current_actor"]["triggers"][0]["event_type"] == "turn_start"
    assert any(message.title == "Aktywowano cechę" for message in session.messages)


def test_enemy_condition_save_is_resolved_automatically_at_turn_boundary():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    enemy = next(actor for actor in session.combat_state.actors if actor.faction == Faction.ENEMY)
    restrained = ConditionState(
        str(enemy.id),
        CombatCondition.RESTRAINED,
        source_label="Lepka ciecz",
        save_ability="dexterity",
        save_dc=0,
        save_timing=ConditionSaveTiming.TURN_END,
    )
    state = replace(session.combat_state, condition_states=(restrained,))

    resolved = session._resolve_automatic_condition_saves(
        state,
        enemy,
        ConditionSaveTiming.TURN_END,
    )

    assert resolved.condition_states == ()
    assert session.messages[-1].title == "Rzut przeciw warunkowi"
    assert "stan usunięty" in session.messages[-1].body


def test_exploration_ui_session_can_equip_carried_weapon_and_attack_from_target_menu():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    hero = next(actor for actor in session.combat_state.actors if str(actor.id) == "hero")
    current_index = next(
        index
        for index, entry in enumerate(session.combat_state.initiative_order.entries)
        if entry.actor.id == hero.id
    )
    session.combat_state = replace(
        session.combat_state,
        initiative_order=replace(session.combat_state.initiative_order, current_index=current_index),
    )
    hero = replace(
        hero,
        inventory=tuple(
            replace(item, equipped=False, held_in=()) if item.kind == "weapon" else item
            for item in hero.inventory
        ),
    )
    session.combat_state = replace_actor(session.combat_state, hero)
    goblin = next(actor for actor in session.combat_state.actors if actor.faction == Faction.ENEMY)
    session.combat_state = replace_actor(
        session.combat_state,
        replace(goblin, position=Coordinate(hero.position.col, hero.position.row + 1)),
    )
    goblin = next(actor for actor in session.combat_state.actors if actor.id == goblin.id)

    opened = session.select_board_position(goblin.position)
    equip_attack = next(
        option
        for option in opened["combat"]["context_menu"]["options"]
        if option["action"] == "equip_and_attack" and option["source_id"] == "crossbow_shot"
    )
    selected = session.confirm_combat_context_menu(equip_attack["id"])

    assert selected["combat"]["pending_player_attack"]["source"]["id"] == "crossbow_shot"
    assert selected["combat"]["pending_player_attack"]["target"]["id"] == str(goblin.id)
    assert selected["combat"]["turn_action"]["object_interaction_available"] is False
    assert selected["combat"]["turn_action"]["action_use"] == "action_available"


def test_exploration_ui_session_cart_climb_moves_actor_and_adds_attack_bonus_next_turn():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)

    state = session.submit_combat_movement(col=7, row=7)
    actor_id = state["combat"]["current_actor"]["id"]
    session.select_board_position(Coordinate(7, 8))
    session.confirm_combat_context_menu("interact:broken_cart")

    climbed = session.confirm_combat_interaction("climb_cart")
    actor = next(candidate for candidate in climbed["combat"]["actors"] if candidate["id"] == actor_id)

    assert actor["position"] == [7, 8]
    assert actor["effects"][0]["kind"] == "grant_attack_bonus_while_on_object"
    assert climbed["combat"]["turn_action"]["action_use"] == "action_used"

    session.finish_combat_turn()
    while session.combat_state is not None and str(session.combat_state.initiative_order.current_actor.id) != actor_id:
        session.finish_combat_turn()

    selected = session.select_player_attack_target_at_position(Coordinate(7, 9))
    modifiers = selected["combat"]["pending_player_attack"]["active_modifiers"]

    assert any(modifier["label"] == "Pozycja na wozie" and modifier["value"] == 2 for modifier in modifiers)


def test_exploration_ui_session_cart_interactions_are_shown_with_interactive_leds():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    board = FakeBoardConnection()
    session.attach_board_connection(board, backend="simulator")
    session.scan_board_selection()

    colored_positions = {}
    for positions, rgb_color in board.led_calls:
        if positions == "off":
            continue
        if rgb_color and all(isinstance(channel, int) for channel in rgb_color):
            colored_positions.update({position: rgb_color for position in positions})
        else:
            colored_positions.update(dict(zip(positions, rgb_color, strict=True)))

    assert colored_positions[(7, 8)] == list(LedColor.INTERACTIVE_OBJECT)
    assert colored_positions[(8, 8)] == list(LedColor.INTERACTIVE_OBJECT)


def test_exploration_ui_session_fallen_gate_remains_non_interactive_blocking_terrain():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    encounter = session._active_encounter()
    assert encounter is not None
    actor = session.combat_state.initiative_order.current_actor

    for position in (Coordinate(8, 5), Coordinate(9, 5)):
        assert encounter.board.terrain_at(position).blocks_movement is True
        assert session._combat_context_options(actor, position) == ()


def test_exploration_ui_session_rubble_action_only_appears_with_adjacent_enemy():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    active_actor = session.combat_state.initiative_order.current_actor
    session.combat_state = replace_actor(session.combat_state, replace(active_actor, position=Coordinate(10, 7)))
    for enemy in tuple(actor for actor in session.combat_state.actors if actor.faction == Faction.ENEMY):
        session.combat_state = replace_actor(session.combat_state, replace(enemy, position=Coordinate(20, 15)))

    without_enemy = session._combat_context_options(
        session.combat_state.initiative_order.current_actor,
        Coordinate(10, 7),
    )

    assert "interact:rubble_patch" not in [option.id for option in without_enemy]

    enemy = next(actor for actor in session.combat_state.actors if actor.faction == Faction.ENEMY)
    session.combat_state = replace_actor(session.combat_state, replace(enemy, position=Coordinate(11, 7)))
    with_enemy = session._combat_context_options(
        session.combat_state.initiative_order.current_actor,
        Coordinate(10, 7),
    )

    assert "interact:rubble_patch" in [option.id for option in with_enemy]


def test_exploration_ui_session_rubble_interaction_penalizes_adjacent_enemy_attack():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    session.encounter_rng = random.Random(1)
    active_actor = session.combat_state.initiative_order.current_actor
    session.combat_state = replace_actor(session.combat_state, replace(active_actor, position=Coordinate(10, 7)))

    selected = session.select_board_position(Coordinate(10, 7))

    assert selected["combat"]["context_menu"]["is_self_menu"] is True
    assert "interact:rubble_patch" in [option["id"] for option in selected["combat"]["context_menu"]["options"]]
    interaction = session.confirm_combat_context_menu("interact:rubble_patch")
    assert interaction["combat"]["pending_combat_interaction"]["object_id"] == "rubble_patch"
    assert [option["id"] for option in interaction["combat"]["pending_combat_interaction"]["options"]] == ["throw_rubble"]

    applied = session.confirm_combat_interaction("throw_rubble")
    enemy = next(actor for actor in applied["combat"]["actors"] if actor["id"] == "goblin_b")

    assert applied["combat"]["turn_action"]["action_use"] == "action_used"
    assert enemy["effects"][0]["kind"] == "grant_next_attack_penalty"
    assert enemy["effects"][0]["value"] == -2
    assert enemy["effects"][0]["value_label"] == "-2 do następnego ataku"
    assert enemy["effects"][0]["expires"] == "znika po następnym ataku"
    assert enemy["effects"][0]["summary"] == (
        "Gruz w oczach | -2 do następnego ataku | "
        "znika po następnym ataku | źródło: Rumowisko"
    )
    assert enemy["effects"][0]["source"] == {
        "type": "scene",
        "id": "rubble_patch",
        "label": "Rumowisko",
    }
    assert any(chip["label"] == "Gruz w oczach: -2 do następnego ataku" and chip["tone"] == "penalty" for chip in enemy["status_chips"])
    assert any(message["title"] == "Interakcja" and "Gruz w oczach" in message["body"] for message in applied["messages"])
    assert any(message["title"] == "Interakcja" and "rzut obronny na Zręczność" in message["body"] for message in applied["messages"])
    assert any(message["title"] == "Interakcja" and "ST 12" in message["body"] for message in applied["messages"])

    enemy_actor = next(actor for actor in session.combat_state.actors if str(actor.id) == "goblin_b")
    source = session.encounter_setup_flow.encounter.attack_sources_by_actor[enemy_actor.id]
    modified_source = session._effective_attack_source(enemy_actor, source)

    assert any(
        modifier.label == "Gruz w oczach" and modifier.value == -2
        for modifier in modified_source.attack_roll_request.modifiers
    )


def test_exploration_ui_session_rubble_tile_is_interactive_when_actor_stands_on_it():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    active_actor = session.combat_state.initiative_order.current_actor
    session.combat_state = replace_actor(session.combat_state, replace(active_actor, position=Coordinate(10, 7)))
    board = FakeBoardConnection()
    session.attach_board_connection(board, backend="simulator")
    session.scan_board_selection()

    colored_positions = {}
    for positions, rgb_color in board.led_calls:
        if positions == "off":
            continue
        if rgb_color and all(isinstance(channel, int) for channel in rgb_color):
            colored_positions.update({position: rgb_color for position in positions})
        else:
            colored_positions.update(dict(zip(positions, rgb_color, strict=True)))

    assert colored_positions[(10, 7)] == list(LedColor.INTERACTIVE_OBJECT)


def test_exploration_ui_session_enemy_turn_waits_for_board_confirmation():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_combat_from_scout_alarm(session)

    while session.combat_state is not None and session.combat_state.initiative_order.current_actor.faction != Faction.ENEMY:
        session.finish_combat_turn()
    assert session.combat_state is not None
    enemy_id = str(session.combat_state.initiative_order.current_actor.id)
    board = FakeBoardConnection()
    session.attach_board_connection(board, backend="simulator")

    intent = session.resolve_enemy_turn()

    assert intent["combat"]["current_actor"]["id"] == enemy_id
    assert intent["combat"]["enemy_turn_intent"] is not None
    assert intent["combat"]["enemy_turn_preview"] is None
    assert any(message["title"] == "Zamiar przeciwnika" for message in intent["messages"])
    intent_payload = intent["combat"]["enemy_turn_intent"]
    highlighted_positions = {
        tuple(position)
        for positions, _color in board.led_calls
        if positions != "off"
        for position in positions
    }
    if intent_payload["kind"] == "movement":
        assert tuple(intent_payload["destination"]) in highlighted_positions
    if intent_payload.get("target_position"):
        assert tuple(intent_payload["target_position"]) in highlighted_positions

    preview = session.resolve_enemy_turn()

    assert preview["combat"]["current_actor"]["id"] == enemy_id
    assert preview["combat"]["enemy_turn_intent"] is None
    assert preview["combat"]["enemy_turn_preview"] is not None
    assert any(message["title"] in {"Ruch przeciwnika", "Atak przeciwnika"} for message in preview["messages"])

    enemy_preview = preview["combat"]["enemy_turn_preview"]
    if enemy_preview["kind"] == "movement":
        click = tuple(enemy_preview["destination"])
    else:
        click = tuple(enemy_preview["target_position"])
    if "natural_roll" in enemy_preview:
        assert isinstance(enemy_preview["natural_roll"], int)
        assert isinstance(enemy_preview["total"], int)
        assert "hit" in enemy_preview
    board.clicks.append(click)

    result = session.scan_board_selection()

    assert result["combat"]["enemy_turn_preview"] is None
    assert result["combat"]["enemy_turn_result"] is not None
    assert result["combat"]["current_actor"]["id"] == enemy_id
    if "natural_roll" in enemy_preview:
        assert "Rzut d20:" in result["combat"]["enemy_turn_result"]["message"]
        assert "wynik końcowy:" in result["combat"]["enemy_turn_result"]["message"]

    state = session.confirm_enemy_turn_result()

    assert any(message["title"] == "Tura przeciwnika" for message in state["messages"])
    if "natural_roll" in enemy_preview:
        assert any(
            message["title"] == "Tura przeciwnika" and "Rzut d20:" in message["body"] and "wynik końcowy:" in message["body"]
            for message in state["messages"]
        )
    assert state["combat"]["enemy_turn_preview"] is None
    assert state["combat"]["enemy_turn_result"] is None
    assert state["combat"]["current_actor"]["id"] != enemy_id or state["combat"]["status"] == "finished"


def test_enemy_save_attack_waits_for_manual_hero_d20_in_ui() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    while session.combat_state is not None and session.combat_state.initiative_order.current_actor.faction != Faction.ENEMY:
        session.finish_combat_turn()
    assert session.combat_state is not None
    enemy = session.combat_state.initiative_order.current_actor
    encounter = session._active_encounter()
    assert encounter is not None
    encounter.attack_sources_by_actor[enemy.id] = replace(
        encounter.attack_sources_by_actor[enemy.id],
        name="Ognisty wyziew",
        range_feet=100,
        attack_kind=AttackKind.RANGED,
        reach_feet=None,
        damage_fixed=8,
        damage_modifier=0,
        damage_type="fire",
        save_ability="dexterity",
        save_dc=12,
        save_damage_on_success="half",
    )
    board = FakeBoardConnection()
    session.attach_board_connection(board, backend="simulator")

    session.resolve_enemy_turn()
    preview = session.resolve_enemy_turn()
    enemy_preview = preview["combat"]["enemy_turn_preview"]
    assert enemy_preview["saving_throw_request"]["ability"] == "dexterity"
    target_id = enemy_preview["target_id"]
    target_before = next(actor for actor in session.combat_state.actors if str(actor.id) == target_id)
    board.clicks.append(tuple(enemy_preview["target_position"]))

    pending = session.scan_board_selection()

    assert pending["combat"]["pending_enemy_saving_throw"] is not None
    assert pending["combat"]["pending_enemy_saving_throw"]["request"]["dc"] == 12
    assert pending["combat"]["enemy_turn_result"] is not None
    assert next(actor for actor in session.combat_state.actors if str(actor.id) == target_id).hp == target_before.hp
    with pytest.raises(ValueError, match="Najpierw wpisz"):
        session.confirm_enemy_turn_result()

    resolved = session.submit_enemy_saving_throw(20)

    save = resolved["combat"]["enemy_turn_result"]["saving_throw_result"]
    assert save["success"] is True
    assert resolved["combat"]["pending_enemy_saving_throw"] is None
    assert resolved["combat"]["enemy_turn_result"]["damage_result"]["damage"] == 4


def test_exploration_ui_session_can_reset_board_scan():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    board = FakeBoardConnection()
    session.attach_board_connection(board, backend="simulator")

    state = session.reset_board_scan()

    assert board.reset_calls == ["reset_connection"]
    assert state["board"]["message"] == "Zresetowano oczekiwanie na kliknięcie planszy."


def test_exploration_ui_session_reset_restores_initial_state():
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(_challenge_proposal()),
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.submit_action("Wyważamy bramę.")
    session.decide("accept")
    session.resolve_rolls({"hero": 16})

    session.reset()
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    state = session.state_payload()

    assert state["active_challenge"]["current_progress"] == 0
    assert state["flags"] == []


def test_exploration_ui_session_applies_resource_modifier_to_roll_plan():
    proposal = _challenge_proposal(
        approach_label="Wspinaczka po linie",
        approach_tags=["climbing"],
        ability="dexterity",
        skill="acrobatics",
        used_resource_ids=["rope"],
        player_narration="Zaczepiacie linę z hakiem i wspinacie się nad bramę.",
    )
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(proposal),
    )
    session.state = replace(
        session.state,
        resources=tuple(
            replace(resource, advantage=True) if resource.id == "rope" else resource
            for resource in session.state.resources
        ),
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    pending = session.submit_action("Przerzucamy linę z hakiem i wspinamy się nad bramę.")
    accepted = session.decide("accept")

    assert pending["pending"]["resources"][0]["id"] == "rope"
    assert pending["pending"]["resources"][0]["consume_on_use"] is False
    plan = accepted["pending"]["check_plan"]
    assert plan["resource"]["id"] == "rope"
    assert plan["resource"]["advantage"] is True
    assert plan["roll_mode"] == "advantage"
    assert accepted["required_rolls"][0]["requires_second_roll"] is True
    hero_modifiers = next(
        entry["modifiers"]
        for entry in plan["roll_modifiers_by_actor_id"]
        if entry["actor_id"] == "hero"
    )
    assert {modifier["label"]: modifier["value"] for modifier in hero_modifiers}["Lina z hakiem"] == 2


def test_exploration_ui_session_consumes_one_use_resource_after_roll_and_logs_effect(tmp_path):
    proposal = _challenge_proposal(
        approach_label="Ciche podważenie bramy",
        approach_tags=["lever", "quiet"],
        ability="intelligence",
        skill=None,
        used_resource_ids=["wedge"],
        player_narration="Wbijacie drewniany klin pod mechanizm i podważacie bramę po cichu.",
    )
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(proposal),
        session_id="resource_consumption_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    pending = session.submit_action("Używamy drewnianego klina, żeby cicho podważyć bramę.")
    session.decide("accept")
    resolved = session.resolve_rolls({"hero": 10})

    assert pending["pending"]["resources"][0]["id"] == "wedge"
    assert pending["pending"]["resources"][0]["consume_on_use"] is True
    assert "wedge" not in session.state.inventory_resource_ids
    assert {resource["id"] for resource in resolved["resources"]} == {"rope"}
    events = [__import__("json").loads(line) for line in session.observer.path.read_text(encoding="utf-8").splitlines()]
    effect = next(
        event
        for event in events
        if event["event_type"] == "ui_effect_applied"
        and event["payload"]["source"] == "challenge_resource_consumption"
    )
    assert effect["payload"]["effect"] == {
        "type": "remove_resource",
        "parameters": {"resource_id": "wedge"},
    }
    assert effect["payload"]["inventory_resource_ids"] == ["rope"]


def test_exploration_ui_session_can_change_or_clear_resource_before_roll():
    proposal = _challenge_proposal(
        approach_label="Ciche podważenie bramy",
        approach_tags=["lever", "quiet"],
        ability="intelligence",
        skill=None,
        used_resource_ids=[],
        player_narration="Próbujecie podważyć bramę po cichu.",
    )
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(proposal),
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.submit_action("Próbujemy cicho podważyć bramę.")

    with pytest.raises(ValueError, match="nie jest dostępny albo nie pasuje"):
        session.update_pending_challenge_decision({"resource_id": "rope"})

    selected = session.update_pending_challenge_decision(
        {
            "mechanic_id": "single_actor_check",
            "check_participants": "single_actor",
            "check_aggregation": "lead_result",
            "lead_actor_id": "hero",
            "ability": "intelligence",
            "dc": 15,
            "resource_id": "wedge",
        }
    )
    cleared = session.update_pending_challenge_decision({"resource_id": ""})
    session.decide("reject")

    assert selected["pending"]["resources"][0]["id"] == "wedge"
    assert "resources" not in cleared["pending"]
    assert "wedge" in session.state.inventory_resource_ids


def test_death_save_failure_is_visible_and_advances_turn() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    combat = _start_gate_skirmish(session)
    actor = combat.initiative_order.current_actor
    session.combat_state = replace_actor(
        combat,
        replace(actor, hp=0, uses_death_saves=True, death_saves=DeathSaveState()),
    )

    before = session.state_payload()
    after = session.submit_death_save(9)

    downed = next(item for item in after["combat"]["actors"] if item["id"] == str(actor.id))
    assert before["combat"]["death_save_required"] is True
    assert after["combat"]["current_actor"]["id"] != str(actor.id)
    assert downed["death_saves"]["failures"] == 1
    assert after["messages"][-1]["title"] == "Rzut śmierci"


def test_natural_twenty_death_save_restores_actor_and_keeps_turn() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    combat = _start_gate_skirmish(session)
    actor = combat.initiative_order.current_actor
    session.combat_state = replace_actor(
        combat,
        replace(
            actor,
            hp=0,
            uses_death_saves=True,
            death_saves=DeathSaveState(successes=1, failures=2),
        ),
    )

    payload = session.submit_death_save(20)

    assert payload["combat"]["current_actor"]["id"] == str(actor.id)
    assert payload["combat"]["current_actor"]["hp"] == 1
    assert payload["combat"]["death_save_required"] is False
    assert payload["combat"]["turn_action"]["action_use"] == "action_available"


def test_dropped_weapon_stays_on_board_and_is_unavailable_after_revival() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    combat = _start_gate_skirmish(session)
    actor = combat.initiative_order.current_actor
    session.combat_state = replace_actor(combat, replace(actor, hp=0, uses_death_saves=True))

    downed = session.state_payload()
    revived = session.submit_death_save(20)

    dropped = downed["combat"]["dropped_weapons"]
    sword = next(source for source in revived["combat"]["available_attack_sources"] if source["source_item_id"])
    assert dropped
    assert all(item["source_actor_id"] == str(actor.id) for item in dropped)
    assert all(item["position"] == [actor.position.col, actor.position.row] for item in dropped)
    assert sword["available"] is False
    assert "leży na polu" in sword["unavailable_reason"]


def test_death_save_route_rejects_skipping_the_roll_and_accepts_d20() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    combat = _start_gate_skirmish(session)
    actor = combat.initiative_order.current_actor
    session.combat_state = replace_actor(combat, replace(actor, hp=0, uses_death_saves=True))
    client = create_app(session).test_client()

    skipped = client.post("/api/combat/end-turn", json={})
    rolled = client.post("/api/combat/death-save", json={"natural_roll": 10})

    assert skipped.status_code == 400
    assert "rzut śmierci" in skipped.get_json()["error"]
    assert rolled.status_code == 200


def test_combat_ui_stabilizes_adjacent_ally_with_medicine() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    combat = _start_gate_skirmish(session)
    healer = combat.initiative_order.current_actor
    target = next(actor for actor in combat.actors if actor.faction == Faction.ALLY and actor.id != healer.id)
    target = replace(
        target,
        hp=0,
        position=Coordinate(healer.position.col + 1, healer.position.row),
        uses_death_saves=True,
        death_saves=DeathSaveState(failures=1),
    )
    session.combat_state = replace_actor(combat, target)

    before = session.state_payload()
    response = create_app(session).test_client().post(
        "/api/combat/stabilize",
        json={"target_id": str(target.id), "method": "medicine", "natural_roll": 20},
    )
    after = response.get_json()

    assert response.status_code == 200
    target_after = next(actor for actor in after["combat"]["actors"] if actor["id"] == str(target.id))
    assert [actor["id"] for actor in before["combat"]["stabilization"]["targets"]] == [str(target.id)]
    assert target_after["death_saves"]["stable"] is True
    assert after["combat"]["turn_action"]["action_use"] == "action_used"
    assert after["messages"][-1]["title"] == "Stabilizacja"


def test_attack_against_unconscious_target_has_advantage_and_close_hit_is_critical() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    combat = _start_gate_skirmish(session)
    attacker = combat.initiative_order.current_actor
    target = next(actor for actor in combat.actors if actor.faction == Faction.ENEMY)
    target = replace(
        target,
        hp=0,
        position=Coordinate(attacker.position.col + 1, attacker.position.row),
        uses_death_saves=True,
        death_saves=DeathSaveState(),
    )
    session.combat_state = replace_actor(combat, target)

    selected = session.select_player_attack_target_at_position(target.position)
    session.confirm_player_attack_target()
    rolled = session.submit_player_attack_roll(natural_roll=10, natural_roll_2=11)

    assert selected["combat"]["pending_player_attack"]["attack_mode"] == "advantage"
    assert rolled["combat"]["pending_player_attack"]["natural_rolls"] == [10, 11]
    assert rolled["combat"]["pending_player_attack"]["critical"] is True
