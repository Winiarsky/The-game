from dataclasses import replace

import pytest

from dnd_board_game.rules.pooled_mana import (
    COLORS, PooledMana, new_mana, confirm_shuffle, start_turn, pay_pool,
    finish_burn, attack_mana, report_removed, recover, reveal, take, drain,
)
from dnd_board_game.scenarios.pooled_mana_catalog import hero_profile, load_catalog, pool_ability
from dnd_board_game.combat.mana_charge import charge_effects, picked_color, saving_modifiers
from tests.unit.test_hero_rules_consistency import heroes
from tests.unit.test_physical_mana import session_for
from tests.unit.test_pooled_mana_runtime import send, prepare


def pool(hero='brakka', hand=()):
    p = new_mana((hero,), hero, values={hero: hero_profile(hero)['values']})
    return replace(p, deck=(None,) * (25 - len(hand)), pools=((hero, hand),), phase='ready', draw_due=False)


def test_charge_payment_retains_all_cards_and_defers_burn():
    p = pool(hand=('C', 'C', 'C'))
    paid = pay_pool(p, 'brakka')
    assert paid.hand('brakka') == p.hand('brakka') and paid.deck == p.deck
    pending = finish_burn(paid)
    assert pending.phase == 'burn' and pending.pending_count == 1
    done = report_removed(pending, 'B')
    assert done.burned == ('B',) and done.hand('brakka') == p.hand('brakka')


@pytest.mark.parametrize('hero', tuple(load_catalog()['heroes']))
def test_cap_and_all_abilities_ignore_color_requirements(hero):
    profile = hero_profile(hero)
    color = max(profile['values'], key=profile['values'].get)
    p = pool(hero, (color, color, color))
    assert p.points(hero) == 6
    assert p.roll_bonus(hero) == 3
    assert start_turn(p, hero).phase == 'reveal'
    assert start_turn(p, hero).draw_due
    for key, a in load_catalog()['abilities'].items():
        if a['hero'] == hero:
            pool_ability(key, hero).validate(p.hand(hero), profile['values'])
    for c in COLORS:
        assert c in profile['color_passives']


def test_sixth_card_caps_charge_and_next_turn_never_draws():
    p = pool(hand=('C','C','N','Z','F'))
    p = replace(p, deck=p.deck[:-2], offer=('N','B'), phase='choose', draw_due=True)
    p = take(p, 0)
    assert p.points('brakka') == 6
    assert p.roll_bonus('brakka') == 6
    assert len(p.hand('brakka')) == 6
    assert start_turn(p, 'brakka').offer == ('B',)
    assert start_turn(p, 'brakka').phase == 'ready'


def test_expiry_cannot_be_recovered_and_drain_collects_every_zone():
    p = pool(hand=('C',))
    p = replace(p, deck=(None,)*20, offer=('N',), burned=('Z',), prisons=(('foe',('F',)),), expired=('B',))
    with pytest.raises(ValueError):
        recover(p, ('B',))
    reset = confirm_shuffle(drain(p, 'test'))
    assert len(reset.deck) == 25 and not reset.pools and not reset.expired and not reset.burned and not reset.prisons
    assert reset.values == p.values
    assert PooledMana.from_payload(p.as_payload()) == p


def test_round_expiry_resumes_mandatory_pick_but_not_full_charge():
    for hand, phase in [((), 'reveal'), (('C','C','C','N','Z','F'), 'ready')]:
        p = start_turn(pool(hand=hand), 'brakka', round_end=True)
        assert p.phase == 'expire'
        p = report_removed(p, 'B')
        assert p.expired == ('B',) and p.phase == phase


def test_drain_does_not_grant_pick_action_or_reset_turn_usage():
    p = replace(pool(hand=('C','C','C')), used=('brakka:once',))
    p = replace(p, deck=(), burned=('C','C', *('B',)*5, *('Z',)*5, *('F',)*5, *('N',)*5))
    p = finish_burn(pay_pool(p, 'brakka'))
    assert p.phase == 'drain'
    p = confirm_shuffle(p)
    assert not p.draw_due and p.used == ('brakka:once',)


def test_statuses_stack_damage_cap_ac_and_modify_real_source(heroes, tmp_path):
    from dnd_board_game.combat.scene_interactions import attack_source_with_combat_effects
    from dnd_board_game.combat.targets import combat_armor_class
    from dnd_board_game.inventory import effective_armor_class
    p = pool('lorian', ('C','C','C','B','B'))
    effects = charge_effects(p, {'lorian': hero_profile('lorian')})
    actor = heroes['lorian']
    assert combat_armor_class(actor, effects) == effective_armor_class(actor)
    session = session_for(actor, tmp_path, pooled=True)
    source = next(s for s in session._attack_sources_for_actor(actor) if s.source_type.value == 'weapon' and s.attack_kind.value == 'ranged')
    changed = attack_source_with_combat_effects(actor, source, effects)
    assert changed.damage_modifier == source.damage_modifier + 6
    assert changed.damage_components[0].modifier == source.damage_components[0].modifier + 6
    twice = attack_source_with_combat_effects(actor, changed, effects)
    assert twice.damage_components == changed.damage_components
    assert twice.damage_modifier == changed.damage_modifier


def test_color_heal_runs_once_and_drain_removes_real_status(heroes, tmp_path):
    s = session_for(replace(heroes['brakka'], hp=5), tmp_path, pooled=True)
    prepare(s, 'Z', 'B')
    assert s._actor_by_string_id('brakka').hp == 10
    s.state_payload(); s.state_payload()
    assert s._actor_by_string_id('brakka').hp == 10
    from dnd_board_game.rules.shared_mana import sync_pool
    p = s.combat_state.shared_mana.pooled
    p = replace(p, deck=p.deck[:-1], pools=(('brakka', ('Z','B')),))
    s.combat_state = replace(s.combat_state, shared_mana=sync_pool(s.combat_state.shared_mana, drain(p, 'test')))
    send(s, 'pool_shuffle')
    assert not any(e.kind.startswith('charge_') for e in s.active_combat_effects)
    assert s._actor_by_string_id('brakka').hp == 10


def test_bard_discount_affects_boost_cost_and_recovery_can_extend_deck(heroes,tmp_path):
    from dnd_board_game.combat.pooled_mana import quote_pool
    from dnd_board_game.rules.shared_mana_catalog import shared_ability
    from dnd_board_game.rules.shared_mana import sync_pool
    s=session_for(heroes['lorian'],tmp_path,pooled=True)
    p=pool('lorian',('N','N','F'))
    s.combat_state=replace(s.combat_state,shared_mana=sync_pool(s.combat_state.shared_mana,p))
    effects=charge_effects(p,{'lorian':hero_profile('lorian')})
    a=shared_ability('lorian','mana_recovery')
    q=quote_pool(s.combat_state,heroes['lorian'],a,pool_ability(a.id),hero_profile('lorian')['values'],{},effects=effects)
    assert len(q.cards)==0
    q=quote_pool(s.combat_state,heroes['lorian'],a,pool_ability(a.id),hero_profile('lorian')['values'],{'recover':1},effects=effects)
    assert len(q.cards)==1


def test_expiry_after_imprisoning_does_not_duplicate_a_card():
    p = attack_mana(pool(), 'deck', captor='enemy')
    p = report_removed(p, 'C')
    p = start_turn(p, 'brakka', round_end=True)
    p = report_removed(p, 'B')
    assert dict(p.prisons) == {'enemy': ('C',)}
    assert p.expired == ('B',)
    assert sum(len(h) for _, h in p.prisons) == 1


def test_spell_damage_and_real_saving_throw_include_color_status(heroes, tmp_path):
    from dnd_board_game.rules import SavingThrowRequest
    from dnd_board_game.combat.spells import resolve_actor_saving_throw
    from dnd_board_game.rules.shared_mana import sync_pool
    from dnd_board_game.combat.shared_mana import synchronize_shared_effects
    actor = heroes['nimra']
    s = session_for(actor, tmp_path, pooled=True)
    p = pool('nimra', ('C','N','F'))
    s.combat_state = replace(s.combat_state, shared_mana=sync_pool(s.combat_state.shared_mana,p))
    s.combat_state,s.active_combat_effects=synchronize_shared_effects(s.combat_state,())
    source=s._attack_source_by_id(actor, 'nimra_frost_pulse')
    effective=s._effective_attack_source(actor,source)
    assert effective.damage_modifier==source.damage_modifier+1
    assert effective.damage_components[0].modifier==source.damage_components[0].modifier+1
    request=SavingThrowRequest(ability='constitution', dc=15, source_label='Test koloru')
    before=resolve_actor_saving_throw(actor,request,natural_roll=10)
    after=resolve_actor_saving_throw(actor,request,natural_roll=10,active_effects=s.active_combat_effects)
    assert after.total==before.total  # Black now unlocks mental saves vs magic; no flat KON bonus.


def test_last_paid_action_heals_before_drain_and_keeps_used_bonus_action(heroes,tmp_path):
    from dnd_board_game.rules.shared_mana import sync_pool
    from dnd_board_game.combat.session import current_actor
    s=session_for(replace(heroes['garran'],hp=5),tmp_path,pooled=True)
    prepare(s,'B','C')
    p=s.combat_state.shared_mana.pooled
    cards=list(COLORS)*5
    cards.remove('B');cards.remove('C')
    p=replace(p,deck=(),burned=tuple(cards))
    s.combat_state=replace(s.combat_state,shared_mana=sync_pool(s.combat_state.shared_mana,p))
    s.use_combat_class_feature('second_wind',natural_roll=5)
    send(s,'pay')
    assert current_actor(s.combat_state).hp>5
    assert s.combat_state.shared_mana.pooled.phase=='drain'
    action=s.combat_state.turn_action
    send(s,'pool_shuffle')
    assert s.combat_state.turn_action==action
    assert not s.combat_state.shared_mana.pooled.draw_due


@pytest.mark.parametrize('ability,boost', [('mana_recovery',False),('mana_recovery',True),('mana_great_tuning',False)])
def test_lorian_actual_card_operation_preserves_charge_and_settles_boost(heroes,tmp_path,ability,boost):
    from dnd_board_game.rules.shared_mana import sync_pool
    s=session_for(heroes['lorian'],tmp_path,pooled=True)
    p=pool('lorian',('N','N','F','N'))
    p=replace(p,deck=p.deck[:-4],burned=('B','Z','C'),expired=('F',))
    s.combat_state=replace(s.combat_state,shared_mana=sync_pool(s.combat_state.shared_mana,p))
    s.state_payload()
    before=s.combat_state.shared_mana.pooled
    s.use_combat_class_feature(ability)
    if boost:
        send(s,'boost',boost_id='recover',count=1)
    send(s,'pay')
    assert s.shared_mana_declaration.stage=='cards'
    selected=('B','Z','C') if boost or ability=='mana_great_tuning' else ('B','Z')
    for color in selected:
        send(s,'pool_color',color=color)
    send(s,'pool_bard_done')
    p=s.combat_state.shared_mana.pooled
    assert p.hand('lorian')==before.hand('lorian') and p.expired==('F',)
    assert (p.deck[:len(selected)] if ability=='mana_great_tuning' else p.deck[-len(selected):])==selected
    if boost:
        assert p.phase=='burn' and p.pending_count==1
        send(s,'pool_color',color='B')
    assert s.combat_state.shared_mana.pooled.phase=='ready'
