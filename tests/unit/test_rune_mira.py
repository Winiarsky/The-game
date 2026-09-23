"""Mira's rune attacks use observer knowledge and the equipped weapon."""
from dataclasses import replace
from pathlib import Path

import pytest

from dnd_board_game.combat import ActionUse, current_actor, replace_actor
from dnd_board_game.combat.attack_flow import legal_attack_targets
from dnd_board_game.combat.attack_positioning import AttackPositioning, attack_source_with_positioning
from dnd_board_game.combat.class_features import plan_sneak_attack
from dnd_board_game.combat.shared_mana_sources import boost_attack
from dnd_board_game.combat.stealth import HiddenState, hide_eligibility, resolve_hide
from dnd_board_game.hardware.board_panel import panel_position
from dnd_board_game.rules import RollMode
from dnd_board_game.rules.runes import spend_runes
from dnd_board_game.rules.shared_mana import sync_runes
from dnd_board_game.ui.board_panel import option_panel_payload
from dnd_board_game.world import Coordinate
from tests.unit.test_rune_combat_actions import playable, pay


def hidden_mira(tmp_path: Path):
    game, ally_id, enemy_id = playable(tmp_path, 'mira', ('Hak', 'Rozwidlenie', 'Błysk', 'Klucz', 'Kielich'))
    state = game.combat_state
    actor = current_actor(state)
    enemy = next(a for a in state.actors if str(a.id) == enemy_id)
    second = next(a for a in state.actors if a.faction == enemy.faction and a.id != enemy.id)
    game.combat_state = replace_actor(state, replace(second, position=Coordinate(actor.position.col, actor.position.row-1)))
    game.combat_state = replace(game.combat_state,
        hidden_states=(HiddenState('mira', 18, (enemy_id,)),))
    return game, enemy_id, str(second.id)


@pytest.mark.parametrize('flanked', [False, True])
def test_blade_uses_rapier_and_only_targets_an_unaware_observer(tmp_path: Path, flanked: bool) -> None:
    game, enemy_id, visible_id = hidden_mira(tmp_path)
    target = next(a for a in game.combat_state.actors if str(a.id) == enemy_id)
    if flanked:
        ally = next(a for a in game.combat_state.actors if str(a.id) == 'garran')
        game.combat_state = replace_actor(game.combat_state,
            replace(ally, position=Coordinate(target.position.col-1, target.position.row)))
    game.use_combat_class_feature('blade_mistress')
    actor = current_actor(game.combat_state)
    source = next(s for s in game._attack_sources_for_actor(actor) if s.id == 'blade_mistress')
    assert source.source_item_id == 'rapier'
    targets = legal_attack_targets(game._active_encounter().board, actor, game.combat_state.actors,
                                   source, game.combat_state.hidden_states)
    assert {str(t.id) for t in targets} == {enemy_id}
    visible = next(a for a in game.combat_state.actors if str(a.id) == visible_id)
    with pytest.raises(ValueError):
        game.select_player_attack_target_at_position(visible.position)
    target = next(a for a in game.combat_state.actors if str(a.id) == enemy_id)
    game.select_player_attack_target_at_position(target.position)
    game.confirm_player_attack_target()
    pay(game)
    assert game.combat_state.shared_mana.runes.discard == ('Hak',)
    game.submit_player_attack_roll(natural_roll=15, natural_roll_2=15)
    assert not game.pending_player_attack.sneak_attack
    assert bool(game.pending_player_attack.flanking_ally_ids) == flanked
    assert not game.combat_state.hidden_states
    totals = {c.id:2 for c in source.damage_components}
    if flanked:
        totals['rune_blade_flank'] = 2
    hp = target.hp
    game.submit_player_damage_roll(component_totals=totals)
    after = next(a for a in game.combat_state.actors if str(a.id) == enemy_id)
    assert hp-after.hp == sum(totals.values())
    assert game.pending_player_attack is None


def test_blade_flank_adds_one_die_and_cannot_double_count_shadow_attack(tmp_path: Path) -> None:
    game, enemy_id, _ = hidden_mira(tmp_path)
    game.use_combat_class_feature('blade_mistress')
    state = game.combat_state
    actor = current_actor(state)
    source = next(s for s in game._attack_sources_for_actor(actor) if s.id == 'blade_mistress')
    assert [(c.id, c.dice.count, c.dice.sides) for c in source.damage_components if c.id == 'rune_blade_mistress'] == [('rune_blade_mistress', 1, 6)]
    flank = AttackPositioning(flanking_ally_ids=('garran',))
    flanked = attack_source_with_positioning(source, flank)
    assert sum(c.dice.count for c in flanked.damage_components if c.id.startswith('rune_blade')) == 2
    again = attack_source_with_positioning(flanked, flank)
    assert again.damage_components == flanked.damage_components
    plain = attack_source_with_positioning(again, AttackPositioning())
    assert not any(c.id == 'rune_blade_flank' for c in plain.damage_components)
    mana = replace(state.shared_mana, pending_ability='blade_mistress', pending_boosts=(('damage', 1),))
    boosted = boost_attack(flanked, mana)
    assert sum(c.dice.count for c in boosted.damage_components if c.id in {'rune_blade_mistress','rune_blade_flank','shared_boost'}) == 3
    target = next(a for a in state.actors if str(a.id) == enemy_id)
    assert not plan_sneak_attack(state=state, active_effects=game.active_combat_effects,
        attacker=actor, target=target, source=flanked, roll_mode=RollMode.ADVANTAGE).eligible
    # Being on the flank alone cannot unlock this attack.
    assert not legal_attack_targets(game._active_encounter().board, actor, state.actors, source, ())


def test_fork_rune_ends_hiding_for_free_even_after_spending_special(tmp_path: Path) -> None:
    game, _, _ = hidden_mira(tmp_path)
    state = game.combat_state
    pool = spend_runes(state.shared_mana.runes, 'mira', state.shared_mana.runes.hand('mira'))
    game.combat_state = replace(state, shared_mana=sync_runes(state.shared_mana, pool),
                               turn_action=replace(state.turn_action, rune_special_used=True,
                                   shared_bonus_actions_used=1, bonus_action_use=ActionUse.ACTION_USED))
    options = game._combat_turn_action_options()
    fork = [o for o in options if option_panel_payload('mira', o)['panel_slot'] == 5]
    assert len(fork) == 1 and fork[0].id == 'basic:end-hide'
    assert game._combat_turn_option_unavailable_reason(fork[0]) is None
    before = game.combat_state
    assert panel_position(5) in game._current_board_scan_target().positions
    game._handle_board_position(panel_position(5))
    assert game.combat_state.hidden_states == before.hidden_states
    assert panel_position(28) in game._current_board_scan_target().positions
    event = game._handle_board_position(panel_position(28))
    assert event['panel_event']['slot'] == 28
    game.confirm_combat_turn_action()  # Browser dispatches the board's ✓ event.
    assert not game.combat_state.hidden_states
    assert game.combat_state.shared_mana.runes == before.shared_mana.runes
    assert game.combat_state.turn_action == before.turn_action


def test_mira_can_hide_in_the_open_but_roll_is_per_observer(tmp_path: Path) -> None:
    game, enemy_id, other_id = hidden_mira(tmp_path)
    actor = current_actor(game.combat_state)
    board = game._active_encounter().board
    assert not hide_eligibility(board, actor, game.combat_state.actors).allowed
    actor = replace(actor, position=Coordinate(1, 1))
    enemies = tuple(replace(a, position=Coordinate(5+i, 1)) for i, a in enumerate(game.combat_state.actors)
                    if str(a.id) in {enemy_id, other_id})
    assert hide_eligibility(board, actor, (actor, *enemies)).allowed
    result = resolve_hide((), actor, enemies, 15, observer_perception_totals={enemy_id:10, other_id:20})
    assert result.hidden_state.hidden_from_actor_ids == (enemy_id,)
    assert result.detected_by_actor_ids == (other_id,)
