"""Mira's optional theft follows only a lost negotiation and is paid once."""
from pathlib import Path

import pytest

from dnd_board_game.application import party_ethos
from dnd_board_game.hardware.board_panel import panel_position
from dnd_board_game.ui import mission_zero as m, confrontation as c
from dnd_board_game.ui.exploration_app import ExplorationUiSession
from tests.unit.test_mission_zero import session, stage, send
from tests.unit.test_mission_autosave import conclude, restored


def failed_negotiation(tmp_path: Path) -> ExplorationUiSession:
    s = session(tmp_path, count=4)  # Garran, Brakka, Dagna, Mira.
    stage(s, 'brief')
    send(s, 'negotiate')
    conclude(s, 'failure')
    return s


@pytest.mark.parametrize('has_mira', [False, True])
@pytest.mark.parametrize('outcome', ['success', 'compromise', 'failure'])
def test_offer_requires_mira_and_failed_negotiation(tmp_path: Path, has_mira: bool, outcome: str) -> None:
    s = session(tmp_path, count=4 if has_mira else 3)
    stage(s, 'brief')
    assert 'nessa_steal_potion' not in {x['action'] for x in m.payload(s)['choices']}
    send(s, 'negotiate')
    conclude(s, outcome)
    offered = has_mira and outcome == 'failure'
    assert m.read(s)['stage'] == ('nessa_theft' if offered else 'brief')
    assert ('nessa_steal_potion' in {x['action'] for x in m.payload(s)['choices']}) == offered
    assert party_ethos.read(s.state.flags).position == 3
    assert [item.id for item in s.state.party_loot.items] == (
        ['mission_potion'] if outcome == 'success' else ['mission_weak_potion'] if outcome == 'compromise' else [])
    if not offered:
        with pytest.raises(ValueError):
            send(s, 'nessa_steal_potion')


def test_theft_by_rune_grants_one_potion_moves_ethos_once_and_survives_save(tmp_path: Path) -> None:
    s = restored(failed_negotiation(tmp_path))
    assert m.read(s)['stage'] == 'nessa_theft'
    p = m.payload(s)
    assert '1k8 + 2 PW' in p['text']['body'] and 'Bezwzględności' in p['text']['body']
    assert panel_position(6) in m.scan_target(s).positions
    stale_revision = p['revision']
    m.select_position(s, panel_position(6))
    assert m.read(s)['stage'] == 'nessa_theft_taken'
    assert [(i.id, i.quantity) for i in s.state.party_loot.items] == [('mission_weak_potion', 1)]
    assert party_ethos.read(s.state.flags).position == 4
    assert party_ethos.read(s.state.flags).events == ('misja_0_dzwon:nessa_steal_potion',)
    assert c.read_store(s)['current']['state']['outcome'] == 'failure'
    for revision in (stale_revision, m.read(s)['revision']):
        with pytest.raises(ValueError):
            m.command(s, dict(action='nessa_steal_potion', revision=revision))
    loaded = restored(s)
    assert m.read(loaded)['stage'] == 'nessa_theft_taken'
    assert party_ethos.read(loaded.state.flags) == party_ethos.read(s.state.flags)
    assert loaded.state.party_loot == s.state.party_loot
    assert len([e for e in m.read(loaded)['ledger'] if e['id'] == 'weak_potion']) == 1
    m.select_position(loaded, panel_position(28))
    assert m.read(loaded)['stage'] == 'brief'
    with pytest.raises(ValueError): send(loaded, 'negotiate')
    # Even a repeated completion cannot offer another theft after consumption.
    m.finish_confrontation(loaded, c.read_store(loaded)['current'])
    assert m.read(loaded)['stage'] == 'brief'
    assert len(loaded.state.party_loot.items) == 1


def test_decline_is_free_final_and_saved(tmp_path: Path) -> None:
    s = failed_negotiation(tmp_path)
    m.select_position(s, panel_position(7))
    loaded = restored(s)
    assert m.read(loaded)['stage'] == 'brief'
    assert not loaded.state.party_loot.items
    assert party_ethos.read(loaded.state.flags).position == 3
    assert not party_ethos.read(loaded.state.flags).events
    assert not m.nessa_theft_available(loaded, m.read(loaded))
    m.finish_confrontation(loaded, c.read_store(loaded)['current'])
    assert m.read(loaded)['stage'] == 'brief'


def test_wrong_stage_or_forged_offer_cannot_grant_theft(tmp_path: Path) -> None:
    s = session(tmp_path, count=4)
    stage(s, 'nessa_theft')
    with pytest.raises(ValueError): send(s, 'nessa_steal_potion')
    assert not s.state.party_loot.items
    stage(s, 'road'); send(s, 'cart'); conclude(s, 'failure')
    assert m.read(s)['stage'] == 'fatigue_roll'
    with pytest.raises(ValueError): send(s, 'nessa_steal_potion')


def test_current_rules_keep_ethos_bounded_at_ruthless_endpoint(tmp_path: Path) -> None:
    from dataclasses import replace
    s = failed_negotiation(tmp_path)
    for i in range(3):
        s.state = replace(s.state, flags=party_ethos.apply_choice(s.state.flags, f'test:{i}', 'ruthlessness'))
    send(s, 'nessa_steal_potion')
    assert party_ethos.read(s.state.flags).position == 6
    assert party_ethos.read(s.state.flags).events.count('misja_0_dzwon:nessa_steal_potion') == 1
