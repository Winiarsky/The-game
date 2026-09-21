"""Mission initiative owns its controls; mana runes retain their color identity."""
from dataclasses import replace
from pathlib import Path

import pytest

from dnd_board_game.application.party_ethos import apply_choice
from dnd_board_game.hardware.board_panel import panel_position
from dnd_board_game.rules.party_ethos import PartyEthos
from dnd_board_game.rules.pooled_mana import new_mana
from dnd_board_game.ui import pooled_mana
from dnd_board_game.ui.exploration_app import ExplorationUiSession, create_app
from dnd_board_game.ui.exploration_mana_board import MANA_LED_COLORS
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
        assert board.leds[(19,3)] == (255,0,0)
        assert board.leds[(19,2)] == (0,255,0)
        assert board.leds[(19,1)] == (0,80,255)
        rejected = client.post('/api/board/panel', json={'context':'decision:late','slots':[28,29], 'exclusive':False})
        assert rejected.status_code == 400
        press(27);assert game.encounter_initiative_flow.roll_panel.values == (11,)
        press(26);assert game.encounter_initiative_flow.roll_panel.values == (10,)
        review = press(28)
        assert review['encounter_initiative']['panel']['review']
        assert set(map(tuple, review['board_selection']['legal_positions'])) == {(19,1),(19,0)}
        press(29);press(27);press(28);press(28)
    assert game.combat_state is not None
    assert game.combat_state.shared_mana.pooled.phase == 'setup'
    assert [entry.roll.natural_roll for entry in game.encounter_initiative_flow.entries[:3]] == [11]*3


@pytest.mark.parametrize('colors', [('C','N'), ('B','Z'), ('F','F')])
def test_combat_mana_reporting_and_offer_have_matching_leds(tmp_path: Path, colors: tuple[str,str]) -> None:
    game = prepared_mission(tmp_path)
    game.start_encounter_initiative()
    while game.encounter_initiative_flow.current_prompt is not None:
        game.submit_encounter_initiative_roll(20)
    board = Board();game.attach_board_connection(board, backend='simulator')
    game._handle_board_position(panel_position(28))
    for slot, color in enumerate(MANA_LED_COLORS, start=6):
        assert board.leds[panel_position(slot).as_tuple()] == tuple(round(v*.65) for v in MANA_LED_COLORS[color])
    for color in colors:
        choice = next(c for c in pooled_mana.view(game)['choices'] if c.get('color')==color)
        game._handle_board_position(panel_position(choice['slot']))
    for slot,color in zip((24,25),colors):
        assert board.leds[panel_position(slot).as_tuple()] == tuple(round(v*.65) for v in MANA_LED_COLORS[color])


def test_deck_notice_survives_save_until_physical_confirmation(tmp_path: Path) -> None:
    game = prepared_mission(tmp_path, deviation=1)
    game.start_encounter_initiative()
    while game.encounter_initiative_flow.current_prompt is not None:
        game.submit_encounter_initiative_roll(10)
    before = pooled_mana.view(game)['deck_preparation']
    assert before['removed'] == {'B':1, 'N':1} and before['total'] == 28
    assert [c['command'] for c in pooled_mana.view(game)['choices']] == ['pool_shuffle']
    game.save_snapshot();game.load_snapshot()
    assert pooled_mana.view(game)['deck_preparation'] == before
    pooled_mana.select_position(game, panel_position(28))
    assert pooled_mana.view(game)['deck_preparation'] is None
    assert pooled_mana.view(game)['phase'] == 'reveal'


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
