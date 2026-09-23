"""The production session resolves rune cards for every playable hero."""
from collections import Counter
from dataclasses import replace
from pathlib import Path

import pytest

from dnd_board_game.combat import ActionUse, current_actor, replace_actor, TurnActionState
from dnd_board_game.rules.runes import RESOURCE_RUNES, new_runes, take_rune, confirm_allocation
from dnd_board_game.rules.shared_mana import sync_runes
from dnd_board_game.ui import shared_mana, mission_zero
from dnd_board_game.ui.training_arena import training_hero
from dnd_board_game.ui.exploration_app import ExplorationUiSession
from dnd_board_game.world import Coordinate
from tests.unit.test_mission_zero import start_battle


def playable(tmp_path: Path, hero: str, opening: tuple[str,...]):
    party=(hero,*[h for h in ('garran','mira','dagna') if h!=hero][:2])
    game=ExplorationUiSession('content/scenarios/misja_0_dzwon/scenario.json',save_dir=tmp_path/'saves',observation_dir=tmp_path/'logs')
    game.configure_custom_party(tuple(training_hero(h) for h in party))
    mission_zero.initialize(game)
    game.encounter_rng.seed(0)
    start_battle(game)
    state=game.combat_state
    index=next(i for i,e in enumerate(state.initiative_order.entries) if str(e.actor.id)==hero)
    game.combat_state=state=replace(state,initiative_order=replace(state.initiative_order,current_index=index),turn_action=TurnActionState())
    pool=state.shared_mana.runes
    deck=[r for _ in pool.heroes for r in RESOURCE_RUNES]
    for rune in opening:deck.remove(rune)
    draft=new_runes(pool.heroes,(*opening,*deck))
    while draft.actor != hero:draft=confirm_allocation(draft)
    for rune in tuple(draft.offer):draft=take_rune(draft,rune)
    while draft.phase=='allocation':draft=confirm_allocation(draft)
    game.combat_state=replace(state,shared_mana=replace(sync_runes(state.shared_mana,draft),turn_actor=hero))
    game.configured_board_backend='none'
    actor=current_actor(game.combat_state)
    ally=next(a for a in game.combat_state.actors if a.faction==actor.faction and a.id!=actor.id)
    enemy=next(a for a in game.combat_state.actors if a.faction!=actor.faction)
    game.combat_state=replace_actor(game.combat_state,replace(ally,position=Coordinate(actor.position.col,actor.position.row+1)))
    game.combat_state=replace_actor(game.combat_state,replace(enemy,position=Coordinate(actor.position.col-1,actor.position.row)))
    game.state_payload()
    return game,str(ally.id),str(enemy.id)


def pay(game, command='pay', **data):
    return shared_mana.command(game,dict(command=command,revision=game.combat_state.shared_mana.revision,**data))


def test_brakka_shoulder_check_preview_and_payment_use_trident(tmp_path: Path) -> None:
    from dnd_board_game.ui.runes import option_metadata
    game, _, enemy = playable(tmp_path, 'brakka', ('Trójząb', 'Błysk', 'Kotwica', 'Kielich', 'Klucz'))
    metadata = option_metadata(game, {'action_id': 'shoulder_check'})
    assert metadata['rune_slot'] == 8
    assert metadata['rune_cost'] == ['Trójząb']
    game.start_combat_class_feature_targeting('shoulder_check')
    target = next(a for a in game.combat_state.actors if str(a.id) == enemy)
    game._handle_board_position(target.position)
    game.confirm_combat_class_feature_targeting()
    pay(game)
    assert game.combat_state.shared_mana.runes.discard == ('Trójząb',)
    assert 'Błysk' in game.combat_state.shared_mana.runes.hand('brakka')


@pytest.mark.parametrize('hero,ability,target,effect',[
    ('garran','defensive_stance','', 'garran_defensive_stance_ac'),
    ('brakka','rage','', 'rage'),
    ('mira','feint','enemy', 'feint'),
    ('dagna','caring_gesture','ally', 'temporary_hit_points'),
    ('lorian','mana_inspiration','ally','bardic_inspiration'),
    ('erynd','aim','', 'erynd_aim_advantage'),
])
def test_card_resolves_and_preserves_ordinary_action(tmp_path,hero,ability,target,effect):
    from dnd_board_game.scenarios.rune_catalog import rune_card
    card=rune_card(hero,ability)
    game,ally,enemy=playable(tmp_path,hero,(card.rune if card.rune!='*' else 'Wieża','Kotwica','Błysk','Kielich','Klucz'))
    before=game.combat_state.shared_mana.runes
    game.use_combat_class_feature(ability,target_id=ally if target=='ally' else enemy if target=='enemy' else '',natural_roll=3 if hero=='dagna' else None)
    assert game.shared_mana_declaration is not None
    assert game.combat_state.shared_mana.runes==before
    assert not shared_mana.payload(game)['declaration'].get('error')
    pay(game)
    assert len(game.combat_state.shared_mana.runes.discard)==(0 if card.free_first else 1)
    assert game.combat_state.turn_action.rune_special_used
    assert game.combat_state.turn_action.action_use==ActionUse.ACTION_AVAILABLE
    assert any(e.kind==effect for e in game.active_combat_effects)


def test_nimra_attack_spell_after_weapon_action_uses_special_budget(tmp_path):
    game,ally,enemy=playable(tmp_path,'nimra',('Rozwidlenie','Kotwica','Błysk','Kielich','Klucz'))
    game.combat_state=replace(game.combat_state,turn_action=replace(game.combat_state.turn_action,action_use=ActionUse.ACTION_USED))
    target=next(a for a in game.combat_state.actors if str(a.id)==enemy)
    game.select_combat_attack_source('nimra_frost_pulse')
    game.select_player_attack_target_at_position(target.position)
    game.confirm_player_attack_target()
    assert game.shared_mana_declaration.ability_id=='nimra_frost_pulse'
    pay(game)
    if game.pending_player_attack and game.pending_player_attack.stage=='damage_roll':
        game.submit_player_damage_roll(damage=4)
    assert game.combat_state.turn_action.rune_special_used
    assert len(game.combat_state.shared_mana.runes.discard)==1
    assert game.combat_state.turn_action.action_use==ActionUse.ACTION_USED


def test_erynd_modes_are_selected_before_payment(tmp_path):
    game,_,_=playable(tmp_path,'erynd',('Wieża','Kotwica','Błysk','Kielich','Klucz'))
    before=game.combat_state.shared_mana.runes
    game.use_combat_class_feature('cunning_action')
    assert shared_mana.payload(game)['declaration']['mode_options']
    with pytest.raises(ValueError):pay(game)
    assert game.combat_state.shared_mana.runes==before
    pay(game,'mode',mode='disengage')
    pay(game)
    assert game.combat_state.turn_action.rune_special_used
    assert game.combat_state.turn_action.action_use==ActionUse.ACTION_AVAILABLE


def test_tuning_substitution_requires_a_remaining_rune_and_previews_it(tmp_path):
    from dnd_board_game.combat.runes import quote_runes
    from dnd_board_game.rules.runes import spend_runes
    game,_,_=playable(tmp_path,'lorian',('Wieża','Klucz','Kotwica','Błysk','Kielich'))
    state=game.combat_state
    remaining=spend_runes(state.shared_mana.runes,'lorian',('Wieża','Klucz'))
    state=replace(state,shared_mana=sync_runes(state.shared_mana,remaining))
    empty_after_payment=spend_runes(remaining,'lorian',('Kielich',))
    no_exchange=replace(state,shared_mana=sync_runes(state.shared_mana,empty_after_payment))
    with pytest.raises(ValueError,match='dodatkowej runy'):
        quote_runes(no_exchange,current_actor(no_exchange),'mana_tuning',{})
    game.combat_state=state
    game.use_combat_class_feature('mana_tuning')
    assert any('wybierzesz runę' in text for text in shared_mana.payload(game)['declaration']['reminders'])
    pay(game)
    pay(game,'rune_choice_take',rune='Kotwica')
    pay(game,'rune_choice_take',rune='Błysk')
    pay(game,'rune_choice_confirm')
    pay(game,'rune_choice_take',rune='Kielich')
    pay(game,'rune_choice_confirm')
    assert len(game.combat_state.shared_mana.runes.hand('lorian'))==1
