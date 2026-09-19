"""Authored approaches, directed support and physical bottom-card inspection."""
from dataclasses import replace
import json
from pathlib import Path

import pytest

from dnd_board_game.application.confrontation import build
from dnd_board_game.inventory.magic_items import effective_ability_modifier
from dnd_board_game.rules import confrontation as r, pooled_mana as mana
from dnd_board_game.scenarios.confrontation import scene_by_id, validate_approaches
from dnd_board_game.ui.training_arena import training_hero
from tests.unit.test_confrontation import charged, settle


def assigned(ids=('compliments', 'logic', 'demands')):
    state = r.begin_preparation(build(tuple(training_hero(h) for h in ('brakka','garran','nimra')), scene_by_id('nessa_raise')))
    for approach in ids:
        state = r.select_approach(state, approach)
    return r.shuffle(state)


def test_assignment_is_unique_in_turn_order_and_has_no_card_cost():
    heroes = tuple(training_hero(h) for h in ('brakka','garran','nimra'))
    state = build(heroes, scene_by_id('nessa_raise'))
    initial = state.mana
    with pytest.raises(ValueError): r.shuffle(replace(state, stage='setup'))
    state = r.begin_preparation(state)
    for actor, chosen in zip(heroes, ('compliments', 'logic', 'demands')):
        assert state.actor.id == str(actor.id)
        with pytest.raises(ValueError): r.select_approach(state, 'not_in_scene')
        with pytest.raises(ValueError): r.declare(state, 0)
        if state.turn:
            with pytest.raises(ValueError): r.select_approach(state, 'compliments')
        state = r.select_approach(state, chosen)
        state = r.Confrontation.from_data(json.loads(json.dumps(state.to_data())))
        assert state.mana == initial
    assert state.stage == 'setup' and state.turn == 0
    assert len({p.approach_id for p in state.participants}) == len(heroes)
    for actor, participant, ability in zip(heroes, state.participants, ('charisma','intelligence','constitution')):
        assert participant.test_modifier == participant.impact_modifier == effective_ability_modifier(actor, ability)
    state = r.shuffle(state)
    with pytest.raises(ValueError): r.select_approach(state, 'logic')


def test_nessa_has_two_distinct_charisma_approaches_and_constitution_demands():
    options = scene_by_id('nessa_raise')['approaches']
    assert [o['id'] for o in options if o['ability']=='charisma'] == ['compliments','bluff','promise']
    demands = next(o for o in options if o['id']=='demands')
    assert (demands['ability'], demands['dc'], demands['die']) == ('constitution',25,10)
    assert 'dexterity' not in {o['ability'] for o in options}


def test_directed_support_checks_selected_target_approach_not_hero_class():
    state = charged(assigned(), {})
    assert [p.id for p in r.support_targets(state)] == ['garran']
    with pytest.raises(ValueError): r.support(state,'nimra')
    with pytest.raises(ValueError): r.support(state,'brakka')
    supported = r.support(state,'garran')
    assert dict(supported.aids) == {'garran':1} and supported.mana.pending_count == 1
    # Logic supports demands, but cannot support compliments: edges are directed.
    state = replace(state,turn=1,mana=replace(state.mana,actor='garran'))
    assert [p.id for p in r.support_targets(state)] == ['nimra']
    with pytest.raises(ValueError): r.support(state,'brakka')


def test_no_matching_target_keeps_test_and_safe_action_available():
    state = charged(assigned(('demands','compliments','logic')), {})
    assert not r.support_targets(state)
    assert r.declare(state,0).stage == 'check'
    assert r.start_peek(state).stage == 'peek_choice'


@pytest.mark.parametrize('move_top',[False,True])
def test_bottom_inspection_retains_zones_consumes_action_and_survives_save(move_top):
    state = charged(assigned(), {})
    state = replace(state,aids=(('brakka',3),))
    before = state.mana
    state = r.start_peek(state)
    with pytest.raises(ValueError): r.declare(state,0)
    with pytest.raises(ValueError): r.support(state,'garran')
    with pytest.raises(ValueError): r.advance(state)
    with pytest.raises(ValueError): r.finish_peek(state,None)
    state = r.Confrontation.from_data(json.loads(json.dumps(state.to_data())))
    state = r.finish_peek(state,move_top)
    assert state.stage == 'after_action' and state.cost == 0
    assert state.mana.deck == ((before.deck[-1],*before.deck[:-1]) if move_top else before.deck)
    assert state.mana.burned == before.burned and state.mana.pools == before.pools and state.mana.offer == before.offer
    assert dict(state.aids)=={'brakka':3}
    with pytest.raises(ValueError): r.start_peek(state)
    assert r.advance(state).actor.id == 'garran'


@pytest.mark.parametrize('move_top',[False,True])
def test_unknown_bottom_stays_unknown_until_normal_reveal(move_top):
    state = r.take(settle(assigned()),0)
    state = replace(state,mana=replace(state.mana,deck=('N',*state.mana.deck[1:])))
    before = state.mana
    state = r.finish_peek(r.start_peek(state),move_top)
    assert state.mana.deck == ((None,*before.deck[:-1]) if move_top else before.deck)
    assert state.mana.pools == before.pools and state.mana.burned == before.burned
    state = r.advance(state)
    if move_top:
        state = r.report_color(state,'C')
        assert state.mana.deck[0]=='N'
    else:
        with pytest.raises(ValueError):r.report_color(state,'C')
        state = r.report_color(state,'N')
    assert state.mana.offer[-1] == ('C' if move_top else 'N')


@pytest.mark.parametrize('size',[0,1])
def test_inspecting_empty_or_single_card_deck_is_safe_but_round_pressure_still_drains(size):
    state = charged(assigned(),{},deck_size=size)
    peek = r.start_peek(state)
    if size:
        peek = r.finish_peek(peek,True)
    assert peek.stage=='after_action' and peek.mana.deck==state.mana.deck
    assert not peek.outcome
    with pytest.raises(ValueError): r.start_peek(peek)
    reaction = r.react(replace(peek,stage='reaction'))
    reaction = settle(reaction)
    assert reaction.outcome=='failure'


def test_known_bottom_is_still_checked_when_later_revealed():
    state = charged(assigned(),{})
    color=state.mana.deck[-1]
    state=r.advance(r.finish_peek(r.start_peek(state),True))
    wrong=next(c for c in mana.COLORS if c!=color)
    with pytest.raises(ValueError):r.report_color(state,wrong)
    assert r.report_color(state,color).mana.offer[-1]==color


@pytest.mark.parametrize('old_stage',['peek_color','peek_choice'])
def test_legacy_color_prompt_resumes_at_position_choice_without_changing_mana(old_stage):
    state=r.start_peek(charged(assigned(),{}))
    data=state.to_data();data['stage']=old_stage;data['last']='Zgłoś kolor dolnej karty.'
    restored=r.Confrontation.from_data(json.loads(json.dumps(data)))
    assert restored.stage=='peek_choice' and restored.mana==state.mana
    assert 'Zgłoś' not in restored.last
    assert r.finish_peek(restored,False).stage=='after_action'


@pytest.mark.parametrize('damage',['duplicate','unknown_link','unknown_ability','empty','wildcard_mix','repeatable_string'])
def test_scene_validation_rejects_bad_options_and_edges(damage):
    options = json.loads(json.dumps(scene_by_id('nessa_raise')['approaches']))
    if damage=='duplicate': options[1]['id']=options[0]['id']
    elif damage=='unknown_link': options[0]['supports']=['absent']
    elif damage=='unknown_ability': options[0]['ability']='luck'
    elif damage=='empty': options=[]
    elif damage=='repeatable_string': options[0]['repeatable']='false'
    else: options[0]['supports']=['*','logic']
    with pytest.raises(ValueError): validate_approaches(options)


def test_all_mission_scenes_have_logical_independent_option_sets():
    scenes = json.loads(Path('content/scenarios/misja_0_dzwon/mechanics/confrontations.json').read_text())
    for scene in scenes.values(): validate_approaches(scene['approaches'])
    assert len({tuple(o['id'] for o in scene['approaches']) for scene in scenes.values()}) == len(scenes)
    assert all(o['ability']!='charisma' for o in scenes['cart']['approaches'])
    assert sum(o['ability']=='intelligence' for o in scenes['quarters']['approaches']) == 2


def test_old_snapshot_without_approaches_keeps_its_started_method():
    state = charged(assigned(),{})
    data = state.to_data();data.pop('approach_options')
    for p in data['participants']:
        for key in ('supports','approach_id','description'):p.pop(key)
    restored = r.Confrontation.from_data(json.loads(json.dumps(data)))
    assert restored.actor.method == state.actor.method
    assert len(r.support_targets(restored))==2
    assert r.declare(restored,0).stage=='check'


@pytest.mark.parametrize('scene_id', ['nessa_raise', 'sealed_cache'])
def test_six_players_can_finish_unique_draft(scene_id):
    heroes = tuple(training_hero(h) for h in ('brakka','garran','nimra','erynd','mira','lorian'))
    original = scene_by_id(scene_id)
    scene = {**original, 'approaches':[{**a, 'repeatable':False} for a in original['approaches']]}
    state = r.begin_preparation(build(heroes, scene))
    for remaining in range(6, 0, -1):
        options = r.available_approaches(state)
        assert len(options) == remaining
        state = r.select_approach(state, options[0].approach_id)
    assert state.stage == 'setup'
    assert len({p.approach_id for p in state.participants}) == 6
    with pytest.raises(ValueError, match='odrębnego'):
        build(heroes, {**scene, 'approaches':scene['approaches'][:5]})


@pytest.mark.parametrize('kind', ['npc', 'object'])
def test_six_heroes_can_share_one_repeatable_approach_and_keep_support_rules(kind):
    scene=scene_by_id('nessa_raise' if kind=='npc' else 'sealed_cache')
    choice=next(a for a in scene['approaches'] if a['repeatable'])
    # A single authored option is enough; repeating it does not create help edges.
    scene={**scene, 'approaches':[{**choice,'supports':[]}]}
    heroes=tuple(training_hero(h) for h in ('brakka','garran','nimra','erynd','mira','lorian'))
    state=r.begin_preparation(build(heroes,scene))
    for _ in heroes:
        assert len(r.available_approaches(state))==1
        state=r.select_approach(state,choice['id'])
        state=r.Confrontation.from_data(json.loads(json.dumps(state.to_data())))
    state=r.shuffle(state)
    assert {p.approach_id for p in state.participants}=={choice['id']}
    assert not r.support_targets(state)


def test_repeatable_empathy_can_support_another_hero_with_same_approach():
    state=charged(assigned(('empathy','empathy','demands')), {})
    assert [p.id for p in r.support_targets(state)]==['garran','nimra']
    assert dict(r.support(state,'garran').aids)=={'garran':1}
    with pytest.raises(ValueError):r.support(state,'brakka')


def test_missing_repeatability_defaults_to_exclusive_for_older_content():
    scene=scene_by_id('nessa_raise')
    option={k:v for k,v in scene['approaches'][0].items() if k!='repeatable'}
    scene={**scene,'approaches':[{**option,'supports':[]}]}
    state=build((training_hero('brakka'),),scene)
    assert not state.approach_options[0][0].repeatable
