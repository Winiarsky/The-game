"""Launcher and tutorial rune masks must never leak across screen changes."""
from pathlib import Path
import threading

import pytest

from dnd_board_game.application.recruitment_arena import HERO_ORDER
from dnd_board_game.hardware.board_panel import panel_position
from dnd_board_game.ui import launcher_board
from dnd_board_game.ui.routes import create_app
from tests.unit.test_initiative_panel import Board
from tests.unit.test_launcher_ui import _session
from tests.unit.test_recruitment_arena import arena


def menu(tmp_path: Path):
    s = _session(tmp_path)
    board = Board()
    s.attach_board_connection(board, backend='simulator')
    client = create_app(s, character_dir=tmp_path/'characters').test_client()
    client.get('/')
    return s, board, client


def arm(s, client, slots=(6, 7, 8, 9), back=False):
    response = client.post('/api/board/navigation', json={
        'token': s.launcher_navigation.token, 'slots': list(slots), 'back': back,
    })
    assert response.status_code == 200, response.json
    return response.json['board_selection']


def test_menu_choice_is_immediate_one_shot_and_does_not_change_game(tmp_path: Path) -> None:
    s, board, client = menu(tmp_path)
    before = s.state
    selection = arm(s, client)
    assert selection['auto_arm'] and selection['confirmation_policy'] == 'immediate'
    assert set(board.leds) == {(19, 23), (19, 22), (19, 21), (19, 20)}
    assert (19, 1) not in board.leds
    board.selected = (19, 21)
    result = client.post('/api/board/scan', json={'revision': selection['revision'], 'automatic': True})
    assert result.json['navigation_event'] == {'token': s.launcher_navigation.token, 'slot': 8}
    assert s.state == before
    assert not result.json['board_selection']['auto_arm']
    assert not board.leds
    assert client.post('/api/board/select', json={'col':19, 'row':21}).status_code == 400


def test_new_page_rejects_old_registration_release_and_scan(tmp_path: Path) -> None:
    s, board, client = menu(tmp_path)
    old_token = s.launcher_navigation.token
    old = arm(s, client)
    client.get('/load-game')
    new = arm(s, client, (6,), back=True)
    assert old['revision'] != new['revision']
    assert client.post('/api/board/navigation', json={'token':old_token, 'slots':[9]}).status_code == 409
    client.post('/api/board/navigation/release', json={'token':old_token})
    assert s._board_selection_payload()['revision'] == new['revision']
    result = client.post('/api/board/scan', json={'revision':old['revision'], 'automatic':True})
    assert 'navigation_event' not in result.json and board.scans == 0
    board.selected = (19, 0)
    result = client.post('/api/board/scan', json={'revision':new['revision'], 'automatic':True})
    assert result.json['navigation_event']['slot'] == 29


@pytest.mark.parametrize('slots', [[28], [29], [5], [26], [6, 6], [True], ['6']])
def test_menu_rejects_nonrunes_and_duplicates(tmp_path: Path, slots: list[object]) -> None:
    s, _, client = menu(tmp_path)
    token = s.launcher_navigation.token
    response = client.post('/api/board/navigation', json={'token':token, 'slots':slots})
    assert response.status_code == 409
    assert not s.launcher_navigation.active_slots


@pytest.mark.parametrize('hero', HERO_ORDER)
def test_tutorial_hero_rune_starts_setup_without_confirm_and_return_restores_roster(tmp_path: Path, hero: str) -> None:
    from dnd_board_game.ui.training_walkthrough import leave
    s = arena(tmp_path)
    board = Board()
    s.attach_board_connection(board, backend='simulator')
    state = s.state_payload()
    assert state['board_selection']['mode'] == 'training_roster'
    assert state['board_selection']['auto_arm']
    assert len(state['board_selection']['legal_positions']) == 8
    assert [19, 1] not in state['board_selection']['legal_positions']
    heroes = state['training_arena']['heroes']
    assert [h['panel_slot'] for h in heroes] == list(range(6, 13))
    board.selected = panel_position(6 + HERO_ORDER.index(hero)).as_tuple()
    result = s.scan_board_selection(expected_revision=state['board_selection']['revision'], automatic=True)
    assert result['training_arena']['current_hero_id'] == hero
    assert result['training_arena']['tutorial']['phase'] == 'introduction'
    assert s.encounter_setup_flow is not None
    leave(s)
    assert s._board_selection_payload()['mode'] == 'training_roster'
    assert {panel_position(slot).as_tuple() for slot in (*range(6, 13), 29)} == set(board.leds)
    board.selected = (19, 0)
    assert s.scan_board_selection(automatic=True) == {'navigate':'/'}
    assert not s._current_board_scan_target().positions


def test_switch_to_arena_reuses_connection_and_releases_old_page(tmp_path: Path) -> None:
    s, board, client = menu(tmp_path)
    arm(s, client)
    response = client.post('/training/open')
    assert response.status_code == 302
    client.get('/play')
    assert s.board_adapter.connection is board
    assert s.launcher_navigation is None
    assert s._board_selection_payload()['mode'] == 'training_roster'
    assert len(board.leds) == 8


def test_menu_connects_once_and_retry_replaces_disconnected_adapter(tmp_path: Path, monkeypatch) -> None:
    from dnd_board_game.hardware.board_session import BoardSessionAdapter
    s = _session(tmp_path)
    client = create_app(s, character_dir=tmp_path/'characters').test_client()
    client.get('/')
    connections = []
    class Connection(Board):
        connected = True
        closed = False
        def close(self):
            self.closed = True
    def connect(**kwargs):
        board = Connection()
        connections.append(board)
        return BoardSessionAdapter(board)
    monkeypatch.setattr(BoardSessionAdapter, 'connect', connect)
    arm(s, client)
    arm(s, client, (6,))
    assert len(connections) == 1
    connections[0].connected = False
    arm(s, client)
    assert connections[0].closed
    assert len(connections) == 2
    assert s._board_selection_payload()['auto_arm']


def test_page_change_cancels_a_waiting_scan_and_discards_old_press(tmp_path: Path) -> None:
    s, _, client = menu(tmp_path)
    waiting, released = threading.Event(), threading.Event()
    class WaitingBoard(Board):
        def scan_board(self, positions, *, timeout_s):
            waiting.set()
            assert released.wait(3)
            return (19, 23)
        def cancel_scan(self):
            released.set()
    board = WaitingBoard()
    s.attach_board_connection(board, backend='simulator')
    selection = arm(s, client)
    result = []
    worker = threading.Thread(target=lambda: result.append(s.scan_board_selection(expected_revision=selection['revision'], automatic=True)))
    worker.start()
    try:
        assert waiting.wait(1)
        client.get('/load-game')
        worker.join(2)
        assert not worker.is_alive()
        assert result and 'navigation_event' not in result[0]
    finally:
        released.set()
        worker.join(2)
