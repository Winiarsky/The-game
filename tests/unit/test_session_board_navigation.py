"""Real HTTP routes and board adapter preserve rules during read-only navigation."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from dnd_board_game.hardware.board_panel import panel_position
from dnd_board_game.application.reputation import read as read_reputation
from dnd_board_game.ui import confrontation
from dnd_board_game.ui.routes import create_app
from tests.unit.test_mission_zero import session as mission_session
from tests.unit.test_progress_confrontation_runtime import start, attempt, command
from tests.unit.test_initiative_panel import Board
from tests.unit.test_launcher_board import menu


def ready_conversation(tmp_path: Path) -> tuple[Any, Board, Any]:
    session = mission_session(tmp_path)
    start(session)
    attempt(session, 10)
    assert confrontation.payload(session)['phase'] == 'summary'
    board = Board()
    session.attach_board_connection(board, backend='simulator')
    client = create_app(session, character_dir=tmp_path/'characters').test_client()
    return session, board, client


def game_snapshot(session: Any) -> Any:
    return deepcopy((session.state, session.combat_state, confrontation.read_store(session)))


def panel(client: Any, session: Any, context: str, *, revision: str | None = None) -> Any:
    return client.post('/api/board/panel', json={
        'context': context, 'exclusive': True, 'slots': [26, 27, 28, 29],
        'revision': revision if revision is not None else session._board_selection_payload()['revision'],
    })


def press(client: Any, board: Board, selection: dict[str, Any], slot: int) -> Any:
    board.selected = panel_position(slot).as_tuple()
    return client.post('/api/board/scan', json={'revision': selection['revision'], 'automatic': True})


@pytest.mark.parametrize('slot', [26, 27, 28])
def test_launcher_function_keys_emit_one_event_without_changing_game(tmp_path: Path, slot: int) -> None:
    session, board, client = menu(tmp_path)
    before = deepcopy((session.state, session.combat_state))
    response = client.post('/api/board/navigation', json={
        'token': session.launcher_navigation.token, 'slots': [6, 7, 8],
        'controls': [26, 27, 28], 'focused': 7, 'selected': [6], 'back': True,
    })
    assert response.status_code == 200, response.json
    selection = response.json['board_selection']
    assert set(map(tuple, selection['legal_positions'])) == {
        panel_position(index).as_tuple() for index in (6, 7, 8, 26, 27, 28, 29)
    }
    assert set(board.leds) == set(map(tuple, selection['legal_positions']))
    result = press(client, board, selection, slot)
    assert result.status_code == 200, result.json
    assert result.json['navigation_event'] == {'token': session.launcher_navigation.token, 'slot': slot}
    assert not result.json['board_selection']['auto_arm']
    assert not board.leds
    assert (session.state, session.combat_state) == before
    repeated = press(client, board, selection, slot)
    assert repeated.status_code == 200
    assert 'navigation_event' not in repeated.json and board.scans == 1


@pytest.mark.parametrize('extra', [
    {'controls': [26, 26]}, {'controls': [True]}, {'controls': [29]},
    {'controls': [6]}, {'focused': 9}, {'focused': True},
])
def test_launcher_rejects_invalid_controls_and_focus_without_changing_mask(
    tmp_path: Path, extra: dict[str, Any],
) -> None:
    session, _, client = menu(tmp_path)
    before = session.launcher_navigation
    result = client.post('/api/board/navigation', json={
        'token': before.token, 'slots': [6, 7], 'controls': [26, 27, 28], 'focused': 6, **extra,
    })
    assert result.status_code == 409
    assert session.launcher_navigation == before


@pytest.mark.parametrize('prefix', ['session-menu', 'session-journal', 'session-help'])
def test_readonly_panels_own_only_function_keys_and_release_restores_game(
    tmp_path: Path, prefix: str,
) -> None:
    session, board, client = ready_conversation(tmp_path)
    before = game_snapshot(session)
    original_positions = session._board_selection_payload()['legal_positions']
    context = prefix + ':test-document'
    response = panel(client, session, context)
    assert response.status_code == 200, response.json
    selection = response.json['board_selection']
    expected = {panel_position(index).as_tuple() for index in (26, 27, 28, 29)}
    assert set(map(tuple, selection['legal_positions'])) == expected
    assert set(board.leds) == expected
    for slot in (26, 27, 28, 29):
        response = press(client, board, selection, slot)
        assert response.status_code == 200, response.json
        assert response.json['panel_event'] == {'context': context, 'slot': slot}
        selection = response.json['board_selection']
        assert game_snapshot(session) == before
    # The browser chooses when to close; hardware accept/back never resolves rules.
    response = client.post('/api/board/panel', json={'release_context': context})
    assert response.status_code == 200
    assert response.json['board_selection']['legal_positions'] == original_positions
    assert session.board_panel_context is None
    assert game_snapshot(session) == before


@pytest.mark.parametrize(('slot', 'option'), [(5, 'plus_one'), (6, 'plus_five'), (7, 'extra_die')])
def test_reputation_preview_survives_readonly_menu_without_spending(
    tmp_path: Path, slot: int, option: str,
) -> None:
    session, board, client = ready_conversation(tmp_path)
    payload = confrontation.payload(session)
    assert any(choice['slot'] == slot and choice['action'] == 'reputation'
               for choice in payload['board_choices'])
    response = press(client, board, session._board_selection_payload(), slot)
    assert response.status_code == 200, response.json
    assert confrontation.payload(session)['reputation']['selected'] == option
    assert read_reputation(session.state.flags).points == 20
    before = game_snapshot(session)
    original = session._board_selection_payload()
    context = 'session-menu:reputation-preview'
    response = panel(client, session, context)
    assert response.status_code == 200, response.json
    selection = response.json['board_selection']
    assert set(map(tuple, selection['legal_positions'])) == {
        panel_position(index).as_tuple() for index in (26, 27, 28, 29)
    }
    # Gameplay input cannot leak through the information panel to change payment.
    blocked = client.post('/api/board/select', json={'col': 19, 'row': 29-slot})
    assert blocked.status_code == 400
    response = press(client, board, selection, 28)
    assert response.status_code == 200 and response.json['panel_event']['context'] == context
    closed = client.post('/api/board/panel', json={'release_context': context})
    assert closed.json['board_selection']['legal_positions'] == original['legal_positions']
    assert game_snapshot(session) == before


def test_stale_registration_scan_and_release_do_not_replace_new_panel(tmp_path: Path) -> None:
    session, board, client = ready_conversation(tmp_path)
    before = game_snapshot(session)
    original = session._board_selection_payload()
    first = panel(client, session, 'session-journal:first').json['board_selection']
    second = panel(client, session, 'session-help:second').json['board_selection']
    delayed = panel(client, session, 'session-menu:old', revision=original['revision'])
    assert delayed.status_code == 200
    assert delayed.json['board_selection']['revision'] == second['revision']
    released = client.post('/api/board/panel', json={'release_context': 'session-journal:first'})
    assert released.json['board_selection']['revision'] == second['revision']
    assert session.board_panel_context[0] == 'session-help:second'
    stale = press(client, board, first, 28)
    assert stale.status_code == 200
    assert 'panel_event' not in stale.json and board.scans == 0
    assert game_snapshot(session) == before
    current = press(client, board, second, 27)
    assert current.status_code == 200 and current.json['panel_event']['slot'] == 27


@pytest.mark.parametrize('detail', ['bonus', 'effects'])
def test_paid_additional_die_rejects_obsolete_mana_detail_contexts(
    tmp_path: Path, detail: str,
) -> None:
    session, _, client = ready_conversation(tmp_path)
    ready_revision = confrontation.payload(session)['revision']
    command(session, 'reputation', option='extra_die')
    command(session, 'confirm')
    payload = confrontation.payload(session)
    assert payload['phase'] == 'extra_check'
    assert read_reputation(session.state.flags).points == 15
    assert not any(choice['action'] == 'inspect' for choice in payload['board_choices'])
    before = game_snapshot(session)
    selection = session._board_selection_payload()
    for revision in (ready_revision, payload['revision']):
        response = panel(client, session, f'confrontation-detail:{revision}:{detail}')
        assert response.status_code == 400, response.json
        assert session.board_panel_context is None
        assert session._board_selection_payload()['legal_positions'] == selection['legal_positions']
        assert game_snapshot(session) == before
