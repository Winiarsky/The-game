from pathlib import Path

import pytest

from dnd_board_game.combat import SetupStepKind
from dnd_board_game.ui import training_walkthrough as guided
from dnd_board_game.ui.routes import create_app
from tests.unit.test_initiative_panel import Board
from tests.unit.test_recruitment_arena import arena
from tests.unit.test_training_walkthrough import prepared


def test_introduction_is_a_separate_board_step_before_any_placement(tmp_path: Path) -> None:
    session = arena(tmp_path)
    board = Board()
    session.attach_board_connection(board, backend='simulator')
    guided.start(session, 'garran')
    intro = session.state_payload()
    assert intro['training_arena']['tutorial']['notice']['phase'] == 'introduction'
    assert intro['training_arena']['tutorial']['notice']['intro']
    assert intro['board_selection']['legal_positions'] == [[19, 1]]
    assert set(board.leds) == {(19, 1)}
    flow = session.encounter_setup_flow
    assert flow.current_index == 0 and flow.current_step.positions
    client = create_app(session).test_client()
    response = client.post('/api/encounter/setup/confirm', json={})
    assert response.status_code == 400
    assert flow.current_index == 0
    board.selected = (19, 1)
    session.scan_board_selection(automatic=True)
    assert guided.flag(session, 'phase') == 'setup'
    assert guided.notice_id(session) == ''
    assert flow.current_index == 0  # This press acknowledged the introduction only.
    assert {p.as_tuple() for p in flow.current_step.positions} <= set(board.leds)
    assert len(board.leds) > 1
    scans = board.scans
    session.scan_board_selection(expected_revision=intro['board_selection']['revision'], automatic=True)
    assert board.scans == scans
    session.scan_board_selection(automatic=True)
    assert flow.current_index == 1


@pytest.mark.parametrize('next_hero,next_index', [('garran', 0), ('garran', 1), ('brakka', 0)])
def test_ready_terrain_survives_retry_next_lesson_and_hero_change(tmp_path: Path, next_hero: str, next_index: int) -> None:
    session = prepared(tmp_path)
    board_before = session._active_encounter().board
    assert guided.flag(session, 'terrain_ready')
    guided.leave(session)
    guided.launch(session, next_hero, next_index)
    assert guided.flag(session, 'phase') == 'introduction'
    assert guided.payload(session)['notice']['intro'] == ''
    flow = session.encounter_setup_flow
    assert flow.steps[0].label == 'Przygotowanie nowej sytuacji'
    assert flow.steps[0].positions == ()
    assert all(step.kind in {SetupStepKind.ACTORS, SetupStepKind.ENEMIES} for step in flow.steps[1:])
    assert flow.encounter.board == board_before
    guided.acknowledge(session, guided.notice_id(session))
    while not flow.completed:
        session.confirm_encounter_setup_step()
    assert guided.flag(session, 'phase') == 'briefing'
    assert guided.payload(session)['notice']['explanation'] == ''


def test_fresh_resumed_lesson_still_requires_terrain_and_partial_setup_does_not_mark_ready(tmp_path: Path) -> None:
    session = arena(tmp_path)
    guided.launch(session, 'garran', 3)
    assert any(step.kind == SetupStepKind.ENVIRONMENT and step.positions for step in session.encounter_setup_flow.steps)
    assert not guided.flag(session, 'terrain_ready', False)
    guided.acknowledge(session, guided.notice_id(session))
    session.confirm_encounter_setup_step()
    guided.leave(session)
    guided.start(session, 'brakka')
    assert any(step.kind == SetupStepKind.ENVIRONMENT and step.positions for step in session.encounter_setup_flow.steps)


@pytest.mark.parametrize('phase', ['introduction', 'setup'])
def test_save_load_reconstructs_the_right_presentation_stage(tmp_path: Path, phase: str) -> None:
    session = arena(tmp_path)
    guided.start(session, 'garran')
    if phase == 'setup':
        guided.acknowledge(session, guided.notice_id(session))
    session.save_snapshot()
    session.load_snapshot()
    assert guided.flag(session, 'phase') == phase
    assert bool(guided.notice_id(session)) == (phase == 'introduction')
    assert session.encounter_setup_flow.current_step is not None
    assert not guided.flag(session, 'terrain_ready', False)
