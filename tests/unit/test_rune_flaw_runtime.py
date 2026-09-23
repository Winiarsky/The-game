"""Board selection of flaw fees, including a later target in one paid power."""
from dataclasses import replace

from dnd_board_game.combat import current_actor, replace_actor
from dnd_board_game.ui import shared_mana, runes
from dnd_board_game.hardware.board_panel import panel_position
from dnd_board_game.world import Coordinate
from tests.unit.test_rune_combat_actions import playable, pay
from tests.unit.test_rune_payment_choices import choose, confirm


def test_lorian_flaw_fee_is_chosen_and_undoable_before_payment(tmp_path):
    game, _, _ = playable(tmp_path, 'lorian', ('Klepsydra', 'Wieża', 'Kotwica', 'Błysk', 'Klucz'))
    actor = current_actor(game.combat_state)
    for other in tuple(game.combat_state.actors):
        if other.faction == actor.faction and other.id != actor.id:
            game.combat_state = replace_actor(game.combat_state, replace(other,
                position=Coordinate(actor.position.col+5, other.position.row)))
    game.use_combat_class_feature('mana_tuning')
    view = shared_mana.payload(game)['declaration']
    assert view['cost'] == ['Wieża', '*']
    assert any('Potrzeba publiczności' in r for r in view['reminders'])
    before = game.combat_state.shared_mana.runes
    pay(game)
    assert panel_position(28) not in runes.scan_target(game).positions
    choose(game, 'Klucz')
    assert panel_position(28) in runes.scan_target(game).positions
    pay(game, 'rune_choice_back')
    assert game.combat_state.shared_mana.runes == before
    choose(game, 'Błysk'); confirm(game)
    assert game.shared_mana_declaration.rune_choice_step == 'exchange'
    choose(game, 'Klucz'); confirm(game)
    assert game.combat_state.shared_mana.runes.discard == ('Wieża', 'Błysk', 'Klucz')
    assert not any(e.kind == 'shared_audience_paid' for e in game.active_combat_effects)


def test_second_shot_opens_only_flaw_fee_without_spending_another_action(tmp_path):
    game, ally_id, enemy_id = playable(tmp_path, 'erynd', ('Hak', 'Kotwica', 'Błysk', 'Kielich', 'Klucz'))
    actor = current_actor(game.combat_state)
    for other in tuple(game.combat_state.actors):
        if other.faction == actor.faction and other.id != actor.id:
            game.combat_state = replace_actor(game.combat_state, replace(other,
                position=Coordinate(actor.position.col+5, other.position.row)))
    enemy = next(a for a in game.combat_state.actors if str(a.id) == enemy_id)
    game.use_combat_class_feature('double_shot')
    game.select_player_attack_target_at_position(enemy.position)
    game.confirm_player_attack_target()
    assert shared_mana.payload(game)['declaration']['cost'] == ['Hak']
    pay(game)
    game.submit_player_attack_roll(natural_roll=1, natural_roll_2=1)
    assert game.combat_state.turn_action.attacks_used == 1
    ally = next(a for a in game.combat_state.actors if str(a.id) == ally_id)
    game.combat_state = replace_actor(game.combat_state, replace(ally,
        position=Coordinate(enemy.position.col, enemy.position.row+1)))
    game.select_player_attack_target_at_position(enemy.position)
    game.confirm_player_attack_target()
    assert game.shared_mana_declaration.rune_flaw_only
    assert shared_mana.payload(game)['declaration']['cost'] == ['*']
    assert not shared_mana.payload(game)['declaration']['boost_options']
    budget = game.combat_state.turn_action
    before = game.combat_state.shared_mana.runes
    pay(game)
    choose(game, 'Klucz')
    assert game.combat_state.shared_mana.runes == before
    confirm(game)
    assert game.combat_state.shared_mana.rune_flaw_paid
    assert game.combat_state.shared_mana.runes.discard == ('Hak', 'Klucz')
    assert game.combat_state.turn_action.shared_bonus_actions_used == budget.shared_bonus_actions_used
    game.submit_player_attack_roll(natural_roll=1, natural_roll_2=1)
    assert game.combat_state.shared_mana.phase.value == "ready"
    assert not game.combat_state.turn_action.attack_action_active
    assert game.combat_state.turn_action.action_use.value == "action_used"
    assert game.shared_mana_declaration is None
