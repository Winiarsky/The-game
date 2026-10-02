"""Placement uses a draft followed by the physical accept button."""
from dataclasses import replace
from pathlib import Path

import pytest

from dnd_board_game.hardware.board_panel import panel_position
from dnd_board_game.hardware.led_palette import LedColor
from dnd_board_game.ui.training_arena import start_training_trial
from dnd_board_game.ui.routes import create_app
from dnd_board_game.world import Coordinate
from tests.unit.test_initiative_panel import Board
from tests.unit.test_recruitment_arena import arena


def setup_session(tmp_path: Path):
    session = arena(tmp_path)
    start_training_trial(session, 'garran', 'basic', 'humanoid')
    board = Board()
    board.selected = (19, 1)
    session.attach_board_connection(board, backend='simulator')
    return session, board


def test_fixed_placement_accepts_on_board_and_rejects_old_scan(tmp_path: Path) -> None:
    session, board = setup_session(tmp_path)
    flow = session.encounter_setup_flow
    session.scan_board_selection(automatic=True)
    assert flow.current_index == 1
    step = flow.current_step
    assert step.label == 'bohater: Garran'
    payload = session.state_payload()
    selection = payload['board_selection']
    assert selection['auto_arm']
    assert {tuple(p) for p in selection['legal_positions']} == {(19, 1), (19, 0)}
    assert board.leds[(19, 1)] == LedColor.PANEL_ACCEPT
    assert board.leds[step.positions[0].as_tuple()] == step.color
    with pytest.raises(ValueError):
        session.select_board_position(step.positions[0])
    session.scan_board_selection(expected_revision=selection['revision'], automatic=True)
    assert flow.current_index == 2
    count = board.scans
    session.scan_board_selection(expected_revision=selection['revision'], automatic=True)
    assert board.scans == count and flow.current_index == 2


def test_choice_is_staged_changeable_and_confirmed_separately(tmp_path: Path) -> None:
    session, board = setup_session(tmp_path)
    flow = session.encounter_setup_flow
    actor = flow.encounter.actors[0]
    other_actor = replace(actor, id=type(actor.id)('second'), name='Drugi')
    flow.encounter = replace(flow.encounter, actors=(actor, other_actor))
    flow.player_start_actor_ids = (str(actor.id), str(other_actor.id))
    a, b, c = Coordinate(7, 8), Coordinate(8, 8), Coordinate(9, 8)
    flow.steps = (replace(flow.steps[1], label='pola startowe bohaterów', positions=(a, b, c)),)
    flow.current_index = 0
    session._sync_board_leds()
    client = create_app(session).test_client()
    assert (19, 1) not in board.leds
    assert client.post('/api/encounter/setup/confirm').status_code == 400
    assert client.post('/api/board/select', json={'col': 19, 'row': 1}).status_code == 400
    assert not flow.player_start_assignments
    board.selected = a.as_tuple()
    session.scan_board_selection(automatic=True)
    assert flow.pending_start_position == a
    assert not flow.player_start_assignments
    assert flow.encounter.actors[0].position == actor.position
    assert board.leds[(19, 1)] == LedColor.PANEL_ACCEPT
    assert board.leds[a.as_tuple()] == LedColor.MOVEMENT_DESTINATION
    session.select_board_position(b)
    assert flow.pending_start_position == b
    assert board.leds[a.as_tuple()] == flow.current_step.color
    before = session.state_payload()['board_selection']['revision']
    board.selected = (19, 1)
    session.scan_board_selection(expected_revision=before, automatic=True)
    assert flow.player_start_assignments == {str(actor.id): b}
    assert flow.encounter.actors[0].position == b
    assert flow.pending_start_position is None
    assert (19, 1) not in board.leds
    assert b.as_tuple() not in board.leds
    with pytest.raises(ValueError):
        session.select_board_position(b)
    session.scan_board_selection(expected_revision=before, automatic=True)
    assert len(flow.player_start_assignments) == 1
    session.select_board_position(c)
    session.select_board_position(panel_position(28))
    assert flow.completed
    assert flow.player_start_assignments[str(other_actor.id)] == c


def test_only_remaining_position_requires_accept_without_extra_selection(tmp_path: Path) -> None:
    session, board = setup_session(tmp_path)
    flow = session.encounter_setup_flow
    position = Coordinate(7, 8)
    flow.steps = (replace(flow.steps[1], label='pola startowe bohaterów', positions=(position,)),)
    assert flow.as_payload()['current_step']['can_confirm']
    assert flow.pending_start_position == position
    session.scan_board_selection(automatic=True)
    assert flow.completed
    assert list(flow.player_start_assignments.values()) == [position]


def test_multi_field_terrain_stays_a_group_and_each_step_needs_accept(tmp_path: Path) -> None:
    session, board = setup_session(tmp_path)
    flow = session.encounter_setup_flow
    step = next(step for step in flow.steps if step.kind.value == 'environment' and len(step.positions) > 1)
    flow.steps = (step, step)
    session._sync_board_leds()
    assert session._current_board_scan_target().positions == (panel_position(28),)
    for position in step.positions:
        assert board.leds[position.as_tuple()] == step.color
    revision = session.state_payload()['board_selection']['revision']
    session.scan_board_selection(expected_revision=revision, automatic=True)
    assert flow.current_index == 1 and not flow.completed
    session.scan_board_selection(expected_revision=revision, automatic=True)
    assert flow.current_index == 1 and not flow.completed
    session.scan_board_selection(automatic=True)
    assert flow.completed


def test_board_accept_starts_initiative_after_last_setup_step(tmp_path: Path) -> None:
    session, board = setup_session(tmp_path)
    flow = session.encounter_setup_flow
    flow.current_index = len(flow.steps) - 1
    setup_revision = session.state_payload()['board_selection']['revision']
    session.scan_board_selection(expected_revision=setup_revision, automatic=True)
    payload = session.state_payload()
    assert flow.completed and session.encounter_initiative_flow is None
    selection = payload['board_selection']
    assert selection['mode'] == 'initiative_start'
    assert selection['auto_arm']
    assert {tuple(p) for p in selection['legal_positions']} == {(19, 1), (19, 0)}
    assert board.leds == {(19, 1): LedColor.PANEL_ACCEPT, (19, 0): LedColor.PANEL_BACK}
    # A delayed setup press cannot also start initiative.
    session.scan_board_selection(expected_revision=setup_revision, automatic=True)
    assert session.encounter_initiative_flow is None
    session.scan_board_selection(expected_revision=selection['revision'], automatic=True)
    panel = session.encounter_initiative_flow.roll_panel
    assert panel is not None and panel.values == (10,)
    assert session.state_payload()['board_selection']['mode'] == 'initiative_roll'
    assert {(19, 1), (19, 2), (19, 3)} == set(board.leds)
    # Starting initiative must not count as accepting its first die.
    session.scan_board_selection(expected_revision=selection['revision'], automatic=True)
    assert not panel.review and session.combat_state is None


def test_reconnect_at_first_map_step_exposes_live_accept(tmp_path: Path, monkeypatch) -> None:
    from dnd_board_game.hardware.board_session import BoardSessionAdapter

    session, board = setup_session(tmp_path)
    session.board_adapter = None
    monkeypatch.setattr(BoardSessionAdapter, 'connect', lambda **kwargs: BoardSessionAdapter(board))
    client = create_app(session).test_client()
    response = client.post('/api/board/configure', json={'backend': 'hardware'})
    assert response.status_code == 200
    selection = response.get_json()['board_selection']
    assert selection['auto_arm'] and selection['mode'] == 'encounter_setup'
    assert session.encounter_setup_flow.current_index == 0
    assert board.leds == {(19, 1): LedColor.PANEL_ACCEPT}
    response = client.post('/api/board/scan', json={'revision': selection['revision'], 'automatic': True})
    assert response.status_code == 200
    assert response.get_json()['encounter_setup']['current_index'] == 1


def test_initiative_start_does_not_skip_optional_stealth(tmp_path: Path) -> None:
    from dnd_board_game.exploration import EncounterOpeningOutcome, EncounterOpeningResolution

    session, board = setup_session(tmp_path)
    session.encounter_setup_flow.completed = True
    session.pending_encounter = replace(
        session.pending_encounter,
        precombat_stealth_completed=False,
        opening_resolution=EncounterOpeningResolution(
            rule_id='quiet', outcome=EncounterOpeningOutcome.PARTY_CAN_HIDE,
            title='Ciche wejście', narration='', noise=0,
        ),
    )
    assert session.state_payload()['board_selection']['mode'] != 'initiative_start'
    with pytest.raises(ValueError, match='skradania'):
        session.start_encounter_initiative()
    payload = session.finish_precombat_stealth()
    assert payload['board_selection']['mode'] == 'initiative_start'
    assert payload['board_selection']['auto_arm']
    assert board.leds == {(19, 1): LedColor.PANEL_ACCEPT, (19, 0): LedColor.PANEL_BACK}


def test_back_reopens_previous_batch_and_invalidates_buffered_input(tmp_path: Path) -> None:
    session, board = setup_session(tmp_path)
    flow = session.encounter_setup_flow
    original_actors = flow.encounter.actors
    client = create_app(session).test_client()
    assert not flow.can_back
    assert client.post('/api/encounter/setup/back').status_code == 400
    session.confirm_encounter_setup_step()
    revision = session.state_payload()['board_selection']['revision']
    board.selected = panel_position(29).as_tuple()
    session.scan_board_selection(expected_revision=revision, automatic=True)
    assert flow.current_index == 0 and not flow.can_back
    assert flow.encounter.actors == original_actors
    assert panel_position(29).as_tuple() not in board.leds
    scans = board.scans
    session.scan_board_selection(expected_revision=revision, automatic=True)
    assert board.scans == scans and flow.current_index == 0
    session.confirm_encounter_setup_step()
    assert client.post('/api/encounter/setup/back').status_code == 200
    assert flow.current_index == 0


def test_back_reopens_one_hero_and_frees_only_their_assigned_field(tmp_path: Path) -> None:
    session, board = setup_session(tmp_path)
    flow = session.encounter_setup_flow
    first = flow.encounter.actors[0]
    second = replace(first, id=type(first.id)('second'), name='Drugi')
    flow.encounter = replace(flow.encounter, actors=(first, second))
    flow.player_start_actor_ids = (str(first.id), str(second.id))
    a, b, c = Coordinate(7, 8), Coordinate(8, 8), Coordinate(9, 8)
    placement = replace(flow.steps[1], label='pola startowe bohaterów', positions=(a, b, c))
    flow.steps = (flow.steps[0], placement, flow.steps[0])
    session.confirm_encounter_setup_step()
    session.assign_encounter_player_start_position(a)
    session.assign_encounter_player_start_position(b)
    assert flow.current_index == 2
    session.select_board_position(panel_position(29))
    assert flow.current_index == 1 and flow.current_player_start_actor.id == second.id
    assert flow.player_start_assignments == {str(first.id): a}
    assert flow.pending_start_position == b
    assert flow.encounter.actors[0].position == a
    assert flow.encounter.actors[1] == second
    assert b in flow.remaining_player_start_positions() and a not in flow.remaining_player_start_positions()
    session.select_board_position(c)
    session.select_board_position(panel_position(28))
    assert flow.encounter.actors[1].position == c and flow.current_index == 2
    session.select_board_position(panel_position(29))
    session.select_board_position(panel_position(29))
    assert not flow.player_start_assignments
    assert flow.current_player_start_actor.id == first.id
    assert flow.encounter.actors == (first, second)
    assert flow.pending_start_position == a
    session.select_board_position(panel_position(29))
    assert flow.current_index == 0 and flow.selected_start_position is None


def test_final_setup_can_be_corrected_until_initiative_starts(tmp_path: Path) -> None:
    session, _ = setup_session(tmp_path)
    flow = session.encounter_setup_flow
    flow.current_index = len(flow.steps) - 1
    session.confirm_encounter_setup_step()
    session.select_board_position(panel_position(29))
    assert not flow.completed and flow.current_index == len(flow.steps) - 1
    session.confirm_encounter_setup_step()
    session.select_board_position(panel_position(28))
    with pytest.raises(ValueError, match='poprzedniego elementu'):
        session.back_encounter_setup_step()


def test_automatic_accept_does_not_flash_or_resend_unchanged_lights(tmp_path: Path) -> None:
    class AtomicBoard(Board):
        def __init__(self):
            super().__init__()
            self.frames = []

        def set_leds(self, positions, rgb_color, **kwargs):
            self.frames.append(kwargs)
            if kwargs.get('replace'):
                self.leds.clear()
            super().set_leds(positions, rgb_color)

    session, _ = setup_session(tmp_path)
    board = AtomicBoard()
    board.selected = (19, 1)
    session.attach_board_connection(board, backend='simulator')
    session._sync_board_leds()
    assert len(board.frames) == 1
    session.scan_board_selection(automatic=True)
    assert session.encounter_setup_flow.current_index == 1
    # Only the next setup step needs sending. Entering/leaving the scan leaves
    # the existing frame and brightness alone.
    assert len(board.frames) == 2
    assert all(frame['brightness'] is None for frame in board.frames)


def test_scan_timing_separates_preparation_wait_and_processing(tmp_path: Path, monkeypatch) -> None:
    session, _ = setup_session(tmp_path)
    events = []
    monkeypatch.setattr(session, '_record', lambda name, payload: events.append((name, payload)))
    session.scan_board_selection(automatic=True)
    started = next(payload for name, payload in events if name == 'ui_board_scan_started')
    received = next(payload for name, payload in events if name == 'ui_board_scan_received')
    assert started['preparation_ms'] >= 0
    assert received['wait_for_input_ms'] >= 0
    assert received['after_input_ms'] >= 0
    assert received['wait_for_input_ms'] + received['after_input_ms'] <= received['elapsed_ms'] + 2
