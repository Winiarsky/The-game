"""Contract branches, repeat protection, room outcomes and ring persistence."""
from dataclasses import replace
from pathlib import Path

import pytest

from tests.unit.test_mission_zero import session, stage, send, PACK
from dnd_board_game.ui import mission_zero as m, confrontation as c
from dnd_board_game.ui import mission_zero_recovery as recovery
from dnd_board_game.ui.training_arena import training_hero
from dnd_board_game.rules import confrontation as rules
from dnd_board_game.application.confrontation import build
from dnd_board_game.application.campaign_rewards import complete_mission
from dnd_board_game.inventory.magic_items import effective_ability_score, effective_ability_modifier


def party(tmp_path, heroes=('garran','lorian','nimra','mira')):
    s=session(tmp_path)
    s.configure_custom_party(tuple(training_hero(h) for h in heroes));m.initialize(s)
    return s


def finish(s, outcome, natural_one=False):
    store=c.read_store(s)
    store['current']['state'].update(stage='result',outcome=outcome,natural_one_seen=natural_one)
    c.write(s,store)
    c.command(s,dict(action='next',revision=c.read_store(s)['revision']))


def collect_all(s):
    stage(s,'explore')
    for room in ('armory','quarters'):
        send(s,room);send(s,'collect',room=room);send(s,'back')
    send(s,'store');send(s,'back')


@pytest.mark.parametrize('outcome,natural,expected',[('success',False,'success'),('failure',False,'failure'),('failure',True,'critical'),('success',True,'success')])
def test_room_confrontation_outcomes_and_no_retry(tmp_path,outcome,natural,expected):
    s=session(tmp_path);stage(s,'explore',outcome='refused')
    send(s,'quarters');send(s,'search',room='quarters')
    assert c.payload(s)['scene']['kind']=='object'
    # Leaving cannot replace this attempt with safe collection or restart its deck.
    token=c.read_store(s)['current']['token']
    c.command(s,dict(action='leave',revision=c.read_store(s)['revision']))
    with pytest.raises(ValueError):send(s,'collect',room='quarters')
    send(s,'resume_search')
    assert c.read_store(s)['current']['token']==token
    finish(s,outcome,natural)
    assert m.read(s)['searches']['quarters']==expected
    assert ('item:ring' in m.read(s)['flags'])==(outcome=='success')
    send(s,'back');send(s,'quarters')
    assert [o['action'] for o in m.payload(s)['choices']]==['back']


def test_truce_repairs_only_first_critical_failure(tmp_path):
    s=session(tmp_path);stage(s,'explore',outcome='accepted')
    for room,expected in [('armory','repaired'),('quarters','damaged')]:
        send(s,room);send(s,'search',room=room);finish(s,'failure',True)
        assert m.read(s)['cargo'][room]==expected
        send(s,'back')
    assert m.read(s)['repair_used']


@pytest.mark.parametrize('bell,extra',[('guild',10),('village',0),('fence',0)])
def test_delivery_settlement_debt_and_delayed_payment(tmp_path,bell,extra):
    s=party(tmp_path);collect_all(s)
    send(s,'leader');send(s,'debt_garran');send(s,'back')
    assert any(i.id=='mission_documents' for i in s.state.party_loot.items)
    assert next(e for e in m.read(s)['ledger'] if e['id']=='documents')['custodian']=='garran'
    send(s,'dilemma');send(s,'bell_'+bell);send(s,'next');send(s,'loaded')
    baseline=s.exploration.actors[0].currency.total_cp
    send(s,'next')
    assert m.read(s)['stage']=='guild_return'
    assert s.exploration.actors[0].currency.total_cp==baseline+(40+extra)*100
    if bell=='fence':
        flags,actors,events=complete_mission(s.state.flags,s.exploration.actors,'misja_1')
        assert not events and actors==s.exploration.actors
        flags,actors,events=complete_mission(flags,actors,'misja_2')
        assert len(events)==1 and actors[0].currency.total_cp==baseline+6000
        _,again,events=complete_mission(flags,actors,'misja_2')
        assert not events and again==actors
    send(s,'summary');send(s,'finish')
    restored=party(tmp_path);restored.load_snapshot()
    assert m.read(restored)['cargo']==m.read(s)['cargo'] and m.read(restored)['bell']==bell
    assert m.read(restored)['debt']=='garran'


def test_contract_gate_and_damage_penalty(tmp_path):
    s=session(tmp_path);stage(s,'explore')
    send(s,'leader');send(s,'back')
    with pytest.raises(ValueError):send(s,'dilemma')
    collect_all(s)
    data=m.read(s);data['cargo']['armory']='damaged';m.write(s,data)
    send(s,'dilemma');send(s,'bell_guild');send(s,'next');send(s,'loaded');send(s,'next')
    assert sum(x['amount'] for x in m.read(s)['ledger'] if x['kind']=='money')==38


def test_lorian_one_shot_bonus_and_hero_gates(tmp_path):
    s=party(tmp_path);stage(s,'brief')
    send(s,'compliments');send(s,'compliment',option='wounded');send(s,'brief_back')
    with pytest.raises(ValueError):send(s,'compliments')
    send(s,'negotiate')
    state=rules.Confrontation.from_data(c.read_store(s)['current']['state'])
    assert state.first_test_bonus==2
    state=rules.begin_preparation(state)
    while state.stage=='approach':
        available=rules.available_approaches(state)
        chosen=next((p for p in available if '*' in p.supports),available[0])
        state=rules.select_approach(state,chosen.approach_id)
    state=rules.shuffle(state)
    for color in ('C','B'):state=rules.report_color(state,color)
    state=rules.take(state,0)
    supported=rules.support(state,state.participants[1].id)
    assert supported.first_test_bonus==2
    declared=rules.declare(state,0)
    assert declared.first_test_bonus==0 and declared.applied_first_test_bonus==2
    ordinary=rules.declare(replace(state,first_test_bonus=0),0)
    assert declared.check_modifier==ordinary.check_modifier+2
    # Real roll tracking includes only check dice, not a 1 on the impact die.
    hit=rules.roll_check(declared,20)
    assert not rules.roll_impact(hit,1).natural_one_seen
    assert rules.roll_check(declared,1).natural_one_seen
    other=session(tmp_path/'other');stage(other,'brief')
    with pytest.raises(ValueError):send(other,'compliments')
    collect_all(other);send(other,'leader');send(other,'back');send(other,'dilemma')
    with pytest.raises(ValueError):send(other,'bell_fence')


def test_rumor_cost_and_dc_are_applied_once(tmp_path):
    s=session(tmp_path);stage(s,'explore',outcome='refused')
    base=m.scene(s,'quarters')['approaches'][0]['dc']
    send(s,'leader');before=s.exploration.actors[0].currency.total_cp
    send(s,'rumor');send(s,'back');send(s,'leader')
    assert s.exploration.actors[0].currency.total_cp==before-100
    assert m.scene(s,'quarters')['approaches'][0]['dc']==base-2
    with pytest.raises(ValueError):send(s,'rumor')


@pytest.mark.parametrize('natural,known',[(1,False),(20,True)])
def test_nimra_identification_and_guild_fallback(tmp_path,natural,known):
    s=party(tmp_path);stage(s,'explore')
    data=m.read(s);m.grant(s,data,'ring');m.write(s,data)
    send(s,'ring');send(s,'identify_nimra')
    assert m.payload(s)['rolling'] and m.payload(s)['roll_sides']==20
    send(s,'roll',roll=natural)
    assert m.read(s)['ring_identified']==known
    if not known:
        send(s,'ring_view')
        with pytest.raises(ValueError):send(s,'identify_nimra')
        stage(s,'guild_return');send(s,'ring');send(s,'identify_guild')
        assert m.read(s)['ring_identified']
    stage(s,'guild_return');send(s,'equipment_open');send(s,'equipment_slots');send(s,'equipment_attach',gear_slot='ring')
    g=s.exploration.actors[0]
    assert effective_ability_score(g,'strength')==g.ability_scores.strength+1
    s.save_snapshot();s.load_snapshot()
    assert effective_ability_score(s.exploration.actors[0],'strength')==g.ability_scores.strength+1


def test_ring_changes_score_not_modifier_and_preserves_base(tmp_path):
    from dnd_board_game.actors.proficiencies import ability_roll_modifier, saving_throw_modifier
    from dnd_board_game.combat.attack_flow import unarmed_strike_source, attack_source_for_actor
    s=session(tmp_path);data=m.read(s);m.grant(s,data,'ring');recovery.identify(s,data);m.write(s,data)
    item=next(i for i in s.state.party_loot.items if i.id=='mission_ring')
    for score,modifier in ((18,4),(19,5)):
        base=s.exploration.actors[0]
        actor=replace(base,ability_scores=replace(base.ability_scores,strength=score),inventory=(replace(item,equipped=True),))
        assert actor.ability_scores.strength==score
        assert effective_ability_modifier(actor,'strength')==modifier
        assert ability_roll_modifier(actor,'strength').value==modifier
        assert saving_throw_modifier(actor,'strength')==modifier
        attack=attack_source_for_actor(unarmed_strike_source(actor),actor)
        assert attack.damage_modifier==modifier
        assert sum(x.value for x in attack.attack_roll_request.modifiers)==modifier
        profile=m.scene(s,'cart')
        chosen=rules.select_approach(rules.begin_preparation(build((actor,),profile)),'lift')
        assert chosen.actor.impact_modifier==chosen.actor.test_modifier==modifier
