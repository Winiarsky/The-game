"""Mission branches, persisted rewards and actual combat modifiers."""
from dataclasses import replace
from pathlib import Path
import json
import pytest
from dnd_board_game.ui import mission_zero as m, confrontation as c
from dnd_board_game.ui.exploration_app import ExplorationUiSession
from dnd_board_game.ui.training_arena import training_hero
from dnd_board_game.scenarios.loader import load_scenario, build_encounter_from_scenario, encounter_for_party_size
from dnd_board_game.scenarios.mission_pack import text_entry
from dnd_board_game.rules.effects import expire_active_effects, EffectEvent, EffectEventType
from dnd_board_game.combat.mission_effects import road_fatigue, surrender_available
from dnd_board_game.combat.scene_interactions import attack_source_with_combat_effects
from dnd_board_game.combat.attack_flow import AttackSource, AttackSourceType
from dnd_board_game.rules import D20RollRequest

PACK=Path('content/scenarios/misja_0_dzwon')
HEROES=('garran','brakka','dagna','mira','lorian','erynd')

def session(tmp_path, count=3):
    s=ExplorationUiSession(PACK/'scenario.json',save_dir=tmp_path/'saves',observation_dir=tmp_path/'logs')
    s.configure_custom_party(tuple(training_hero(h) for h in HEROES[:count]))
    m.initialize(s)
    return s

def send(s,action,**kwargs):
    return m.command(s,dict(action=action,revision=m.read(s)['revision'],**kwargs))

def stage(s,stage,**kwargs):
    data=m.read(s);data.update(stage=stage,**kwargs);m.write(s,data)

@pytest.mark.parametrize('count',[3,4,5,6])
def test_selected_intro_setup_and_scaled_battle(tmp_path,count):
    s=session(tmp_path,count);send(s,'next')
    seen=[]
    for _ in range(count):
        seen.append(m.payload(s)['text']['id']);send(s,'next')
    assert seen==['hero_'+h for h in HEROES[:count]]
    assert m.read(s)['stage']=='party'
    send(s,'next')
    for _ in range(4):send(s,'next')
    assert m.read(s)['stage']=='brief'
    assert (s.save_dir/'misja_0_dzwon.brief.checkpoint.json').exists()
    encounter=encounter_for_party_size(build_encounter_from_scenario(load_scenario(PACK/'mechanics/battle.json')),count)
    assert sum(a.faction.value=='enemy' for a in encounter.actors)==count+2

@pytest.mark.parametrize('outcome,item',[('success','mission_potion'),('compromise','mission_weak_potion'),('failure',None)])
def test_confrontation_returns_real_reward_once(tmp_path,outcome,item):
    s=session(tmp_path);stage(s,'brief');send(s,'negotiate')
    store=c.read_store(s);store['current']['state'].update(stage='result',outcome=outcome);c.write(s,store)
    c.command(s,dict(action='next',revision=c.read_store(s)['revision']))
    assert m.read(s)['stage']=='brief'
    actual=[i.id for a in s.exploration.actors for i in a.inventory if i.id.startswith('mission_')]
    assert actual==([item] if item else [])
    with pytest.raises(ValueError):send(s,'negotiate')

@pytest.mark.parametrize('rounds',[1,4])
def test_road_failure_roll_and_fatigue_lifetime(tmp_path,rounds):
    s=session(tmp_path);stage(s,'road');send(s,'cart')
    store=c.read_store(s);store['current']['state'].update(stage='result',outcome='failure');c.write(s,store)
    c.command(s,dict(action='next',revision=c.read_store(s)['revision']))
    send(s,'roll',roll=rounds)
    assert m.read(s)['fatigue']==rounds
    effects=road_fatigue(('garran',),rounds,'Zmęczenie')
    assert expire_active_effects(effects,EffectEvent(EffectEventType.DECK_REFRESHED)).active_effects==effects
    for _ in range(rounds-1):
        effects=expire_active_effects(effects,EffectEvent(EffectEventType.ROUND_ENDED)).active_effects
        assert effects
    assert not expire_active_effects(effects,EffectEvent(EffectEventType.ROUND_ENDED)).active_effects


def test_fatigue_changes_attack_and_damage_once():
    actor=training_hero('garran')
    source=AttackSource(id='test',name='Miecz',source_type=AttackSourceType.WEAPON,range_feet=5,attack_roll_request=D20RollRequest(),damage_die_sides=8,damage_modifier=4,damage_type='slashing')
    effects=road_fatigue(('garran',),2,'Zmęczenie')
    altered=attack_source_with_combat_effects(actor,source,effects)
    assert altered.damage_modifier==2
    assert altered.damage_components[0].modifier==2
    assert sum(x.value for x in altered.attack_roll_request.modifiers)==-2
    again=attack_source_with_combat_effects(actor,altered,effects)
    assert again.damage_modifier==2
    assert sum(x.value for x in again.attack_roll_request.modifiers)==-2

@pytest.mark.parametrize('debt',['help','report','fraud'])
def test_decisions_summary_rewards_and_checkpoint(tmp_path,debt):
    s=session(tmp_path);stage(s,'explore',outcome='accepted')
    m.checkpoint(s,m.read(s))
    send(s,'leader');send(s,'back');send(s,'dilemma');send(s,debt);send(s,'next');send(s,'loaded');send(s,'next')
    assert m.read(s)['stage']=='summary'
    assert m.read(s)['debt']==debt
    assert sum(x['amount'] for x in m.read(s)['ledger'] if x['kind']=='money')==30+(5 if debt!='help' else 0)
    assert any(i.id=='mission_documents' for a in s.exploration.actors for i in a.inventory)==(debt!='report')
    with pytest.raises(ValueError):send(s,'next')
    send(s,'checkpoint',id='explore')
    assert m.read(s)['stage']=='explore' and not m.read(s)['ledger']


def test_discoveries_and_amulet_transfer_are_not_repeatable_rewards(tmp_path):
    s=session(tmp_path);stage(s,'explore')
    send(s,'armory');send(s,'medallion');send(s,'back')
    send(s,'quarters');send(s,'cache');send(s,'back')
    from dnd_board_game.inventory.armor import effective_armor_class
    before={str(a.id):effective_armor_class(a) for a in s.exploration.actors}
    send(s,'amulet');send(s,'equip_amulet',target='brakka')
    send(s,'amulet');send(s,'equip_amulet',target='dagna')
    assert {str(a.id):effective_armor_class(a) for a in s.exploration.actors}=={k:v+(k=='dagna') for k,v in before.items()}
    send(s,'armory')
    with pytest.raises(ValueError):send(s,'medallion')


def test_editable_text_and_safe_paths(tmp_path):
    (tmp_path/'text').mkdir();(tmp_path/'text/index.json').write_text(json.dumps({'a':dict(title='A',speaker='Narrator',path='text/a.md')}))
    p=tmp_path/'text/a.md';p.write_text('Pierwsza wersja')
    assert text_entry(tmp_path,'a')['body']=='Pierwsza wersja'
    p.write_text('Poprawiona wersja')
    assert text_entry(tmp_path,'a')['body']=='Poprawiona wersja'
    assert surrender_available(3,2,False) and not surrender_available(3,3,False)
    assert not surrender_available(3,0,False) and not surrender_available(3,2,True)


def start_battle(s):
    stage(s,'arrival',fatigue=2)
    send(s,'battle')
    for _ in range(60):
        flow=s.encounter_setup_flow
        if flow.completed:break
        if flow.is_player_start_step:s.assign_encounter_player_start_position(flow.remaining_player_start_positions()[0])
        else:s.confirm_encounter_setup_step()
    s.start_encounter_initiative()
    for i in range(len(s.custom_party)):
        s.submit_encounter_initiative_roll(20-i)
    assert s.combat_state is not None
    return s


def test_real_setup_six_players_fatigue_save_and_surrender(tmp_path):
    s=start_battle(session(tmp_path,6))
    assert len([e for e in s.active_combat_effects if e.kind=='scenario_fatigue'])==6
    # Resolve physical deck preparation through production transport.
    from tests.unit.test_pooled_mana_runtime import prepare
    prepare(s,'B','C')
    s.save_snapshot()
    s.load_snapshot()
    assert len([e for e in s.active_combat_effects if e.kind=='scenario_fatigue'])==6
    enemies=[a for a in s.combat_state.actors if a.faction.value=='enemy']
    defeated={a.id for a in enemies[:3]}
    s.combat_state=replace(s.combat_state,actors=tuple(replace(a,hp=0) if a.id in defeated else a for a in s.combat_state.actors))
    s.state_payload()
    assert m.read(s)['stage']=='surrender'
    send(s,'accept')
    assert s.combat_state is None
    assert m.read(s)['outcome']=='accepted' and m.read(s)['stage']=='post_battle'


def test_potion_uses_actual_item_action_and_physical_dice(tmp_path):
    s=session(tmp_path);data=m.read(s);m.grant(s,data,'potion');m.write(s,data)
    start_battle(s)
    from tests.unit.test_pooled_mana_runtime import prepare
    from dnd_board_game.combat.session import current_actor
    prepare(s,'B','C')
    actor=current_actor(s.combat_state)
    s.combat_state=replace(s.combat_state,actors=tuple(replace(a,hp=max(1,a.hp-12)) if a.id==actor.id else a for a in s.combat_state.actors))
    hp=next(a.hp for a in s.combat_state.actors if a.id==actor.id)
    send(s,'potion');send(s,'potion_target',target=str(actor.id));send(s,'roll',rolls=[2,3])
    assert next(a.hp for a in s.combat_state.actors if a.id==actor.id)==hp+9
    assert not m.available_potions(s)
    assert s.combat_state.turn_action.action_use.value=='action_used'


def test_finished_mission_keeps_party_and_ledger_after_reload(tmp_path):
    s=session(tmp_path,6)
    stage(s,'return',debt='help')
    data=m.read(s);m.grant(s,data,'documents');m.grant(s,data,'medallion');m.write(s,data)
    send(s,'next')
    assert (s.save_dir/'misja_0_dzwon.completed.json').exists()
    assert send(s,'finish')=={'redirect':'/'}
    restored=session(tmp_path)
    restored.load_snapshot()
    assert len(restored.exploration.actors)==6
    assert m.read(restored)['stage']=='summary'
    assert m.read(restored)['debt']=='help'
    assert restored.exploration.actors[0].currency.gp==s.exploration.actors[0].currency.gp
    assert {'mission_documents','mission_medallion'} <= {i.id for a in restored.exploration.actors for i in a.inventory}


def test_declining_compromise_is_persistent_and_cannot_be_replayed(tmp_path):
    s=session(tmp_path);stage(s,'brief');send(s,'negotiate')
    for _ in range(2):c.command(s,dict(action='acknowledge',revision=c.read_store(s)['revision']))
    for color in ('C','B'):c.command(s,dict(action='color',color=color,revision=c.read_store(s)['revision']))
    c.command(s,dict(action='take',index=0,revision=c.read_store(s)['revision']))
    store=c.read_store(s);store['current']['state']['resistance']=10;c.write(s,store)
    assert any(o['action']=='compromise' for o in c.payload(s)['board_choices'])
    c.command(s,dict(action='test',bonus=0,revision=c.read_store(s)['revision']))
    assert c.read_store(s)['current']['compromise_declined']
    c.command(s,dict(action='leave',revision=c.read_store(s)['revision']))
    send(s,'negotiate')
    assert c.payload(s)['phase']=='check'
    with pytest.raises(ValueError,match='odrzucona'):
        c.command(s,dict(action='compromise',revision=c.read_store(s)['revision']))


def test_result_pause_keeps_result_instead_of_restarting(tmp_path):
    s=session(tmp_path);stage(s,'brief');send(s,'negotiate')
    store=c.read_store(s);store['current']['state'].update(stage='result',outcome='failure');c.write(s,store)
    c.command(s,dict(action='leave',revision=c.read_store(s)['revision']))
    send(s,'negotiate')
    assert c.payload(s)['outcome']=='failure'
    c.command(s,dict(action='next',revision=c.read_store(s)['revision']))
    with pytest.raises(ValueError,match='zamknięta'):
        c.command(s,dict(action='next',revision=c.read_store(s)['revision']))


def test_exploration_points_are_selected_on_the_board(tmp_path):
    from dnd_board_game.world import Coordinate
    s=session(tmp_path);stage(s,'explore')
    p=Coordinate(5,7)
    assert p in m.scan_target(s).positions
    m.select_position(s,p)
    assert m.read(s)['stage']=='armory'
    assert s.state.party_position.marker_position==p


def test_mission_save_is_accessible_from_another_active_scenario(tmp_path):
    from dnd_board_game.ui.exploration_app import create_app
    s=session(tmp_path);stage(s,'brief');s.save_snapshot()
    s.configure_scenario(Path('content/scenarios/recruitment_arena.json'))
    client=create_app(s,character_dir=tmp_path/'characters').test_client()
    assert 'Wczytaj Misję 0' in client.get('/load-game').get_data(as_text=True)
    assert client.post('/load-game/mission-zero').status_code==302
    assert m.read(s)['stage']=='brief'
    assert len(s.exploration.actors)==3


def test_launcher_accepts_six_for_mission_and_rejects_two(tmp_path):
    import shutil
    from dnd_board_game.ui.exploration_app import create_app
    character_dir=tmp_path/'characters';character_dir.mkdir()
    for h in HEROES:shutil.copy(Path(f'data/characters/{h}.character.json'),character_dir)
    s=session(tmp_path)
    client=create_app(s,character_dir=character_dir).test_client()
    assert client.post('/new-game/start',data=dict(scenario_id='misja_0_dzwon',character_ids=list(HEROES[:2]))).status_code==400
    assert client.post('/new-game/start',data=dict(scenario_id='misja_0_dzwon',character_ids=list(HEROES))).status_code==302
    assert m.read(s)['stage']=='world' and len(s.exploration.actors)==6
    assert client.post('/new-game/start',data=dict(scenario_id='ostatni_transport_00_gildia',character_ids=list(HEROES))).status_code==400


@pytest.mark.parametrize('previous_outcome',['','refused'])
def test_defeat_overrides_previous_refusal_and_does_not_grant_spoils(tmp_path,previous_outcome):
    s=start_battle(session(tmp_path))
    data=m.read(s);data['outcome']=previous_outcome;m.write(s,data)
    from dnd_board_game.combat.scene import SceneResult,SceneConclusionType
    from dnd_board_game.actors import Faction
    s.combat_state=replace(s.combat_state,actors=tuple(replace(a,hp=0) if a.faction==Faction.ALLY else a for a in s.combat_state.actors))
    s.pending_encounter_result=SceneResult(True,'Pokonani',SceneConclusionType.DEFEAT,Faction.ENEMY)
    s.resolve_active_combat()
    assert m.read(s)['outcome']=='defeated'
    assert all(a.hp==1 for a in s.exploration.actors)
    assert not any(i.id=='mission_tools' for a in s.exploration.actors for i in a.inventory)
    for _ in range(5):send(s,'next')
    assert m.read(s)['stage']=='explore'
    send(s,'leader');send(s,'back');send(s,'dilemma')
    assert {c['action'] for c in m.payload(s)['choices']}=={'help','back'}
