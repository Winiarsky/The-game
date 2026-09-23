"""Physical fields and current masks drive the playable rune combat flow."""
from collections import Counter
from dataclasses import replace
from pathlib import Path

import pytest

from dnd_board_game.combat import current_actor, replace_actor
from dnd_board_game.hardware.board_panel import panel_position
from dnd_board_game.rules.runes import RESOURCE_RUNES, new_runes
from dnd_board_game.rules.shared_mana import sync_runes
from dnd_board_game.ui import runes
from dnd_board_game.ui.exploration_app import ExplorationUiSession
from dnd_board_game.ui.board_panel_symbols import rune_slot
from dnd_board_game.ui.routes import create_app
from dnd_board_game.world import Coordinate
from tests.unit.test_initiative_panel import Board
from tests.unit.test_mission_zero import session, start_battle


def rune_game(tmp_path: Path, count: int = 3):
    game = session(tmp_path, count)
    game.encounter_rng.seed(0)
    start_battle(game)
    game.configured_board_backend = 'none'
    pool = game.combat_state.shared_mana.runes
    assert pool is not None
    opening = ['Kotwica', 'Kotwica', 'Błysk', 'Wieża', 'Kielich']
    deck = [rune for _ in pool.heroes for rune in RESOURCE_RUNES]
    for rune in opening:
        deck.remove(rune)
    pool = new_runes(pool.heroes, (*opening, *deck))
    game.combat_state = replace(game.combat_state, shared_mana=sync_runes(game.combat_state.shared_mana, pool))
    game.state_payload()
    return game


def allocate(game) -> None:
    while game.combat_state.shared_mana.runes.phase == 'allocation':
        pool = game.combat_state.shared_mana.runes
        if pool.actor == 'garran' and pool.offer and len(pool.hand('garran')) < 7:
            runes.select_position(game, panel_position(rune_slot(pool.offer[0])))
        else:
            runes.select_position(game, panel_position(28))


def test_new_resource_symbols_light_and_transfer_the_matching_rune(tmp_path: Path) -> None:
    game = rune_game(tmp_path)
    for rune in ('Rozwidlenie', 'Trójząb', 'Romb', 'Hak', 'Schody', 'Grot'):
        state = game.combat_state
        heroes = state.shared_mana.runes.heroes
        opening = (rune, rune, 'Wieża', 'Błysk', 'Klucz')
        deck = [r for _ in heroes for r in RESOURCE_RUNES]
        for r in opening:
            deck.remove(r)
        pool = new_runes(heroes, (*opening, *deck))
        game.combat_state = replace(state, shared_mana=sync_runes(state.shared_mana, pool))
        position = panel_position(rune_slot(rune))
        target = runes.scan_target(game)
        assert position in target.positions
        assert any(position in frame.positions for frame in target.feedback.frames)
        runes.select_position(game, position)
        assert game.combat_state.shared_mana.runes.hand(pool.actor) == (rune,)
        assert position in runes.scan_target(game).positions
        runes.select_position(game, position)
        assert game.combat_state.shared_mana.runes.hand(pool.actor) == (rune, rune)
        assert position not in runes.scan_target(game).positions


def enemy_turn_game(tmp_path: Path) -> ExplorationUiSession:
    game = rune_game(tmp_path)
    allocate(game)
    state = game.combat_state
    index = next(i for i, entry in enumerate(state.initiative_order.entries)
                 if entry.actor.faction.value == 'enemy')
    game.combat_state = replace(state, initiative_order=replace(state.initiative_order, current_index=index))
    return game


def test_enemy_turn_start_lights_accept_and_physical_scan_emits_confirmation(tmp_path: Path) -> None:
    from dnd_board_game.hardware.led_palette import LedColor
    game = enemy_turn_game(tmp_path)
    board = Board()
    game.attach_board_connection(board, backend='simulator')
    game._sync_board_leds()
    target = game._current_board_scan_target()
    assert panel_position(28) in target.positions
    assert board.leds[panel_position(28).as_tuple()] == LedColor.PANEL_ACCEPT
    assert panel_position(23) not in target.positions
    assert panel_position(23).as_tuple() not in board.leds
    before = game.combat_state
    board.selected = panel_position(28).as_tuple()
    result = game.scan_board_selection(automatic=True)
    assert result['panel_event'] == {'slot':28, 'context':None}
    assert game.combat_state == before  # The browser dispatches the enemy action.


@pytest.mark.parametrize('step', ['pending_enemy_turn_intent', 'pending_enemy_turn_ack_result'])
def test_enemy_confirmation_yields_to_board_targets_and_interrupts(tmp_path: Path, step: str) -> None:
    from dnd_board_game.ui.combat_board_controls import preview_confirmation
    game = enemy_turn_game(tmp_path)
    setattr(game, step, object())
    assert preview_confirmation(game) is True
    for interrupt in ('pending_enemy_turn_result', 'pending_enemy_opportunity_attack',
                      'pending_reaction_window', 'pending_enemy_saving_throw', 'pending_concentration_check'):
        setattr(game, interrupt, object())
        assert preview_confirmation(game) is None
        setattr(game, interrupt, None)


def test_physical_allocation_counts_duplicates_undo_and_stale_click(tmp_path: Path) -> None:
    game = rune_game(tmp_path)
    board = Board()
    game.attach_board_connection(board, backend='simulator')
    game._sync_board_leds()
    client = create_app(game).test_client()

    def press(slot: int):
        board.selected = panel_position(slot).as_tuple()
        result = client.post('/api/board/scan', json={'revision': game._board_selection_payload()['revision'], 'automatic': True})
        assert result.status_code == 200, result.json
        return result.json

    slot = rune_slot('Kotwica')
    old = game._board_selection_payload()['revision']
    assert panel_position(slot).as_tuple() in board.leds
    press(slot)
    assert game.combat_state.shared_mana.runes.hand('garran') == ('Kotwica',)
    assert panel_position(slot).as_tuple() in board.leds
    count = board.scans
    client.post('/api/board/scan', json={'revision': old, 'automatic': True})
    assert board.scans == count
    assert game.combat_state.shared_mana.runes.hand('garran') == ('Kotwica',)
    press(slot)
    assert panel_position(slot).as_tuple() not in board.leds
    press(29)
    assert panel_position(slot).as_tuple() in board.leds
    assert game.combat_state.shared_mana.runes.hand('garran') == ('Kotwica',)
    press(28)
    assert game.combat_state.shared_mana.runes.actor == 'brakka'
    assert panel_position(29).as_tuple() not in board.leds
    press(28)
    press(28)
    assert game.combat_state.shared_mana.runes.actor == 'garran'
    while game.combat_state.shared_mana.runes.phase == 'allocation':
        pool = game.combat_state.shared_mana.runes
        press(rune_slot(pool.offer[0]) if pool.offer else 28)
    assert game.combat_state.shared_mana.runes.phase == 'ready'
    assert not any(p.col != 19 for p in game._current_board_scan_target().positions)
    assert not {panel_position(4), panel_position(25)} & set(game._current_board_scan_target().positions)


def test_no_legal_target_extinguishes_attack_and_movement_requires_field(tmp_path: Path) -> None:
    game = rune_game(tmp_path)
    allocate(game)
    board = Board()
    game.attach_board_connection(board, backend='simulator')
    assert panel_position(1) not in game._current_board_scan_target().positions
    assert panel_position(1).as_tuple() not in board.leds
    before = game.combat_state
    game._handle_board_position(panel_position(0))
    target = game._current_board_scan_target()
    assert panel_position(28) not in target.positions
    assert panel_position(28).as_tuple() not in board.leds
    assert panel_position(24) in target.positions
    actor = current_actor(game.combat_state)
    field = next(p for p in target.positions if p.col != 19 and p != actor.position)
    game.select_board_position(field)
    assert game.combat_state == before
    assert panel_position(28) in game._current_board_scan_target().positions
    assert panel_position(28).as_tuple() in board.leds
    game.confirm_combat_turn_action()
    assert current_actor(game.combat_state).position == field
    assert game.combat_state.shared_mana.runes == before.shared_mana.runes


def test_hero_information_roundtrip_preserves_target_and_rejects_old_mask(tmp_path: Path) -> None:
    game = rune_game(tmp_path)
    allocate(game)
    actor = current_actor(game.combat_state)
    enemy = next(a for a in game.combat_state.actors if str(a.id) == 'borut')
    enemy = replace(enemy, position=Coordinate(actor.position.col - 1, actor.position.row))
    game.combat_state = replace_actor(game.combat_state, enemy)
    game.state_payload()
    game._handle_board_position(panel_position(1))
    assert panel_position(28) not in game._current_board_scan_target().positions
    game.select_board_position(enemy.position)
    assert game.pending_player_attack.target_id == enemy.id
    assert panel_position(28) in game._current_board_scan_target().positions
    before = (game.combat_state, game.pending_player_attack, game.combat_turn_preview_option_id)
    revision = game._board_selection_payload()['revision']
    event = game._handle_board_position(panel_position(24))
    assert event['panel_event']['slot'] == 24
    game.configure_board_panel('combat-inspect:1:garran:garran', [24, 26, 27, 29], True)
    assert set(game._current_board_scan_target().positions) == {panel_position(s) for s in (24, 26, 27, 29)}
    game.configure_board_panel('dice:obsolete', [26, 27, 28], True, expected_revision=revision)
    assert game.board_panel_context[0] == 'combat-inspect:1:garran:garran'
    game.release_board_panel('combat-inspect:1:garran:garran')
    assert (game.combat_state, game.pending_player_attack, game.combat_turn_preview_option_id) == before
    assert any(enemy.position in frame.positions for frame in game._current_board_scan_target().feedback.frames)
    assert panel_position(28) in game._current_board_scan_target().positions


def test_save_reload_keeps_opening_hand_and_finite_deck(tmp_path: Path) -> None:
    game = rune_game(tmp_path)
    runes.select_position(game, panel_position(rune_slot('Kotwica')))
    before = game.combat_state.shared_mana.runes
    game.save_snapshot()
    game.load_snapshot()
    assert game.combat_state.shared_mana.runes == before
    cards = (*before.deck, *before.offer, *before.discard, *(r for _, hand in before.hands for r in hand))
    assert Counter(cards) == Counter({r: len(before.heroes) for r in RESOURCE_RUNES})


def test_switching_action_clears_old_movement_preview_without_spending(tmp_path: Path) -> None:
    game = rune_game(tmp_path)
    allocate(game)
    actor = current_actor(game.combat_state)
    enemy = next(a for a in game.combat_state.actors if str(a.id) == 'borut')
    enemy = replace(enemy, position=Coordinate(actor.position.col - 1, actor.position.row))
    game.combat_state = replace_actor(game.combat_state, enemy)
    game.state_payload()
    before = game.combat_state
    game._handle_board_position(panel_position(0))
    field = next(p for p in game._current_board_scan_target().positions
                 if p.col != 19 and p != actor.position and p != enemy.position)
    game.select_board_position(field)
    assert game.selected_combat_movement_path is not None
    game._handle_board_position(panel_position(1))
    assert game.selected_combat_movement_path is None
    target = game._current_board_scan_target()
    assert enemy.position in target.positions
    assert field not in target.positions
    assert panel_position(28) not in target.positions
    assert game.combat_state == before
    game.cancel_combat_turn_action_preview()
    assert game.combat_state == before
    assert not any(p.col != 19 for p in game._current_board_scan_target().positions)
