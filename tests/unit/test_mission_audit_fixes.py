"""Regressions from the September Mission 0 UI playtest."""
from dataclasses import replace

import pytest

from dnd_board_game.inventory import CurrencyWallet
from dnd_board_game.rules import ActiveEffect, EffectDuration, EffectEvent, EffectEventType, expire_active_effects
from dnd_board_game.ui import mission_zero as m
from dnd_board_game.ui import mission_zero_recovery as recovery
from dnd_board_game.ui.exploration_app import create_app
from tests.unit.test_mission_zero import session, stage, send
from tests.unit.test_mission_recovery import party, collect_all


@pytest.mark.parametrize('gold', [0, 20])
def test_nimra_success_is_free_even_with_empty_wallet(tmp_path, gold):
    s = party(tmp_path)
    owner = s.exploration.actors[0]
    m._set_actor(s, replace(owner, currency=CurrencyWallet(gp=gold)))
    stage(s, 'explore')
    data = m.read(s); m.grant(s, data, 'ring'); m.write(s, data)
    send(s, 'ring'); send(s, 'identify_nimra'); send(s, 'roll', roll=20)
    assert m.read(s)['ring_identified']
    assert s.exploration.actors[0].currency.total_cp == gold * 100
    assert not any(e['id'] == 'identification' for e in m.read(s)['ledger'])


def test_guild_identification_still_costs_five_gold_without_coin_inflation(tmp_path):
    s = party(tmp_path)
    owner = s.exploration.actors[0]
    m._set_actor(s, replace(owner, currency=CurrencyWallet(gp=20)))
    data = m.read(s); m.grant(s, data, 'ring'); m.write(s, data)
    stage(s, 'guild_return'); send(s, 'ring'); send(s, 'identify_guild')
    wallet = s.exploration.actors[0].currency
    assert wallet.total_cp == 1500
    assert wallet.total_coins <= 15
    assert next(e['amount'] for e in m.read(s)['ledger'] if e['id']=='identification') == -5


@pytest.mark.parametrize('fee', ['rumor', 'cargo'])
def test_other_fees_keep_wallet_value_and_reasonable_coin_count(tmp_path, fee):
    s = session(tmp_path)
    owner = s.exploration.actors[0]
    m._set_actor(s, replace(owner, currency=CurrencyWallet(gp=20)))
    stage(s, 'explore', outcome='refused')
    if fee == 'rumor':
        send(s, 'leader'); send(s, 'rumor'); expected = 1900
    else:
        collect_all(s)
        data=m.read(s); data['cargo']['armory']='damaged'; data['bell']='village'
        recovery.settle(s, data); expected = 4800
    wallet=s.exploration.actors[0].currency
    assert wallet.total_cp == expected
    assert wallet.total_coins <= expected // 100


@pytest.mark.parametrize('duration', [EffectDuration.UNTIL_TURN_END, EffectDuration.UNTIL_TURN_START,
    EffectDuration.UNTIL_ROUND_END, EffectDuration.UNTIL_NEXT_ATTACK])
def test_encounter_end_expires_turn_state_but_preserves_long_effects(duration):
    transient=ActiveEffect('turn','garran','mana_series_source','Seria','source',0,duration=duration)
    permanent=replace(transient,id='permanent',duration=EffectDuration.PERMANENT)
    long_rest=replace(transient,id='rest',duration=EffectDuration.UNTIL_LONG_REST)
    result=expire_active_effects((transient,permanent,long_rest),EffectEvent(EffectEventType.ENCOUNTER_ENDED))
    assert result.active_effects == (permanent,long_rest)
    assert result.expired_effects == (transient,)


@pytest.mark.parametrize('count,word', [(1,'1 pełną rundę'),(2,'2 pełne rundy'),(4,'4 pełne rundy')])
def test_fatigue_result_declension(tmp_path,count,word):
    s=session(tmp_path);stage(s,'fatigue_result',fatigue=count)
    assert word in m.payload(s)['text']['body']


@pytest.mark.parametrize('present', [False,True])
def test_optional_hero_narration_matches_party(tmp_path,present):
    s=party(tmp_path) if present else session(tmp_path)
    for key,name in [('dilemma','Mira'),('quarters_success','Nimra'),('ring','Nimra')]:
        body=m.narrative(s,key)['body']
        assert (name in body) == present
        assert '{' not in body
    assert 'Gildii' in m.narrative(s,'ring')['body']


def test_new_game_brakka_matches_print_and_tutorial(tmp_path):
    from dnd_board_game.ui.training_arena import training_hero
    from dnd_board_game.physical_cards.mana_print import build_print_hero
    s=session(tmp_path)
    response=create_app(s).test_client().post('/new-game/start',data={
        'scenario_id':'misja_0_dzwon','character_ids':['brakka','garran','dagna']})
    assert response.status_code == 302
    brakka=next(a for a in s.exploration.actors if str(a.id)=='brakka')
    assert brakka.max_hp == training_hero('brakka').max_hp == 35
    assert brakka.ability_scores == training_hero('brakka').ability_scores
    printed=build_print_hero('brakka')
    assert printed.hp == brakka.max_hp


def test_road_instruction_uses_rotated_cart_geometry(tmp_path):
    from dnd_board_game.ui.mission_setup import road_placement
    from tests.unit.test_mission_zero import PACK
    s=session(tmp_path)
    layout=road_placement(PACK)
    body=m.narrative(s,'road')['body']
    assert layout['positions']==[(9,16),(9,17)]
    assert '(9,16), (9,17)' in body and '(10,17)' not in body
    assert '{' not in m.scene(s,'cart')['description']


def test_accepting_truce_removes_turn_markers(tmp_path):
    from tests.unit.test_mission_zero import start_battle
    from tests.unit.test_pooled_mana_runtime import prepare
    s=start_battle(session(tmp_path));prepare(s,'B','C')
    s.active_combat_effects += tuple(ActiveEffect(kind,'garran',kind,kind,'source',1,
        duration=EffectDuration.UNTIL_TURN_END) for kind in ('mana_series_source','shared_offensive_used'))
    enemy=next(a for a in s.combat_state.actors if a.faction.value=='enemy')
    s.combat_state=replace(s.combat_state,actors=tuple(replace(a,hp=0) if a.id==enemy.id else a for a in s.combat_state.actors))
    s.state_payload();send(s,'accept')
    assert s.combat_state is None
    assert not any(e.kind in {'mana_series_source','shared_offensive_used'} for e in s.active_combat_effects)


def test_pooled_action_reminders_and_move_prompt(tmp_path):
    from tests.unit.test_mission_zero import start_battle
    from tests.unit.test_pooled_mana_runtime import prepare
    s=start_battle(session(tmp_path));prepare(s,'B','C')
    actor=next(a for a in s.combat_state.actors if str(a.id)=='garran')
    assert 'Wydaj:' not in s._physical_card_resource_note(actor,'second_wind')
    assert 'pkt' in s._physical_card_resource_note(actor,'second_wind')
    assert 'Bez many' in s.state_payload()['combat']['reaction_costs']['shield']
    menu=s._combat_turn_action_menu_payload()
    assert all('Wydaj:' not in option['description'] for option in menu['options'])
    s.confirm_combat_turn_action('turn:move')
    assert 'Wskaż podświetlone' in s._current_board_scan_target().empty_message
