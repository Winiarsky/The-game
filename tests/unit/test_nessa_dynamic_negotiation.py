from dnd_board_game.combat import scene_flag
from dnd_board_game.llm import NpcInteractionProposal, NpcOutcomeRenderProposal
from dnd_board_game.ui.exploration_app import (
    ExplorationUiSession,
    _npc_render_contract_is_safe,
)


SCENARIO_PATH = "content/scenarios/ostatni_transport_00_gildia.json"


class DynamicNessaClient:
    model = "fake-nessa"

    def __init__(self, declaration_class: str) -> None:
        self.declaration_class = declaration_class
        self.interaction_requests = []
        self.render_requests = []

    def interact_npc(self, request):
        self.interaction_requests.append(request)
        return NpcInteractionProposal.model_validate(
            {
                "action_type": "contract_negotiation",
                "target_id": "fair_request",
                "argument_intent_fit": (
                    1 if self.declaration_class == "valid_argument" else -2
                ),
                "argument_specificity": (
                    1 if self.declaration_class == "valid_argument" else 0
                ),
                "argument_credibility": (
                    0 if self.declaration_class == "valid_argument" else -2
                ),
                "argument_leverages": [],
                "declaration_class": self.declaration_class,
                "requires_roll": False,
            }
        )

    def render_npc_outcome(self, request):
        self.render_requests.append(request)
        return NpcOutcomeRenderProposal(
            gm_narration="Nessa obraca pióro między palcami i odpowiada bez pośpiechu.",
            npc_response="Słyszałam gorsze argumenty, kochaniutki. Ten akurat ma swoją cenę.",
            acknowledged_mechanical_summary=request.mechanical_summary,
        )


class UnsafeRenderNessaClient(DynamicNessaClient):
    def render_npc_outcome(self, request):
        self.render_requests.append(request)
        return NpcOutcomeRenderProposal(
            gm_narration="Nessa wyciąga spod stołu legendarny skarb.",
            npc_response="Daję wam tysiąc sztuk złota.",
            acknowledged_mechanical_summary="Inny wynik niż ustalony przez grę.",
        )


class CorrectingRenderNessaClient(DynamicNessaClient):
    def render_npc_outcome(self, request):
        self.render_requests.append(request)
        if len(self.render_requests) == 1:
            return NpcOutcomeRenderProposal(
                gm_narration="Nessa poprawia kontrakt.",
                npc_response="Dostaniecie premię, jeśli odzyskacie wszystkie skrzynie.",
                acknowledged_mechanical_summary=request.mechanical_summary,
            )
        return NpcOutcomeRenderProposal(
            gm_narration="Nessa waży argument, po czym sięga po pióro.",
            npc_response="Za sprowadzenie ocalałych przyznaję wam premię, kochaniutcy.",
            acknowledged_mechanical_summary=request.mechanical_summary,
        )

def _session(client) -> ExplorationUiSession:
    return ExplorationUiSession(
        SCENARIO_PATH,
        npc_client=client,
        debug_point_id="nessa_desk",
    )


def _submit(session: ExplorationUiSession, text: str):
    return session.submit_action(
        text,
        selected_goal_id="negotiate_nessa_reward",
        selected_check_participants="single_actor",
        participant_actor_ids=("lorian",),
        selected_social_skill="persuasion",
    )


def test_successful_roll_uses_dynamic_nessa_response_and_separate_mechanical_result() -> None:
    client = DynamicNessaClient("valid_argument")
    session = _session(client)

    pending = _submit(
        session,
        "Jeżeli sprowadzimy twoich ludzi żywych, uczciwa premia leży w interesie gildii.",
    )
    assert pending["pending"]["proposal"]["declaration_class"] == "valid_argument"

    session.decide("accept")
    state = session.resolve_rolls({"lorian": 20})

    assert len(client.render_requests) == 1
    render_request = client.render_requests[0]
    assert render_request.outcome == "critical_success"
    assert "sprowadzimy twoich ludzi" in render_request.interaction.player_action
    assert scene_flag(session.state.flags, "nessa_contract_outcome") == "request_critical_success"
    assert "guild_medical_pack" in session.state.inventory_resource_ids
    assert any(
        message["title"] == "Nessa"
        and "Ten akurat ma swoją cenę" in message["body"]
        for message in state["messages"]
    )
    assert any(
        message["title"] == "Rezultat mechaniczny"
        and "pakiet medyczny" in message["body"]
        for message in state["messages"]
    )


def test_disruptive_declaration_gets_real_reaction_and_immediate_authored_consequence() -> None:
    client = DynamicNessaClient("disruptive")
    session = _session(client)

    state = _submit(session, "Sikam na stół i obrażam Nessę.")

    assert state["pending"] is None
    assert len(client.render_requests) == 1
    assert client.render_requests[0].outcome == "critical_failure"
    assert client.render_requests[0].declaration_class == "disruptive"
    assert scene_flag(session.state.flags, "nessa_contract_resolved", False) is True
    assert scene_flag(session.state.flags, "nessa_contract_outcome") == "base_rate"
    assert any(message["title"] == "Nessa" for message in state["messages"])
    assert any(message["title"] == "Rezultat mechaniczny" for message in state["messages"])


def test_off_topic_declaration_does_not_consume_negotiation_attempt() -> None:
    client = DynamicNessaClient("off_topic")
    session = _session(client)

    state = _submit(session, "Czy ktoś widział mojego kota?")

    assert state["pending"] is None
    assert client.render_requests[0].outcome == "off_topic"
    assert scene_flag(session.state.flags, "nessa_contract_resolved", False) is False
    npc_state = state["active_point"]["npc"]["runtime_state"]
    assert npc_state["relationship_events"] == []
    assert any(
        message["title"] == "Rezultat mechaniczny"
        and "nie została zużyta" in message["body"]
        for message in state["messages"]
    )


def test_unfaithful_dynamic_response_is_replaced_with_safe_fallback() -> None:
    client = UnsafeRenderNessaClient("valid_argument")
    session = _session(client)
    _submit(session, "Premia za uratowanych ludzi zmotywuje drużynę.")
    session.decide("accept")

    state = session.resolve_rolls({"lorian": 15})

    assert not any(
        "tysiąc sztuk złota" in message["body"]
        for message in state["messages"]
    )
    assert any(
        message["title"] == "Nessa"
        and "Macie lepsze warunki" in message["body"]
        for message in state["messages"]
    )
    assert scene_flag(session.state.flags, "nessa_contract_outcome") == "survivor_bonus"


def test_contract_renderer_rejects_per_person_and_new_conditional_terms() -> None:
    summary = "Nessa przyznaje premię za sprowadzenie ocalałych."

    assert _npc_render_contract_is_safe(
        "Nessa poprawia kontrakt.",
        "Dostaniecie premię za każdą uratowaną osobę.",
        summary,
    ) is False
    assert _npc_render_contract_is_safe(
        "Nessa poprawia kontrakt.",
        "Premia będzie wasza, jeśli odzyskacie wszystkie skrzynie.",
        summary,
    ) is False
    assert _npc_render_contract_is_safe(
        "Nessa poprawia kontrakt.",
        "Przyznaję wam premię za sprowadzenie ocalałych.",
        summary,
    ) is True
    assert _npc_render_contract_is_safe(
        "Nessa poprawia kontrakt.",
        "Wpisuję do umowy premię w wysokości 500 gp.",
        "Kontrakt przewiduje premię 5 gp.",
    ) is False
    assert _npc_render_contract_is_safe(
        "Nessa poprawia kontrakt.",
        "Wpisuję do umowy premię 5 gp.",
        "Kontrakt przewiduje premię 5 gp.",
    ) is True
    assert _npc_render_contract_is_safe(
        "Nessa poprawia kontrakt.",
        "Dorzucę premię, jeśli sprowadzicie moich ludzi żywych.",
        summary,
    ) is True
    assert _npc_render_contract_is_safe(
        "Nessa mierzy bohatera chłodnym spojrzeniem.",
        (
            "Wydatki rozliczę co do miedziaka, ale wyłącznie w ramach tego, "
            "co wcześniej zatwierdziłam."
        ),
        "Nessa ogranicza rozliczenie wydatków do wcześniej zatwierdzonych kosztów.",
    ) is True
    assert _npc_render_contract_is_safe(
        "Nessa rozważa plotkę o konkurencji.",
        (
            "Dostaniecie zaliczkę, ale oczekuję, że dotrzecie tam pierwsi "
            "i odzyskacie wszystko bez wymówek."
        ),
        "Nessa zgadza się na zaliczkę.",
    ) is False
    assert _npc_render_contract_is_safe(
        "Nessa zgadza się na zaliczkę.",
        (
            "Jeśli to prawda, dostaniecie zaliczkę. Jeśli wrócicie z pustymi "
            "rękami, spotkają was dodatkowe konsekwencje."
        ),
        "Nessa zgadza się na zaliczkę.",
    ) is False


def test_renderer_gets_one_correction_attempt_before_fallback() -> None:
    client = CorrectingRenderNessaClient("valid_argument")
    session = _session(client)
    _submit(session, "Ratowanie ocalałych zwiększa ryzyko wyprawy.")
    session.decide("accept")

    state = session.resolve_rolls({"lorian": 15})

    assert len(client.render_requests) == 2
    assert "stawek jednostkowych" in client.render_requests[1].correction_note
    assert any(
        message["title"] == "Nessa"
        and "Za sprowadzenie ocalałych" in message["body"]
        for message in state["messages"]
    )


class LieNessaClient(DynamicNessaClient):
    def interact_npc(self, request):
        self.interaction_requests.append(request)
        return NpcInteractionProposal.model_validate(
            {
                "action_type": "contract_negotiation",
                "target_id": "calculated_lie",
                "argument_intent_fit": 1,
                "argument_specificity": 1,
                "argument_credibility": 0,
                "argument_leverages": [],
                "declaration_class": "valid_argument",
                "requires_roll": False,
            }
        )


def test_successful_lie_pays_three_gp_advance_to_every_living_party_member() -> None:
    client = LieNessaClient("valid_argument")
    session = _session(client)
    before = {
        str(actor.id): actor.currency.total_cp
        for actor in session.exploration.actors
        if actor.faction.value == "ally" and not actor.is_defeated()
    }

    session.submit_action(
        "Musimy pilnie opłacić przewodnika, którego Nessa nie zdąży sprawdzić.",
        selected_goal_id="negotiate_nessa_reward",
        selected_check_participants="single_actor",
        participant_actor_ids=("lorian",),
        selected_social_skill="deception",
    )
    session.decide("accept")
    session.resolve_rolls({"lorian": 15})

    after = {
        str(actor.id): actor.currency.total_cp
        for actor in session.exploration.actors
        if actor.faction.value == "ally" and not actor.is_defeated()
    }
    assert after == {actor_id: amount + 300 for actor_id, amount in before.items()}
    assert scene_flag(session.state.flags, "contract.advance_gp_per_hero") == 3
