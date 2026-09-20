"""Rules invariants of retained charge and finite party confrontations."""
from dataclasses import replace
import json
import pytest
from dnd_board_game.application.confrontation import build
from dnd_board_game.rules import confrontation as r
from dnd_board_game.rules import pooled_mana as m
from dnd_board_game.scenarios.confrontation import scene_by_id, passives
from dnd_board_game.ui.training_arena import training_hero


def game(heroes=('garran','brakka','dagna'), scene='nessa_raise'):
    s=build(tuple(training_hero(h) for h in heroes),scene_by_id(scene))
    s=r.begin_preparation(s)
    while s.stage=='approach':
        options=r.available_approaches(s)
        chosen=next((p for p in options if '*' in p.supports), options[0])
        s=r.select_approach(s,chosen.approach_id)
    # These economy tests isolate support cost/consumption from authored edges.
    s=replace(s,participants=tuple(replace(p,supports=('*',)) for p in s.participants))
    return r.shuffle(s)


def charged(s, hands, *, deck_size=None):
    """Construct conserved physical zones; unassigned cards are burned."""
    remaining=[c for c in m.COLORS for _ in range(s.mana.copies)]
    for hand in hands.values():
        for c in hand: remaining.remove(c)
    size=len(remaining) if deck_size is None else deck_size
    pool=replace(s.mana,deck=tuple(remaining[:size]),burned=tuple(remaining[size:]),offer=(),
                 pools=tuple((h,tuple(cards)) for h,cards in hands.items()),phase='ready',draw_due=False)
    return replace(s,mana=pool,stage='turn')


def settle(s):
    if s.stage=='recovery': s=r.confirm_recovery(s)
    while s.mana.phase in {'reveal','burn'} and s.stage!='result':
        color=s.mana.deck[0]
        if color is None:
            known=(*s.mana.offer,*s.mana.burned,*(c for _,h in s.mana.pools for c in h))
            color=next(c for c in m.COLORS if known.count(c)<s.mana.copies)
        s=r.report_color(s,color)
    return s


def test_draw_is_mandatory_offer_stays_and_six_cards_stop_draw():
    s=game();s=r.report_color(s,'C');s=r.report_color(s,'B')
    with pytest.raises(ValueError): r.declare(s,0)
    s=r.take(s,0)
    assert s.mana.hand('garran')==('C',) and s.mana.offer==('B',)
    s=r.advance(settle(r.support(s,'brakka')))
    assert s.actor.id=='brakka' and s.mana.offer==('B',) and s.mana.phase=='reveal'
    s=charged(s,{'garran':('B','B','B','C','N','F')})
    s=replace(s,stage='after_reaction')
    s=r.advance(s)
    assert s.mana.points('garran')==6 and s.mana.phase=='ready'
    assert r.available_tiers(s)[-1]==(6,6,1)


@pytest.mark.parametrize('bonus,cost',[(0,1),(2,1),(4,1),(6,1)])
def test_every_charge_tier_costs_one_and_keeps_hand_on_failure(bonus,cost):
    s=charged(game(),{'garran':('B','B','B','C','N','F')})
    s=r.declare(s,bonus);s=r.roll_check(s,1)
    assert s.stage=='after_action' and s.mana.pending_count==cost
    s=settle(s)
    assert len(s.mana.burned)==cost and s.mana.points('garran')==6
    assert s.resistance==s.maximum


def test_hit_uses_attribute_without_proficiency_and_applies_effect_before_cost():
    s=charged(game(),{'garran':('C','C','C')},deck_size=0)
    s=replace(s,resistance=1+s.actor.impact_modifier+2,aids=(('garran',1),))
    s=r.declare(s,0)
    assert s.check_modifier==s.actor.test_modifier+1
    s=r.roll_check(s,20)
    assert s.stage=='impact' and s.mana.phase=='ready'
    s=r.roll_impact(s,1)
    assert s.last_impact==1+s.actor.impact_modifier+2
    assert s.outcome=='success' and s.mana.phase=='drain'


def test_failed_unpayable_test_ends_without_free_last_round():
    s=charged(game(),{},deck_size=0)
    s=r.roll_check(r.declare(s,0),1)
    assert s.outcome=='failure'
    with pytest.raises(ValueError):r.advance(s)


def test_exact_last_card_paid_allows_next_turn_and_support_but_next_burn_drains():
    s=charged(game(),{'brakka':('C','C','C','B','Z','N')},deck_size=1)
    s=settle(r.roll_check(r.declare(s,0),1))
    assert s.stage=='after_action' and not s.mana.deck
    s=r.advance(s)
    assert s.actor.id=='brakka' and s.stage=='turn' and s.mana.phase=='ready'
    s=r.roll_check(r.declare(s,0),1)
    assert s.outcome=='failure'


@pytest.mark.parametrize('natural', [1, 20])
@pytest.mark.parametrize('scene', ['nessa_raise', 'sealed_cache'])
def test_support_stacks_across_turns_and_all_expires_on_own_attempt(natural, scene):
    s=charged(game(('erynd','garran','nimra'),scene),{})
    def act(state, index):
        return replace(state, stage='turn', turn=index,
                       mana=replace(state.mana,actor=state.participants[index].id))
    s=settle(r.support(s,'garran'))
    assert dict(s.aids)['garran']==1 and len(s.mana.burned)==1
    # Garran supports Nimra instead of using the bonus; it remains for later.
    s=settle(r.support(act(s,1),'nimra'))
    assert dict(s.aids)=={'garran':1,'nimra':1}
    s=settle(r.support(act(s,2),'garran'))
    s=settle(r.support(act(s,0),'garran'))
    assert dict(s.aids)['garran']==3 and len(s.mana.burned)==4
    s=r.declare(act(s,1),0)
    assert s.check_modifier==s.actor.test_modifier+3
    assert dict(s.aids)['garran']==3  # No attempt yet, including save/load.
    s=r.Confrontation.from_data(json.loads(json.dumps(s.to_data())))
    with pytest.raises(ValueError):r.roll_check(s,0)
    after=r.roll_check(s,natural)
    assert dict(after.aids)=={'nimra':1}
    assert after.last_total==natural+s.actor.test_modifier+3
    assert after.stage==('impact' if natural==20 else 'after_action')
    if natural==20:after=r.roll_impact(after,1)
    after=settle(after)
    assert len(after.mana.burned)==5
    again=r.declare(act(after,1),0)
    assert again.check_modifier==again.actor.test_modifier


def test_cooperation_adds_one_without_stacking_from_duplicate_color_cards():
    s=charged(game(('dagna','garran','brakka')),{'dagna':('B','B')})
    assert r.support_bonus(s)==2
    supported=r.support(s,'garran')
    assert dict(supported.aids)['garran']==2
    assert supported.mana.phase=='burn' and supported.mana.pending_count==1
    assert supported.mana.hand('dagna')==('B','B')
    with pytest.raises(ValueError):r.advance(supported)
    with pytest.raises(ValueError):r.support(supported,'garran')
    supported=replace(settle(supported),stage='turn')
    supported=settle(r.support(supported,'garran'))
    assert dict(supported.aids)['garran']==4


def test_support_without_card_to_burn_ends_confrontation():
    s=charged(game(),{},deck_size=0)
    result=r.support(s,'brakka')
    assert result.outcome=='failure' and result.mana.phase=='drain'
    with pytest.raises(ValueError):r.advance(result)


def test_recovery_is_active_on_each_success_not_on_pick():
    s=charged(game(('dagna','garran','brakka')),{},deck_size=20)
    color=s.mana.burned[0]
    remaining=list(s.mana.deck);remaining.remove('Z');remaining.remove('C')
    s=replace(s,mana=replace(s.mana,deck=tuple(remaining),offer=('Z','C'),phase='choose',draw_due=True))
    s=r.take(s,0)
    assert len(s.mana.burned)==10
    supported=r.support(s,'brakka')
    assert len(supported.mana.burned)==10
    for _ in range(2):
        s=r.roll_impact(r.roll_check(r.declare(s,0),20),1)
        assert s.stage=='recovery' and len(s.mana.burned)==10
        s=r.confirm_recovery(s)
        assert s.mana.deck[-1]==color and len(s.mana.burned)==9
        s=settle(s)
        color=s.mana.burned[0]
        s=replace(s,stage='turn')


@pytest.mark.parametrize('guard',[True,False])
def test_counterargument_removes_charge_and_its_passive_unless_guarded(guard):
    hand=('B','B','B') if guard else ('C','C','C','C','C','C')
    s=charged(game(),{'garran':hand})
    s=r.react(replace(s,stage='reaction',round=2))
    assert len(s.mana.hand('garran'))==len(hand)-(not guard)
    assert s.mana.phase=='burn' and s.mana.pending_count==3


def test_reaction_heals_once_and_pressure_ends_support_loop():
    s=charged(game(),{},deck_size=2)
    s=r.react(replace(s,stage='reaction',round=3,resistance=1),4)
    assert s.resistance==5 and s.outcome=='failure'
    with pytest.raises(ValueError): r.react(s,4)


def test_save_roundtrip_in_middle_of_two_stage_roll():
    s=charged(game(),{'garran':('F',)})
    s=r.roll_check(r.declare(s,0),20)
    loaded=r.Confrontation.from_data(json.loads(json.dumps(s.to_data())))
    assert loaded==s
    assert r.roll_impact(loaded,3)==r.roll_impact(s,3)


@pytest.mark.parametrize('scene,action',[('nessa_compromise','compromise'),('nessa_favor','favor')])
def test_scene_decisions_are_guarded_and_favor_is_not_repeatable(scene,action):
    s=charged(game(scene=scene),{},deck_size=20)
    if action=='compromise':
        with pytest.raises(ValueError):r.compromise(s)
        assert r.compromise(replace(s,resistance=s.maximum//2)).outcome=='compromise'
    else:
        s=r.favor(s);assert s.obligation and len(s.mana.deck)==21
        with pytest.raises(ValueError):r.favor(s)


def test_invalid_natural_rolls_do_not_mutate_state():
    s=charged(game(),{})
    for invalid in (0,21,True,'20'):
        with pytest.raises(ValueError):r.roll_check(r.declare(s,0),invalid)
    assert s.stage=='turn'


@pytest.mark.parametrize('hero',('garran','brakka','mira','dagna','lorian','nimra','erynd'))
def test_prepared_charge_reaction_and_drain_cases_use_conserved_cards(hero):
    from dnd_board_game.application.confrontation import prepare_lesson
    s=game((hero,))
    charge=prepare_lesson(s,'charge')
    assert charge.mana.phase=='choose' and len(charge.mana.hand(hero))==5
    charge=r.take(charge,0)
    assert len(charge.mana.hand(hero))==6 and charge.reached_charge
    reaction=prepare_lesson(s,'reaction')
    assert reaction.stage=='reaction' and reaction.round==2
    reaction=r.react(reaction)
    assert reaction.reacted
    drain=prepare_lesson(s,'drain')
    assert drain.mana.deck==('C','B','N') and len(drain.mana.burned)==22
    drain=r.report_color(drain,'C');drain=r.report_color(drain,'B');drain=r.take(drain,0)
    drain=r.roll_check(r.declare(drain,0),1)
    assert drain.mana.phase=='burn'
    with pytest.raises(ValueError):r.report_color(drain,'C')
    drain=r.report_color(drain,'N')
    assert not drain.mana.deck


def test_color_goal_and_sensitive_consequence_are_party_wide_and_need_success():
    s=charged(game(scene='nessa_color_goal'),{'brakka':('N',),'dagna':('N',)})
    s=replace(s,resistance=1)
    s=settle(r.roll_impact(r.roll_check(r.declare(s,0),20),1))
    assert s.goal and s.outcome=='success'
    s=charged(game(scene='nessa_color_goal'),{'brakka':('N',),'dagna':('N',)},deck_size=0)
    assert not r.roll_check(r.declare(s,0),1).goal
    s=game(scene='nessa_sensitive');s=r.report_color(s,'C');s=r.report_color(s,'B')
    assert r.take(s,0).sensitive and not r.take(s,1).sensitive
