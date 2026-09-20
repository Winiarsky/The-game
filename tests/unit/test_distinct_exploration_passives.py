"""The 35 exploration effects change decisions, resources or actual resolution."""
from dataclasses import replace

import pytest

from dnd_board_game.rules import confrontation as r
from dnd_board_game.rules import confrontation_passives as p
from dnd_board_game.scenarios.confrontation import catalog
from tests.unit.test_confrontation import game, charged, settle


def scene(hero: str, hand: tuple[str, ...], **changes) -> r.Confrontation:
    others = tuple(h for h in ('garran', 'dagna', 'erynd') if h != hero)[:2]
    state = charged(game((hero, *others)), {hero: hand})
    actors = tuple(replace(a, dc=10, die=6, test_modifier=0, impact_modifier=0) for a in state.participants)
    return replace(state, **dict(participants=actors, maximum=60, resistance=60) | changes)


def reaction(state: r.Confrontation, kind: str = 'strip', heal: int = 4) -> r.Confrontation:
    return r.react(replace(state, stage='reaction', reactions=(kind,)), heal)


def success(state: r.Confrontation, roll: int = 20, impact: int = 3) -> r.Confrontation:
    return r.roll_impact(r.roll_check(r.declare(state, 0), roll), impact)


def failure(state: r.Confrontation, roll: int = 1) -> r.Confrontation:
    return r.roll_check(r.declare(state, 0), roll)


def test_all_thirty_five_rules_and_names_are_unique():
    entries = [v for profile in catalog()['passives'].values() for v in profile.values()]
    assert len(entries) == len({v['kind'] for v in entries}) == len({v['display']['name'] for v in entries}) == 35
    assert {v['kind'] for v in entries} == p.KINDS


@pytest.mark.parametrize('hero,color', [(h, c) for h in catalog()['passives'] for c in catalog()['passives'][h]])
def test_every_passive_turns_off_without_its_color_and_during_drain(hero, color):
    state = scene(hero, (color,))
    kind = catalog()['passives'][hero][color]['kind']
    assert p.enabled(state, hero, kind)
    assert not p.enabled(replace(state, mana=replace(state.mana, phase='drain')), hero, kind)
    removed = replace(state.mana, pools=(), burned=(color,))
    assert not p.enabled(replace(state, mana=removed), hero, kind)
    assert r.Confrontation.from_data(state.to_data()) == state


def test_garran_follow_guard_line_rally_and_example():
    state = scene('garran', ('C', 'C'), aids=(('garran', 1),))
    assert success(state).last_impact == 5
    assert success(replace(state, aids=())).last_impact == 3
    guarded = scene('garran', ('B',))
    assert reaction(guarded).mana.hand('garran') == ('B',)
    state = scene('garran', ('Z','C','C','F','N','B'), pressure=3)
    assert reaction(state, 'burn').mana.pending_count == 2
    rallied = failure(scene('garran', ('F',)))
    assert dict(rallied.aids) == {'dagna':1, 'erynd':1}
    state = r.support(scene('garran', ('N',)), 'dagna')
    assert dict(state.aids) == {'dagna':1, 'garran':1}


def test_brakka_pressure_stubborn_force_defiance_and_persistence():
    state = scene('brakka', ('C','C','C'))
    assert state.passive('brakka','impact') == 0
    state = replace(state, participants=(replace(state.actor,dc=22),*state.participants[1:]))
    assert state.passive('brakka','impact') == 3
    assert dict(failure(scene('brakka', ('B',))).aids)['brakka'] == 2
    forced = failure(scene('brakka', ('Z',)))
    assert forced.resistance == 59 and forced.last_impact == 1 and forced.mana.pending_count == 1
    assert settle(failure(scene('brakka', ('Z',),resistance=1))).outcome == 'success'
    state = scene('brakka', ('F',))
    assert state.passive('brakka','test') == 2
    assert replace(state,aids=(('brakka',1),)).passive('brakka','test') == 0
    state = scene('brakka', ('N',),resistance=40)
    assert reaction(state,'heal').resistance == 43


def test_mira_opening_slip_precision_shortcut_and_switch():
    state = scene('mira', ('C',),last_action_actor='garran',last_action_kind='test',last_action_success=True)
    assert state.passive('mira','test') == 2
    assert replace(state,last_action_kind='support').passive('mira','test') == 0
    state = r.finish_peek(r.start_peek(scene('mira', ('B',))),False)
    assert reaction(state).mana.hand('mira') == ('B',)
    assert not reaction(scene('mira', ('B',))).mana.hand('mira')
    assert success(scene('mira', ('Z','Z')),impact=6).last_impact == 8
    assert success(scene('mira', ('Z','Z')),impact=5).last_impact == 5
    state = scene('mira', ('F',))
    state = replace(state,participants=(replace(state.actor,supports=(),approach_id='same'),replace(state.participants[1],approach_id='same'),replace(state.participants[2],approach_id='other')))
    assert [a.id for a in r.support_targets(state)] == ['garran']
    state = r.finish_peek(r.start_peek(scene('mira', ('N',))),True)
    assert dict(state.aids)['mira'] == 1 and state.cost == 0


def test_dagna_care_cooperate_recover_shelter_and_patience():
    state = scene('dagna', ('C','C'),last_action_actor='garran',last_action_kind='test',last_action_success=False)
    assert success(state).last_impact == 5
    assert r.support(scene('dagna', ('B',)), 'garran').aids == (('garran',2),)
    state = scene('dagna', ('Z',))
    state = replace(state,mana=replace(state.mana,deck=state.mana.deck[:-1],burned=('N',)))
    pending = success(state)
    assert pending.stage == 'recovery' and pending.mana.burned == ('N',)
    paid = r.confirm_recovery(pending)
    assert paid.mana.deck[-1] == 'N' and not paid.mana.burned and paid.mana.pending_count == 1
    state = scene('dagna', ('F',))
    state = charged(state, {'dagna':('F',),'garran':('N','N')})
    assert reaction(state).mana.hand('garran') == ('N','N')
    assert not reaction(scene('dagna', ('F',))).mana.hand('dagna')
    assert failure(scene('dagna', ('N',)),roll=5).cost == 0
    assert failure(scene('dagna', ('N',)),roll=6).cost == 1


def test_lorian_ensemble_echo_refrain_tempo_and_recycle():
    state = scene('lorian', ('C','C'))
    assert state.passive('lorian','impact') == 0
    state = charged(state, {'lorian':('C','C'), 'garran':('C',)})
    assert state.passive('lorian','impact') == 2
    assert dict(r.support(scene('lorian', ('B',)), 'garran').aids) == {'garran':1,'dagna':1}
    state = scene('garran', ())
    # Receiving help is independent of whose turn is active.
    state = scene('lorian', ('Z',))
    state = replace(state,turn=1,mana=replace(state.mana,actor='garran'))
    assert dict(r.support(state,'lorian').aids)['lorian'] == 2
    state = scene('lorian', ('F',))
    helped = r.support(state,'garran')
    assert helped.cost == 0 and helped.mana.deck == state.mana.deck and helped.stage == 'after_action'
    state = scene('lorian', ('N','F'))
    state = replace(state,mana=replace(state.mana,deck=state.mana.deck[:-1],burned=(state.mana.deck[-1],)))
    pending = r.support(state,'garran')
    assert pending.stage == 'recovery' and pending.recovery_label == 'Drugi obieg'
    result = r.confirm_recovery(pending)
    assert result.mana.phase == 'ready' and result.mana.deck[-1] == state.mana.burned[0] and result.cost == 0


def test_nimra_exact_pattern_stability_focus_and_deduction():
    assert success(scene('nimra', ('C',)),roll=10).last_impact == 6
    assert success(scene('nimra', ('C',)),roll=11).last_impact == 3
    assert scene('nimra', ('B','C','Z')).passive('nimra','test') == 1
    assert scene('nimra', ('B','C','Z','F','N')).passive('nimra','test') == 2
    assert success(scene('nimra', ('Z',)),impact=1).last_impact == 2
    assert success(scene('nimra', ('Z',)),impact=3).last_impact == 3
    assert scene('nimra', ('F','F','N','N')).passive('nimra','impact') == 2
    assert scene('nimra', ('F','F','N')).passive('nimra','impact') == 0
    state = r.finish_peek(r.start_peek(scene('nimra', ('N',))),False)
    assert dict(state.aids)['nimra'] == 2 and state.cost == 0


def test_erynd_finish_scout_prepare_signal_and_track():
    assert scene('erynd', ('C','C'),resistance=20).passive('erynd','impact') == 2
    assert scene('erynd', ('C','C'),resistance=21).passive('erynd','impact') == 0
    assert p.enabled(scene('erynd', ('B',)),'erynd','erynd_scout')
    state = scene('erynd', ('Z',))
    state = charged(state,{'erynd':('Z',)},deck_size=6)
    assert state.passive('erynd','test') == 2
    assert charged(state,{'erynd':('Z',)},deck_size=7).passive('erynd','test') == 0
    state = scene('erynd', ('F',))
    state = charged(state, {'erynd':('F',),'garran':('N','N')})
    assert dict(r.support(state,'garran').aids)['garran'] == 2
    assert dict(success(scene('erynd', ('N',))).aids) == {'garran':1}


def test_saved_old_passives_migrate_without_changing_physical_cards_or_pending_roll(tmp_path):
    from dnd_board_game.ui import confrontation as ui
    from tests.unit.test_confrontation_confirmations import prepared
    session=prepared(tmp_path,recovery=False)
    store=ui.read_store(session)
    state=r.Confrontation.from_data(store['current']['state'])
    state=charged(replace(state,stage='turn'),{'garran':('C','F')})
    state=r.declare(state,2)
    legacy=replace(state,passive_rules_version=1,
        participants=tuple(replace(a,passives=tuple((c,'test') for c,_ in a.passives)) for a in state.participants))
    store['current']['state']=legacy.to_data();ui.write(session,store)
    restored=r.Confrontation.from_data(ui.read_store(session)['current']['state'])
    assert restored.passive_rules_version==2
    assert restored.mana==legacy.mana and restored.check_modifier==legacy.check_modifier
    assert restored.stage=='check' and restored.aids==legacy.aids
    assert dict(restored.actor.passives)['F']=='garran_rally'
    assert all(dict(option.passives)['F']=='garran_rally' for option in restored.approach_options[0])


def test_scout_forecast_is_shown_only_while_erynd_holds_white(tmp_path):
    from dnd_board_game.ui import confrontation as ui
    from tests.unit.test_confrontation_confirmations import prepared
    session=prepared(tmp_path,recovery=False)
    store=ui.read_store(session)
    state=scene('erynd',('B',))
    store['current']['state']=state.to_data();ui.write(session,store)
    assert ui.payload(session)['forecast']
    store['current']['state']=charged(state,{}).to_data();ui.write(session,store)
    assert ui.payload(session)['forecast']==''
