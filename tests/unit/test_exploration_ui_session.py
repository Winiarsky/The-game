import json
import random
from dataclasses import replace

import pytest

from dnd_board_game.actors import (
    ActorResourcePool,
    ActorTrigger,
    CreatureSize,
    DamageAffinityProfile,
    DeathSaveState,
    Faction,
    FeatureGrant,
    FeatureSourceKind,
    RecoveryPeriod,
    TriggerEffectKind,
    TriggerEventType,
)
from dnd_board_game.actions import PlayerIntentHint
from dnd_board_game.combat import (
    ActionUse,
    AmmunitionExpenditure,
    AttackDeclaration,
    AttackKind,
    AttackSource,
    AttackSourceType,
    BattlefieldLoot,
    CombatMenuAction,
    CombatStatus,
    CombatCondition,
    ConditionSaveTiming,
    ConditionState,
    EnemyAutoTurnResult,
    HiddenState,
    ReactionKind,
    ReactionOption,
    SceneConclusionType,
    SceneObjective,
    SceneObjectiveCondition,
    SpellSlotState,
    open_reaction_window,
    actor_as_combat_target,
    current_actor,
    replace_actor,
    reaction_available_for,
    resolve_attack,
    scene_flag,
    set_scene_flag,
)
from dnd_board_game.combat.damage import DamageComponentInput, DamageType, apply_damage_result, resolve_damage
from dnd_board_game.exploration import (
    advance_exploration_time,
    CraftingComponentSelection,
    CraftingDraft,
    ExplorationChallengeState,
    challenge_state_for,
    add_exploration_condition,
    ExplorationTrapStatus,
    reveal_exploration_points,
    trap_state_for,
    build_crafting_source_registry,
    craft_temporary_item,
)
from dnd_board_game.hardware import LedColor, LedRole
from dnd_board_game.inventory import ArmorCategory, HandSlot, InventoryItem, LootBundle
from dnd_board_game.inventory.economy import CurrencyWallet
from dnd_board_game.llm import (
    GmClassifierProposal,
    GmDeclarationAnalysis,
    GmDeclarationAnalysisType,
    NpcInteractionProposal,
)
from dnd_board_game.rules import (
    ActiveEffect,
    D20RollInput,
    D20RollRequest,
    EffectDuration,
    EffectSource,
    EffectSourceType,
    RollMode,
    resolve_d20_roll,
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


class FakeConversationCheckGmClient:
    model = "fake-conversation-check-gm"

    def __init__(self):
        self.requests = []

    def analyze(self, request):
        self.requests.append(request)
        return GmDeclarationAnalysis.model_validate(
            {
                "analysis_type": "player_question",
                "action_flow": "player_question",
                "player_message": (
                    "Brama nie nosi tabliczki „w środku siedzą gobliny”, bo nawet gobliny "
                    "mają resztki instynktu samozachowawczego. Jeśli chcecie pewności, "
                    "nasłuchajcie albo zajrzyjcie przez szczelinę."
                ),
                "reason": "Pytanie dotyczy ukrytej informacji i wymaga działania graczy.",
                "confidence": 1.0,
                "response_kind": "requires_check",
                "requires_check": True,
                "suggested_followup": "Nasłuchuję albo zaglądam przez szczelinę.",
                "observation_id": "look_through_gate_gap",
            }
        )

    def classify(self, request):  # noqa: ARG002
        raise AssertionError("Swobodna rozmowa z MG nie powinna uruchamiać klasyfikatora próby.")


class FakeInvalidConversationGmClient:
    model = "fake-invalid-conversation-gm"

    def analyze(self, request):  # noqa: ARG002
        return GmDeclarationAnalysis.model_validate(
            {
                "analysis_type": "player_question",
                "player_message": "Okolica jest na pewno bezpieczna.",
                "response_kind": "observation",
                "grounded_fact_ids": ["fact:nieistniejacy_fakt"],
                "hint_level": 1,
            }
        )

    def classify(self, request):  # noqa: ARG002
        raise AssertionError("Swobodna rozmowa z MG nie powinna uruchamiać próby.")


class FakeWorldActionGmClient:
    model = "fake-world-action-gm"

    def analyze(self, request):
        return GmDeclarationAnalysis.model_validate(
            {
                "analysis_type": "world_action",
                "action_flow": "world_action",
                "player_message": (
                    "Struga spływa po murze z godnością godną królewskiego herbu. "
                    "Wasza deklaracja o siekaniu goblinów niesie się jednak znacznie dalej — "
                    "za bramą milkną głosy, po czym szczękają wyciągane ostrza. Subtelność właśnie umarła."
                ),
                "normalized_intent": "Głośna prowokacja goblinów pod murem.",
                "reason": "Czynność nie otwiera bramy, ale natychmiast alarmuje strażników.",
                "confidence": 1.0,
                "immediate_effects": [
                    {
                        "type": "add_noise",
                        "parameters": {"challenge_id": "closed_gate", "value": 3},
                    },
                    {
                        "type": "add_complication",
                        "parameters": {
                            "challenge_id": "closed_gate",
                            "value": "alarm_w_strażnicy",
                        },
                    },
                ],
            }
        )

    def classify(self, request):  # noqa: ARG002
        raise AssertionError("Działanie w świecie nie powinno trafiać do klasyfikatora challenge.")


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
            ExplorationChallengeState(challenge_id="closed_gate", noise=2),
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


def _prepare_gate_encounter_setup(session: ExplorationUiSession) -> None:
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    flags = set_scene_flag(session.state.flags, "gate_passed", True)
    flags = set_scene_flag(flags, "gate_lock_critical", True)
    flags = set_scene_flag(flags, "gate_bolt_critical", True)
    session.state = replace(
        session.state,
        flags=flags,
    )
    session.state_payload()
    session.resolve_encounter_opening()
    session.start_encounter_setup()
    while session.encounter_setup_flow is not None and not session.encounter_setup_flow.completed:
        if session.encounter_setup_flow.is_player_start_step:
            position = session.encounter_setup_flow.remaining_player_start_positions()[0]
            session.assign_encounter_player_start_position(position)
        else:
            session.confirm_encounter_setup_step()


@pytest.mark.parametrize("party_size", (1, 3, 4, 5))
def test_gate_encounter_start_zone_expands_for_selected_custom_party(party_size):
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
    )
    templates = tuple(
        actor
        for actor in session.exploration.actors
        if actor.faction == Faction.ALLY
    )
    party = tuple(
        replace(
            templates[index % len(templates)],
            id=f"custom_{index + 1}",
            name=f"Bohater {index + 1}",
        )
        for index in range(party_size)
    )
    session.configure_custom_party(party)
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    flags = set_scene_flag(session.state.flags, "gate_passed", True)
    session.state = replace(session.state, flags=flags)
    session.state_payload()
    session.resolve_encounter_opening()

    session.start_encounter_setup()
    flow = session.encounter_setup_flow
    assert flow is not None
    start_step = next(
        step
        for step in flow.steps
        if step.label == "pola startowe bohaterów"
    )
    assert len(start_step.positions) >= party_size
    while flow is not None and not flow.completed:
        if flow.is_player_start_step:
            session.assign_encounter_player_start_position(
                flow.remaining_player_start_positions()[0]
            )
        else:
            session.confirm_encounter_setup_step()
        flow = session.encounter_setup_flow

    assert session.encounter_setup_flow is not None
    assert session.encounter_setup_flow.completed is True
    assert len(session.encounter_setup_flow.player_start_assignments) == party_size


def test_submit_action_rejects_new_declaration_while_resolution_is_pending():
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        debug_challenge_id="closed_gate",
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.pending = PendingInteraction(
        kind=PendingKind.TRAP,
        stage=PendingStage.DECISION,
    )
    message_count = len(session.messages)

    with pytest.raises(ValueError, match="Najpierw rozstrzygnij"):
        session.submit_action("Próbuję teraz użyć łomu.")

    assert len(session.messages) == message_count


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

    state = session.submit_action(
        "Wyważamy bramę.",
        selected_goal_id="force_entry",
        selected_check_participants="single_actor",
        participant_actor_ids=("hero",),
    )
    assert state["pending"]["stage"] == "decision"
    assert state["active_challenge"]["current_progress"] == 0
    assert state["conversation"]["entries"][-1]["title"] == "Narracja MG"
    assert state["conversation"]["entries"][-1]["body"] == "Napieracie na skrzydła bramy."
    assert "Test:" not in state["conversation"]["entries"][-1]["body"]
    assert state["pending"]["option"]["ability"] == "strength"
    assert state["pending"]["option"]["dc"] == 15
    assert state["pending"]["option"]["progress_on_success"] == 0
    assert state["pending"]["option"]["progress_on_failure"] == 0

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


def test_open_lock_goal_is_consumed_and_makes_later_force_check_easier():
    lock_proposal = _challenge_proposal(
        approach_label="Ciche otwarcie zamka",
        approach_tags=["lockpicking", "rusted_lock", "quiet"],
        ability="dexterity",
        skill=None,
        tool="thieves_tools",
        player_narration="Łotrzyca bierze zamek na osobistą rozmowę przy pomocy wytrychów.",
    )
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(lock_proposal),
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    preview = session.submit_action(
        "Otwieram zamek po cichu.",
        selected_goal_id="open_lock",
        participant_actor_ids=("rogue",),
    )

    assert preview["pending"]["option"]["id"] == "lockpick_gate"
    assert preview["pending"]["option"]["dc"] == 15
    session.decide("accept", lead_actor_id="rogue")
    resolved = session.resolve_rolls({"rogue": 16})

    assert resolved["pending"] is None
    assert scene_flag(session.state.flags, "gate_lock_cleared") is True
    assert scene_flag(session.state.flags, "gate_bolt_cleared") is not True
    assert challenge_state_for(session.state, "closed_gate").noise == 0
    assert "open_lock" not in {
        goal["id"] for goal in resolved["active_challenge"]["goals"]
    }
    bolt_goal = next(
        goal
        for goal in resolved["active_challenge"]["goals"]
        if goal["id"] == "remove_bolt"
    )
    assert bolt_goal["image"] == "assets/gate_bolt.webp"
    with pytest.raises(ValueError, match="Wybrany cel nie jest dostępny"):
        session.submit_action(
            "Otwieram ten sam zamek jeszcze raz.",
            selected_goal_id="open_lock",
        )

    session.gm_client = FakeGmClient(_challenge_proposal())
    force_preview = session.submit_action(
        "Teraz wyważamy to, co jeszcze trzyma.",
        selected_goal_id="force_entry",
        selected_check_participants="lead_with_help",
        participant_actor_ids=("hero",),
    )

    assert force_preview["pending"]["option"]["id"] == "force_gate"
    assert force_preview["pending"]["option"]["dc"] == 13
    assert force_preview["selected_lead_actor_id"] == "hero"


def test_gate_flow_owns_check_mechanics_and_drops_llm_numeric_modifier():
    client = FakeGmClient(
        _challenge_proposal(
            ability="charisma",
            skill="deception",
            difficulty_tier="hard",
            dc=18,
            situational_modifiers=[
                {
                    "label": "Prowizoryczny taran",
                    "modifier": 1,
                    "source": "player_declaration",
                    "reason": "Gracze opisali użycie ciężkiej belki jako tarana.",
                    "roll_mode": "normal",
                }
            ],
            player_narration=(
                "Bohater prowadzi belkę prosto w bramę, jakby drewno właśnie "
                "obraziło honor całej drużyny."
            ),
        )
    )
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=client,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    preview = session.submit_action(
        "Bohater bierze ciężką belkę i używa jej jak tarana.",
        selected_goal_id="force_entry",
        selected_check_participants="single_actor",
        participant_actor_ids=("hero",),
    )

    option = preview["pending"]["option"]
    assert option["id"] == "force_gate"
    assert option["ability"] == "strength"
    assert option["skill"] == "athletics"
    assert option["dc"] == 15
    assert option["situational_modifiers"] == []
    flow_route = client.requests[0].to_prompt_payload()["challenge"][
        "selected_flow_route"
    ]
    assert flow_route == {
        "transition_id": "force_gate",
        "route_kind": "challenge_option",
        "option_id": "force_gate",
        "mechanics_owned_by_runtime": True,
        "ability": "strength",
        "skill": "athletics",
        "tool": None,
        "dc": 15,
    }


def test_gate_flow_accepts_reduced_llm_method_contract_without_check_fields():
    proposal = GmClassifierProposal.model_validate(
        {
            "intent_type": "challenge_attempt",
            "approach_label": "Bohaterskie użycie barku",
            "approach_tags": ["heavy_force"],
            "action_flow": "challenge_attempt",
            "requires_roll_now": True,
            "player_narration": (
                "Bohater rozpędza się ku bramie. Brama, choć pozbawiona nóg, "
                "wygląda jakby przez moment rozważała ucieczkę."
            ),
        }
    )
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(proposal),
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    preview = session.submit_action(
        "Bohater z rozpędu wali barkiem w bramę.",
        selected_goal_id="force_entry",
        selected_check_participants="single_actor",
        participant_actor_ids=("hero",),
    )

    option = preview["pending"]["option"]
    assert option["ability"] == "strength"
    assert option["skill"] == "athletics"
    assert option["dc"] == 15
    assert option["check_participants"] == "single_actor"
    assert option["check_aggregation"] == "lead_result"


def test_goal_single_check_requires_exactly_one_capable_actor():
    proposal = _challenge_proposal(
        approach_label="Otwarcie zamka",
        approach_tags=["lockpicking", "quiet"],
        ability="dexterity",
        skill=None,
        tool="thieves_tools",
    )
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(proposal),
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    open_lock = next(
        goal
        for goal in session.state_payload()["active_challenge"]["goals"]
        if goal["id"] == "open_lock"
    )
    assert open_lock["check_participants"] == "single_actor"
    assert open_lock["eligible_actor_ids"] == ["rogue"]
    with pytest.raises(ValueError, match="dokładnie jedna"):
        session.submit_action("Otwieram zamek.", selected_goal_id="open_lock")
    with pytest.raises(ValueError, match="nie spełniają wymagań"):
        session.submit_action(
            "Otwieram zamek.",
            selected_goal_id="open_lock",
            participant_actor_ids=("hero",),
        )
    with pytest.raises(ValueError, match="wymusza inny typ"):
        session.submit_action(
            "Wszyscy otwieramy zamek.",
            selected_goal_id="open_lock",
            selected_check_participants="whole_party",
        )


def test_allow_goal_accepts_player_selected_single_check():
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(_challenge_proposal()),
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    preview = session.submit_action(
        "Bohater sam wyważa bramę.",
        selected_goal_id="force_entry",
        selected_check_participants="single_actor",
        participant_actor_ids=("hero",),
    )

    assert preview["pending"]["option"]["check_participants"] == "single_actor"
    assert preview["pending"]["option"]["check_aggregation"] == "lead_result"


def test_goal_help_check_allows_optional_helper_and_only_lead_rolls():
    proposal = _challenge_proposal()
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(proposal),
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    force_goal = next(
        goal
        for goal in session.state_payload()["active_challenge"]["goals"]
        if goal["id"] == "force_entry"
    )
    assert force_goal["participant_mode"] == "allow"
    assert force_goal["allowed_check_participants"] == [
        "single_actor",
        "lead_with_help",
        "whole_party",
    ]
    with pytest.raises(ValueError, match="wybierz typ testu"):
        session.submit_action(
            "Wyważam bramę barkiem.",
            selected_goal_id="force_entry",
            participant_actor_ids=("hero",),
        )
    without_help = session.submit_action(
        "Wyważam bramę barkiem.",
        selected_goal_id="force_entry",
        selected_check_participants="lead_with_help",
        participant_actor_ids=("hero",),
    )
    assert without_help["pending"]["option"]["check_participants"] == "lead_with_help"
    session.decide("accept")
    assert session.pending is not None and session.pending.check_plan is not None
    assert session.pending.check_plan.roll_mode == RollMode.NORMAL
    assert [roll["actor_id"] for roll in session.state_payload()["required_rolls"]] == ["hero"]

    helped_session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(proposal),
    )
    helped_session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    preview = helped_session.submit_action(
        "Bohater napiera, a Kapłan pomaga.",
        selected_goal_id="force_entry",
        selected_check_participants="lead_with_help",
        participant_actor_ids=("hero", "cleric"),
    )
    assert preview["pending"]["participant_actor_ids"] == ["hero", "cleric"]
    helped_session.decide("accept", lead_actor_id="rogue")
    assert helped_session.pending is not None and helped_session.pending.check_plan is not None
    assert helped_session.pending.check_plan.lead_actor_id == "hero"
    assert helped_session.pending.check_plan.helper_actor_id == "cleric"
    assert helped_session.pending.check_plan.roll_mode == RollMode.ADVANTAGE
    assert [roll["actor_id"] for roll in helped_session.state_payload()["required_rolls"]] == ["hero"]


def test_goal_group_check_rolls_for_everyone_and_uses_majority():
    proposal = _challenge_proposal(
        approach_label="Wspólne wyważenie",
        approach_tags=["heavy_force"],
        ability="strength",
        skill="athletics",
    )
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(proposal),
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    with pytest.raises(ValueError, match="automatycznie cała drużyna"):
        session.submit_action(
            "Wszyscy wyważamy bramę.",
            selected_goal_id="force_entry",
            selected_check_participants="whole_party",
            participant_actor_ids=("hero",),
        )
    preview = session.submit_action(
        "Wszyscy wyważamy bramę.",
        selected_goal_id="force_entry",
        selected_check_participants="whole_party",
    )
    assert preview["pending"]["participant_actor_ids"] == ["hero", "rogue", "cleric"]
    assert preview["pending"]["option"]["check_participants"] == "whole_party"
    assert preview["pending"]["option"]["check_aggregation"] == "majority"
    session.decide("accept")
    required = session.state_payload()["required_rolls"]
    assert [roll["actor_id"] for roll in required] == ["hero", "rogue", "cleric"]


def test_absurd_but_possible_world_action_gets_fictional_response_and_alerts_goblins() -> None:
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeWorldActionGmClient(),
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    state = session.submit_action("Sikam na mur i krzyczę, że rozsiekam gobliny!")

    challenge_state = challenge_state_for(session.state, "closed_gate")
    assert challenge_state.noise == 3
    assert "alarm_w_strażnicy" in challenge_state.complications
    assert state["pending"] is None
    assert state["conversation"]["entries"][-1]["title"] == "Świat odpowiada"
    assert "Subtelność właśnie umarła" in state["conversation"]["entries"][-1]["body"]


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


def test_failed_hazard_save_adds_prone_and_persistent_poisoned_conditions() -> None:
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
    assert [condition["id"] for condition in hero_payload["conditions"]] == [
        "prone",
        "poisoned",
    ]
    assert hero_payload["conditions"][0]["recoverable"] is True
    assert hero_payload["conditions"][1]["duration"] == "until_short_rest"
    assert any(item["label"] == "Stan: Bohater" for item in failed["scene_status"])

    recovered = session.recover_exploration_condition(actor_id="hero", condition="prone")

    hero_payload = next(actor for actor in recovered["actors"] if actor["id"] == "hero")
    assert [condition["id"] for condition in hero_payload["conditions"]] == [
        "poisoned",
    ]
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


def test_scenario_condition_returns_from_encounter_until_its_rest_boundary() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    poisoned = ConditionState(
        "hero",
        CombatCondition.POISONED,
        source_label="Zatrute kolce",
        duration=EffectDuration.UNTIL_SHORT_REST,
    )
    session.state = replace(session.state, condition_states=(poisoned,))

    _start_combat_from_scout_alarm(session)

    assert session.combat_state is not None
    assert poisoned in session.combat_state.condition_states
    for actor in tuple(session.combat_state.actors):
        if actor.faction == Faction.ENEMY:
            session.combat_state = replace_actor(
                session.combat_state,
                replace(actor, hp=0),
            )

    resolved = session.resolve_active_combat()

    assert session.state.condition_states == (poisoned,)
    hero = next(actor for actor in resolved["actors"] if actor["id"] == "hero")
    assert len(hero["conditions"]) == 1
    assert hero["conditions"][0]["id"] == "poisoned"
    assert hero["conditions"][0]["duration"] == "until_short_rest"
    assert hero["conditions"][0]["source_label"] == "Zatrute kolce"


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
    detected = session.resolve_rolls(
        {"rogue": {"natural_roll": 20, "natural_roll_2": 20}}
    )
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
    session.resolve_rolls(
        {"rogue": {"natural_roll": 20, "natural_roll_2": 20}}
    )
    session.submit_action("/akcja rozbrajam linkę alarmową")
    session.decide("accept")

    triggered = session.resolve_rolls({"rogue": 1})

    assert triggered["pending"]["stage"] == "hazard_save"
    assert triggered["pending"]["hazard"]["id"] == "gate_alarm_wire_trigger"
    assert trap_state_for(session.state, "gate_alarm_wire").status == ExplorationTrapStatus.TRIGGERED
    assert next(
        item
        for item in triggered["scene_status"]
        if item["label"].startswith("Pułapka:")
    )["value"] == "uruchomiona — oczekuje na rzut obronny"

    resolved = session.resolve_rolls({"rogue": 1})

    assert resolved["pending"] is None
    assert next(
        item
        for item in resolved["scene_status"]
        if item["label"].startswith("Pułapka:")
    )["value"] == "uruchomiona — rozstrzygnięta"
    assert next(
        item for item in session.state.challenge_states if item.challenge_id == "closed_gate"
    ).noise == 3
    assert scene_flag(session.state.flags, "gate_alarm_triggered") is True


def test_hidden_trap_does_not_trigger_after_critical_gate_breach() -> None:
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
    resolved = session.resolve_rolls({"hero": 20})

    assert resolved["pending"] is None
    assert scene_flag(session.state.flags, "gate_critical_breach") is True
    assert trap_state_for(session.state, "gate_alarm_wire").status == ExplorationTrapStatus.HIDDEN


def test_hidden_trap_still_triggers_after_normal_gate_success() -> None:
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
    triggered = session.resolve_rolls({"hero": 15})

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


def test_use_command_accepts_full_actor_inventory_source_id_from_classifier(tmp_path):
    source_id = "actor:rogue:item:thieves_tools"
    proposal = _challenge_proposal(
        selected_mechanic="use_item_check",
        approach_label="Otwieranie zatartego zamka",
        approach_tags=["lockpicking", "rusted_lock", "quiet"],
        ability="dexterity",
        skill="sleight_of_hand",
        used_resource_ids=[source_id],
    )
    client = FakeUseSourceGmClient(proposal, source_id)
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=client,
        session_id="use_actor_inventory_source_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    state = session.submit_action(
        "/uzyj używam narzędzi złodziejskich i próbuję otworzyć zardzewiały zamek"
    )

    assert state["pending"]["kind"] == "challenge"
    assert state["pending"]["option"]["requires_item_ids"] == ["thieves_tools"]
    assert state["pending"]["source_use"]["id"] == source_id
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
    assert preview["pending"]["option"]["progress_on_success"] == 0
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

    state = session.submit_action(
        "szukam jakiegoś kija, którym mógłbym zdjąć rygiel przez szparę",
        selected_goal_id="look_around",
        participant_actor_ids=("hero",),
    )

    assert state["pending"]["kind"] == "source_selection"
    assert state["pending"].get("observation") is None
    assert state["pending"]["source_selection"]["requested_name"] == "kij"
    assert state["pending"]["source_selection"]["candidates"][0]["label"] == "Drewniana deska"
    assert client.requests == []


def test_known_plank_use_routes_to_authored_bolt_action_without_llm(tmp_path):
    client = FakeGmClient(_challenge_proposal())
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=client,
        session_id="procedural_plank_bolt_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.state = replace(
        session.state,
        flags=set_scene_flag(session.state.flags, "gate_lock_cleared", True),
    )

    proposed = session.submit_action(
        "Używam znalezionej deski i podważam nią rygiel możliwie cicho.",
        selected_goal_id="remove_bolt",
        selected_check_participants="single_actor",
        participant_actor_ids=("hero",),
    )

    assert proposed["pending"]["option"]["id"] == "pry_bolt_with_plank"
    assert proposed["pending"]["source_use"]["id"] == "zone:gate:item:gate_rotten_planks"
    assert proposed["pending"]["option"]["ability"] == "strength"
    assert proposed["pending"]["option"]["skill"] == "athletics"
    assert proposed["pending"]["option"]["dc"] == 12
    assert client.requests == []

    session.decide("accept")
    resolved = session.resolve_rolls({"hero": 12})

    assert scene_flag(session.state.flags, "gate_bolt_cleared", False) is True
    assert resolved["pending"]["kind"] == "trap"


def test_conversation_only_question_gives_gm_hint_without_starting_check(tmp_path):
    client = FakeConversationCheckGmClient()
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=client,
        session_id="gm_conversation_only_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    state = session.submit_action(
        "Czy ta brama wygląda na strzeżoną od środka?",
        conversation_only=True,
    )

    assert state["pending"] is None
    assert state["conversation"]["entries"][-1]["title"] == "Odpowiedź MG"
    assert "nasłuchajcie" in state["conversation"]["entries"][-1]["body"]
    assert scene_flag(session.state.flags, "gate_goblins_spotted", False) is False
    assert client.requests[0].to_prompt_payload()["conversation_only"] is True


def test_conversation_only_never_executes_action_even_if_llm_misclassifies_it(tmp_path):
    client = FakeGmClient(_challenge_proposal())
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=client,
        session_id="gm_conversation_guard_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    state = session.submit_action(
        "Rozwalam bramę barkiem.",
        conversation_only=True,
    )

    assert state["pending"] is None
    assert "wybierzcie odpowiedni cel" in state["conversation"]["entries"][-1]["body"].lower()
    assert client.requests == []


def test_invalid_gm_conversation_is_recovered_as_fiction_instead_of_technical_error(tmp_path):
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeInvalidConversationGmClient(),
        session_id="gm_conversation_fallback_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    state = session.submit_action(
        "Czy okolica jest w miarę bezpieczna? Czy nie kręci się tu jakiś przeciwnik?",
        conversation_only=True,
    )

    assert state["pending"] is None
    answer = state["conversation"]["entries"][-1]
    assert answer["title"] == "Odpowiedź MG"
    assert "Ruiny nie wystawiają certyfikatów bezpieczeństwa" in answer["body"]
    assert "hint_level" not in answer["body"]
    assert "Deklaracja wymaga korekty" not in {
        entry["title"] for entry in state["conversation"]["entries"]
    }


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
    assert rolling["required_rolls"][0]["roll_mode"] == "disadvantage"
    resolved = session.resolve_rolls(
        {"hero": {"natural_roll": 16, "natural_roll_2": 16}}
    )

    assert resolved["pending"] is None
    assert scene_flag(session.state.flags, "courtyard_activity_suspected", False) is True
    assert scene_flag(session.state.flags, "gate_goblins_spotted", False) is True
    assert scene_flag(session.state.flags, "gate_goblins_positions_known", False) is False
    assert resolved["messages"][-1]["title"] == "Wynik rozpoznania"
    assert "dwie niewielkie" in resolved["messages"][-1]["body"]
    assert resolved["active_challenge"]["current_progress"] == 0


def test_look_around_keeps_preselected_actor_and_reveals_contextual_finds(tmp_path):
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(_challenge_proposal()),
        session_id="contextual_gate_search_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    proposed = session.submit_action(
        "Rozglądam się za czymś przydatnym.",
        selected_goal_id="look_around",
        participant_actor_ids=("hero",),
    )

    assert proposed["pending"]["kind"] == "observation"
    assert proposed["pending"]["observation"]["id"] == "survey_gate_surroundings"
    assert proposed["pending"]["participant_actor_ids"] == ["hero"]

    rolling = session.decide("accept", lead_actor_id="rogue")
    assert [roll["actor_id"] for roll in rolling["required_rolls"]] == ["hero"]
    resolved = session.resolve_rolls({"hero": 16})

    assert scene_flag(session.state.flags, "gate_ram_materials_found", False) is True
    assert scene_flag(session.state.flags, "weak_left_hinge_found", False) is True
    assert scene_flag(session.state.flags, "gate_wall_route_found", False) is True
    assert "use_wall_route" in {
        goal["id"] for goal in resolved["active_challenge"]["goals"]
    }


def test_rope_can_be_selected_then_attached_for_later_wall_attempt(tmp_path):
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(
            _challenge_proposal(
                approach_label="Mocowanie liny",
                approach_tags=["climbing", "wall_climb"],
                ability="wisdom",
                skill="survival",
                player_narration="Bohater sprawdza kamień i osadza hak.",
            )
        ),
        session_id="attach_wall_rope_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.state = replace(
        session.state,
        flags=set_scene_flag(
            session.state.flags,
            "gate_wall_route_found",
            True,
        ),
    )

    goals_before = {
        goal["id"]: goal
        for goal in session.state_payload()["active_challenge"]["goals"]
    }
    assert "use_wall_route" in goals_before
    assert "use_attached_wall_route" not in goals_before
    assert goals_before["attach_wall_rope"]["source_required"] is True
    assert [
        source["id"]
        for source in goals_before["attach_wall_rope"]["action_sources"]
        if source["available"]
    ] == ["resource:rope"]

    proposed = session.submit_action(
        "Zakładam hak w szczelinie i szarpię linę, zanim zaufa jej reszta.",
        selected_goal_id="attach_wall_rope",
        participant_actor_ids=("hero",),
        selected_action_source_id="resource:rope",
    )

    assert proposed["pending"] is not None, (
        session.gm_client.requests[-1].declaration_thread[-1].content
        if session.gm_client.requests[-1].declaration_thread
        else proposed["messages"][-1]["body"]
    )
    assert proposed["pending"]["action_source"]["id"] == "resource:rope"
    assert proposed["pending"]["resources"][0]["id"] == "rope"
    assert session.gm_client.requests == []
    rolling = proposed
    assert rolling["pending"]["check_plan"]["resource"]["label"] == "Lina z hakiem"
    assert rolling["pending"]["check_plan"]["resource"]["modifier"] == 2

    resolved = session.resolve_rolls({"hero": 20})

    assert scene_flag(
        session.state.flags,
        "gate_climbing_rope_attached",
        False,
    ) is True
    goals_after = {
        goal["id"]: goal
        for goal in resolved["active_challenge"]["goals"]
    }
    assert "use_wall_route" not in goals_after
    assert "attach_wall_rope" not in goals_after
    assert "use_attached_wall_route" in goals_after
    attached_route = next(
        option
        for option in session.active_challenge.options
        if option.id == "find_way_around"
    )
    assert ("gate_climbing_rope_attached", -2) in attached_route.dc_modifiers_if_flags


def test_exploration_time_burns_out_active_torch(tmp_path):
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        session_id="light_duration_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    lit = session.change_actor_light(
        actor_id="hero",
        item_id="torch",
        action="ignite",
    )
    hero = next(
        actor for actor in session.exploration.actors if str(actor.id) == "hero"
    )
    assert hero.active_light is not None
    assert lit["flow"]["visibility"][0]["light_source_actor_id"] == "hero"

    session._advance_scenario_time(60, source="test")
    state = session.state_payload()
    hero = next(
        actor for actor in session.exploration.actors if str(actor.id) == "hero"
    )

    assert hero.active_light is None
    assert state["flow"]["visibility"][0]["perceived_light"] == "dim"
    assert state["messages"][-1]["title"] == "Źródło światła zgasło"


def test_active_exploration_search_reveals_trap_and_advances_time(tmp_path):
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        session_id="active_search_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    rolling = session.start_exploration_search("rogue")

    assert rolling["pending"]["kind"] == "search"
    assert rolling["required_rolls"][0]["roll_mode"] == "disadvantage"

    resolved = session.resolve_rolls(
        {"rogue": {"natural_roll": 20, "natural_roll_2": 20}}
    )

    assert resolved["pending"] is None
    assert session.state.elapsed_minutes == 10
    assert session.state.exhausted_search_zones == ("gate",)
    assert (
        trap_state_for(session.state, "gate_alarm_wire").status
        == ExplorationTrapStatus.REVEALED
    )
    assert resolved["flow"]["awareness"]["search_available"] is False


def test_exploration_hide_is_saved_and_igniting_light_reveals_actor(tmp_path):
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        session_id="exploration_hide_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    rolling = session.start_exploration_hide("hero")
    assert rolling["pending"]["kind"] == "hide"
    hidden = session.resolve_rolls({"hero": 15})

    assert hidden["flow"]["awareness"]["hidden_actor_states"][0][
        "actor_id"
    ] == "hero"

    revealed = session.change_actor_light(
        actor_id="hero",
        item_id="torch",
        action="ignite",
    )

    assert revealed["flow"]["awareness"]["hidden_actor_states"] == []


def test_fixture_unlock_open_and_loot_flow_is_local_and_persistent(tmp_path):
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        session_id="fixture_container_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    chest_id = "gate_supply_chest"

    initial = next(
        item for item in session.state_payload()["flow"]["fixtures"]
        if item["id"] == chest_id
    )
    assert initial["locked"] is True
    assert initial["current_hit_points"] == 10

    rolling = session.start_exploration_fixture_action(
        actor_id="rogue",
        fixture_id=chest_id,
        operation="unlock",
    )
    assert rolling["pending"]["kind"] == "fixture"
    assert rolling["required_rolls"][0]["tool"] == "thieves_tools"
    session.resolve_rolls({"rogue": 20})

    opened = session.start_exploration_fixture_action(
        actor_id="rogue",
        fixture_id=chest_id,
        operation="open",
    )
    chest = next(
        item for item in opened["flow"]["fixtures"] if item["id"] == chest_id
    )
    assert chest["opened"] is True
    assert chest["locked"] is False

    looted = session.start_exploration_fixture_action(
        actor_id="rogue",
        fixture_id=chest_id,
        operation="loot",
    )
    chest = next(
        item for item in looted["flow"]["fixtures"] if item["id"] == chest_id
    )
    assert chest["looted"] is True
    assert any(
        item.source_id == "zone:gate:item:gate_chest_arrows"
        for item in session.state.source_discoveries
    )


def test_hidden_cache_becomes_a_lootable_fixture_only_after_its_point_is_revealed():
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.state = replace(
        session.state,
        party_position=replace(
            session.state.party_position,
            zone_id="courtyard",
        ),
    )

    assert not any(
        item["id"] == "hidden_cache"
        for item in session.state_payload()["flow"]["fixtures"]
    )

    session.state, _ = reveal_exploration_points(
        session.state,
        ("hidden_cache",),
    )
    fixture = next(
        item
        for item in session.state_payload()["flow"]["fixtures"]
        if item["id"] == "hidden_cache"
    )
    assert {action["operation"] for action in fixture["actions"]} == {"open"}

    session.start_exploration_fixture_action(
        actor_id="rogue",
        fixture_id="hidden_cache",
        operation="open",
    )
    looted = session.start_exploration_fixture_action(
        actor_id="rogue",
        fixture_id="hidden_cache",
        operation="loot",
    )

    fixture = next(
        item for item in looted["flow"]["fixtures"]
        if item["id"] == "hidden_cache"
    )
    assert fixture["looted"] is True
    assert any(
        item.source_id == "zone:courtyard:item:scout_cache_dagger"
        for item in session.state.source_discoveries
    )
    proposed = session.submit_action("/wez sztylet")
    assert proposed["pending"]["kind"] == "collection"

    collected = session.decide("accept", lead_actor_id="rogue")
    rogue = next(actor for actor in collected["actors"] if actor["id"] == "rogue")
    assert any(
        item["id"] == "collected:courtyard:scout_cache_dagger"
        and item["source_ref"] == "dagger"
        for item in rogue["inventory"]
    )


def test_fixture_damage_respects_ac_threshold_hp_and_destruction(tmp_path):
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        session_id="fixture_damage_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    chest_id = "gate_supply_chest"

    missed = session.damage_exploration_fixture(
        actor_id="hero",
        fixture_id=chest_id,
        attack_total=14,
        damage=20,
    )
    chest = next(
        item for item in missed["flow"]["fixtures"] if item["id"] == chest_id
    )
    assert chest["current_hit_points"] == 10

    resisted = session.damage_exploration_fixture(
        actor_id="hero",
        fixture_id=chest_id,
        attack_total=15,
        damage=2,
    )
    chest = next(
        item for item in resisted["flow"]["fixtures"] if item["id"] == chest_id
    )
    assert chest["current_hit_points"] == 10

    destroyed = session.damage_exploration_fixture(
        actor_id="hero",
        fixture_id=chest_id,
        attack_total=15,
        damage=10,
    )
    chest = next(
        item for item in destroyed["flow"]["fixtures"] if item["id"] == chest_id
    )
    assert chest["destroyed"] is True
    assert chest["current_hit_points"] == 0


def test_open_exploration_door_is_non_blocking_in_encounter_projection(tmp_path):
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        session_id="fixture_encounter_bridge_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.start_exploration_fixture_action(
        actor_id="rogue",
        fixture_id="watchtower_gate",
        operation="unlock",
    )
    session.resolve_rolls({"rogue": 20})
    session.start_exploration_fixture_action(
        actor_id="rogue",
        fixture_id="watchtower_gate",
        operation="open",
    )
    flags = set_scene_flag(session.state.flags, "gate_passed", True)
    flags = set_scene_flag(flags, "gate_lock_critical", True)
    flags = set_scene_flag(flags, "gate_bolt_critical", True)
    session.state = replace(session.state, flags=flags)
    session.state_payload()
    session.resolve_encounter_opening()
    session.start_encounter_setup()

    assert session.encounter_setup_flow is not None
    gate = next(
        item
        for item in session.encounter_setup_flow.encounter.scene_objects
        if item.id == "fixture:gate:watchtower_gate"
    )
    assert gate.blocks_movement is False
    assert gate.projectile_cover_bonus == 0


def test_exploration_hide_is_reused_after_encounter_setup(tmp_path):
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        session_id="exploration_hide_bridge_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.start_exploration_hide("rogue")
    session.resolve_rolls({"rogue": 15})
    flags = set_scene_flag(session.state.flags, "gate_passed", True)
    flags = set_scene_flag(flags, "gate_lock_critical", True)
    flags = set_scene_flag(flags, "gate_bolt_critical", True)
    session.state = replace(session.state, flags=flags)
    session.state_payload()
    session.resolve_encounter_opening()
    session.start_encounter_setup()

    while (
        session.encounter_setup_flow is not None
        and not session.encounter_setup_flow.completed
    ):
        if session.encounter_setup_flow.is_player_start_step:
            session.assign_encounter_player_start_position(
                session.encounter_setup_flow.remaining_player_start_positions()[0]
            )
        else:
            session.confirm_encounter_setup_step()

    stealth = session.state_payload()["encounter_stealth"]
    rogue = next(
        actor for actor in stealth["actors"] if actor["actor_id"] == "rogue"
    )

    assert rogue["attempted"] is True
    assert rogue["result"]["total"] == 22
    assert rogue["can_attempt"] is False
    assert session.state.hidden_actor_states == ()


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


def test_selected_observer_names_leader_and_does_not_add_technical_gm_chat(tmp_path):
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(_challenge_proposal()),
        session_id="selected_observer_narration_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    state = session.submit_action(
        "Cicho podkradam się pod bramę i zerkam przez szczelinę, czy nikogo nie ma po drugiej stronie.",
        selected_goal_id="look_around",
        participant_actor_ids=("rogue",),
    )

    assert state["pending"]["kind"] == "observation"
    assert state["pending"]["observation"]["description"].startswith(
        "Łotrzyca zagląda"
    )
    assert not any(
        entry["title"] == "MG proponuje sprawdzenie"
        for entry in state["conversation"]["entries"]
    )


def test_initiative_passively_moves_led_focus_between_actors_without_board_scan() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _prepare_gate_encounter_setup(session)
    session.finish_precombat_stealth()
    board = FakeBoardConnection()
    session.attach_board_connection(board, backend="simulator")

    state = session.start_encounter_initiative()

    first_prompt = session.encounter_initiative_flow.current_prompt
    assert first_prompt is not None
    assert board.led_calls[-1] == (
        [first_prompt.actor.position.as_tuple()],
        list(LedColor.ACTIVE_ACTOR),
    )
    assert session._current_board_scan_target().positions == ()

    state = session.submit_encounter_initiative_roll(12)

    second_prompt = session.encounter_initiative_flow.current_prompt
    assert second_prompt is not None
    assert second_prompt.actor.id != first_prompt.actor.id
    assert board.led_calls[-2] == ("off", None)
    assert board.led_calls[-1] == (
        [second_prompt.actor.position.as_tuple()],
        list(LedColor.ACTIVE_ACTOR),
    )
    assert state["encounter_initiative"]["current_prompt"]["actor_id"] == str(second_prompt.actor.id)


def test_active_exploration_npc_does_not_claim_actor_led_focus() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    board = FakeBoardConnection()
    session.attach_board_connection(board, backend="simulator")
    session.active_point_id = "wounded_scout"
    point = session.active_point
    assert point is not None

    session._sync_board_leds()

    target = session._current_board_scan_target()
    pads = session.state_payload()["flow"]["board_interaction"]["pads"]
    assert target.positions == tuple(
        Coordinate(*pad["position"]) for pad in pads
    )
    assert target.feedback.frames
    assert all(
        frame.role == LedRole.INTERACTIVE_OBJECT
        for frame in target.feedback.frames
    )
    assert all(frame.role != LedRole.ACTIVE_ACTOR for frame in target.feedback.frames)
    assert not any(
        positions == [position.as_tuple() for position in point.positions]
        and color == list(LedColor.ACTIVE_ACTOR)
        for positions, color in board.led_calls
        if positions != "off"
    )

    selection = session.set_exploration_board_selection(True)

    assert selection["active_point"]["id"] == "wounded_scout"
    assert session._current_board_scan_target().positions


def test_entering_courtyard_requires_scout_placement_then_exposes_actions_and_npc_led() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    board = FakeBoardConnection()
    session.attach_board_connection(board, backend="simulator")
    flags = set_scene_flag(session.state.flags, "gate_passed", True)
    flags = set_scene_flag(flags, "gate_skirmish_cleared", True)
    session.state = replace(session.state, flags=flags)
    session.resolved_encounter_trigger_ids.add("gate_open_skirmish")
    session.state, _ = reveal_exploration_points(session.state, ("wounded_scout",))
    session.ui_flow_stage = UiFlowStage.LOCATION_PREVIEW
    session.preview_zone_id = "courtyard"

    setup = session.confirm_location_preview()

    assert setup["flow"]["stage"] == "party_setup"
    assert setup["exploration_setup"]["paper_map"]["id"] == "watchtower_overview"

    setup = session.confirm_exploration_setup_step()

    step = setup["exploration_setup"]["current_step"]
    assert step["requires_board_assignment"] is True
    assert step["assignment_point_id"] == "wounded_scout"
    assert step["assignment_point_name"] == "Ranny zwiadowca"
    assert step["available_positions"] == [[8, 8], [8, 9], [9, 8], [9, 9]]
    assert "Ranny zwiadowca" in step["message"]
    assert "Dziedziniec" in step["message"]
    with pytest.raises(ValueError, match="Najpierw ustaw figurkę"):
        session.confirm_exploration_setup_step()

    active = session._handle_board_position(Coordinate(9, 9))

    assert active["flow"]["stage"] == "location_active"
    assert active["exploration_setup"] is None
    scout = next(point for point in active["current_zone_points"] if point["id"] == "wounded_scout")
    assert scout["positions"] == [[9, 9]]
    assert [goal["id"] for goal in active["active_challenge"]["goals"]] == [
        "survey_courtyard"
    ]
    assert active["active_challenge"]["goals"][0]["image"] == "assets/courtyard_search.png"
    assert scout["interaction_label"] == "Podejdź do rannego zwiadowcy"
    assert scout["image"] == "assets/courtyard_wounded_scout.png"
    assert scene_flag(
        session.state.flags,
        "exploration_point_placed_wounded_scout",
        False,
    ) is True

    session.select_point("wounded_scout")
    assert session.active_point is not None
    assert session.active_point.id == "wounded_scout"
    assert session.pending_encounter is None
    assert session.exploration_setup_flow is None
    assert session.ui_flow_stage == UiFlowStage.LOCATION_ACTIVE
    target = session._current_board_scan_target()

    pads = session.state_payload()["flow"]["board_interaction"]["pads"]
    assert target.positions == tuple(
        Coordinate(*pad["position"]) for pad in pads
    )
    assert len(target.feedback.frames) == len(pads)
    assert all(
        frame.role == LedRole.INTERACTIVE_OBJECT
        for frame in target.feedback.frames
    )


def test_debug_courtyard_entry_starts_with_description_and_scout_setup() -> None:
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        debug_courtyard_entry=True,
    )

    state = session.state_payload()

    assert state["current_zone"]["id"] == "courtyard"
    assert state["flow"]["stage"] == "party_setup"
    assert state["exploration_setup"]["current_step"]["assignment_point_id"] == "wounded_scout"
    assert [message["title"] for message in state["messages"]] == [
        "Dziedziniec",
        "Setup punktu eksploracji",
    ]
    assert "zarośnięty, błotnisty dziedziniec" in state["messages"][0]["body"]
    assert "ranny zwiadowca" in state["messages"][0]["body"]
    assert "Postaw figurkę" in state["messages"][1]["body"]

    active = session.select_board_position(Coordinate(8, 8))

    assert active["flow"]["stage"] == "location_active"
    assert [goal["label"] for goal in active["active_challenge"]["goals"]] == [
        "Rozejrzyjcie się po okolicy"
    ]
    scout = next(
        point
        for point in active["current_zone_points"]
        if point["id"] == "wounded_scout"
    )
    assert scout["interaction_label"] == "Podejdź do rannego zwiadowcy"


def test_legacy_courtyard_challenge_debug_uses_complete_entry_setup() -> None:
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        debug_challenge_id="courtyard_search",
    )

    state = session.state_payload()

    assert state["current_zone"]["id"] == "courtyard"
    assert state["flow"]["stage"] == "party_setup"
    assert (
        state["exploration_setup"]["current_step"]["assignment_point_id"]
        == "wounded_scout"
    )

    active = session.select_board_position(Coordinate(8, 9))

    assert [
        point["interaction_label"]
        for point in active["current_zone_points"]
        if point["id"] == "wounded_scout"
    ] == ["Podejdź do rannego zwiadowcy"]
    assert [goal["label"] for goal in active["active_challenge"]["goals"]] == [
        "Rozejrzyjcie się po okolicy"
    ]


def test_open_zone_interaction_exposes_numbered_pads_then_navigation_markers() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    interaction_target = session._current_board_scan_target()

    pads = session.state_payload()["flow"]["board_interaction"]["pads"]
    assert interaction_target.positions == tuple(
        Coordinate(*pad["position"]) for pad in pads
    )
    assert len(interaction_target.feedback.frames) == len(pads)

    navigation = session.set_exploration_board_selection(True)
    selection_target = session._current_board_scan_target()

    assert navigation["flow"]["board_interaction"]["pads"] == []
    assert session.current_zone.marker_position in selection_target.positions


def test_precombat_stealth_moves_passive_led_focus_after_each_roll() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _prepare_gate_encounter_setup(session)
    board = FakeBoardConnection()
    session.attach_board_connection(board, backend="simulator")
    encounter = session.encounter_setup_flow.encounter
    allies = tuple(actor for actor in encounter.actors if actor.faction == Faction.ALLY)

    session._sync_board_leds()
    assert board.led_calls[-1][0] == [allies[0].position.as_tuple()]

    session.submit_precombat_stealth_roll(actor_id=str(allies[0].id), natural_roll=14)

    assert board.led_calls[-2] == ("off", None)
    assert board.led_calls[-1][0] == [allies[1].position.as_tuple()]
    assert session._current_board_scan_target().positions == ()


def test_exploration_roll_does_not_focus_selected_actor_on_party_token_board() -> None:
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=FakeGmClient(_challenge_proposal(progress_on_success=1)),
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    board = FakeBoardConnection()
    session.attach_board_connection(board, backend="simulator")
    actor = session.exploration.actors[1]
    session.submit_action("Napieramy na bramę ramieniem.")

    session.decide("accept", lead_actor_id=str(actor.id))

    target = session._current_board_scan_target()
    assert target.positions == ()
    assert all(frame.role != LedRole.ACTIVE_ACTOR for frame in target.feedback.frames)

    session.resolve_rolls({str(actor.id): 10})

    assert all(
        color != list(LedColor.ACTIVE_ACTOR)
        for positions, color in board.led_calls
        if positions != "off"
    )


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
    session.resolve_rolls(
        {"hero": {"natural_roll": 20, "natural_roll_2": 20}}
    )

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
    assert opening["pending_encounter"]["opening"]["outcome"] == "no_surprise"
    session.start_encounter_setup()
    while session.encounter_setup_flow is not None and not session.encounter_setup_flow.completed:
        if session.encounter_setup_flow.is_player_start_step:
            session.assign_encounter_player_start_position(
                session.encounter_setup_flow.remaining_player_start_positions()[0]
            )
        else:
            session.confirm_encounter_setup_step()

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


def test_critical_gate_breach_gives_every_ally_initiative_advantage_without_hiding(tmp_path):
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        session_id="quiet_gate_surprise_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    flags = set_scene_flag(session.state.flags, "gate_passed", True)
    flags = set_scene_flag(flags, "gate_critical_breach", True)
    session.state = replace(session.state, flags=flags)
    session.state_payload()

    opening = session.resolve_encounter_opening()
    assert opening["pending_encounter"]["opening"]["outcome"] == "party_initiative_advantage"

    session.start_encounter_setup()
    while session.encounter_setup_flow is not None and not session.encounter_setup_flow.completed:
        if session.encounter_setup_flow.is_player_start_step:
            session.assign_encounter_player_start_position(
                session.encounter_setup_flow.remaining_player_start_positions()[0]
            )
        else:
            session.confirm_encounter_setup_step()
    assert session.state_payload()["encounter_stealth"] is None
    state = session.start_encounter_initiative()
    ally_modes: list[str] = []
    while session.combat_state is None:
        prompt = state["encounter_initiative"]["current_prompt"]
        ally_modes.append(prompt["roll_mode"])
        state = session.submit_encounter_initiative_roll(20, 19)

    assert ally_modes == ["advantage", "advantage", "advantage"]
    final_state = session.state_payload()
    enemy_entries = [
        entry
        for entry in final_state["encounter_initiative"]["order"]
        if entry["actor_id"] in {"goblin_a", "goblin_b"}
    ]
    assert len(enemy_entries) == 2
    assert all(entry["roll_mode"] == "normal" for entry in enemy_entries)
    assert all(len(entry["natural_rolls"]) == 1 for entry in enemy_entries)


def test_critical_wall_entry_allows_hiding_and_gives_party_initiative_advantage(tmp_path):
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        session_id="critical_wall_entry_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    flags = set_scene_flag(session.state.flags, "gate_passed", True)
    flags = set_scene_flag(flags, "gate_wall_critical_entry", True)
    session.state = replace(session.state, flags=flags)
    session.state_payload()

    opening = session.resolve_encounter_opening()
    assert (
        opening["pending_encounter"]["opening"]["outcome"]
        == "party_initiative_advantage_and_can_hide"
    )

    session.start_encounter_setup()
    while session.encounter_setup_flow is not None and not session.encounter_setup_flow.completed:
        if session.encounter_setup_flow.is_player_start_step:
            session.assign_encounter_player_start_position(
                session.encounter_setup_flow.remaining_player_start_positions()[0]
            )
        else:
            session.confirm_encounter_setup_step()

    assert session.state_payload()["encounter_stealth"] is not None
    session.finish_precombat_stealth()
    initiative = session.start_encounter_initiative()
    assert initiative["encounter_initiative"]["current_prompt"]["roll_mode"] == "advantage"


def test_precombat_stealth_roll_becomes_per_observer_hidden_state_in_combat(tmp_path):
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        session_id="precombat_stealth_bridge_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    flags = set_scene_flag(session.state.flags, "gate_passed", True)
    flags = set_scene_flag(flags, "gate_lock_critical", True)
    flags = set_scene_flag(flags, "gate_bolt_critical", True)
    session.state = replace(session.state, flags=flags)
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


def test_action_without_active_interaction_returns_guidance_and_is_not_kept_in_chat(tmp_path):
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        session_id="no_active_interaction_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.state = replace(
        session.state,
        challenge_states=(
            ExplorationChallengeState(challenge_id="closed_gate", completed=True),
        ),
    )

    state = session.submit_action("Otwieram skrzynię, która na pewno gdzieś tu jest.")

    assert state["pending"] is None
    assert state["messages"][-1]["title"] == "Najpierw wybierz interakcję"
    assert all(
        message["body"] != "Otwieram skrzynię, która na pewno gdzieś tu jest."
        for message in state["messages"]
    )
    assert state["conversation"]["entries"] == []


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
    assert "bezpiecznie zinterpretować" in state["messages"][-1]["body"]
    assert not any(
        entry["role"] == "player" and "działa laserowego" in entry["body"]
        for entry in state["conversation"]["entries"]
    )
    events = [__import__("json").loads(line) for line in session.observer.path.read_text(encoding="utf-8").splitlines()]
    assert any(event["event_type"] == "ui_gm_declaration_rejected" for event in events)


def test_exploration_ui_session_retries_invalid_gm_payload_once(tmp_path):
    invalid = _challenge_proposal(
        selected_mechanic="single_actor_check",
        check_participants="single_actor",
        check_aggregation="lead_result",
        improvised_tool={
            "label": "Pan Łomot",
            "source": "interaction_object",
            "source_detail": "dębowa belka",
            "effect_modifier": 1,
            "reason": "Belka służy jako taran.",
        },
    )
    valid = _challenge_proposal(
        selected_mechanic="single_actor_check",
        check_participants="single_actor",
        check_aggregation="lead_result",
        improvised_tool=None,
    )

    class RecoveringGmClient(FakeGmClient):
        def __init__(self):
            super().__init__(invalid)
            self.proposals = [invalid, valid]

        def classify(self, request):
            self.requests.append(request)
            return self.proposals.pop(0)

    client = RecoveringGmClient()
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        gm_client=client,
        session_id="validation_retry_test",
        observation_dir=tmp_path,
    )
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    state = session.submit_action("Uderzamy w bramę belką zwaną Panem Łomotem.")

    assert state["pending"]["kind"] == "challenge"
    assert len(client.requests) == 2
    events = [
        json.loads(line)
        for line in session.observer.path.read_text(encoding="utf-8").splitlines()
    ]
    assert any(
        event["event_type"] == "ui_gm_proposal_validation_recovered"
        for event in events
    )


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

    assert [roll["actor_id"] for roll in accepted["required_rolls"]] == ["rogue"]
    assert all(roll["die_sides"] == 20 and roll["label"] == "d20" for roll in accepted["required_rolls"])
    assert accepted["required_rolls"][0]["roll_mode"] == "advantage"
    assert accepted["required_rolls"][0]["requires_second_roll"] is True
    plan = accepted["pending"]["check_plan"]
    assert plan["lead_actor_id"] == "rogue"
    assert plan["helper_actor_id"] == "hero"
    assert plan["mechanic"]["id"] == "lead_with_help_check"

    resolved = session.resolve_rolls(
        {"rogue": {"natural_roll": 8, "natural_roll_2": 16}}
    )

    assert all(roll["actor_id"] == "rogue" for roll in resolved["required_rolls"])


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

    session.submit_action(
        "Wyważamy bramę.",
        selected_goal_id="force_entry",
        selected_check_participants="single_actor",
        participant_actor_ids=("hero",),
    )
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
    session.attach_board_connection(FakeBoardConnection(), backend="simulator")

    state = session.start_session()

    assert state["flow"]["stage"] == "party_setup"
    assert state["exploration_setup"]["current_step"]["label"] == (
        "papierowa mapa: Brama strażnicy"
    )
    assert state["exploration_setup"]["paper_map"]["id"] == "watchtower_overview"

    state = session.confirm_exploration_setup_step()

    assert state["exploration_setup"]["current_step"]["label"] == "elementy mapy"
    assert state["exploration_setup"]["current_step"]["has_positions"] is False
    assert state["exploration_setup"]["current_step"]["color"] is None

    while session.exploration_setup_flow is not None:
        state = session.confirm_exploration_setup_step()

    assert state["flow"]["stage"] == "spell_preparation"
    assert state["exploration_setup"] is None

    state = session.confirm_spell_preparation(
        actor_id="cleric",
        spell_ids=("healing_word", "bless_attack_bonus"),
    )

    assert state["flow"]["stage"] == "location_preview"


def test_exploration_ui_session_requires_spell_preparation_after_physical_setup():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    board = FakeBoardConnection()

    initial = session.state_payload()

    assert initial["flow"]["stage"] == "waiting_for_board"
    assert initial["spell_preparation"]["current_actor_id"] == "cleric"
    cleric = initial["spell_preparation"]["actors"][0]
    assert cleric["preparation_limit"] == 2
    assert cleric["selected_count"] == 2
    assert {spell["id"] for spell in cleric["spells"]} == {
        "radiant_line",
        "healing_word",
        "cure_wounds",
        "inflict_wounds",
        "bless_attack_bonus",
    }
    for spell in cleric["spells"]:
        assert spell["flavor_description"]
        assert "Rzucanie:" in spell["mechanical_description"]
        assert "zasięg:" in spell["mechanical_description"]

    session.attach_board_connection(board, backend="simulator")
    assert session.state_payload()["flow"]["stage"] == "ready_to_start"
    session.start_session()
    while session.exploration_setup_flow is not None:
        session.confirm_exploration_setup_step()
    assert session.state_payload()["flow"]["stage"] == "spell_preparation"

    confirmed = session.confirm_spell_preparation(
        actor_id="cleric",
        spell_ids=("radiant_line", "healing_word"),
    )

    assert confirmed["flow"]["stage"] == "location_preview"
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
    cleric_preview = next(
        actor
        for actor in preview["short_rest"]["pending"]["actors"]
        if actor["actor_id"] == "cleric"
    )
    assert cleric_preview["attunement_count"] == 0
    assert cleric_preview["attunement_maximum"] == 3
    assert cleric_preview["attunement_items"][0]["item_id"] == "binding_wand"
    assert cleric_preview["attunement_items"][0]["action"] == "attune"

    completed = session.confirm_short_rest(
        attunement_choices=[
            {
                "actor_id": "cleric",
                "item_id": "binding_wand",
                "action": "attune",
            }
        ]
    )

    assert completed["short_rest"]["pending"]["completed"] is True
    assert completed["short_rest"]["elapsed_minutes"] == 60
    assert completed["active_challenge"] is None
    assert next(
        item for item in completed["scene_status"]
        if item["label"] == "Czujność goblinów"
    )["value"] == "gobliny są zaalarmowane"
    hero_before_die = next(actor for actor in completed["actors"] if actor["id"] == "hero")
    assert hero_before_die["hp"] == 10
    cleric = next(actor for actor in completed["actors"] if actor["id"] == "cleric")
    wand = next(item for item in cleric["inventory"] if item["id"] == "binding_wand")
    assert wand["attuned"] is True

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
    permanent_condition = ConditionState(
        "hero",
        CombatCondition.PRONE,
        duration=EffectDuration.PERMANENT,
    )
    session.state = replace(
        session.state,
        condition_states=(
            ConditionState(
                "hero",
                CombatCondition.POISONED,
                duration=EffectDuration.UNTIL_SCENARIO_END,
            ),
            permanent_condition,
        ),
    )

    payload = session.finish_scenario()

    assert payload["flow"]["stage"] == "scenario_complete"
    assert [effect["id"] for effect in payload["active_effects"]] == ["permanent"]
    assert session.state.condition_states == (permanent_condition,)
    assert any(message["title"] == "Stan wygasł" for message in payload["messages"])
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


def test_exploration_ui_session_social_reaction_sets_flags_and_changes_attitude():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "social",
            "request_risk": "no_risk",
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
    assert state["pending"]["check_plan"]["dc"] == 10
    state = session.resolve_rolls({"hero": 20})

    assert state["pending"] is None
    assert {"key": "scout_calmed", "value": True} in state["flags"]
    runtime = state["active_point"]["npc"]["runtime_state"]
    assert runtime["attitude"] == "friendly"
    assert "Spokojniejszy" in runtime["emotional_state"]
    assert runtime["relationship_events"][0]["intent"] == "social"
    assert any(message["title"] == "Zmiana nastawienia" for message in state["messages"])


def test_selected_npc_goal_locks_flow_intent_and_participants_before_description():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "medical",
            "request_risk": "no_risk",
            "player_narration": "Kapłan przemawia spokojnie, a Bohater pilnuje dystansu.",
            "npc_response": "Dobrze. Tylko bez gwałtownych ruchów.",
            "requires_roll": True,
            "ability": "charisma",
            "skill": "persuasion",
            "dc": 10,
        }
    )
    client = FakeNpcClient(proposal)
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        npc_client=client,
        debug_point_id="wounded_scout",
    )

    state = session.submit_action(
        "Kapłan odkłada broń i spokojnie zapewnia, że przyszliśmy pomóc.",
        selected_goal_id="calm_scout",
        selected_check_participants="lead_with_help",
        participant_actor_ids=("cleric", "hero"),
    )

    assert client.requests[0].routed_intent_id == "social"
    assert state["pending"]["proposal"]["action_type"] == "social"
    assert state["pending"]["participant_actor_ids"] == ["cleric", "hero"]

    state = session.decide("accept")

    assert state["pending"]["check_plan"]["lead_actor_id"] == "cleric"
    assert state["pending"]["check_plan"]["helper_actor_id"] == "hero"
    assert state["pending"]["check_plan"]["roll_mode"] == "advantage"


def test_selected_social_skill_is_authoritative_in_npc_goal_flow():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "social",
            "request_risk": "no_risk",
            "player_narration": "Zwiadowca słucha deklaracji drużyny.",
            "npc_response": "Dobrze, mówcie.",
            "requires_roll": True,
            "ability": "charisma",
            "skill": "persuasion",
            "dc": 20,
        }
    )
    client = FakeNpcClient(proposal)
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        npc_client=client,
        debug_point_id="wounded_scout",
    )

    pending = session.submit_action(
        "Oszukujemy zwiadowcę, że przysłał nas jego dowódca.",
        selected_goal_id="calm_scout",
        selected_check_participants="single_actor",
        participant_actor_ids=("hero",),
        selected_social_skill="deception",
    )

    assert client.requests[0].selected_social_skill == "deception"
    assert pending["pending"]["proposal"]["ability"] == "charisma"
    assert pending["pending"]["proposal"]["skill"] == "deception"
    assert pending["pending"]["proposal"]["dc"] == 10


def test_selected_medical_npc_goal_uses_authored_check_and_effects():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "harm",
            "player_narration": "Kapłan ogląda ranę i przygotowuje opatrunek.",
            "npc_response": "Tylko ostrożnie.",
            "requires_roll": True,
            "ability": "strength",
            "skill": "athletics",
            "dc": 20,
            "effects_on_success": [
                {"type": "set_flag", "parameters": {"key": "scout_dead", "value": True}}
            ],
        }
    )
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        npc_client=FakeNpcClient(proposal),
        debug_point_id="wounded_scout",
    )

    state = session.submit_action(
        "Kapłan oczyszcza ranę i zakłada opatrunek.",
        selected_goal_id="help_scout",
        selected_check_participants="single_actor",
        participant_actor_ids=("cleric",),
    )

    assert state["pending"]["proposal"]["action_type"] == "medical"
    assert state["pending"]["proposal"]["ability"] == "wisdom"
    assert state["pending"]["proposal"]["skill"] == "medicine"
    assert state["pending"]["proposal"]["dc"] == 12
    assert state["pending"]["proposal"]["effects_on_success"] == []

    state = session.decide("accept")
    assert state["pending"]["check_plan"]["lead_actor_id"] == "cleric"
    assert state["pending"]["check_plan"]["dc"] == 12
    state = session.resolve_rolls({"cleric": 20})

    assert scene_flag(session.state.flags, "scout_treated", False) is True
    assert scene_flag(session.state.flags, "scout_stabilized", False) is True
    assert scene_flag(session.state.flags, "scout_trusts_party", False) is True
    assert scene_flag(session.state.flags, "scout_dead", False) is False


def test_explicit_healing_spell_on_npc_uses_spell_rules_without_medicine_roll():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "medical",
            "player_narration": "Kapłan wypowiada krótką modlitwę nad rannym.",
            "npc_response": "Oddech zwiadowcy natychmiast się uspokaja.",
            "requires_roll": True,
            "ability": "wisdom",
            "skill": "medicine",
            "dc": 12,
        }
    )
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        npc_client=FakeNpcClient(proposal),
        debug_point_id="wounded_scout",
    )

    pending = session.submit_action(
        "Kapłan rzuca Słowo leczenia na zwiadowcę.",
        selected_goal_id="help_scout",
        selected_check_participants="single_actor",
        participant_actor_ids=("cleric",),
    )

    assert pending["pending"]["proposal"]["requires_roll"] is False
    assert pending["pending"]["spell_use"] == {
        "actor_id": "cleric",
        "spell_id": "healing_word",
        "spell_name": "Słowo leczenia",
        "spell_level": 1,
    }
    cleric_before = next(actor for actor in pending["actors"] if actor["id"] == "cleric")
    assert cleric_before["spell_slots"][0]["remaining"] == 2
    assert not any(
        message["title"] == "Odpowiedź NPC"
        and "natychmiast się uspokaja" in message["body"]
        for message in pending["messages"]
    )

    resolved = session.decide("accept")

    assert resolved["pending"] is None
    assert resolved["required_rolls"] == []
    cleric_after = next(actor for actor in resolved["actors"] if actor["id"] == "cleric")
    assert cleric_after["spell_slots"][0]["remaining"] == 1
    assert scene_flag(session.state.flags, "scout_treated", False) is True
    assert scene_flag(session.state.flags, "scout_stabilized", False) is True
    assert scene_flag(session.state.flags, "scout_trusts_party", False) is True
    assert any(
        message["title"] == "Zużyty slot czaru"
        and "Słowo leczenia" in message["body"]
        for message in resolved["messages"]
    )
    assert any(
        message["title"] == "Odpowiedź NPC"
        and "natychmiast się uspokaja" in message["body"]
        for message in resolved["messages"]
    )


def test_selected_intimidation_goal_always_offers_authored_roll_without_technical_refusal():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "intimidation",
            "request_risk": "significant_risk",
            "target_id": "scout_information",
            "player_narration": (
                "Bohater wysuwa miecz z pochwy i żąda pokazania zawartości torby."
            ),
            "npc_response": (
                "Zwiadowca blednie i odsuwa się w błoto, kurczowo ściskając torbę."
            ),
            "requires_roll": False,
            "success_message": "Zwiadowca zdradza trop o bestii.",
            "failure_message": "Zwiadowca wpada w panikę.",
        }
    )
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        npc_client=FakeNpcClient(proposal),
        debug_point_id="wounded_scout",
    )

    state = session.submit_action(
        "Albo pokażesz nam torbę, albo skrócę twoje cierpienie mieczem.",
        selected_goal_id="pressure_scout",
        selected_check_participants="single_actor",
        participant_actor_ids=("hero",),
    )

    assert state["pending"]["proposal"]["requires_roll"] is True
    assert state["pending"]["proposal"]["ability"] == "charisma"
    assert state["pending"]["proposal"]["skill"] == "intimidation"
    assert state["pending"]["proposal"]["dc"] == 18
    assert "social_plan" not in state["pending"]
    assert state["pending"]["npc_action_plan"]["target_id"] == "scout_information"
    assert state["messages"][-1]["title"] == "Gracze"
    assert not any(
        message["title"] == "Narracja MG"
        and "wysuwa miecz" in message["body"]
        for message in state["messages"]
    )

    roll = session.decide("accept")

    assert roll["pending"]["stage"] == "roll"
    assert roll["pending"]["check_plan"]["dc"] == 18
    assert not any(
        message["title"] == "Reakcja NPC"
        and "nie wymaga rzutu" in message["body"]
        for message in roll["messages"]
    )

    resolved = session.resolve_rolls({"hero": 20})

    assert resolved["pending"] is None
    assert scene_flag(session.state.flags, "scout_coerced", False) is True
    assert scene_flag(session.state.flags, "beast_hint_learned", False) is True
    assert any(
        message["title"] == "Wynik interakcji NPC"
        and "dokładnie opisuje" in message["body"]
        for message in resolved["messages"]
    )


def test_npc_instance_gm_chat_does_not_address_npc_or_apply_effects():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "social",
            "request_risk": "no_risk",
            "player_narration": (
                "Zwiadowca wygląda na człowieka, którego dzień zdecydowanie nie zmierza "
                "ku lepszemu. Jeśli chcecie poznać jego zamiary, porozmawiajcie z nim."
            ),
            "npc_response": "To nie powinno zostać pokazane jako odpowiedź NPC.",
            "requires_roll": True,
            "effects_on_success": [
                {"type": "set_flag", "parameters": {"key": "scout_calmed", "value": True}},
            ],
        }
    )
    client = FakeNpcClient(proposal)
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        npc_client=client,
        debug_point_id="wounded_scout",
    )

    state = session.submit_action(
        "Czy zwiadowca wygląda na godnego zaufania?",
        conversation_only=True,
    )

    assert state["pending"] is None
    assert state["conversation"]["entries"][-1]["title"] == "Odpowiedź MG"
    assert "dzień zdecydowanie" in state["conversation"]["entries"][-1]["body"]
    assert scene_flag(session.state.flags, "scout_calmed", False) is False
    assert client.requests[0].to_prompt_payload()["conversation_only"] is True


def test_cosmetic_npc_exchange_resolves_without_extra_acceptance():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "search",
            "player_narration": "Zwiadowca zerka na zabłocone buty Bohatera.",
            "npc_response": "Ładny marsz. Błoto wygląda na bardziej wypoczęte.",
            "requires_roll": False,
        }
    )
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        npc_client=FakeNpcClient(proposal),
        debug_point_id="wounded_scout",
    )

    state = session.submit_action("Jak oceniasz nasz marsz?")

    assert state["pending"] is None
    assert state["messages"][-2]["title"] == "Narracja MG"
    assert state["messages"][-1] == {
        "title": "Odpowiedź NPC",
        "body": "Ładny marsz. Błoto wygląda na bardziej wypoczęte.",
    }


def test_invalid_npc_payload_retries_then_returns_player_facing_message():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "information",
            "request_risk": "no_risk",
            "npc_response": "Sekret, którego nie wolno jeszcze ujawnić.",
            "requires_roll": False,
        }
    )
    client = FakeNpcClient(proposal)
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        npc_client=client,
        debug_point_id="wounded_scout",
    )

    state = session.submit_action("Powiedz nam od razu całą prawdę.")

    assert state["pending"] is None
    assert len(client.requests) == 2
    assert state["messages"][-1]["title"] == "Rozmowa wymaga doprecyzowania"
    assert "bezpiecznie zinterpretować" in state["messages"][-1]["body"]
    assert not any(
        entry["role"] == "player"
        and "całą prawdę" in entry["body"]
        for entry in state["conversation"]["entries"]
    )


def test_exploration_ui_session_refuses_request_beyond_current_npc_attitude():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "social",
            "request_risk": "significant_risk",
            "npc_response": "Nie mogę tego dla was zrobić.",
            "requires_roll": True,
            "ability": "charisma",
            "skill": "persuasion",
            "dc": 15,
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

    pending = session.submit_action("Zaryzykuj życie i wróć sam do wieży.")
    assert pending["pending"]["social_plan"] == {
        "attitude": "indifferent",
        "request_risk": "significant_risk",
        "possible": False,
        "requires_roll": False,
        "dc": None,
    }

    state = session.decide("accept")

    assert state["pending"] is None
    assert {"key": "scout_calmed", "value": True} not in state["flags"]
    assert any(message["title"] == "Reakcja NPC" for message in state["messages"])


def test_exploration_ui_session_blocks_retry_until_context_changes_then_exhausts_it():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "social",
            "request_risk": "no_risk",
            "npc_response": "Zwiadowca nie jest jeszcze przekonany.",
            "requires_roll": False,
            "failure_message": "Zwiadowca nadal wam nie ufa.",
        }
    )
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        npc_client=FakeNpcClient(proposal),
        debug_point_id="wounded_scout",
    )

    first = session.submit_action("Próbujemy zdobyć jego zaufanie.")
    assert first["pending"]["attempt_plan"]["attempts_used"] == 0
    session.decide("accept")
    failed = session.resolve_rolls({"hero": 1})
    assert failed["active_point"]["npc"]["runtime_state"]["used_attempt_ids"] == [
        "scout_build_trust"
    ]

    blocked = session.submit_action("Próbujemy przekonać go jeszcze raz.")
    assert blocked["pending"]["attempt_plan"]["available"] is False
    assert blocked["pending"]["attempt_plan"]["attempts_used"] == 1
    after_block = session.decide("accept")
    assert len(after_block["active_point"]["npc"]["runtime_state"]["relationship_events"]) == 1
    assert any(
        message["title"] == "Reakcja NPC" and "Najpierw pokażcie czynami" in message["body"]
        for message in after_block["messages"]
    )

    session.state = replace(
        session.state,
        flags=set_scene_flag(session.state.flags, "scout_stabilized", True),
    )
    retry = session.submit_action("Po opatrzeniu ran wracamy do rozmowy.")
    assert retry["pending"]["attempt_plan"]["available"] is True
    assert retry["pending"]["attempt_plan"]["is_retry"] is True
    assert retry["pending"]["attempt_plan"]["attempts_remaining"] == 1
    session.decide("accept")
    session.resolve_rolls({"hero": 1})

    exhausted = session.submit_action("Naciskamy na niego po raz trzeci.")
    assert exhausted["pending"]["attempt_plan"]["available"] is False
    assert exhausted["pending"]["attempt_plan"]["attempts_remaining"] == 0
    assert "podjął już decyzję" in exhausted["pending"]["attempt_plan"]["blocked_reason"]


def test_exploration_ui_session_executes_critical_success_npc_target_branch():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "theft",
            "target_id": "scout_reports",
            "quantity": 1,
            "player_narration": "Łotrzyca sięga w stronę torby zwiadowcy.",
            "requires_roll": False,
        }
    )
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        npc_client=FakeNpcClient(proposal),
        debug_point_id="wounded_scout",
    )

    pending = session.submit_action("Próbuję ukraść jego torbę z meldunkami.")
    action_plan = pending["pending"]["npc_action_plan"]
    assert action_plan["target_id"] == "scout_reports"
    assert action_plan["max_quantity"] == 1
    assert set(action_plan["outcomes"]) == {
        "critical_success",
        "success",
        "failure",
        "critical_failure",
    }
    assert "nóż" not in action_plan["outcomes"]["critical_failure"]["preview"]
    roll_pending = session.decide("accept")
    assert roll_pending["pending"]["check_plan"]["dc"] == 14

    state = session.resolve_rolls({"hero": 20})

    assert "scout_reports" in session.state.inventory_resource_ids
    assert scene_flag(session.state.flags, "scout_reports_taken", False) is True
    assert scene_flag(session.state.flags, "scout_robbed", False) is False
    assert state["active_point"]["npc"]["runtime_state"]["attitude"] == "indifferent"
    assert any(
        message["title"] == "Wynik interakcji NPC" and "nie zauważa" in message["body"]
        for message in state["messages"]
    )


def test_exploration_ui_session_executes_critical_failure_npc_target_branch():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "theft",
            "target_id": "scout_reports",
            "requires_roll": False,
        }
    )
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        npc_client=FakeNpcClient(proposal),
        debug_point_id="wounded_scout",
    )

    session.submit_action("Próbuję ukraść meldunki.")
    session.decide("accept")
    state = session.resolve_rolls({"hero": 1})

    assert "scout_reports" not in session.state.inventory_resource_ids
    assert scene_flag(session.state.flags, "hidden_knife_response", False) is True
    assert challenge_state_for(session.state, "closed_gate").noise == 2
    assert state["active_point"]["npc"]["runtime_state"]["attitude"] == "hostile"
    assert state["active_point"]["npc"]["runtime_state"]["relationship_events"][-1]["outcome"] == "failure"
    assert state["pending_encounter"] is None
    assert state["pending_npc_transition"]["variant_id"] == "danger_nearby"


def test_npc_escalation_can_resume_dialogue_without_automatic_encounter():
    proposal = NpcInteractionProposal.model_validate(
        {"action_type": "theft", "target_id": "scout_reports", "requires_roll": False}
    )
    client = FakeNpcClient(proposal)
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        npc_client=client,
        debug_point_id="wounded_scout",
    )
    session.submit_action("Próbuję ukraść meldunki.")
    session.decide("accept")
    session.resolve_rolls({"hero": 1})

    state = session.resolve_npc_transition("try_to_calm")

    assert state["pending_npc_transition"] is None
    assert state["pending_encounter"] is None
    assert state["active_point"]["id"] == "wounded_scout"
    assert state["active_point"]["npc"]["runtime_state"]["interaction_status"] == "active"
    assert scene_flag(session.state.flags, "scout_panicked", True) is False
    assert "scout_panic_alarm" not in session.resolved_encounter_trigger_ids


def test_npc_escalation_can_start_content_encounter_only_after_player_choice():
    proposal = NpcInteractionProposal.model_validate(
        {"action_type": "theft", "target_id": "scout_reports", "requires_roll": False}
    )
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        npc_client=FakeNpcClient(proposal),
        debug_point_id="wounded_scout",
    )
    session.submit_action("Próbuję ukraść meldunki.")
    session.decide("accept")
    session.resolve_rolls({"hero": 1})

    state = session.resolve_npc_transition("hold_your_ground")

    assert state["pending_npc_transition"] is None
    assert state["pending_encounter"]["trigger_id"] == "scout_panic_alarm"
    assert state["active_point"] is None


def test_npc_escalation_can_close_reusable_interaction_without_calling_llm_again():
    proposal = NpcInteractionProposal.model_validate(
        {"action_type": "theft", "target_id": "scout_reports", "requires_roll": False}
    )
    client = FakeNpcClient(proposal)
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        npc_client=client,
        debug_point_id="wounded_scout",
    )
    session.submit_action("Próbuję ukraść meldunki.")
    session.decide("accept")
    session.resolve_rolls({"hero": 1})
    session.resolve_npc_transition("back_off")
    assert len(client.requests) == 1

    session.active_point_id = "wounded_scout"
    state = session.submit_action("Czy teraz porozmawiasz?")

    assert len(client.requests) == 1
    assert state["active_point"]["npc"]["runtime_state"]["interaction_status"] == "closed"
    assert any(
        message["title"] == "Odpowiedź NPC" and "nie chce już" in message["body"]
        for message in state["messages"]
    )


def test_second_npc_fixture_uses_transition_without_starting_combat():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "social",
            "target_id": "demand_advance_payment",
            "quantity": 1,
            "requires_roll": False,
        }
    )
    client = FakeNpcClient(proposal)
    session = ExplorationUiSession(
        "content/scenarios/village_square_mvp.json",
        npc_client=client,
        debug_point_id="elder_npc",
    )
    session.submit_action(
        "Żądamy zapłaty z góry.",
        selected_goal_id="negotiate_advance",
        selected_check_participants="single_actor",
        participant_actor_ids=("hero",),
    )
    assert client.requests[0].selected_goal_id == "negotiate_advance"
    assert client.requests[0].routed_intent_id == "social"
    session.decide("accept")

    escalated = session.resolve_rolls({"hero": 1})

    assert escalated["pending_npc_transition"]["transition_id"] == "elder_negotiation_breakdown"
    assert escalated["pending_npc_transition"]["variant_id"] == "default"
    assert escalated["pending_encounter"] is None

    resumed = session.resolve_npc_transition("apologize")

    assert resumed["pending_npc_transition"] is None
    assert resumed["pending_encounter"] is None
    assert resumed["active_point"]["npc"]["runtime_state"]["interaction_status"] == "active"
    assert scene_flag(session.state.flags, "elder_argument", True) is False


def test_village_elder_ui_goals_follow_guarded_flow_state():
    session = ExplorationUiSession(
        "content/scenarios/village_square_mvp.json",
        debug_point_id="elder_npc",
    )

    initial = session.state_payload()
    assert {
        goal["id"] for goal in initial["active_point"]["npc"]["goals"]
    } == {"ask_watchtower_problem", "negotiate_advance"}

    session.state = replace(
        session.state,
        flags=set_scene_flag(session.state.flags, "quest_hook_found", True),
    )
    informed = session.state_payload()
    assert [
        goal["id"] for goal in informed["active_point"]["npc"]["goals"]
    ] == ["ask_watchtower_problem", "accept_watchtower_quest"]

    session.state = replace(
        session.state,
        flags=set_scene_flag(session.state.flags, "quest_accepted", True),
    )
    accepted = session.state_payload()
    assert [
        goal["id"] for goal in accepted["active_point"]["npc"]["goals"]
    ] == ["ask_watchtower_problem", "confirm_watchtower_departure"]

    session.state = replace(
        session.state,
        flags=set_scene_flag(session.state.flags, "elder_refuses_party", True),
    )
    closed = session.state_payload()
    assert closed["active_point"]["npc"]["goals"] == []


def test_village_authored_npc_route_hides_gemini_invented_reward_and_purchase():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "information",
            "player_narration": "Bohater kupuje mapę od Brena za kilka monet.",
            "npc_response": (
                "Bren obiecuje sto sztuk złota i ujawnia obecność niebieskiego smoka."
            ),
            "success_message": "Drużyna otrzymuje złoto.",
            "requires_roll": False,
        }
    )
    session = ExplorationUiSession(
        "content/scenarios/village_square_mvp.json",
        npc_client=FakeNpcClient(proposal),
        debug_point_id="elder_npc",
    )

    state = session.submit_action(
        "Pytamy Brena, co wydarzyło się przy strażnicy.",
        selected_goal_id="ask_watchtower_problem",
        selected_check_participants="single_actor",
        participant_actor_ids=("hero",),
    )

    assert state["pending"] is None
    assert session.npc_client.requests == []
    bodies = [message["body"] for message in state["messages"]]
    assert any("Bren rozwija starą mapę" in body for body in bodies)
    assert any("Na trakcie widywano gobliny" in body for body in bodies)
    assert not any("sto sztuk złota" in body for body in bodies)
    assert not any("niebieskiego smoka" in body for body in bodies)
    assert not any("kupuje mapę" in body for body in bodies)


def test_village_zone_options_are_exposed_and_resolve_authored_effects():
    session = ExplorationUiSession("content/scenarios/village_square_mvp.json")
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    initial = session.state_payload()

    options = {
        option["id"]: option
        for option in initial["flow"]["zone_options"]
    }
    assert set(options) == {"read_notice_board", "ask_for_rumors"}
    assert options["read_notice_board"]["completed"] is False
    assert options["ask_for_rumors"]["check"] == {
        "ability": "charisma",
        "skill": "persuasion",
        "tool": None,
        "dc": 10,
    }
    assert [
        milestone["completed"]
        for milestone in initial["flow"]["objectives"][0]["milestones"]
    ] == [False, False, False]

    notice = session.select_exploration_option("read_notice_board")

    assert scene_flag(session.state.flags, "notice_read", False) is True
    notice_option = next(
        option
        for option in notice["flow"]["zone_options"]
        if option["id"] == "read_notice_board"
    )
    assert notice_option["completed"] is True
    assert notice["messages"][-1]["title"] == "Sprawdź tablicę ogłoszeń"

    rolling = session.select_exploration_option(
        "ask_for_rumors",
        actor_id="rogue",
        player_description="Łotrzyca zagaduje mieszkańców bez wzbudzania podejrzeń.",
    )

    assert rolling["pending"]["kind"] == "zone_option"
    assert rolling["required_rolls"][0]["actor_id"] == "rogue"
    assert rolling["required_rolls"][0]["dc"] == 10

    resolved = session.resolve_rolls({"rogue": 12})

    assert scene_flag(session.state.flags, "rumors_collected", False) is True
    assert resolved["pending"] is None
    assert resolved["messages"][-1]["title"] == "Popytaj mieszkańców"


def test_tavern_dice_game_resolves_wager_tool_check_and_can_be_replayed():
    session = ExplorationUiSession("content/scenarios/village_square_mvp.json")
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.active_paper_map_id = "village_overview"
    session.travel_to("tavern")
    session.assign_exploration_point_position(Coordinate(3, 12))
    session.confirm_exploration_setup_step()

    option = next(
        item
        for item in session.state_payload()["flow"]["zone_options"]
        if item["id"] == "tavern_dice_game"
    )
    assert option["completed"] is False
    assert option["entry_cost_cp"] == 10
    assert option["success_reward_cp"] == 20
    assert option["time_cost_minutes"] == 15
    assert option["check"]["tool_label"] == "Zestaw kości"

    currency_before = session._trade_actor("hero").currency.total_cp
    rolling = session.select_exploration_option(
        "tavern_dice_game",
        actor_id="hero",
        player_description="Bohater siada do stołu i obserwuje sposób gry przeciwnika.",
    )
    assert rolling["required_rolls"][0]["dc"] == 12
    assert rolling["required_rolls"][0]["tool"] == "dice_set"
    assert rolling["required_rolls"][0]["tool_label"] == "Zestaw kości"

    won = session.resolve_rolls({"hero": 20})
    assert session._trade_actor("hero").currency.total_cp == currency_before + 10
    assert session.state.elapsed_minutes == 20
    assert "Bilans gry: +10 cp" in won["messages"][-1]["body"]

    session.select_exploration_option(
        "tavern_dice_game",
        actor_id="hero",
        player_description="Bohater rewanżuje się, tym razem grając bardziej zachowawczo.",
    )
    lost = session.resolve_rolls({"hero": 1})
    assert session._trade_actor("hero").currency.total_cp == currency_before
    assert session.state.elapsed_minutes == 35
    assert "Bilans gry: -10 cp" in lost["messages"][-1]["body"]


def test_village_interaction_pads_link_board_colors_to_ui_actions():
    session = ExplorationUiSession("content/scenarios/village_square_mvp.json")
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.active_paper_map_id = "village_overview"
    session.travel_to("tavern")
    session.assign_exploration_point_position(Coordinate(3, 12))
    session.confirm_exploration_setup_step()

    board = FakeBoardConnection()
    session.attach_board_connection(board, backend="simulator")
    interaction = session.state_payload()["flow"]["board_interaction"]

    assert interaction["mode"] == "interaction"
    assert [
        (pad["symbol"], pad["action_kind"], pad["target_id"])
        for pad in interaction["pads"]
    ] == [
        ("1", "point", "tavern_keeper"),
        ("2", "zone_option", "tavern_dice_game"),
        ("3", "short_rest", "short_rest"),
    ]
    assert interaction["pads"][0]["color"] != interaction["pads"][1]["color"]
    assert len(session._current_board_scan_target().feedback.frames) == 3

    selected = session.select_board_position(Coordinate(3, 9))

    assert selected["pending"] is None
    assert selected["flow"]["board_interaction"]["selected_action_kind"] == (
        "zone_option"
    )
    assert selected["flow"]["board_interaction"]["selected_action_id"] == (
        "tavern_dice_game"
    )

    rolling = session.select_exploration_option(
        "tavern_dice_game",
        actor_id="hero",
    )
    assert rolling["pending"]["kind"] == "zone_option"
    assert rolling["required_rolls"][0]["tool_label"] == "Zestaw kości"
    assert rolling["conversation"]["entries"] == []


def test_board_pad_can_choose_an_npc_goal_without_free_text_guessing():
    session = ExplorationUiSession("content/scenarios/village_square_mvp.json")
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.active_paper_map_id = "village_overview"
    session.travel_to("tavern")
    session.assign_exploration_point_position(Coordinate(3, 12))
    session.confirm_exploration_setup_step()
    session.select_point("tavern_keeper")

    interaction = session.state_payload()["flow"]["board_interaction"]
    first_goal = interaction["pads"][0]
    selected = session.select_board_position(
        Coordinate(*first_goal["position"]),
    )

    assert selected["flow"]["board_interaction"]["selected_goal_id"] == (
        first_goal["target_id"]
    )
    assert selected["flow"]["board_interaction"]["selection_revision"] == 1
    assert first_goal["label"]


def test_village_npc_setup_and_travel_messages_use_current_location():
    session = ExplorationUiSession("content/scenarios/village_square_mvp.json")
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.active_paper_map_id = "village_overview"

    session._queue_current_zone_npc_setup()

    setup = session.state_payload()
    step = setup["exploration_setup"]["current_step"]
    assert step["assignment_point_id"] == "elder_npc"
    assert "Sołtys Bren" in step["message"]
    assert "rannego człowieka" not in step["message"]
    assert "dziedziń" not in step["message"].lower()

    session.assign_exploration_point_position(Coordinate(8, 5))
    active = session.confirm_exploration_setup_step()

    assert active["flow"]["stage"] == "location_active"
    assert "Rynek" in active["board"]["message"]
    assert "dziedziń" not in active["board"]["message"].lower()

    traveled = session.travel_to("elder_house")

    assert "Dom sołtysa" in traveled["board"]["message"]
    assert traveled["flow"]["stage"] == "location_active"
    assert traveled["exploration_setup"] is None
    assert "Rozłóż papierową mapę" not in traveled["board"]["message"]
    assert "Dom sołtysa" in traveled["current_zone"]["name"]


def test_village_leaving_olan_and_traveling_clears_his_active_conversation():
    session = ExplorationUiSession(
        "content/scenarios/village_square_mvp.json",
        debug_point_id="tavern_keeper",
    )

    session.select_point("")
    session.travel_to("forest_road")
    arrived = session.state_payload()

    assert arrived["current_zone"]["id"] == "forest_road"
    assert arrived["active_point"] is None
    assert arrived["conversation"]["interaction_id"] == "zone:forest_road"
    assert all(
        "Olan" not in entry["body"]
        for entry in arrived["conversation"]["entries"]
    )
    assert "sołtysem Brenem" in arrived["flow"]["continuation"]["unavailable_hint"]


def test_village_initial_setup_starts_with_printable_paper_map():
    session = ExplorationUiSession("content/scenarios/village_square_mvp.json")
    session.attach_board_connection(FakeBoardConnection(), backend="simulator")

    state = session.start_session()

    setup = state["exploration_setup"]
    assert setup["current_step"]["label"] == "papierowa mapa: Rynek"
    assert setup["paper_map"]["id"] == "village_overview"
    assert setup["paper_map"]["width_cm"] == 50.0
    assert setup["paper_map"]["height_cm"] == 75.0
    assert setup["paper_map"]["a4_pdf_url"].endswith("/village_overview.pdf")


def test_village_npc_intro_is_only_added_on_first_open():
    session = ExplorationUiSession(
        "content/scenarios/village_square_mvp.json",
        debug_point_id="elder_npc",
    )

    intro = session.active_point.npc_interaction.dialogue_intro
    assert intro
    session.select_point("")
    first_open = session.select_point("elder_npc")
    initial_count = sum(
        entry["body"] == intro
        for entry in first_open["conversation"]["entries"]
    )

    session.select_point("")
    reopened = session.select_point("elder_npc")

    assert initial_count == 1
    assert sum(
        entry["body"] == intro
        for entry in reopened["conversation"]["entries"]
    ) == 1


def test_village_quest_lifecycle_creates_guarded_watchtower_handoff(tmp_path):
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "information",
            "player_narration": "Bren rozwija mapę i słucha decyzji drużyny.",
            "npc_response": "Bren potwierdza kolejne ustalenie.",
            "requires_roll": False,
        }
    )
    client = FakeNpcClient(proposal)
    session = ExplorationUiSession(
        "content/scenarios/village_square_mvp.json",
        npc_client=client,
        debug_point_id="elder_npc",
        observation_dir=tmp_path / "observations",
        save_dir=tmp_path / "saves",
    )

    with pytest.raises(ValueError, match="autorskie wyjście"):
        session.finish_scenario()
    with pytest.raises(ValueError, match="nie jest jeszcze gotowa"):
        session.continue_scenario()

    after_hook = session.submit_action(
        "Pytamy Brena, co dzieje się przy strażnicy.",
        selected_goal_id="ask_watchtower_problem",
        selected_check_participants="single_actor",
        participant_actor_ids=("hero",),
    )
    assert scene_flag(session.state.flags, "quest_hook_found", False) is True
    assert after_hook["flow"]["objectives"][0]["status"] == "active"
    assert {
        goal["id"] for goal in after_hook["active_point"]["npc"]["goals"]
    } == {"ask_watchtower_problem", "accept_watchtower_quest"}

    after_acceptance = session.submit_action(
        "Przyjmujemy zadanie i zajmiemy się strażnicą.",
        selected_goal_id="accept_watchtower_quest",
        selected_check_participants="single_actor",
        participant_actor_ids=("hero",),
    )
    assert scene_flag(session.state.flags, "quest_accepted", False) is True
    assert after_acceptance["flow"]["objectives"][0]["status"] == "active"
    assert {
        goal["id"] for goal in after_acceptance["active_point"]["npc"]["goals"]
    } == {"ask_watchtower_problem", "confirm_watchtower_departure"}

    ready = session.submit_action(
        "Jesteśmy przygotowani. Ruszamy starym traktem.",
        selected_goal_id="confirm_watchtower_departure",
        selected_check_participants="single_actor",
        participant_actor_ids=("hero",),
    )
    assert scene_flag(session.state.flags, "ready_for_watchtower", False) is True
    assert ready["flow"]["objectives"][0]["status"] == "completed"
    assert ready["flow"]["continuation"]["available"] is False
    assert ready["flow"]["continuation"]["requires_departure_zone"] is True
    assert ready["active_point"]["npc"]["goals"] == []

    session.travel_to("forest_road")
    at_departure = session.confirm_exploration_setup_step()
    assert at_departure["flow"]["continuation"]["available"] is True

    completed = session.continue_scenario(
        navigator_actor_id="hero",
        navigation_roll=20,
    )

    handoff = completed["flow"]["scenario_handoff"]
    assert completed["flow"]["stage"] == "scenario_complete"
    assert handoff["source_scenario_id"] == "village_square_mvp"
    assert handoff["target_scenario_id"] == "abandoned_watchtower"
    assert handoff["target_scenario_name"] == "Opuszczona strażnica"
    assert "Opuszczona strażnica" in completed["board"]["message"]
    assert "abandoned_watchtower" not in completed["board"]["message"]
    continuation_message = next(
        message
        for message in completed["messages"]
        if message["title"] == "Dalsza droga"
    )
    assert "Opuszczona strażnica" in continuation_message["body"]
    assert "abandoned_watchtower" not in continuation_message["body"]
    assert handoff["source_zone_id"] == "forest_road"
    assert handoff["target_scenario_path"].endswith(
        "content/scenarios/abandoned_watchtower.json"
    )
    assert handoff["departure_minute"] == 35
    assert handoff["travel_minutes"] == 45
    assert handoff["travel"]["pace"] == "normal"
    assert handoff["travel"]["navigation"]["success"] is True
    assert handoff["arrival_minute"] == 80
    assert handoff["arrival_clock"]["time"] == "18:20"
    assert handoff["triggered_clock_event_ids"] == []
    assert handoff["outcome"]["id"] == "prepared_watchtower_arrival"
    assert handoff["outcome"]["kind"] == "success"
    assert handoff["source_objectives"] == [
        {
            "id": "find_watchtower_hook",
            "name": "Przygotujcie wyprawę do strażnicy",
            "status": "completed",
        },
    ]
    assert {
        effect["parameters"]["key"]
        for effect in handoff["outcome"]["target_effects"]
    } >= {
        "quest_hook_found",
        "quest_accepted",
        "watchtower_clean_approach",
    }
    assert scene_flag(session.state.flags, "watchtower_dusk_arrival", False) is False
    assert scene_flag(session.state.flags, "watchtower_alerted", False) is False
    assert session.snapshot_path.exists()
    saved = json.loads(session.snapshot_path.read_text(encoding="utf-8"))
    assert {actor["id"] for actor in saved["actors"]} == {"hero", "rogue"}
    saved_flags = {
        item["key"]: item["value"]
        for item in saved["exploration"]["flags"]
    }
    assert saved_flags.items() >= {
        "quest_hook_found": True,
        "quest_accepted": True,
        "ready_for_watchtower": True,
    }.items()
    assert saved["exploration"]["party_position"]["zone_id"] == "forest_road"
    assert saved["exploration"]["elapsed_minutes"] == 80
    assert "elder_bren" in {
        item["npc_id"] for item in saved["exploration"]["npc_states"]
    }
    assert client.requests == []

    source_hero = next(
        actor for actor in session.exploration.actors if str(actor.id) == "hero"
    )
    started = session.start_scenario_handoff()

    assert started["scenario"]["id"] == "abandoned_watchtower"
    assert started["flow"]["stage"] == "waiting_for_board"
    assert started["flow"]["clock"]["time"] == "18:20"
    assert {
        actor["id"] for actor in started["actors"] if actor["faction"] == "ally"
    } == {"hero", "rogue", "cleric"}
    target_hero = next(
        actor for actor in session.exploration.actors if str(actor.id) == "hero"
    )
    target_hero_items = {item.id: item for item in target_hero.inventory}
    assert {
        item.id: item.quantity for item in source_hero.inventory
    }.items() <= {
        item.id: item.quantity for item in target_hero.inventory
    }.items()
    assert target_hero.currency == source_hero.currency
    target_rogue = next(
        actor for actor in session.exploration.actors if str(actor.id) == "rogue"
    )
    assert "thieves_tools" in target_rogue.proficiencies.tools
    assert {
        "crossbow",
        "dagger",
        "sticky_flask",
        "thieves_tools",
        "crossbow_bolt",
    } <= {item.id for item in target_rogue.inventory}
    assert target_hero_items["longsword"].equipped is True
    assert scene_flag(session.state.flags, "quest_hook_found", False) is True
    assert scene_flag(session.state.flags, "quest_accepted", False) is True
    assert scene_flag(session.state.flags, "watchtower_clean_approach", False) is True
    assert started["flow"]["scenario_handoff"]["applied"] is True


def test_village_delay_triggers_clock_consequences_during_watchtower_travel(
    tmp_path,
):
    session = ExplorationUiSession(
        "content/scenarios/village_square_mvp.json",
        debug_point_id="elder_npc",
        observation_dir=tmp_path / "observations",
        save_dir=tmp_path / "saves",
    )
    flags = session.state.flags
    for key in (
        "quest_hook_found",
        "quest_accepted",
        "ready_for_watchtower",
        "exploration_point_placed_elder_npc",
    ):
        flags = set_scene_flag(flags, key, True)
    session.state = replace(session.state, flags=flags)

    session.travel_to("tavern")
    session.confirm_exploration_setup_step()
    session.assign_exploration_point_position(Coordinate(3, 12))
    session.confirm_exploration_setup_step()
    session.start_short_rest()
    rested = session.confirm_short_rest()
    assert rested["flow"]["clock"]["time"] == "18:05"
    session.finish_short_rest()
    session.travel_to("market")
    session.confirm_exploration_setup_step()
    session.travel_to("forest_road")
    session.confirm_exploration_setup_step()

    completed = session.continue_scenario(
        navigator_actor_id="hero",
        navigation_roll=20,
    )
    handoff = completed["flow"]["scenario_handoff"]

    assert handoff["departure_minute"] == 85
    assert handoff["arrival_minute"] == 130
    assert handoff["arrival_clock"]["time"] == "19:10"
    assert handoff["triggered_clock_event_ids"] == [
        "dusk_on_old_road",
        "watchtower_defenders_alerted",
    ]
    assert handoff["outcome"]["id"] == "alerted_watchtower_arrival"
    assert handoff["outcome"]["kind"] == "partial_success"
    assert {
        effect["parameters"]["key"]
        for effect in handoff["outcome"]["target_effects"]
    } >= {
        "watchtower_dusk_arrival",
        "watchtower_alerted",
        "watchtower_reinforced",
    }
    assert scene_flag(session.state.flags, "watchtower_dusk_arrival", False) is True
    assert scene_flag(session.state.flags, "watchtower_alerted", False) is True
    saved = json.loads(session.snapshot_path.read_text(encoding="utf-8"))
    saved_flags = {
        item["key"]: item["value"]
        for item in saved["exploration"]["flags"]
    }
    assert saved_flags["clock_event:dusk_on_old_road"] is True
    assert saved_flags["clock_event:watchtower_defenders_alerted"] is True
    clock_messages = {
        message.title
        for message in session.messages
        if message.title in {"Zapada zmierzch", "Czas działa na korzyść goblinów"}
    }
    assert clock_messages == {"Zapada zmierzch", "Czas działa na korzyść goblinów"}


def test_village_failed_fast_navigation_adds_authored_delay(tmp_path):
    session = ExplorationUiSession(
        "content/scenarios/village_square_mvp.json",
        observation_dir=tmp_path / "observations",
        save_dir=tmp_path / "saves",
    )
    flags = set_scene_flag(session.state.flags, "ready_for_watchtower", True)
    session.state = replace(session.state, flags=flags)
    session.travel_to("forest_road")
    session.confirm_exploration_setup_step()
    departure_minute = session.state.elapsed_minutes

    completed = session.continue_scenario(
        pace="fast",
        navigator_actor_id="hero",
        navigation_roll=1,
    )
    handoff = completed["flow"]["scenario_handoff"]

    assert handoff["travel"]["pace_minutes"] == 34
    assert handoff["travel"]["navigation"]["success"] is False
    assert handoff["travel"]["navigation"]["delay_minutes"] == 30
    assert handoff["travel_minutes"] == 64
    assert handoff["arrival_minute"] == departure_minute + 64
    assert handoff["outcome"]["id"] == "lost_old_road"
    assert handoff["outcome"]["kind"] == "fail_forward"
    assert handoff["outcome"]["target_effects"][-1] == {
        "type": "set_flag",
        "parameters": {"key": "watchtower_route_lost", "value": True},
    }


def test_village_keeper_rumor_uses_authored_route_completes_hook_and_hides_goal():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "social",
            "player_narration": "Olan przypomina sobie rozmowę z woźnicą.",
            "npc_response": (
                "Przy starym trakcie widziano gobliny, a nocą w strażnicy paliły się światła."
            ),
            "requires_roll": False,
            "effects_on_success": [
                {
                    "type": "set_flag",
                    "parameters": {"key": "untrusted_llm_flag", "value": True},
                }
            ],
        }
    )
    client = FakeNpcClient(proposal)
    session = ExplorationUiSession(
        "content/scenarios/village_square_mvp.json",
        npc_client=client,
        debug_point_id="tavern_keeper",
    )

    initial = session.state_payload()
    assert {
        goal["id"] for goal in initial["active_point"]["npc"]["goals"]
    } == {"ask_watchtower_rumors", "chat_with_keeper", "order_olan_ale"}

    pending = session.submit_action(
        "Pytamy Olana, co słyszał o starym trakcie i opuszczonej strażnicy.",
        selected_goal_id="ask_watchtower_rumors",
        selected_check_participants="single_actor",
        participant_actor_ids=("rogue",),
    )

    assert client.requests == []
    resolved = pending
    assert resolved["pending"] is None
    assert scene_flag(session.state.flags, "tavern_rumor_heard", False) is True
    assert scene_flag(session.state.flags, "quest_hook_found", False) is True
    assert scene_flag(session.state.flags, "untrusted_llm_flag", False) is False
    assert {
        goal["id"] for goal in resolved["active_point"]["npc"]["goals"]
    } == {"chat_with_keeper", "order_olan_ale"}


def test_village_keeper_beer_branch_replaces_order_with_tasting_and_updates_attitude():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "social",
            "request_risk": "no_risk",
            "player_narration": (
                "Bohater próbuje piwa powoli, najpierw wyłapując zapach słodu."
            ),
            "npc_response": (
                "Olan uśmiecha się, słysząc porównanie chmielowej goryczki "
                "do zapachu mokrego lasu."
            ),
            "requires_roll": False,
            "rubric_outcome": "success",
            "success_message": "Szczera i obrazowa odpowiedź trafia do Olana.",
            "failure_message": "Zdawkowa odpowiedź rozczarowuje Olana.",
        }
    )
    client = FakeNpcClient(proposal)
    session = ExplorationUiSession(
        "content/scenarios/village_square_mvp.json",
        npc_client=client,
        debug_point_id="tavern_keeper",
    )

    initial_goal_ids = {
        goal["id"]
        for goal in session.state_payload()["active_point"]["npc"]["goals"]
    }
    assert "order_olan_ale" in initial_goal_ids
    assert "describe_olan_ale" not in initial_goal_ids

    after_order = session.submit_action(
        "Janek prosi Olana o kufel miejscowego piwa.",
        selected_goal_id="order_olan_ale",
        selected_check_participants="single_actor",
        participant_actor_ids=("hero",),
    )
    assert scene_flag(session.state.flags, "olan_beer_ordered", False) is True
    after_order_goal_ids = {
        goal["id"] for goal in after_order["active_point"]["npc"]["goals"]
    }
    assert "order_olan_ale" not in after_order_goal_ids
    assert "describe_olan_ale" in after_order_goal_ids
    assert client.requests == []

    pending_tasting = session.submit_action(
        (
            "Janek mówi, że piwo pachnie mokrym lasem po deszczu, "
            "a karmelowy słód łagodnie przechodzi w wytrawną goryczkę."
        ),
        selected_goal_id="describe_olan_ale",
        selected_check_participants="single_actor",
        participant_actor_ids=("hero",),
    )
    assert pending_tasting["pending"] is None
    assert client.requests[0].routed_intent_id == "beer_tasting"
    after_tasting = pending_tasting

    assert scene_flag(session.state.flags, "olan_beer_reviewed", False) is True
    assert after_tasting["active_point"]["npc"]["runtime_state"]["attitude"] == "friendly"
    final_goal_ids = {
        goal["id"] for goal in after_tasting["active_point"]["npc"]["goals"]
    }
    assert "describe_olan_ale" not in final_goal_ids


def test_npc_request_receives_only_that_npc_interaction_history():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "social",
            "request_risk": "no_risk",
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
    session.resolve_rolls({"hero": 20})
    session.submit_action("Wracamy do wcześniejszego pytania.")

    assert len(client.requests) == 2
    assert client.requests[0].conversation_thread == ()
    assert [entry.role for entry in client.requests[1].conversation_thread] == ["player", "gm", "gm", "gm"]
    assert client.requests[1].conversation_thread[0].content == "Pytamy zwiadowcę o bramę."
    assert client.requests[1].to_prompt_payload()["npc_runtime_state"]["relationship_events"][0]["intent"] == "social"


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
    runtime = state["active_point"]["npc"]["runtime_state"]
    assert runtime["revealed_information_ids"] == ["tower_hint"]
    assert "ustabilizowany" in runtime["physical_state"]


def test_failed_npc_roll_records_attempt_without_revealing_success_information():
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "medical",
            "player_narration": "Próbujecie opatrzyć zwiadowcę.",
            "npc_response": "Zwiadowca krzywi się z bólu.",
            "requires_roll": True,
            "ability": "wisdom",
            "skill": "medicine",
            "dc": 16,
            "success_message": "Rana została opatrzona.",
            "failure_message": "Nie udaje się ustabilizować rany.",
            "flag_changes_on_success": [{"key": "scout_stabilized", "value": True}],
            "revealed_information_ids": ["tower_hint"],
        }
    )
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        npc_client=FakeNpcClient(proposal),
        debug_point_id="wounded_scout",
    )

    session.submit_action("Próbujemy opatrzyć ranę.")
    session.decide("accept")
    state = session.resolve_rolls({"hero": 1})

    runtime = state["active_point"]["npc"]["runtime_state"]
    assert runtime["used_attempt_ids"] == ["medical"]
    assert runtime["revealed_information_ids"] == []
    assert runtime["relationship_events"][0]["outcome"] == "failure"
    assert "Nadal ranny" in runtime["physical_state"]
    assert {"key": "tower_hint_learned", "value": True} not in state["flags"]


def test_exploration_ui_session_writes_debug_log_for_npc_effects(tmp_path):
    proposal = NpcInteractionProposal.model_validate(
        {
            "action_type": "social",
            "request_risk": "no_risk",
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
    session.resolve_rolls({"hero": 20})

    events = [__import__("json").loads(line) for line in session.observer.path.read_text(encoding="utf-8").splitlines()]
    event_types = [event["event_type"] for event in events]
    effect_event = next(event for event in events if event["event_type"] == "ui_effect_applied")

    assert event_types[:1] == ["ui_session_started"]
    assert "ui_action_submitted" in event_types
    assert "ui_npc_proposal_validated" in event_types
    assert "ui_npc_runtime_updated" in event_types
    assert effect_event["payload"]["source"] == "npc_proposal"
    assert effect_event["payload"]["effect"]["parameters"]["key"] == "scout_calmed"
    assert {"key": "scout_calmed", "value": True} in effect_event["payload"]["flags"]
    assert "message" not in effect_event["payload"]

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


def test_exploration_ui_session_applies_retreat_outcome_without_a_winner():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)

    concluded = session.retreat_from_combat()

    assert concluded["combat"]["status"] == "finished"
    assert concluded["combat"]["winner"] is None
    assert concluded["combat"]["encounter_result"]["conclusion"] == "retreat"

    resolved = session.resolve_active_combat()

    assert resolved["combat"] is None
    assert {"key": "party_retreated_at_gate", "value": True} in resolved["flags"]


def test_gate_victory_awards_level_two_threshold_to_every_hero():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    for actor in tuple(session.combat_state.actors):
        if actor.faction == Faction.ENEMY:
            session.combat_state = replace_actor(
                session.combat_state,
                replace(actor, hp=0),
            )

    resolved = session.resolve_active_combat()

    heroes = tuple(
        actor
        for actor in session.exploration.actors
        if actor.faction == Faction.ALLY and actor.uses_death_saves
    )
    experience = resolved["flow"]["interaction_result"]["experience"]
    assert heroes
    assert all(actor.level == 1 for actor in heroes)
    assert all(actor.experience_points == 300 for actor in heroes)
    assert experience["per_actor"] == 300
    assert experience["total"] == 300 * len(heroes)
    assert {
        actor["id"]
        for actor in experience["level_up_actors"]
    } == {str(actor.id) for actor in heroes}
    assert all(
        actor["eligible_level"] == 2
        for actor in experience["level_up_actors"]
    )
    assert any(
        message["title"] == "Awans dostępny"
        for message in resolved["messages"]
    )


def test_gate_victory_persists_custom_party_xp_and_exposes_level_up_links():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    templates = tuple(
        actor
        for actor in session.exploration.actors
        if actor.faction == Faction.ALLY
    )
    party = tuple(
        replace(
            actor,
            id=f"saved_{actor.id}",
            experience_points=0,
        )
        for actor in templates
    )
    persisted = []
    session.configure_custom_party(party)
    session.character_progress_sink = lambda actors: persisted.extend(actors)
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    for actor in tuple(session.combat_state.actors):
        if actor.faction == Faction.ENEMY:
            session.combat_state = replace_actor(
                session.combat_state,
                replace(actor, hp=0),
            )

    resolved = session.resolve_active_combat()

    level_up_actors = resolved["flow"]["interaction_result"]["experience"][
        "level_up_actors"
    ]
    assert {actor["id"] for actor in level_up_actors} == {
        str(actor.id) for actor in party
    }
    assert all(actor["can_open_level_up"] for actor in level_up_actors)
    assert {str(actor.id): actor.experience_points for actor in persisted} == {
        str(actor.id): 300 for actor in party
    }


def test_combat_resolution_stashes_unclaimed_corpse_and_battlefield_loot():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    recovered_bolts = InventoryItem(
        "aftermath_bolts",
        "Odzyskane bełty",
        "ammunition",
        quantity=3,
        weight_lb=0.075,
        ammunition_type="bolt",
    )
    session.combat_state = replace(
        session.combat_state,
        battlefield_loot=(
            BattlefieldLoot(
                id="test_aftermath_bolts",
                position=Coordinate(7, 7),
                bundle=LootBundle(
                    id="test_aftermath_bolts",
                    label="Bełty z pola walki",
                    items=(recovered_bolts,),
                ),
            ),
        ),
    )
    for actor in tuple(session.combat_state.actors):
        if actor.faction == Faction.ENEMY:
            session.combat_state = replace_actor(
                session.combat_state,
                replace(actor, hp=0),
            )

    resolved = session.resolve_active_combat()

    assert resolved["combat"] is None
    hero = next(
        actor for actor in session.exploration.actors if str(actor.id) == "hero"
    )
    assert any(
        item.id == "poison_vial" and item.quantity == 2
        for item in hero.inventory
    )
    assert any(
        item.id == "aftermath_bolts" and item.quantity == 3
        for item in hero.inventory
    )
    assert hero.currency.sp == 10
    assert any(
        message["title"] == "Zabezpieczono łup po walce"
        for message in resolved["messages"]
    )


def test_exploration_ui_session_applies_surrender_outcome():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)

    concluded = session.surrender_combat()

    assert concluded["combat"]["status"] == "finished"
    assert concluded["combat"]["winner"] == "enemy"
    assert concluded["combat"]["encounter_result"]["conclusion"] == "surrender"

    resolved = session.resolve_active_combat()

    assert resolved["combat"] is None
    assert {"key": "party_surrendered_at_gate", "value": True} in resolved["flags"]


def test_combat_interaction_can_complete_objective_and_end_encounter():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    encounter = session._active_encounter()
    assert encounter is not None
    session._replace_active_encounter(
        replace(
            encounter,
            objectives=(
                SceneObjective(
                    id="secure_cart",
                    name="Zabezpiecz wóz",
                    description="Użyj wozu, aby zabezpieczyć pozycję.",
                    condition=SceneObjectiveCondition.INTERACT_WITH_OBJECT,
                    target_id="broken_cart",
                ),
            ),
        )
    )

    session.submit_combat_movement(col=7, row=7)
    session.select_board_position(Coordinate(7, 8))
    session.confirm_combat_context_menu("interact:broken_cart")
    concluded = session.confirm_combat_interaction("take_cover_cart")

    assert concluded["combat"]["status"] == "finished"
    assert concluded["combat"]["encounter_result"]["conclusion"] == (
        SceneConclusionType.OBJECTIVE_COMPLETED.value
    )
    assert concluded["combat"]["encounter_result"]["completed_objectives"] == [
        "secure_cart"
    ]
    assert any(
        actor["faction"] == "enemy" and not actor["defeated"]
        for actor in concluded["combat"]["actors"]
    )


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
    encounter = session._active_encounter()
    assert encounter is not None
    extra_attack_source = replace(
        session._attack_sources_for_actor(current_actor(session.combat_state))[0],
        loading=False,
    )
    encounter.attack_source_options_by_actor[hero.id] = (extra_attack_source,)
    encounter.attack_sources_by_actor[hero.id] = extra_attack_source
    session.selected_attack_source_ids[str(hero.id)] = extra_attack_source.id
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
    board = FakeBoardConnection(clicks=[tuple(target["position"])])
    session.attach_board_connection(board, backend="simulator")

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
    positions, colors = next(
        call for call in reversed(board.led_calls) if call[0] != "off"
    )
    highlighted = {
        tuple(position): color
        for position, color in zip(positions, colors, strict=True)
    }
    attacker_position = tuple(
        confirmed["combat"]["pending_player_attack"]["attacker"]["position"]
    )
    target_position = tuple(
        confirmed["combat"]["pending_player_attack"]["target"]["position"]
    )
    assert highlighted[attacker_position] == list(LedColor.ACTIVE_ACTOR)
    assert highlighted[target_position] == list(LedColor.SELECTED_ATTACK_TARGET)

    attack_roll = session.submit_player_attack_roll(natural_roll=20, natural_roll_2=20)
    pending = attack_roll["combat"]["pending_player_attack"]
    assert pending["stage"] == "damage_roll"
    assert pending["hit"] is True
    assert pending["critical"] is True
    assert any(
        positions != "off" and colors == list(LedColor.RANGED_PROJECTILE)
        for positions, colors in board.led_calls
    )
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


def test_exploration_ui_session_cannot_end_turn_during_pending_attack():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_combat_from_scout_alarm(session)
    target = session.state_payload()["combat"]["legal_targets"][0]

    selected = session.select_player_attack_target_at_position(
        Coordinate(*target["position"]),
    )

    assert selected["combat"]["pending_player_attack"]["stage"] == "confirm_attack"
    with pytest.raises(
        ValueError,
        match="Najpierw dokończ albo anuluj rozpoczętą akcję",
    ):
        session.finish_combat_turn()
    assert session.pending_player_attack is not None


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
    assert all(
        set(tile) == {"col", "row", "cost_feet"}
        for tile in state["combat"]["movement"]["destinations"]
    )
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


def test_limited_attack_consumes_resource_and_becomes_unavailable_in_ui() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    while str(session.combat_state.initiative_order.current_actor.id) != "hero":
        session.finish_combat_turn()
    hero_actor = current_actor(session.combat_state)
    enemies = [actor for actor in session.combat_state.actors if actor.faction == Faction.ENEMY]
    session.combat_state = replace_actor(
        session.combat_state,
        replace(
            enemies[0],
            position=Coordinate(hero_actor.position.col, hero_actor.position.row + 1),
        ),
    )
    for index, enemy in enumerate(enemies[1:], start=1):
        session.combat_state = replace_actor(
            session.combat_state,
            replace(enemy, position=Coordinate(15, index)),
        )

    selected = session.select_combat_attack_source("heroic_strike")
    source = next(
        item
        for item in selected["combat"]["available_attack_sources"]
        if item["id"] == "heroic_strike"
    )
    assert source["available"] is True
    assert source["resource_pool_id"] == "heroic_strike_uses"
    target_id = selected["combat"]["legal_targets"][0]["id"]

    resolved = session.submit_player_attack(
        target_id=target_id,
        natural_roll=20,
        natural_roll_2=20,
        damage=1,
    )

    hero = next(actor for actor in resolved["combat"]["actors"] if actor["id"] == "hero")
    assert hero["features"][0]["id"] == "heroic_strike"
    assert hero["features"][0]["source_kind"] == "scenario"
    resource = next(pool for pool in hero["resource_pools"] if pool["id"] == "heroic_strike_uses")
    source = next(
        item
        for item in resolved["combat"]["available_attack_sources"]
        if item["id"] == "heroic_strike"
    )
    assert resource["current"] == 0
    assert source["available"] is False
    assert "Brak dostępnych użyć" in source["unavailable_reason"]


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
        "ranged_threats": [],
        "flanking": False,
        "flanking_ally_ids": [],
    }
    assert pending["target_ac"] == goblin.ac + 2


def test_exploration_ui_session_sacred_flame_ignores_dexterity_save_cover() -> None:
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

    assert not any(
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
    assert pending["source"]["resource_label"] == "amunicja bolt: 20"
    assert pending["source"]["ammunition_remaining"] == 20
    assert pending["positioning"]["ranged_in_melee"] is True
    assert pending["positioning"]["ranged_threat_actor_ids"] == ["goblin_b"]
    assert pending["positioning"]["ranged_threats"] == [
        {
            "id": "goblin_b",
            "name": goblin.name,
            "position": [goblin.position.col, goblin.position.row],
        }
    ]
    assert any(
        modifier["label"] == "Atak dystansowy w zwarciu"
        for modifier in pending["active_modifiers"]
    )


def test_exploration_ui_crossbow_attack_consumes_and_displays_bolts() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    rogue = session.combat_state.initiative_order.current_actor
    assert str(rogue.id) == "rogue"
    session.selected_attack_source_ids["rogue"] = "crossbow_shot"
    before = session.state_payload()
    crossbow_before = next(
        source
        for source in before["combat"]["available_attack_sources"]
        if source["id"] == "crossbow_shot"
    )
    target_id = before["combat"]["legal_targets"][0]["id"]

    after = session.submit_player_attack(
        target_id=target_id,
        natural_roll=1,
        natural_roll_2=1,
    )

    rogue_after = next(
        actor for actor in after["combat"]["actors"] if actor["id"] == "rogue"
    )
    bolts_after = next(
        item for item in rogue_after["inventory"] if item["id"] == "crossbow_bolt"
    )
    crossbow_after = next(
        source
        for source in after["combat"]["available_attack_sources"]
        if source["id"] == "crossbow_shot"
    )
    assert crossbow_before["ammunition_remaining"] == 20
    assert bolts_after["quantity"] == 19
    assert crossbow_after["ammunition_remaining"] == 19
    assert crossbow_after["loading"] is True


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
    assert healed["combat"]["turn_action"]["action_use"] == "action_available"
    assert healed["combat"]["turn_action"]["bonus_action_use"] == "action_used"
    assert any(message["title"] == "Leczenie" and "HP 10 -> 16" in message["body"] for message in healed["messages"])


def test_exploration_ui_session_can_select_a_higher_spell_slot():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    while str(session.combat_state.initiative_order.current_actor.id) != "cleric":
        session.finish_combat_turn()
    cleric = next(actor for actor in session.combat_state.actors if str(actor.id) == "cleric")
    hero = next(actor for actor in session.combat_state.actors if str(actor.id) == "hero")
    session.combat_state = replace_actor(
        session.combat_state,
        replace(
            cleric,
            spell_slots=(SpellSlotState(1, 1, 2), SpellSlotState(2, 1, 1)),
        ),
    )
    session.combat_state = replace_actor(
        session.combat_state,
        replace(hero, hp=10),
    )

    selected = session.select_combat_healing_source("healing_word", cast_level=2)
    assert selected["combat"]["selected_healing_source_id"] == "healing_word@2"
    healing_payload = next(
        source
        for source in selected["combat"]["available_healing_sources"]
        if source["id"] == "healing_word"
    )
    assert healing_payload["available_cast_levels"] == [1, 2]

    target_position = next(
        actor.position
        for actor in session.combat_state.actors
        if str(actor.id) == "hero"
    )
    pending = session.select_player_healing_target_at_position(target_position)
    assert "2d4 + 3" in pending["combat"]["pending_player_healing"]["healing_instruction"]
    healed = session.submit_player_healing_roll(healing=4)
    cleric_payload = next(
        actor for actor in healed["combat"]["actors"] if actor["id"] == "cleric"
    )
    assert cleric_payload["spell_slots"] == [
        {"level": 1, "remaining": 1, "maximum": 2},
        {"level": 2, "remaining": 0, "maximum": 1},
    ]


def test_exploration_ui_session_casts_ritual_without_spending_a_slot():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    cleric_before = next(
        actor for actor in session.exploration.actors if str(actor.id) == "cleric"
    )
    slots_before = cleric_before.spell_slots
    elapsed_before = session.state.elapsed_minutes

    payload = session.cast_exploration_ritual(
        "cleric",
        "comprehend_languages",
    )

    cleric_after = next(
        actor for actor in session.exploration.actors if str(actor.id) == "cleric"
    )
    assert cleric_after.spell_slots == slots_before
    assert session.state.elapsed_minutes == elapsed_before + 10
    assert scene_flag(session.state.flags, "comprehend_languages_active") is True
    assert len(session.state.magic_effects) == 1
    effect = session.state.magic_effects[0]
    assert effect.spell_id == "comprehend_languages"
    assert effect.expires_at_minute == elapsed_before + 70
    payload_effect = next(
        active_effect
        for active_effect in payload["active_effects"]
        if active_effect["id"] == effect.id
    )
    assert payload_effect["expires"] == "Pozostało 60 min"
    assert any(
        message["title"] == "Rytuał"
        and "slot czaru nie został zużyty" in message["body"]
        for message in payload["messages"]
    )

    session.state = advance_exploration_time(session.state, 59).state
    assert scene_flag(session.state.flags, "comprehend_languages_active") is True
    session.state = advance_exploration_time(session.state, 1).state
    assert session.state.magic_effects == ()
    assert scene_flag(session.state.flags, "comprehend_languages_active") is False


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


def test_exploration_ui_session_upcasts_bless_for_multiple_targets():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    while str(session.combat_state.initiative_order.current_actor.id) != "cleric":
        session.finish_combat_turn()
    cleric_actor = next(
        actor for actor in session.combat_state.actors if str(actor.id) == "cleric"
    )
    session.combat_state = replace_actor(
        session.combat_state,
        replace(
            cleric_actor,
            spell_slots=(SpellSlotState(1, 2, 2), SpellSlotState(2, 1, 1)),
        ),
    )

    started = session.start_combat_concentration_action(
        "bless_attack_bonus",
        cast_level=2,
    )
    pending = started["combat"]["pending_concentration_action"]
    target_ids = tuple(target["id"] for target in pending["targets"])

    assert pending["cast_level"] == 2
    assert pending["maximum_targets"] == 4
    assert pending["action"]["target_count"] == 3
    assert pending["action"]["upcast_targets_per_level"] == 1
    assert pending["action"]["available_cast_levels"] == [1, 2]
    assert 1 <= len(target_ids) <= 4

    confirmed = session.confirm_combat_concentration_action(
        target_ids=target_ids,
    )
    cleric = next(
        actor for actor in confirmed["combat"]["actors"] if actor["id"] == "cleric"
    )

    assert cleric["spell_slots"] == [
        {"level": 1, "remaining": 2, "maximum": 2},
        {"level": 2, "remaining": 0, "maximum": 1},
    ]
    assert cleric["concentration"]["target_count"] == len(target_ids)
    assert set(cleric["concentration"]["target_actor_ids"]) == set(target_ids)
    blessed_targets = {
        actor["id"]
        for actor in confirmed["combat"]["actors"]
        if any(
            effect["kind"] == "concentration_attack_bonus"
            for effect in actor["effects"]
        )
    }
    assert blessed_targets == set(target_ids)


def test_bardic_inspiration_target_is_selected_on_the_board():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    bard = session.combat_state.initiative_order.current_actor
    bard = replace(
        bard,
        features=(
            *bard.features,
            FeatureGrant(
                feature_id="bardic_inspiration",
                label="Inspiracja bardowska",
                source_kind=FeatureSourceKind.CLASS,
                source_ref="bard",
                resource_ids=("bardic_inspiration_uses",),
                action_ids=("bardic_inspiration",),
            ),
        ),
        resource_pools=(
            *bard.resource_pools,
            ActorResourcePool(
                "bardic_inspiration_uses",
                "Inspiracja bardowska",
                2,
                2,
                RecoveryPeriod.LONG_REST,
            ),
        ),
    )
    session.combat_state = replace_actor(session.combat_state, bard)

    started = session.start_combat_class_feature_targeting(
        "bardic_inspiration",
    )
    targeting = started["combat"]["class_feature_targeting"]
    legal_positions = session._current_board_scan_target().positions

    assert targeting["action_id"] == "bardic_inspiration"
    assert "rzutu ataku" in targeting["instructions"]
    assert legal_positions

    resolved = session.select_board_position(legal_positions[0])

    assert resolved["combat"]["class_feature_targeting"] is None
    assert any(
        effect["kind"] == "bardic_inspiration"
        for actor in resolved["combat"]["actors"]
        for effect in actor["effects"]
    )


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
    session.ui_flow_stage = UiFlowStage.SPELL_PREPARATION
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

    cleric = session.combat_state.initiative_order.current_actor
    opened = session.select_board_position(cleric.position)
    area_option = next(
        option
        for option in opened["combat"]["context_menu"]["options"]
        if option["id"] == "attack-source:radiant_line"
    )
    assert area_option["label"] == "Rzuć czar obszarowy: Smuga światła"
    assert "linia 30 × 5 ft" in area_option["description"]

    selected = session.confirm_combat_context_menu("attack-source:radiant_line")

    assert selected["combat"]["selected_attack_source_id"] == "radiant_line"
    assert selected["combat"]["targeting"] == {
        "active": True,
        "source_id": "radiant_line",
        "source_name": "Smuga światła",
        "kind": "area",
        "area_shape": "line",
    }
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
    legal_area_positions = {tuple(position) for position in selected["combat"]["legal_area_positions"]}
    movement_only = next(
        Coordinate(position["col"], position["row"])
        for position in selected["combat"]["movement"]["destinations"]
        if (position["col"], position["row"]) not in legal_area_positions
        and (position["col"], position["row"]) != cleric.position.as_tuple()
    )
    with pytest.raises(ValueError, match="nie jest teraz aktywnym polem"):
        session.select_board_position(movement_only)

    pending = session.select_board_position(Coordinate(10, 6))

    area_spell = pending["combat"]["pending_area_spell"]
    assert pending["combat"]["targeting"] is None
    assert area_spell["source"]["id"] == "radiant_line"
    assert [11, 6] in area_spell["area_positions"]
    assert [target["id"] for target in area_spell["targets"]] == ["goblin_b"]

    confirmed = session.confirm_player_area_spell()
    cleric_after_confirm = next(actor for actor in confirmed["combat"]["actors"] if actor["id"] == "cleric")

    assert confirmed["combat"]["pending_area_spell"]["stage"] == "damage_roll"
    assert confirmed["combat"]["pending_area_spell"]["damage_components"]
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
    cleric = session.combat_state.initiative_order.current_actor
    opened = session.select_board_position(cleric.position)
    assert "Nieprzygotowane czary są niedostępne: Smuga światła" in opened["combat"]["context_menu"]["notice"]
    with pytest.raises(ValueError, match="nie został przygotowany"):
        session.select_combat_attack_source("radiant_line")


def test_exploration_ui_session_sacred_flame_uses_enemy_save_instead_of_attack_roll():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    while str(session.combat_state.initiative_order.current_actor.id) != "cleric":
        session.finish_combat_turn()
    session.encounter_rng = random.Random(0)

    cleric = session.combat_state.initiative_order.current_actor
    opened = session.select_board_position(cleric.position)
    sacred_flame_option = next(
        option
        for option in opened["combat"]["context_menu"]["options"]
        if option["id"] == "attack-source:sacred_flame"
    )
    assert sacred_flame_option["label"] == "Rzuć czar na pojedynczy cel: Święty płomień"
    selected = session.confirm_combat_context_menu("attack-source:sacred_flame")
    assert selected["combat"]["targeting"]["kind"] == "single_target"
    target_position = next(actor.position for actor in session.combat_state.actors if str(actor.id) == "goblin_b")
    target = session._current_board_scan_target()
    assert cleric.position in target.positions
    assert target_position in target.positions
    movement_only = next(
        Coordinate(position["col"], position["row"])
        for position in selected["combat"]["movement"]["destinations"]
        if Coordinate(position["col"], position["row"]) not in target.positions
    )
    with pytest.raises(ValueError, match="nie jest teraz aktywnym polem"):
        session.select_board_position(movement_only)

    pending = session.select_board_position(target_position)

    assert pending["combat"]["pending_player_attack"]["source"]["save_ability"] == "dexterity"
    assert pending["combat"]["pending_player_attack"]["spell_save_dc"] == 13
    assert pending["combat"]["targeting"] is None

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


def test_exploration_ui_session_reaction_window_advances_from_ready_to_opportunity():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)

    session.start_combat_ready()
    readied_actor, target = _prepare_ready_attack_trigger(session, "enemy_moves")
    pending_ready = session.pending_ready_attack
    assert pending_ready is not None
    opportunity_actor = next(
        actor
        for actor in session.combat_state.actors
        if actor.faction == Faction.ALLY and actor.id != readied_actor.id
    )
    session.pending_reaction_window = open_reaction_window(
        interrupted_actor_id=str(target.id),
        trigger_event="enemy_action",
        options=(
            ReactionOption(
                id=f"ready:{pending_ready.effect_id}:{target.id}",
                kind=ReactionKind.READY_ATTACK,
                reactor_actor_id=str(readied_actor.id),
                target_actor_id=str(target.id),
                trigger_event="enemy_moves",
                effect_id=pending_ready.effect_id,
                label="Ready",
            ),
            ReactionOption(
                id=f"opportunity:{opportunity_actor.id}:{target.id}",
                kind=ReactionKind.OPPORTUNITY_ATTACK,
                reactor_actor_id=str(opportunity_actor.id),
                target_actor_id=str(target.id),
                trigger_event="enemy_leaves_reach",
                label="Atak okazyjny",
            ),
        ),
    )
    session._activate_current_reaction_option()

    advanced = session.skip_ready_attack()

    assert advanced["combat"]["reaction_window"]["current_index"] == 1
    assert advanced["combat"]["pending_ready_attack"] is None
    assert (
        advanced["combat"]["pending_enemy_opportunity_attack"]["attacker"]["id"]
        == str(opportunity_actor.id)
    )

    resumed = session.skip_enemy_opportunity_attack()

    assert resumed["combat"]["reaction_window"] is None
    assert resumed["combat"]["pending_enemy_opportunity_attack"] is None
    assert resumed["combat"]["enemy_turn_preview"] is not None


def test_exploration_ui_session_reaction_window_skips_spent_reactor_options():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)

    session.start_combat_ready()
    readied_actor, target = _prepare_ready_attack_trigger(session, "enemy_moves")
    pending_ready = session.pending_ready_attack
    assert pending_ready is not None
    session.pending_reaction_window = open_reaction_window(
        interrupted_actor_id=str(target.id),
        trigger_event="enemy_action",
        options=(
            ReactionOption(
                id=f"ready:{pending_ready.effect_id}:{target.id}",
                kind=ReactionKind.READY_ATTACK,
                reactor_actor_id=str(readied_actor.id),
                target_actor_id=str(target.id),
                trigger_event="enemy_moves",
                effect_id=pending_ready.effect_id,
                label="Ready",
            ),
            ReactionOption(
                id=f"opportunity:{readied_actor.id}:{target.id}",
                kind=ReactionKind.OPPORTUNITY_ATTACK,
                reactor_actor_id=str(readied_actor.id),
                target_actor_id=str(target.id),
                trigger_event="enemy_leaves_reach",
                label="Atak okazyjny",
            ),
        ),
    )
    session._activate_current_reaction_option()

    session.start_ready_attack()
    resumed = session.submit_ready_attack_roll(natural_roll=1)

    assert resumed["combat"]["reaction_window"] is None
    assert resumed["combat"]["pending_ready_attack"] is None
    assert resumed["combat"]["pending_enemy_opportunity_attack"] is None
    assert resumed["combat"]["enemy_turn_preview"] is not None


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
    assert rolled["combat"]["pending_ready_attack"]["damage_components"]
    assert rolled["combat"]["pending_ready_attack"]["damage_components"][0]["dice"].startswith("2d")
    assert any(
        message["title"] == "Ready" and "2d" in message["body"]
        for message in rolled["messages"]
    )
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
    assert rolled["combat"]["pending_enemy_opportunity_attack"]["damage_components"]
    assert rolled["combat"]["pending_enemy_opportunity_attack"]["damage_components"][0]["dice"].startswith("2d")
    assert any(
        message["title"] == "Atak okazyjny" and "2d" in message["body"]
        for message in rolled["messages"]
    )
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
    assert "Kliknięte pole obiektu: (7, 8)" in approach["description"]
    assert f"faktyczne pole po ruchu: {tuple(approach['destination'])}" in approach["description"]
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
            InventoryItem(
                "borrowed_crossbow_bolt",
                "Pożyczony bełt",
                "ammunition",
                equipped=False,
                ammunition_type="bolt",
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


def test_exploration_ui_session_self_menu_keeps_bonus_class_feature_after_action():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    actor = session.combat_state.initiative_order.current_actor
    actor = replace(
        actor,
        hp=max(1, actor.hp - 1),
        features=(
            *actor.features,
            FeatureGrant(
                feature_id="second_wind",
                label="Drugi oddech",
                source_kind=FeatureSourceKind.CLASS,
                source_ref="fighter",
                resource_ids=("second_wind_uses",),
                action_ids=("second_wind",),
            ),
        ),
        resource_pools=(
            *actor.resource_pools,
            ActorResourcePool(
                id="second_wind_uses",
                label="Drugi oddech",
                current=1,
                maximum=1,
                recovery=RecoveryPeriod.SHORT_REST,
            ),
        ),
    )
    session.combat_state = replace_actor(session.combat_state, actor)
    session.combat_state = replace(
        session.combat_state,
        turn_action=replace(
            session.combat_state.turn_action,
            action_use=ActionUse.ACTION_USED,
        ),
    )

    opened = session.select_board_position(actor.position)
    option = next(
        item
        for item in opened["combat"]["context_menu"]["options"]
        if item["id"] == "class-feature:second_wind"
    )

    assert option["label"] == "Drugi oddech"
    assert option["provider"] == "class_feature"


def test_exploration_ui_session_cunning_action_keeps_mobility_after_action():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    actor = session.combat_state.initiative_order.current_actor
    actor = replace(
        actor,
        features=(
            *actor.features,
            FeatureGrant(
                feature_id="cunning_action",
                label="Sprytna akcja",
                source_kind=FeatureSourceKind.CLASS,
                source_ref="rogue",
            ),
        ),
    )
    session.combat_state = replace_actor(session.combat_state, actor)
    session.combat_state = replace(
        session.combat_state,
        turn_action=replace(
            session.combat_state.turn_action,
            action_use=ActionUse.ACTION_USED,
        ),
    )

    opened = session.select_board_position(actor.position)
    options = {
        item["id"]: item
        for item in opened["combat"]["context_menu"]["options"]
    }

    assert options["basic:dash"]["label"] == "Sprint"
    assert options["basic:disengage"]["label"] == "Odwrót"


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
        replace(
            source,
            attack_kind=AttackKind.MELEE,
            range_feet=5,
            ammunition_type=None,
            loading=False,
        )
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


def test_exploration_ui_session_charged_item_action_spends_charge_not_item() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.start_short_rest()
    session.confirm_short_rest(
        attunement_choices=[
            {
                "actor_id": "cleric",
                "item_id": "binding_wand",
                "action": "attune",
            }
        ]
    )
    session.finish_short_rest()
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    cleric_index = next(
        index
        for index, entry in enumerate(session.combat_state.initiative_order.entries)
        if str(entry.actor.id) == "cleric"
    )
    session.combat_state = replace(
        session.combat_state,
        initiative_order=replace(
            session.combat_state.initiative_order,
            current_index=cleric_index,
        ),
        turn_action=replace(
            session.combat_state.turn_action,
            action_use=ActionUse.ACTION_AVAILABLE,
        ),
    )
    cleric = current_actor(session.combat_state)
    goblin = next(
        actor for actor in session.combat_state.actors if actor.faction == Faction.ENEMY
    )
    goblin = replace(
        goblin,
        position=Coordinate(cleric.position.col, cleric.position.row + 1),
    )
    session.combat_state = replace_actor(session.combat_state, goblin)

    opened = session.select_board_position(goblin.position)
    option = next(
        item
        for item in opened["combat"]["context_menu"]["options"]
        if item["action_id"] == "binding_wand_restraint"
    )
    resolved = session.confirm_combat_context_menu(option["id"])
    cleric_payload = next(
        actor for actor in resolved["combat"]["actors"] if actor["id"] == "cleric"
    )
    wand = next(
        item for item in cleric_payload["inventory"] if item["id"] == "binding_wand"
    )

    assert wand["quantity"] == 1
    assert wand["charges_current"] == 6
    assert wand["charges_maximum"] == 7
    assert wand["attuned"] is True


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


def test_turn_start_recharge_is_applied_and_logged_in_combat_ui():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    entries = session.combat_state.initiative_order.entries
    goblin_index = next(
        index for index, entry in enumerate(entries) if str(entry.actor.id) == "goblin_a"
    )
    previous_index = (goblin_index - 1) % len(entries)
    goblin = next(actor for actor in session.combat_state.actors if str(actor.id) == "goblin_a")
    depleted = replace(
        goblin,
        resource_pools=(replace(goblin.resource_pools[0], current=0),),
    )
    session.combat_state = replace_actor(session.combat_state, depleted)
    session.combat_state = replace(
        session.combat_state,
        initiative_order=replace(
            session.combat_state.initiative_order,
            current_index=previous_index,
        ),
    )
    session.encounter_rng = type(
        "FixedRechargeRandom",
        (),
        {"randint": lambda self, _minimum, _maximum: 6},
    )()

    payload = session.finish_combat_turn()["combat"]

    current = payload["current_actor"]
    resource = next(pool for pool in current["resource_pools"] if pool["id"] == "frenzied_lunge_charge")
    assert current["id"] == "goblin_a"
    assert resource["current"] == 1
    assert resource["recharge"] == {"die_sides": 6, "minimum_roll": 5}
    assert any(message.title == "Recharge" and "d6 6" in message.body for message in session.messages)


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


def test_rubble_approach_option_names_diagonally_adjacent_target_and_disappears_without_one():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    actor = replace(session.combat_state.initiative_order.current_actor, position=Coordinate(8, 6))
    session.combat_state = replace_actor(session.combat_state, actor)
    enemies = tuple(candidate for candidate in session.combat_state.actors if candidate.faction == Faction.ENEMY)
    target = enemies[0]
    session.combat_state = replace_actor(session.combat_state, replace(target, position=Coordinate(9, 6)))
    for enemy in enemies[1:]:
        session.combat_state = replace_actor(session.combat_state, replace(enemy, position=Coordinate(20, 15)))

    with_target = session._combat_context_options(actor, Coordinate(11, 8))
    approach = next(option for option in with_target if option.id == "approach-interact:rubble_patch")

    assert "Aktualny cel:" in approach.description
    assert target.name in approach.description
    assert "obejmuje także skos" in approach.description

    session.combat_state = replace_actor(session.combat_state, replace(target, position=Coordinate(20, 14)))
    without_target = session._combat_context_options(actor, Coordinate(11, 8))

    assert "approach-interact:rubble_patch" not in [option.id for option in without_target]


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
    enemy_position = session.combat_state.initiative_order.current_actor.position.as_tuple()
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
    assert enemy_position in highlighted_positions
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
        assert result["combat"]["enemy_turn_result"]["message"].count("wynik końcowy:") == 1
        assert result["combat"]["enemy_turn_result"]["message"].count("HP celu:") <= 1

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


def test_exploration_ui_session_offers_and_casts_shield_before_enemy_damage():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    cleric = next(
        actor for actor in session.combat_state.actors if str(actor.id) == "cleric"
    )
    enemy = next(
        actor for actor in session.combat_state.actors if actor.faction == Faction.ENEMY
    )
    target = actor_as_combat_target(cleric)
    source = AttackSource(
        "Testowy atak",
        AttackSourceType.WEAPON,
        5,
        D20RollRequest(),
        damage_fixed=4,
    )
    attack_roll = resolve_d20_roll(D20RollInput(source.attack_roll_request, target.ac))
    attack = resolve_attack(
        AttackDeclaration(enemy, target, source),
        attack_roll,
        ActionUse.ACTION_AVAILABLE,
    )
    damage = resolve_damage((DamageComponentInput(4, DamageType.SLASHING),))
    applied = apply_damage_result(cleric, damage)
    session.pending_enemy_turn_result = EnemyAutoTurnResult(
        state=replace_actor(session.combat_state, applied.actor_after),
        enemy=enemy,
        target=target,
        message="Trafienie.",
        attack_roll=attack_roll,
        attack_resolution=attack,
        damage=damage,
        applied_damage=applied,
        updated_target=applied.actor_after,
        action_used=True,
        source=source,
    )

    offered = session._commit_pending_enemy_turn()

    window = offered["combat"]["reaction_window"]
    assert window["options"][0]["kind"] == "defensive_spell"
    assert offered["combat"]["enemy_turn_result"] is None
    with pytest.raises(ValueError, match="oczekującą reakcję"):
        session._commit_pending_enemy_turn()

    resolved = session.cast_defensive_spell_reaction()

    cleric_after = next(
        actor for actor in session.combat_state.actors if actor.id == cleric.id
    )
    assert cleric_after.hp == cleric.hp
    assert resolved["combat"]["enemy_turn_result"]["hit"] is False
    assert resolved["combat"]["enemy_turn_result"].get("damage") is None
    assert any(
        effect["kind"] == "spell_ac_bonus" and effect["value"] == 5
        for effect in resolved["combat"]["active_effects"]
    )


def test_exploration_ui_session_hellish_rebuke_spends_reaction_and_slot_once():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    encounter = session._active_encounter()
    assert encounter is not None
    cleric = next(
        actor for actor in session.combat_state.actors if str(actor.id) == "cleric"
    )
    enemy = next(
        actor for actor in session.combat_state.actors if actor.faction == Faction.ENEMY
    )
    counterspell = next(
        action
        for action in encounter.combat_actions_by_actor[cleric.id]
        if action.action_type == "spell_counter"
    )
    rebuke = replace(
        counterspell,
        action_type="reaction_damage",
        label="Hellish Rebuke",
        save_ability="dexterity",
        damage_die_sides=10,
        damage_type="fire",
        ongoing_damage_dice_count=2,
        upcast_value_per_level=1,
    )
    encounter.combat_actions_by_actor[cleric.id] = (rebuke,)
    target = actor_as_combat_target(cleric)
    source = AttackSource(
        "Testowy atak",
        AttackSourceType.WEAPON,
        5,
        D20RollRequest(),
        damage_fixed=4,
    )
    attack_roll = resolve_d20_roll(
        D20RollInput(source.attack_roll_request, target.ac)
    )
    attack = resolve_attack(
        AttackDeclaration(enemy, target, source),
        attack_roll,
        ActionUse.ACTION_AVAILABLE,
    )
    damage = resolve_damage((DamageComponentInput(4, DamageType.SLASHING),))
    applied = apply_damage_result(cleric, damage)
    session.pending_enemy_turn_result = EnemyAutoTurnResult(
        state=replace_actor(session.combat_state, applied.actor_after),
        enemy=enemy,
        target=target,
        message="Trafienie.",
        attack_roll=attack_roll,
        attack_resolution=attack,
        damage=damage,
        applied_damage=applied,
        updated_target=applied.actor_after,
        action_used=True,
        source=source,
    )
    slots_before = next(
        slot.remaining for slot in cleric.spell_slots if slot.level == rebuke.spell_level
    )
    enemy_hp_before = enemy.hp

    offered = session._commit_pending_enemy_turn()

    assert offered["combat"]["reaction_window"]["options"][0]["kind"] == (
        "retaliation_spell"
    )

    resolved = session.cast_retaliation_spell_reaction()

    cleric_after = next(
        actor for actor in session.combat_state.actors if actor.id == cleric.id
    )
    enemy_after = next(
        actor for actor in session.combat_state.actors if actor.id == enemy.id
    )
    assert next(
        slot.remaining
        for slot in cleric_after.spell_slots
        if slot.level == rebuke.spell_level
    ) == slots_before - 1
    assert reaction_available_for(session.combat_state, cleric_after) is False
    assert enemy_after.hp < enemy_hp_before
    assert resolved["combat"]["reaction_window"] is None
    assert resolved["combat"]["enemy_turn_result"] is not None


def test_exploration_ui_session_counterspell_interrupts_enemy_spell_before_shield():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    cleric = next(
        actor for actor in session.combat_state.actors if str(actor.id) == "cleric"
    )
    enemy = next(
        actor for actor in session.combat_state.actors if actor.faction == Faction.ENEMY
    )
    target = actor_as_combat_target(cleric)
    source = AttackSource(
        "Wrogi płomień",
        AttackSourceType.SPELL,
        60,
        D20RollRequest(),
        damage_fixed=4,
        id="enemy_flame",
        spell_level=3,
        cast_level=3,
    )
    attack_roll = resolve_d20_roll(D20RollInput(source.attack_roll_request, 15))
    attack = resolve_attack(
        AttackDeclaration(enemy, target, source),
        attack_roll,
        ActionUse.ACTION_AVAILABLE,
    )
    damage = resolve_damage((DamageComponentInput(4, DamageType.FIRE),))
    applied = apply_damage_result(cleric, damage)
    session.pending_enemy_turn_result = EnemyAutoTurnResult(
        state=replace_actor(session.combat_state, applied.actor_after),
        enemy=enemy,
        target=target,
        message="Trafienie czarem.",
        attack_roll=attack_roll,
        attack_resolution=attack,
        damage=damage,
        applied_damage=applied,
        updated_target=applied.actor_after,
        action_used=True,
        source=source,
    )

    offered = session._commit_pending_enemy_turn()

    window = offered["combat"]["reaction_window"]
    assert window["options"][0]["kind"] == "spell_counter"
    assert window["options"][0]["cast_levels"] == [3]

    resolved = session.cast_counterspell_reaction(cast_level=3)

    cleric_after = next(
        actor for actor in session.combat_state.actors if actor.id == cleric.id
    )
    assert cleric_after.hp == cleric.hp
    assert resolved["combat"]["enemy_turn_result"]["spell_countered"] is True
    assert resolved["combat"]["enemy_turn_result"].get("damage") is None
    assert next(
        slot for slot in cleric_after.spell_slots if slot.level == 3
    ).remaining == 0


def test_exploration_ui_session_starts_and_discloses_long_cast_progress():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    while str(session.combat_state.initiative_order.current_actor.id) != "cleric":
        session.finish_combat_turn()
    cleric = session.combat_state.initiative_order.current_actor
    slot_before = next(
        slot.remaining for slot in cleric.spell_slots if slot.level == 1
    )

    started = session.start_long_cast("warding_rite", cast_level=1)

    pending = started["combat"]["long_cast"]
    assert pending["spell_id"] == "warding_rite"
    assert pending["completed_actions"] == 1
    assert pending["required_actions"] == 10
    assert any(
        effect["kind"] == "concentration_long_cast"
        for effect in started["combat"]["active_effects"]
    )
    cleric_after = next(
        actor for actor in session.combat_state.actors if actor.id == cleric.id
    )
    assert next(
        slot.remaining for slot in cleric_after.spell_slots if slot.level == 1
    ) == slot_before


def test_exploration_ui_session_summons_actor_with_player_turn_and_attack():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    while str(session.combat_state.initiative_order.current_actor.id) != "cleric":
        session.finish_combat_turn()

    started = session.start_summon("call_guardian_spirit", cast_level=1)

    pending = started["combat"]["pending_summon"]
    assert pending["action_id"] == "call_guardian_spirit"
    position = pending["legal_positions"][0]
    confirmed = session.confirm_summon(
        col=position["col"],
        row=position["row"],
    )

    summon = confirmed["combat"]["summoned_creatures"][0]
    assert summon["name"] == "Duch strażnik"
    assert any(
        effect["kind"] == "concentration_summon"
        for effect in confirmed["combat"]["active_effects"]
    )
    summoned_actor_id = summon["actor_id"]
    session.finish_combat_turn()
    payload = session.state_payload()["combat"]
    assert payload["current_actor"]["id"] == summoned_actor_id
    assert payload["available_attack_sources"][0]["id"] == "spirit_claw"


def test_exploration_ui_session_lost_concentration_dismisses_summon():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    while str(session.combat_state.initiative_order.current_actor.id) != "cleric":
        session.finish_combat_turn()
    cleric = session.combat_state.initiative_order.current_actor
    started = session.start_summon("call_guardian_spirit", cast_level=1)
    position = started["combat"]["pending_summon"]["legal_positions"][0]
    confirmed = session.confirm_summon(
        col=position["col"],
        row=position["row"],
    )
    summoned_actor_id = confirmed["combat"]["summoned_creatures"][0]["actor_id"]
    damage = resolve_damage((DamageComponentInput(4, DamageType.FIRE),))
    applied = apply_damage_result(cleric, damage)
    session.combat_state = replace_actor(session.combat_state, applied.actor_after)

    session._maybe_prompt_concentration_check(applied)
    assert session.pending_concentration_check is not None
    resolved = session.submit_concentration_check(natural_roll=1)

    assert resolved["combat"]["summoned_creatures"] == []
    assert all(
        actor["id"] != summoned_actor_id
        for actor in resolved["combat"]["actors"]
    )
    assert all(
        entry.actor.id != summoned_actor_id
        for entry in session.combat_state.initiative_order.entries
    )


def test_exploration_ui_session_teleports_without_spending_movement():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    while str(session.combat_state.initiative_order.current_actor.id) != "cleric":
        session.finish_combat_turn()
    origin = session.combat_state.initiative_order.current_actor.position
    session.use_combat_dodge()
    cleric = session.combat_state.initiative_order.current_actor
    options = session._combat_context_options(cleric, cleric.position)
    assert "combat-action:veil_step" in {option.id for option in options}

    started = session.start_magic_movement("veil_step", cast_level=1)

    pending = started["combat"]["pending_magic_movement"]
    assert pending["kind"] == "teleport"
    movement_before = started["combat"]["movement"]["remaining_feet"]
    destination = pending["legal_positions"][0]
    confirmed = session.confirm_magic_movement(
        col=destination["col"],
        row=destination["row"],
    )

    assert confirmed["combat"]["pending_magic_movement"] is None
    assert confirmed["combat"]["current_actor"]["position"] == [
        destination["col"],
        destination["row"],
    ]
    assert confirmed["combat"]["current_actor"]["position"] != list(origin.as_tuple())
    assert confirmed["combat"]["movement"]["remaining_feet"] == movement_before


def test_exploration_ui_session_forced_movement_selects_target_from_board_flow():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    while str(session.combat_state.initiative_order.current_actor.id) != "cleric":
        session.finish_combat_turn()
    session.encounter_rng = random.Random(1)

    started = session.start_magic_movement("repelling_pulse", cast_level=1)

    pending = started["combat"]["pending_magic_movement"]
    assert pending["kind"] == "push"
    target = pending["targets"][0]
    origin = target["position"]
    confirmed = session._handle_board_position(
        Coordinate(target["position"][0], target["position"][1])
    )
    target_after = next(
        actor
        for actor in confirmed["combat"]["actors"]
        if actor["id"] == target["id"]
    )

    assert confirmed["combat"]["pending_magic_movement"] is None
    assert target_after["position"] != origin


def test_exploration_ui_session_spell_debuff_selects_target_from_board_flow():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    while str(session.combat_state.initiative_order.current_actor.id) != "cleric":
        session.finish_combat_turn()
    session.encounter_rng = random.Random(1)
    cleric = session.combat_state.initiative_order.current_actor
    options = session._combat_context_options(cleric, cleric.position)
    assert "combat-action:weakening_miasma" in {option.id for option in options}

    started = session.start_spell_debuff("weakening_miasma", cast_level=1)

    pending = started["combat"]["pending_spell_debuff"]
    assert pending["condition"] == "poisoned"
    assert pending["save_ability"] == "constitution"
    target = pending["targets"][0]
    confirmed = session._handle_board_position(
        Coordinate(target["position"][0], target["position"][1])
    )
    target_after = next(
        actor
        for actor in confirmed["combat"]["actors"]
        if actor["id"] == target["id"]
    )

    assert confirmed["combat"]["pending_spell_debuff"] is None
    assert "poisoned" in target_after["conditions"]
    condition = next(
        item
        for item in session.combat_state.condition_states
        if item.actor_id == target["id"]
    )
    assert condition.save_timing == ConditionSaveTiming.TURN_END


def test_exploration_ui_session_spell_dispel_removes_magical_condition_from_board():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    while str(session.combat_state.initiative_order.current_actor.id) != "cleric":
        session.finish_combat_turn()
    enemy = next(
        actor
        for actor in session.combat_state.actors
        if actor.faction == Faction.ENEMY
    )
    condition = ConditionState(
        actor_id=str(enemy.id),
        condition=CombatCondition.POISONED,
        source_actor_id="enemy_caster",
        source_label="Wroga miazma",
        save_ability="constitution",
        save_dc=13,
        save_timing=ConditionSaveTiming.TURN_END,
        source_spell_id="enemy_miasma",
        source_spell_level=1,
    )
    session.combat_state = replace(
        session.combat_state,
        condition_states=(condition,),
    )
    cleric = session.combat_state.initiative_order.current_actor
    options = session._combat_context_options(cleric, cleric.position)
    assert "combat-action:unravel_magic" in {option.id for option in options}

    started = session.start_spell_dispel("unravel_magic", cast_level=1)

    pending = started["combat"]["pending_spell_dispel"]
    target = next(
        target for target in pending["targets"] if target["id"] == str(enemy.id)
    )
    confirmed = session._handle_board_position(
        Coordinate(target["position"][0], target["position"][1])
    )

    assert confirmed["combat"]["pending_spell_dispel"] is None
    assert session.combat_state.condition_states == ()
    enemy_after = next(
        actor
        for actor in confirmed["combat"]["actors"]
        if actor["id"] == str(enemy.id)
    )
    assert "poisoned" not in enemy_after["conditions"]


def test_exploration_ui_session_damage_can_interrupt_long_cast_without_slot():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    while str(session.combat_state.initiative_order.current_actor.id) != "cleric":
        session.finish_combat_turn()
    cleric = session.combat_state.initiative_order.current_actor
    slot_before = next(
        slot.remaining for slot in cleric.spell_slots if slot.level == 1
    )
    session.start_long_cast("warding_rite", cast_level=1)
    damage = resolve_damage((DamageComponentInput(4, DamageType.FIRE),))
    applied = apply_damage_result(cleric, damage)
    session.combat_state = replace_actor(session.combat_state, applied.actor_after)

    session._maybe_prompt_concentration_check(applied)
    assert session.pending_concentration_check is not None
    resolved = session.submit_concentration_check(natural_roll=1)

    assert resolved["combat"]["long_cast"] is None
    assert not any(
        effect["kind"] == "concentration_long_cast"
        for effect in resolved["combat"]["active_effects"]
    )
    cleric_after = next(
        actor for actor in session.combat_state.actors if actor.id == cleric.id
    )
    assert next(
        slot.remaining for slot in cleric_after.spell_slots if slot.level == 1
    ) == slot_before


def test_exploration_ui_session_missing_required_action_interrupts_long_cast():
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    _start_gate_skirmish(session)
    assert session.combat_state is not None
    while str(session.combat_state.initiative_order.current_actor.id) != "cleric":
        session.finish_combat_turn()
    session.start_long_cast("warding_rite", cast_level=1)
    session.finish_combat_turn()
    while str(session.combat_state.initiative_order.current_actor.id) != "cleric":
        session.finish_combat_turn()

    resolved = session.finish_combat_turn()

    assert session.combat_state.long_casts == ()
    assert not any(
        effect["kind"] == "concentration_long_cast"
        for effect in resolved["combat"]["active_effects"]
    )
    assert any(
        message["title"] == "Przerwane rzucanie"
        and "nie poświęcono akcji" in message["body"]
        for message in resolved["messages"]
    )


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


def test_context_menu_loots_defeated_enemy_and_spends_action() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    combat = _start_gate_skirmish(session)
    actor = combat.initiative_order.current_actor
    source = next(candidate for candidate in combat.actors if candidate.faction == Faction.ENEMY)
    source = replace(
        source,
        hp=0,
        position=Coordinate(actor.position.col + 1, actor.position.row),
        inventory=(
            InventoryItem(
                "test_loot",
                "Łup testowy",
                "treasure",
                equipped=False,
                weight_lb=1,
                value_cp=250,
            ),
        ),
        currency=CurrencyWallet(sp=5),
    )
    session.combat_state = replace(
        combat,
        actors=tuple(source if candidate.id == source.id else candidate for candidate in combat.actors),
    )

    options = session._combat_context_options(actor, source.position)
    opened = session._open_combat_context_menu(actor, source.position, options)
    option = next(
        candidate
        for candidate in opened["combat"]["context_menu"]["options"]
        if candidate["action"] == "loot"
    )
    looted = session.confirm_combat_context_menu(option["id"])

    actor_after = next(
        candidate for candidate in looted["combat"]["actors"] if candidate["id"] == str(actor.id)
    )
    source_after = next(
        candidate for candidate in looted["combat"]["actors"] if candidate["id"] == str(source.id)
    )
    assert actor_after["currency"]["sp"] == 5
    assert any(item["id"] == "test_loot" for item in actor_after["inventory"])
    assert source_after["currency"]["sp"] == 0
    assert source_after["inventory"] == []
    assert looted["combat"]["turn_action"]["action_use"] == "action_used"


def test_finished_combat_keeps_defeated_enemy_loot_selectable_without_action_cost() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    combat = _start_gate_skirmish(session)
    actor = combat.initiative_order.current_actor
    source = next(candidate for candidate in combat.actors if candidate.faction == Faction.ENEMY)
    source = replace(
        source,
        hp=0,
        inventory=(
            InventoryItem(
                "post_combat_loot",
                "Łup po walce",
                "treasure",
                equipped=False,
                weight_lb=1,
            ),
        ),
    )
    session.combat_state = replace(
        combat,
        status=CombatStatus.FINISHED,
        actors=tuple(source if candidate.id == source.id else candidate for candidate in combat.actors),
    )

    scan_target = session._current_board_scan_target()
    assert source.position in scan_target.positions
    options = session._combat_context_options(actor, source.position)
    opened = session._open_combat_context_menu(actor, source.position, options)
    option = next(
        candidate
        for candidate in opened["combat"]["context_menu"]["options"]
        if candidate["action"] == "loot"
    )
    looted = session.confirm_combat_context_menu(option["id"])

    actor_after = next(
        candidate for candidate in looted["combat"]["actors"] if candidate["id"] == str(actor.id)
    )
    assert any(item["id"] == "post_combat_loot" for item in actor_after["inventory"])
    assert looted["combat"]["status"] == "finished"


def test_finished_combat_partially_collects_recovered_ammunition_from_battlefield() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    combat = _start_gate_skirmish(session)
    actor = combat.initiative_order.current_actor
    bolt = replace(
        next(
            item
            for item in actor.inventory
            if item.ammunition_type == "bolt"
        ),
        quantity=4,
    )
    position = Coordinate(actor.position.col + 1, actor.position.row)
    session.combat_state = replace(
        combat,
        status=CombatStatus.FINISHED,
        winner=Faction.ALLY,
        ammunition_expenditures=(
            AmmunitionExpenditure(
                shooter_actor_id=actor.id,
                shooter_faction=Faction.ALLY,
                ammunition_type="bolt",
                item=replace(bolt, quantity=1),
                quantity=9,
            ),
        ),
        battlefield_loot=(
            BattlefieldLoot(
                id="recovered_ammunition",
                position=position,
                bundle=LootBundle(
                    id="battlefield:recovered_ammunition",
                    label="Odzyskana amunicja",
                    items=(bolt,),
                ),
            ),
        ),
    )

    scan_target = session._current_board_scan_target()
    assert position in scan_target.positions
    options = session._combat_context_options(actor, position)
    option = next(
        candidate
        for candidate in options
        if candidate.provider == "battlefield_loot"
        and candidate.action == CombatMenuAction.LOOT_ITEM
    )
    opened = session._open_combat_context_menu(actor, position, options)
    looted = session.confirm_combat_context_menu(option.id, quantity=2)

    actor_after = next(
        candidate
        for candidate in looted["combat"]["actors"]
        if candidate["id"] == str(actor.id)
    )
    assert any(
        item["ammunition_type"] == "bolt" and item["quantity"] >= 2
        for item in actor_after["inventory"]
    )
    assert looted["combat"]["battlefield_loot"][0]["items"][0]["quantity"] == 2
    assert looted["combat"]["ammunition_recovery"] == {
        "fired": 9,
        "recoverable": 4,
    }


def test_combat_loot_can_take_part_of_item_stack_and_leave_remainder() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    combat = _start_gate_skirmish(session)
    actor = combat.initiative_order.current_actor
    source = next(candidate for candidate in combat.actors if candidate.faction == Faction.ENEMY)
    source = replace(
        source,
        hp=0,
        position=Coordinate(actor.position.col + 1, actor.position.row),
        inventory=(
            InventoryItem(
                "bolt_stack",
                "Bełty testowe",
                "ammunition",
                quantity=7,
                equipped=False,
                ammunition_type="bolt",
                weight_lb=0.075,
            ),
        ),
    )
    session.combat_state = replace(
        combat,
        actors=tuple(
            source if candidate.id == source.id else candidate
            for candidate in combat.actors
        ),
    )

    options = session._combat_context_options(actor, source.position)
    option = next(
        candidate
        for candidate in options
        if candidate.id == f"loot-item:{source.id}:bolt_stack"
    )
    assert option.loot_quantity_max == 7
    assert option.loot_unit_weight_lb == 0.075
    opened = session._open_combat_context_menu(actor, source.position, options)
    payload_option = next(
        candidate
        for candidate in opened["combat"]["context_menu"]["options"]
        if candidate["id"] == option.id
    )
    assert payload_option["loot_quantity_max"] == 7

    looted = session.confirm_combat_context_menu(option.id, quantity=3)

    actor_after = next(
        candidate for candidate in looted["combat"]["actors"] if candidate["id"] == str(actor.id)
    )
    source_after = next(
        candidate for candidate in looted["combat"]["actors"] if candidate["id"] == str(source.id)
    )
    assert next(item for item in actor_after["inventory"] if item["id"] == "bolt_stack")["quantity"] == 3
    assert next(item for item in source_after["inventory"] if item["id"] == "bolt_stack")["quantity"] == 4
    assert looted["combat"]["turn_action"]["action_use"] == "action_used"


def test_combat_loot_can_take_selected_coin_denomination_quantity() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    combat = _start_gate_skirmish(session)
    actor = combat.initiative_order.current_actor
    source = next(candidate for candidate in combat.actors if candidate.faction == Faction.ENEMY)
    source = replace(
        source,
        hp=0,
        position=Coordinate(actor.position.col + 1, actor.position.row),
        currency=CurrencyWallet(sp=25, gp=2),
    )
    session.combat_state = replace(
        combat,
        actors=tuple(
            source if candidate.id == source.id else candidate
            for candidate in combat.actors
        ),
    )

    options = session._combat_context_options(actor, source.position)
    option = next(
        candidate
        for candidate in options
        if candidate.currency_denomination == "sp"
    )
    session._open_combat_context_menu(actor, source.position, options)
    looted = session.confirm_combat_context_menu(option.id, quantity=7)

    actor_after = next(
        candidate for candidate in looted["combat"]["actors"] if candidate["id"] == str(actor.id)
    )
    source_after = next(
        candidate for candidate in looted["combat"]["actors"] if candidate["id"] == str(source.id)
    )
    assert actor_after["currency"]["sp"] == 7
    assert source_after["currency"]["sp"] == 18
    assert source_after["currency"]["gp"] == 2


def test_invalid_partial_loot_quantity_keeps_context_menu_open() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    combat = _start_gate_skirmish(session)
    actor = combat.initiative_order.current_actor
    actor = replace(
        actor,
        ability_scores=replace(actor.ability_scores, strength=1),
        inventory=(
            InventoryItem(
                "ballast",
                "Ciężki bagaż",
                "gear",
                equipped=False,
                weight_lb=15,
            ),
        ),
    )
    source = next(candidate for candidate in combat.actors if candidate.faction == Faction.ENEMY)
    source = replace(
        source,
        hp=0,
        position=Coordinate(actor.position.col + 1, actor.position.row),
        inventory=(
            InventoryItem(
                "heavy_loot",
                "Ciężki łup",
                "treasure",
                quantity=2,
                equipped=False,
                weight_lb=1,
            ),
        ),
    )
    session.combat_state = replace(
        combat,
        actors=tuple(
            actor
            if candidate.id == actor.id
            else source
            if candidate.id == source.id
            else candidate
            for candidate in combat.actors
        ),
    )
    options = session._combat_context_options(actor, source.position)
    option = next(candidate for candidate in options if candidate.item_id == "heavy_loot")
    assert option.recipient_remaining_capacity_lb == 0
    session._open_combat_context_menu(actor, source.position, options)

    with pytest.raises(ValueError, match="przekracza udźwig"):
        session.confirm_combat_context_menu(option.id, quantity=1)

    assert session.pending_combat_context_menu is not None
    assert session.combat_state.turn_action.action_use.value == "action_available"


def test_village_merchant_supports_partial_buy_and_resale() -> None:
    session = ExplorationUiSession("content/scenarios/village_square_mvp.json")
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    opened = session.select_point("merchant_stall")

    assert opened["active_point"]["has_merchant"] is True
    assert opened["trade"]["merchant_id"] == "mira_market_stall"
    assert next(
        item for item in opened["trade"]["stock"] if item["id"] == "crossbow_bolt"
    )["quantity"] == 40

    purchased = session.buy_merchant_item(
        merchant_id="mira_market_stall",
        actor_id="hero",
        item_id="crossbow_bolt",
        quantity=10,
    )

    hero = next(actor for actor in purchased["actors"] if actor["id"] == "hero")
    assert hero["currency"]["total_cp"] == 950
    assert next(
        item for item in hero["inventory"] if item["id"] == "crossbow_bolt"
    )["quantity"] == 10
    assert next(
        item for item in purchased["trade"]["stock"] if item["id"] == "crossbow_bolt"
    )["quantity"] == 30

    sold = session.sell_merchant_item(
        merchant_id="mira_market_stall",
        actor_id="hero",
        item_id="crossbow_bolt",
        quantity=4,
    )

    hero = next(actor for actor in sold["actors"] if actor["id"] == "hero")
    assert hero["currency"]["total_cp"] == 958
    assert next(
        item for item in hero["inventory"] if item["id"] == "crossbow_bolt"
    )["quantity"] == 6
    assert next(
        item for item in sold["trade"]["stock"] if item["id"] == "crossbow_bolt"
    )["quantity"] == 34


def test_village_downtime_crafting_spends_materials_adds_item_and_advances_clock() -> None:
    session = ExplorationUiSession("content/scenarios/village_square_mvp.json")
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE

    before = session.state_payload()

    assert before["downtime"]["zone_id"] == "market"
    recipe = before["downtime"]["recipes"][0]
    assert recipe["id"] == "forge_dagger"
    assert recipe["material_cost_cp"] == 100
    assert recipe["time_cost_minutes"] == 480
    hero_availability = next(
        entry
        for entry in recipe["availability"]
        if entry["actor_id"] == "hero"
    )
    rogue_availability = next(
        entry
        for entry in recipe["availability"]
        if entry["actor_id"] == "rogue"
    )
    assert hero_availability["available"] is True
    assert rogue_availability["available"] is False

    completed = session.complete_downtime_crafting(
        actor_id="hero",
        recipe_id="forge_dagger",
    )

    hero = next(actor for actor in completed["actors"] if actor["id"] == "hero")
    assert hero["currency"]["total_cp"] == 900
    dagger = next(item for item in hero["inventory"] if item["id"] == "dagger")
    assert dagger["quantity"] == 1
    assert dagger["equipped"] is False
    assert session.state.elapsed_minutes == 480
    flags = {entry["key"]: entry["value"] for entry in completed["flags"]}
    assert flags["watchtower_dusk_arrival"] is True
    assert flags["watchtower_alerted"] is True
    assert any(
        message["title"] == "Rzemiosło ukończone"
        for message in completed["messages"]
    )


def test_village_merchant_rejects_unaffordable_purchase_without_changing_stock() -> None:
    session = ExplorationUiSession("content/scenarios/village_square_mvp.json")
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.select_point("merchant_stall")
    before = session.state_payload()

    with pytest.raises(ValueError, match="dość monet"):
        session.buy_merchant_item(
            merchant_id="mira_market_stall",
            actor_id="rogue",
            item_id="strength_potion",
            quantity=1,
        )

    after = session.state_payload()
    assert after["trade"]["stock"] == before["trade"]["stock"]
    rogue = next(actor for actor in after["actors"] if actor["id"] == "rogue")
    assert rogue["currency"]["total_cp"] == 500


def test_village_hero_can_buy_don_and_doff_light_armor_during_exploration() -> None:
    session = ExplorationUiSession("content/scenarios/village_square_mvp.json")
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    hero = next(actor for actor in session.exploration.actors if str(actor.id) == "hero")
    hero = replace(
        hero,
        proficiencies=replace(
            hero.proficiencies,
            armor=("light",),
        ),
    )
    session.exploration = session._replace_exploration_actor(hero)
    session.select_point("merchant_stall")
    purchased = session.buy_merchant_item(
        merchant_id="mira_market_stall",
        actor_id="hero",
        item_id="leather_armor",
        quantity=1,
    )

    armor = next(
        item
        for item in next(actor for actor in purchased["actors"] if actor["id"] == "hero")["inventory"]
        if item["id"] == "leather_armor"
    )
    assert armor["armor_category"] == ArmorCategory.LIGHT.value
    before_minutes = session.state.elapsed_minutes

    donned = session.change_actor_armor(
        actor_id="hero",
        armor_id="leather_armor",
        equip=True,
    )
    hero_payload = next(actor for actor in donned["actors"] if actor["id"] == "hero")
    assert next(item for item in hero_payload["inventory"] if item["id"] == "leather_armor")[
        "equipped"
    ] is True
    assert session.state.elapsed_minutes == before_minutes + 1

    doffed = session.change_actor_armor(
        actor_id="hero",
        armor_id="leather_armor",
        equip=False,
    )
    hero_payload = next(actor for actor in doffed["actors"] if actor["id"] == "hero")
    assert next(item for item in hero_payload["inventory"] if item["id"] == "leather_armor")[
        "equipped"
    ] is False
    assert session.state.elapsed_minutes == before_minutes + 2


def test_selective_combat_loot_takes_item_and_leaves_currency_on_corpse() -> None:
    session = ExplorationUiSession("content/scenarios/abandoned_watchtower.json")
    combat = _start_gate_skirmish(session)
    actor = combat.initiative_order.current_actor
    source = next(candidate for candidate in combat.actors if candidate.faction == Faction.ENEMY)
    source = replace(
        source,
        hp=0,
        position=Coordinate(actor.position.col + 1, actor.position.row),
        inventory=(
            InventoryItem(
                "selective_loot",
                "Lekki łup",
                "treasure",
                equipped=False,
                weight_lb=0.5,
            ),
        ),
        currency=CurrencyWallet(gp=2),
    )
    session.combat_state = replace(
        combat,
        actors=tuple(source if candidate.id == source.id else candidate for candidate in combat.actors),
    )

    options = session._combat_context_options(actor, source.position)
    assert {option.action for option in options if option.provider == "loot"} == {
        CombatMenuAction.LOOT,
        CombatMenuAction.LOOT_ITEM,
        CombatMenuAction.LOOT_CURRENCY,
    }
    opened = session._open_combat_context_menu(actor, source.position, options)
    looted = session.confirm_combat_context_menu(
        f"loot-item:{source.id}:selective_loot"
    )

    actor_after = next(
        candidate for candidate in looted["combat"]["actors"] if candidate["id"] == str(actor.id)
    )
    source_after = next(
        candidate for candidate in looted["combat"]["actors"] if candidate["id"] == str(source.id)
    )
    assert any(item["id"] == "selective_loot" for item in actor_after["inventory"])
    assert actor_after["currency"]["gp"] == 0
    assert source_after["inventory"] == []
    assert source_after["currency"]["gp"] == 2
    assert looted["combat"]["turn_action"]["action_use"] == "action_used"
    AttackDeclaration,
    AttackSource,
    AttackSourceType,
