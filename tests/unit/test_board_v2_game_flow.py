"""Application input contracts persist within a die and end at real decisions."""
from pathlib import Path
import threading

from dnd_board_game.ui.routes import create_app
from tests.unit.test_initiative_panel import Board, session_at_initiative
from tests.unit.test_recruitment_arena import arena, begin


class ContextBoard(Board):
    def __init__(self) -> None:
        super().__init__()
        self.contracts: list[dict] = []
        self.cancelled = 0

    def prepare_scan(self, positions, **contract):
        self.contracts.append(dict(positions=positions, **contract))
        return lambda timeout_s=None: self.selected

    def cancel_scan(self) -> None:
        self.cancelled += 1


def test_initiative_mask_and_context_remain_stable_at_bounds(tmp_path: Path) -> None:
    session = session_at_initiative(tmp_path)
    board = ContextBoard()
    session.attach_board_connection(board, backend='hardware')
    for _ in range(12):
        session.scan_board_selection(automatic=True)
    assert session.encounter_initiative_flow.roll_panel.values == (20,)
    assert len({c['context_key'] for c in board.contracts}) == 1
    assert all(c['mode'] == 'stream' and c['finish_positions'] == ((19, 1),) for c in board.contracts)
    assert all(set(c['positions']) == {(19, 1), (19, 2), (19, 3)} for c in board.contracts)
    board.selected = (19, 1)
    session.scan_board_selection(automatic=True)
    session.scan_board_selection(automatic=True)
    assert board.contracts[-1]['mode'] == 'single'
    assert board.contracts[-1]['context_key'] != board.contracts[0]['context_key']
    assert session.combat_state is not None


def test_browser_dice_and_review_have_distinct_contracts(tmp_path: Path) -> None:
    session = arena(tmp_path)
    begin(session, 'garran')
    session.configure_board_panel('dice:1:0:false', [26, 27, 28], True)
    target = session._current_board_scan_target()
    first = session._board_input_contract(target, 'revision1')
    assert first[1] == 'stream'
    assert [p.as_tuple() for p in first[2]] == [(19, 1)]
    assert session._board_input_contract(target, 'revision2') == first
    session.configure_board_panel('dice:1:0:true', [28, 29], True)
    assert session._board_input_contract(session._current_board_scan_target(), 'revision3')[1] == 'single'


def test_screen_confirmation_cancels_waiting_board_scan_without_deadlock(tmp_path: Path) -> None:
    session = session_at_initiative(tmp_path)
    armed = threading.Event()
    released = threading.Event()

    class WaitingBoard(ContextBoard):
        def prepare_scan(self, positions, **contract):
            self.contracts.append(contract)
            armed.set()
            def wait(timeout_s=None):
                assert released.wait(2)
                return (19, 2)  # A late buffered press must not modify the review.
            return wait

        def cancel_scan(self) -> None:
            super().cancel_scan()
            released.set()

    board = WaitingBoard()
    session.attach_board_connection(board, backend='hardware')
    app = create_app(session, character_dir=tmp_path / 'characters')
    outcomes = []
    def scan():
        with app.test_client() as client:
            outcomes.append(client.post('/api/board/scan', json={'automatic': True}).status_code)
    worker = threading.Thread(target=scan)
    worker.start()
    assert armed.wait(2)
    with app.test_client() as client:
        result = client.post('/api/encounter/initiative/panel', json={'command': 'accept', 'value': 13})
    worker.join(2)
    assert not worker.is_alive() and outcomes == [200]
    assert result.status_code == 200
    assert session.encounter_initiative_flow.roll_panel.review
    assert session.encounter_initiative_flow.roll_panel.values == (13,)
    assert board.cancelled == 1


def test_defensive_stance_payment_then_reset_releases_orphan_scan(tmp_path: Path) -> None:
    session = arena(tmp_path)
    begin(session, 'garran')
    armed = threading.Event()
    released = threading.Event()

    class WaitingBoard(ContextBoard):
        waiting = False

        def prepare_scan(self, positions, **contract):
            if not self.waiting:
                return super().prepare_scan(positions, **contract)
            self.contracts.append(dict(positions=positions, **contract))
            armed.set()

            def wait(timeout_s=None):
                assert released.wait(2), 'reset did not wake the old board reader'
                return (19, 29)  # Buffered old press must be discarded.
            return wait

        def cancel_scan(self) -> None:
            super().cancel_scan()
            released.set()

    board = WaitingBoard()
    session.attach_board_connection(board, backend='hardware')
    app = create_app(session, character_dir=tmp_path / 'characters')
    with app.test_client() as client:
        session.use_combat_class_feature('defensive_stance')
        board.selected = (19, 1)
        paid = client.post('/api/board/scan', json={'automatic': True})
        assert paid.status_code == 200
        assert session.shared_mana_declaration is None
        selection = paid.json['board_selection']
        assert selection['auto_arm'] and [19, 29] in selection['legal_positions']
        assert paid.json['combat']['turn_action_menu']['preview_option_id'] is None

    board.waiting = True
    outcomes = []

    def old_scan() -> None:
        with app.test_client() as client:
            outcomes.append(client.post('/api/board/scan', json={
                'revision': selection['revision'], 'automatic': True,
            }).status_code)

    worker = threading.Thread(target=old_scan)
    worker.start()
    try:
        assert armed.wait(2)
        with app.test_client() as client:
            reset = client.post('/api/board/reset-scan', json={})
            assert reset.status_code == 200
            assert not session._board_scan_lock.locked(), 'reset returned before the old reader finished'
            assert reset.json['combat']['turn_action_menu']['preview_option_id'] is None
            board.waiting = False
            board.selected = (19, 29)
            next_scan = client.post('/api/board/scan', json={
                'automatic': True, 'revision': reset.json['board_selection']['revision'],
            })
            assert next_scan.status_code == 200
            assert next_scan.json['combat']['turn_action_menu']['preview_option_id'] == 'turn:move'
    finally:
        released.set()
        worker.join(2)
    assert not worker.is_alive() and outcomes == [200]
