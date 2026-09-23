"""Native initiative and opening rune allocation own the current physical mask."""
from collections import Counter
from dataclasses import replace
from pathlib import Path

import pytest

from dnd_board_game.application.party_ethos import apply_choice
from dnd_board_game.hardware.board_panel import panel_position
from dnd_board_game.hardware.led_palette import LedColor
from dnd_board_game.rules.party_ethos import PartyEthos
from dnd_board_game.rules.pooled_mana import new_mana
from dnd_board_game.rules.runes import RESOURCE_RUNES
from dnd_board_game.ui import runes
from dnd_board_game.ui.exploration_app import ExplorationUiSession, create_app
from dnd_board_game.ui.party_ethos import deck_preparation
from tests.unit.test_initiative_panel import Board
from tests.unit.test_mission_zero import session, stage, send


def prepared_mission(tmp_path: Path, deviation: int = 0) -> ExplorationUiSession:
    game = session(tmp_path)
    for index in range(abs(deviation)):
        game.state = replace(game.state, flags=apply_choice(
            game.state.flags, f'test:{index}', 'ruthlessness' if deviation > 0 else 'solidarity'))
    stage(game, 'arrival')
    send(game, 'battle')
    while not game.encounter_setup_flow.completed:
        if game.encounter_setup_flow.is_player_start_step:
            game.assign_encounter_player_start_position(game.encounter_setup_flow.remaining_player_start_positions()[0])
        else:
            game.confirm_encounter_setup_step()
    return game


def test_mission_native_initiative_overrides_old_browser_context(tmp_path: Path) -> None:
    game = prepared_mission(tmp_path)
    board = Board()
    game.attach_board_connection(board, backend='simulator')
    client = create_app(game).test_client()
    game.board_panel_context = ('decision:old', (28,29), False)

    def press(slot: int) -> dict:
        board.selected = panel_position(slot).as_tuple()
        response = client.post('/api/board/scan', json={
            'automatic': True, 'revision': game._board_selection_payload()['revision']})
        assert response.status_code == 200, response.json
        assert 'panel_event' not in response.json
        return response.json

    assert game._current_board_scan_target().positions == (panel_position(28),)
    press(28)
    assert game.board_panel_context is None
    for index in range(3):
        view = game.state_payload()
        assert view['encounter_initiative']['current_prompt_index'] == index
        assert set(map(tuple, view['board_selection']['legal_positions'])) == {(19,3),(19,2),(19,1)}
        assert board.leds[(19,3)] == (0,255,0)
        assert board.leds[(19,2)] == (255,0,0)
        assert board.leds[(19,1)] == (0,80,255)
        rejected = client.post('/api/board/panel', json={'context':'decision:late','slots':[28,29], 'exclusive':False})
        assert rejected.status_code == 400
        press(26);assert game.encounter_initiative_flow.roll_panel.values == (11,)
        press(27);assert game.encounter_initiative_flow.roll_panel.values == (10,)
        review = press(28)
        assert review['encounter_initiative']['panel']['review']
        assert set(map(tuple, review['board_selection']['legal_positions'])) == {(19,1),(19,0)}
        press(29);press(26);press(28);press(28)
    assert game.combat_state is not None
    assert game.combat_state.shared_mana.runes.phase == 'allocation'
    assert game.combat_state.shared_mana.pooled is None
    assert [entry.roll.natural_roll for entry in game.encounter_initiative_flow.entries[:3]] == [11]*3


@pytest.mark.parametrize('seed', [0, 1, 2])
def test_opening_offer_lights_available_runes_without_information_or_map(tmp_path: Path, seed: int) -> None:
    game = prepared_mission(tmp_path)
    game.encounter_rng.seed(seed)
    game.start_encounter_initiative()
    while game.encounter_initiative_flow.current_prompt is not None:
        game.submit_encounter_initiative_roll(20)
    board = Board();game.attach_board_connection(board, backend='simulator')
    game._sync_board_leds()
    offer = runes.view(game)
    assert sum(item['count'] for item in offer['offer']) == 5
    slots = {item['slot'] for item in offer['offer']}
    assert set(game._current_board_scan_target().positions) == {panel_position(s) for s in (*slots, 28)}
    available_color = tuple(round(component * .65) for component in LedColor.PANEL_RUNE)
    assert all(board.leds[panel_position(s).as_tuple()] == available_color for s in slots)
    assert panel_position(24).as_tuple() not in board.leds
    game._handle_board_position(panel_position(next(iter(slots))))
    assert panel_position(29).as_tuple() in board.leds


def test_rune_allocation_save_retains_offer_without_old_mana_preparation(tmp_path: Path) -> None:
    game = prepared_mission(tmp_path, deviation=1)
    game.start_encounter_initiative()
    while game.encounter_initiative_flow.current_prompt is not None:
        game.submit_encounter_initiative_roll(10)
    before = game.combat_state.shared_mana.runes
    assert len(before.offer) == 5 and len(before.deck) == 25
    assert Counter((*before.offer, *before.deck)) == Counter({r: 3 for r in RESOURCE_RUNES})
    game.save_snapshot();game.load_snapshot()
    assert game.combat_state.shared_mana.runes == before
    game._handle_board_position(panel_position(28))
    assert game.combat_state.shared_mana.runes.actor == before.heroes[1]
    assert game.combat_state.shared_mana.runes.offer == before.offer


@pytest.mark.parametrize('position', range(7))
def test_deck_notice_describes_actual_composition_only_when_deviated(position: int) -> None:
    pool = new_mana(('brakka','garran','nimra'), excluded=PartyEthos(position).excluded)
    notice = deck_preparation(pool)
    if position == 3:
        assert notice is None
    else:
        assert notice['label'] == PartyEthos(position).label
        assert notice['steps'] == abs(position-3)
        assert notice['total'] == 30-2*abs(position-3)
        assert sum(notice['composition'].values()) == notice['total']
        assert sum(notice['removed'].values()) + notice['total'] == 30
