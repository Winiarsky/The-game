"""Briefing review, one-shot checks, and disclosed negotiation stakes."""
from dataclasses import replace
from pathlib import Path

import pytest

from dnd_board_game.combat import scene_flag, set_scene_flag
from dnd_board_game.ui.exploration_app import ExplorationUiSession
from dnd_board_game.ui.nessa_briefing import briefing_contract
from tests.unit.test_nessa_dynamic_negotiation import DynamicNessaClient
from dnd_board_game.llm import NpcInteractionProposal

SCENARIO = 'content/scenarios/ostatni_transport_00_gildia.json'


def session(tmp_path: Path) -> ExplorationUiSession:
    return ExplorationUiSession(SCENARIO, debug_point_id='nessa_desk', save_dir=tmp_path)


def goals(s: ExplorationUiSession) -> dict[str, dict]:
    return {g['id']: g for g in s.state_payload()['active_point']['npc']['goals']}


def act(s: ExplorationUiSession, goal: str, actor: str | None = None) -> dict:
    return s.submit_action('Podejmujemy działanie.', selected_goal_id=goal,
                           selected_check_participants='single_actor' if actor else 'no_actor',
                           participant_actor_ids=(actor,) if actor else ())


def test_discussed_question_keeps_slot_and_recap_without_replaying(tmp_path: Path) -> None:
    s = session(tmp_path)
    before = goals(s)
    act(s, 'ask_nessa_about_cargo')
    after = goals(s)
    assert list(before) == list(after)
    assert [g['slot'] for g in after.values()] == list(range(1, 8))
    cargo = after['ask_nessa_about_cargo']
    assert cargo['read_only'] and cargo['topic_status'] == 'Omówione'
    assert 'miedzianym gwoździu' in cargo['recap']['speech']
    state_before = s.state
    with pytest.raises(ValueError, match='przypomnienia'):
        act(s, 'ask_nessa_about_cargo')
    assert s.state == state_before
    assert goals(s) == after


@pytest.mark.parametrize('roll', [1, 5, 20])
def test_insight_is_one_local_check_without_negotiation_penalty(tmp_path: Path, roll: int) -> None:
    s = session(tmp_path)
    result = act(s, 'read_nessa_priorities', 'dagna')
    assert result['pending'] is not None
    s.decide('accept')
    s.resolve_rolls({'dagna': roll})
    reviewed = goals(s)['read_nessa_priorities']
    assert reviewed['read_only']
    assert not scene_flag(s.state.flags, 'nessa_negotiation_scrutiny_penalty', False)
    if roll == 20:
        assert scene_flag(s.state.flags, 'knowledge.nessa_true_priority_known', False)
        assert goals(s)['negotiate_nessa_reward']['known_arguments']
    else:
        assert not scene_flag(s.state.flags, 'knowledge.nessa_true_priority_known', False)
        assert goals(s)['negotiate_nessa_reward']['known_arguments'] == []
        assert 'wyjątkowo cenne' not in str(reviewed['recap'])
    with pytest.raises(ValueError, match='przypomnienia'):
        act(s, 'read_nessa_priorities', 'lorian')


def test_erynd_failure_keeps_basic_route_and_does_not_claim_magic(tmp_path: Path) -> None:
    s = session(tmp_path)
    act(s, 'review_transport_documents', 'erynd')
    s.decide('accept')
    s.resolve_rolls({'erynd': 1})
    recap = goals(s)['review_transport_documents']['recap']
    assert 'Kamiennym Słupie' in recap['result']
    assert not scene_flag(s.state.flags, 'knowledge.convoy_route_magic_suspected', False)
    assert goals(s)['review_transport_documents']['read_only']


def test_finish_closes_unvisited_actions_without_revealing_them(tmp_path: Path) -> None:
    s = session(tmp_path)
    act(s, 'finish_nessa_briefing')
    after = goals(s)
    for goal_id in ['read_nessa_priorities', 'review_transport_documents', 'ask_nessa_about_cargo']:
        goal = after[goal_id]
        assert goal['read_only'] and goal['topic_status'] == 'Niedostępne'
        assert 'wyjątkowo cenne' not in str(goal)
        assert 'miedzianym gwoździu' not in str(goal)
        with pytest.raises(ValueError):
            act(s, goal_id, 'dagna')
    assert scene_flag(s.state.flags, 'guild_departure_unlocked', False)
    assert s.scenario_path.name == 'ostatni_transport_00_gildia.json'
    assert s.state_payload()['active_point']['npc']['briefing_contract']['status'] == 'Ustalone'


def test_absent_erynd_keeps_disabled_slot_and_optional_departure(tmp_path: Path) -> None:
    s = session(tmp_path)
    s.exploration = replace(s.exploration, actors=tuple(a for a in s.exploration.actors if str(a.id) != 'erynd'))
    displayed = goals(s)
    assert displayed['review_transport_documents']['read_only']
    assert displayed['review_transport_documents']['slot'] == 5
    assert not displayed['finish_nessa_briefing']['read_only']
    act(s, 'ask_nessa_about_disappearance')
    assert scene_flag(s.state.flags, 'knowledge.transport_last_contact_details', False)


def test_recap_survives_save_and_load(tmp_path: Path) -> None:
    s = session(tmp_path)
    act(s, 'ask_nessa_about_people')
    expected = goals(s)['ask_nessa_about_people']
    s.save_snapshot()
    restored = session(tmp_path)
    restored.load_snapshot()
    assert goals(restored)['ask_nessa_about_people'] == expected


class RiskClient(DynamicNessaClient):
    def interact_npc(self, request) -> NpcInteractionProposal:
        return super().interact_npc(request).model_copy(update={'target_id': 'risk_request'})


def test_reasoned_risk_request_uses_persuasion_and_agreed_contract(tmp_path: Path) -> None:
    s = session(tmp_path)
    s.npc_client = RiskClient('valid_argument')
    targets = goals(s)['negotiate_nessa_reward']['negotiation_targets']
    assert sum(t['skill'] == 'persuasion' for t in targets) == 2
    s.submit_action('Prosimy o dopłatę za ryzyko niebezpiecznej wyprawy.',
                    selected_goal_id='negotiate_nessa_reward', selected_check_participants='single_actor',
                    participant_actor_ids=('lorian',), selected_social_skill='persuasion')
    assert s.pending.proposal.skill == 'persuasion'
    s.decide('accept')
    s.resolve_rolls({'lorian': 20})
    assert scene_flag(s.state.flags, 'contract.hazard_bonus_gp_per_hero') == 10
    contract = briefing_contract(s.state.flags)
    assert contract['status'] == 'Ustalone'
    assert contract['rows'][2]['value'].startswith('3 ')
    assert contract['rows'][3]['value'].startswith('17 ')
    wallet = tuple(a.currency for a in s.exploration.actors)
    goals(s)
    with pytest.raises(ValueError):
        act(s, 'negotiate_nessa_reward', 'lorian')
    assert tuple(a.currency for a in s.exploration.actors) == wallet


def test_contract_completion_does_not_reveal_unattempted_insight(tmp_path: Path) -> None:
    s = session(tmp_path)
    s.state = replace(s.state, flags=set_scene_flag(s.state.flags, 'nessa_contract_resolved', True))
    insight = goals(s)['read_nessa_priorities']
    assert insight['topic_status'] == 'Niedostępne'
    assert 'wyjątkowo cenne' not in str(insight)


def test_board_review_uses_same_authored_pad_and_needs_no_actor(tmp_path: Path) -> None:
    s = session(tmp_path)
    before = s._board_interaction_pads()
    act(s, 'ask_nessa_about_cargo')
    after = s._board_interaction_pads()
    cargo_before = next(p for p in before if p.target_id == 'ask_nessa_about_cargo')
    cargo_after = next(p for p in after if p.target_id == 'ask_nessa_about_cargo')
    assert (cargo_before.symbol, cargo_before.position) == (cargo_after.symbol, cargo_after.position)
    assert goals(s)['ask_nessa_about_cargo']['check_participants'] == 'no_actor'
