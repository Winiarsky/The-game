"""Opening draft, atomic costs and separate ordinary/special budgets."""
from collections import Counter
from dataclasses import replace

import pytest

from dnd_board_game.actors import Actor, ActorId, Faction, FeatureGrant, FeatureSourceKind
from dnd_board_game.character_creation.runes import apply_rune_profile
from dnd_board_game.combat import ActionUse, InitiativeEntry, InitiativeOrder, start_combat, use_turn_action, use_attack_action
from dnd_board_game.combat.runes import quote_runes, commit_budget
from dnd_board_game.combat.session import use_actor_reaction, finish_turn, current_actor
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.rules.runes import RESOURCE_RUNES, new_runes, take_rune, undo_rune, confirm_allocation, spend_runes, plan_payment, plan_card_payment, RunePool
from dnd_board_game.rules.shared_mana import SharedMana, sync_runes, pay_mana, finish_mana_action, begin_mana_turn, request_mana_refresh
from dnd_board_game.scenarios.rune_catalog import rune_cards, rune_card
from dnd_board_game.world import Coordinate


def pool(opening=('Kotwica','Kotwica','Błysk','Kielich','Klucz')):
    heroes=('garran','mira','nimra')
    deck=[r for _ in heroes for r in RESOURCE_RUNES]
    for rune in opening:
        deck.remove(rune)
    return new_runes(heroes, (*opening,*deck))


def state_with_hand(cards=('Kotwica','Błysk','Kielich','Wieża','Klucz')):
    heroes=[]
    for index,key in enumerate(('garran','mira','nimra','enemy')):
        hero=Actor(id=ActorId(key), name=key, ac=14, hp=20,max_hp=20,temp_hp=0,speed_feet=30,
                   position=Coordinate(index,1), faction=Faction.ENEMY if key=='enemy' else Faction.ALLY)
        if key!='enemy':
            hero=apply_rune_profile(hero)
        heroes.append(hero)
    order=InitiativeOrder(tuple(InitiativeEntry(a,resolve_d20_roll(D20RollInput(D20RollRequest(),20-i)),0,i) for i,a in enumerate(heroes)))
    state=start_combat(tuple(heroes),order)
    draft=pool(cards)
    for rune in cards:
        draft=take_rune(draft,rune)
    while draft.phase == "allocation":
        draft=confirm_allocation(draft)
    return replace(state, shared_mana=sync_runes(state.shared_mana,draft))


def test_opening_duplicates_undo_sealed_turn_and_conservation():
    draft=pool()
    before=draft
    draft=take_rune(draft,'Kotwica')
    assert draft.offer.count('Kotwica')==1
    draft=take_rune(draft,'Kotwica')
    assert 'Kotwica' not in draft.offer
    draft=undo_rune(draft)
    assert draft.offer.count('Kotwica')==1 and draft.hand('garran')==('Kotwica',)
    draft=confirm_allocation(draft)
    assert draft.actor=='mira'
    with pytest.raises(ValueError):
        undo_rune(draft)
    for rune in tuple(draft.offer):
        draft=take_rune(draft,rune)
    draft=confirm_allocation(draft)
    assert draft.actor=='nimra'
    draft=confirm_allocation(draft)
    assert draft.phase=='ready' and draft.deck==before.deck
    assert RunePool.from_payload(draft.as_payload())==draft


def test_remaining_offer_returns_to_first_hero_without_new_draw():
    draft=pool()
    for _ in draft.heroes:
        draft=confirm_allocation(draft)
    assert draft.actor=='garran' and len(draft.offer)==5 and len(draft.deck)==len(RESOURCE_RUNES)*len(draft.heroes)-5


def test_legacy_saved_deck_keeps_hands_order_and_conservation() -> None:
    legacy = ('Wieża', 'Klepsydra', 'Brama', 'Błysk', 'Oko', 'Korona', 'Węzeł', 'Kotwica', 'Kielich', 'Klucz')
    raw = dict(heroes=['brakka'], deck=list(legacy[3:]), offer=[legacy[2]],
               hands=[['brakka', list(legacy[:2])]], picks=list(legacy[:2]))
    restored = RunePool.from_payload(raw)
    assert restored.deck_version == 1
    assert restored.hand('brakka') == legacy[:2]
    assert restored.deck == legacy[3:]
    ready = confirm_allocation(take_rune(restored, legacy[2]))
    paid = spend_runes(ready, 'brakka', plan_card_payment(ready.hand('brakka'), ('Trójząb',), legacy[:2]))
    assert paid.discard == legacy[:2]
    assert RunePool.from_payload(paid.as_payload()) == paid
    with pytest.raises(ValueError, match='skład'):
        replace(paid, deck=paid.deck[:-1])


def test_new_deck_version_survives_save_and_requires_all_six_new_symbols() -> None:
    draft = pool()
    assert draft.deck_version == 2
    assert {'Rozwidlenie', 'Trójząb', 'Romb', 'Hak', 'Schody', 'Grot'} <= set(draft.deck)
    assert RunePool.from_payload(draft.as_payload()) == draft
    with pytest.raises(ValueError, match='skład'):
        replace(draft, deck=draft.deck[:-1])
    with pytest.raises(ValueError, match='wersja'):
        replace(draft, deck_version=3)


def test_payment_reserves_specific_rune_before_wildcard_and_cannot_replay():
    assert plan_payment(('Kotwica','Błysk'),('*','Kotwica'))==('Kotwica','Błysk')
    assert plan_card_payment(('Błysk','Wieża','Klucz'),('Kotwica','Błysk'))==('Wieża','Klucz','Błysk')
    with pytest.raises(ValueError):
        plan_card_payment(('Wieża','Klucz'),('Kotwica','Błysk'))
    state=state_with_hand()
    mana=state.shared_mana
    paid=pay_mana(mana,revision=mana.revision,actor_id='garran',ability_id='shield_bash',count=2,boosts=(('damage',1),))
    assert paid.runes.hand('garran')==('Kielich','Wieża','Klucz')
    assert paid.runes.discard==('Kotwica','Błysk')
    with pytest.raises(ValueError):
        pay_mana(paid,revision=mana.revision,actor_id='garran',ability_id='shield_bash',count=1)
    assert SharedMana.from_payload(paid.as_payload())==paid


def test_no_next_round_draw_or_refresh():
    state=state_with_hand()
    mana=state.shared_mana
    for hero in (*mana.runes.heroes,'enemy','garran'):
        mana=begin_mana_turn(mana,hero,round_end=True)
    assert mana.runes==state.shared_mana.runes
    with pytest.raises(ValueError):
        request_mana_refresh(mana,revision=mana.revision)


def test_special_after_ordinary_attack_and_ordinary_after_special():
    state=state_with_hand()
    ordinary=use_attack_action(state).state
    actor=current_actor(ordinary)
    quote_runes(ordinary,actor,'shield_bash',{})
    committed=commit_budget(ordinary,actor,rune_card('garran','shield_bash'))
    paid=pay_mana(committed.shared_mana,revision=committed.shared_mana.revision,actor_id='garran',ability_id='shield_bash',count=1)
    committed=replace(committed,shared_mana=paid)
    assert use_turn_action(committed).accepted
    assert committed.turn_action.action_use==ActionUse.ACTION_USED
    with pytest.raises(ValueError):
        quote_runes(committed,actor,'second_wind',{})
    early=commit_budget(state,current_actor(state),rune_card('garran','defensive_stance'))
    assert early.turn_action.action_use==ActionUse.ACTION_AVAILABLE
    assert use_attack_action(early).accepted


def test_expensive_power_requires_unused_action_and_movement():
    state=state_with_hand()
    spent=use_turn_action(state).state
    with pytest.raises(ValueError):
        quote_runes(spent,current_actor(spent),'iron_bastion',{})
    moved=replace(state,turn_action=replace(state.turn_action,movement_used_feet=5))
    with pytest.raises(ValueError):
        quote_runes(moved,current_actor(moved),'counterattack_command',{})


def test_opportunity_attack_uses_only_reaction_and_second_wind_once():
    state=state_with_hand()
    hand=state.shared_mana.runes.hand('garran')
    reaction=use_actor_reaction(state,current_actor(state))
    assert reaction.accepted and reaction.state.shared_mana.runes.hand('garran')==hand
    paid=pay_mana(state.shared_mana,revision=state.shared_mana.revision,actor_id='garran',ability_id='second_wind',count=1)
    ready=finish_mana_action(paid,revision=paid.revision)
    assert ('garran','second_wind') in ready.runes.used_once
    with pytest.raises(ValueError):
        spend_runes(ready.runes,'garran',(),once='second_wind')


def test_every_hero_has_live_cards_with_at_most_one_boost_and_star_reserved():
    for hero in ('garran','brakka','mira','dagna','lorian','nimra','erynd'):
        cards=rune_cards(hero)
        assert cards and all(c.rune in (*RESOURCE_RUNES,'*') and c.slot != 24 and c.description for c in cards)
        for card in cards:
            assert len(card.boosts)<=3 and card.payment({})==(card.rune,)
            if len(card.boosts)>1:
                with pytest.raises(ValueError):
                    card.payment({card.boosts[0].id:1,card.boosts[1].id:1})
