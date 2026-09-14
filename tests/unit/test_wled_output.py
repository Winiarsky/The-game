"""Slow and failed LED delivery must not block game commands or arm stale input."""
from pathlib import Path
import threading
from types import SimpleNamespace

import pytest

from board.connection import Connection
from board.led_output import LedFrame, LedOutput, LedOutputError


def frame(index: int) -> LedFrame:
    return LedFrame(((index, (0, 80, 220)),))


def test_latest_frame_replaces_backlog_and_old_ack_cannot_confirm_it() -> None:
    sending, release = threading.Event(), threading.Event()
    calls = []
    def send(value):
        calls.append(value)
        if len(calls) == 1:
            sending.set()
            assert release.wait(2)
        return True
    output = LedOutput(send)
    try:
        first = output.submit(frame(1))
        assert sending.wait(1)
        output.submit(frame(2))
        newest = output.submit(frame(3))
        assert output.status['pending'] is True
        assert not output.wait_applied(first, threading.Event())
        release.set()
        assert output.wait_applied(newest, threading.Event(), timeout_s=1)
        assert calls == [frame(1), frame(3)]
    finally:
        release.set()
        output.close(timeout_s=1)


def test_failed_frame_is_retried_without_another_ui_request() -> None:
    calls = []
    def send(value):
        calls.append(value)
        return len(calls) > 1
    output = LedOutput(send, retry_s=.01)
    try:
        revision = output.submit(frame(1))
        assert output.submit(frame(1)) == revision
        assert output.wait_applied(revision, threading.Event(), timeout_s=1)
        assert calls == [frame(1), frame(1)]
        assert output.status['error'] == ''
    finally:
        output.close(timeout_s=1)


def test_failed_delivery_cannot_be_reported_as_ready() -> None:
    output = LedOutput(lambda _: False, retry_s=.01)
    try:
        revision = output.submit(frame(1))
        with pytest.raises(LedOutputError, match='podświetlenia'):
            output.wait_applied(revision, threading.Event(), timeout_s=.04)
        assert output.status['pending'] and output.status['applied_revision'] == 0
    finally:
        output.close(timeout_s=.01)


@pytest.fixture
def hardware(monkeypatch):
    import board.connection as module
    sending, release = threading.Event(), threading.Event()
    release.set()
    calls = []
    class Input:
        def __init__(self, *_):
            self.connected = True
            self.contracts = []
            self.selected = None
        def prepare_input(self, positions, **contract):
            self.contracts.append((positions, contract))
            return lambda timeout_s=None: self.selected
        def cancel(self):
            pass
        def close(self):
            self.connected = False
    class Wled:
        def __init__(self, *_):
            pass
        def clear(self):
            return True
        def set_leds(self, updates, **metadata):
            calls.append((updates, metadata))
            sending.set()
            assert release.wait(3)
            return True
    monkeypatch.setattr(module, '_open_serial_probe', lambda _: SimpleNamespace(
        serial_handle=object(), port='fake', info={}))
    monkeypatch.setattr(module, 'SerialV2', Input)
    monkeypatch.setattr(module, '_WledClient', Wled)
    connection = Connection(backend='hardware')
    assert connection._backend.output.wait_applied(connection._backend.output.revision, threading.Event())
    try:
        yield connection, sending, release, calls
    finally:
        release.set()
        connection.close()


def test_cancel_before_read_cannot_arm_old_menu_while_led_delivery_waits(hardware) -> None:
    connection, sending, release, _ = hardware
    release.clear()
    connection.set_leds([(19, 1)], [0, 80, 220], replace=True)
    assert sending.wait(1)
    read = connection.prepare_scan([(19, 1)], context_key='old', mode='single', finish_positions=())
    connection.cancel_scan()
    assert read() is None
    release.set()
    assert not connection._backend.input.contracts


def test_scanner_reads_confirm_while_led_confirmation_is_still_pending(hardware) -> None:
    connection, sending, release, _ = hardware
    release.clear()
    connection.set_leds([(19, 1)], [0, 80, 220], replace=True)
    assert sending.wait(1)
    read = connection.prepare_scan([(19, 1)], context_key='confirm', mode='single', finish_positions=())
    connection._backend.input.selected = (19, 1)
    results = []
    worker = threading.Thread(target=lambda: results.append(read()))
    worker.start()
    worker.join(1)
    try:
        assert not worker.is_alive(), 'USB input waited for a WLED HTTP acknowledgement'
        assert results == [(19, 1)]
        assert connection._backend.output.status['pending']
        assert connection._backend.input.contracts[0][1]['context_key'] == 'confirm'
    finally:
        release.set()
        worker.join(1)


@pytest.mark.parametrize('value', [LedFrame(()), frame(617)])
def test_hardware_led_failure_keeps_cause_and_recovers_without_blocking_input(hardware, monkeypatch, value: LedFrame) -> None:
    connection, _, _, _ = hardware
    backend = connection._backend
    cause = 'set_leds: Read timed out (read timeout=2.0)'
    monkeypatch.setattr(backend.wled, 'last_error', cause, raising=False)
    # Start from a different frame so the failed clear is also submitted.
    revision = backend.output.submit(frame(1))
    assert backend.output.wait_applied(revision, threading.Event(), timeout_s=1)
    with monkeypatch.context() as failed:
        failed.setattr(backend.wled, 'clear', lambda: False)
        failed.setattr(backend.wled, 'set_leds', lambda *args, **kwargs: False)
        revision = backend.output.submit(value)
        with pytest.raises(LedOutputError):
            backend.output.wait_applied(revision, threading.Event(), timeout_s=.05)
        status = backend.output.status
        assert status['pending']
        assert status['error'] == status['last_attempt']['error'] == cause
        backend.input.selected = (19, 1)
        assert connection.prepare_scan([(19, 1)], context_key='confirm', mode='single', finish_positions=())() == (19, 1)
    backend.output.wake()
    assert backend.output.wait_applied(revision, threading.Event(), timeout_s=1)
    assert backend.output.status['error'] == ''


def test_attack_confirmation_ui_returns_while_wled_is_still_sending(hardware, tmp_path: Path) -> None:
    from dataclasses import replace
    from dnd_board_game.ui.routes import create_app
    from dnd_board_game.world import Coordinate
    from tests.unit.test_recruitment_arena import arena, begin

    connection, sending, release, calls = hardware
    session = arena(tmp_path)
    begin(session, 'garran')
    hero = session._actor_by_string_id('garran')
    enemy = session._actor_by_string_id('recruitment_dummy')
    session.combat_state = replace(session.combat_state, actors=tuple(
        replace(actor, position=Coordinate(hero.position.col, hero.position.row - 1))
        if actor.id == enemy.id else actor for actor in session.combat_state.actors))
    enemy = session._actor_by_string_id('recruitment_dummy')
    session.select_combat_attack_source('longsword_slash')
    session.combat_targeting_attack_source_id = 'longsword_slash'
    session.configure_board_panel('decision:attack', [28, 29], False)
    session.attach_board_connection(connection, backend='hardware')
    output = connection._backend.output
    assert output.wait_applied(output.revision, threading.Event())
    sending.clear()
    release.clear()
    app = create_app(session)
    result = []
    def select():
        with app.test_client() as client:
            result.append(client.post('/api/board/select', json={'col': enemy.position.col, 'row': enemy.position.row}))
    worker = threading.Thread(target=select)
    worker.start()
    assert sending.wait(2)
    worker.join(1)
    try:
        assert not worker.is_alive(), 'Game response waited for WLED HTTP'
        assert result[0].status_code == 200
        state = result[0].get_json()
        assert [19, 1] in state['board_selection']['legal_positions']
        assert state['board']['led_output']['pending'] is True
        # Another API request also remains usable while the LED request stalls.
        with app.test_client() as client:
            assert client.get('/api/state').status_code == 200
        # Physical ✓ is LED 617 in the configured serpentine mapping.
        assert (617, [0, 68, 217]) in calls[-1][0]
    finally:
        release.set()
        worker.join(2)


def test_failed_old_frame_is_replaced_by_current_confirmation() -> None:
    sending, release = threading.Event(), threading.Event()
    calls = []
    def send(value):
        calls.append(value)
        if len(calls) == 1:
            sending.set()
            assert release.wait(2)
            return False
        return True
    output = LedOutput(send, retry_s=.01)
    try:
        output.submit(frame(1))
        assert sending.wait(1)
        latest = output.submit(frame(617))
        release.set()
        assert output.wait_applied(latest, threading.Event(), timeout_s=1)
        assert calls == [frame(1), frame(617)]
        assert output.status['last_attempt']['confirmed'] is True
    finally:
        release.set()
        output.close(timeout_s=1)


def test_connection_preserves_explicit_led_failure(monkeypatch) -> None:
    import board.connection as module
    class Backend:
        def __init__(self, *_):
            pass
        def set_leds(self, *args, **kwargs):
            return False
        def leds_off(self):
            return False
    monkeypatch.setattr(module, '_SimulatorBackend', Backend)
    connection = Connection(backend='simulator')
    assert connection.set_leds([(19, 1)], [0, 80, 220]) is False
    assert connection.leds_off() is False


def test_wled_http_error_body_does_not_confirm_frame(monkeypatch) -> None:
    from board.connection import _WledClient
    response = SimpleNamespace(raise_for_status=lambda: None, json=lambda: {'error': 9})
    monkeypatch.setattr('board.connection.requests.post', lambda *args, **kwargs: response)
    client = _WledClient({'base_url': 'http://wled.test'})
    client.available = True
    assert not client.set_leds([(617, [0, 80, 220])])
    assert client.available is False
    assert 'odrzucił' in client.last_error


def test_close_releases_usb_and_led_worker_even_if_stop_fails(hardware, monkeypatch) -> None:
    connection, _, _, _ = hardware
    backend = connection._backend
    def fail_stop():
        raise ConnectionError('USB STOP failed')
    with monkeypatch.context() as patch:
        patch.setattr(backend.input, 'cancel', fail_stop)
        with pytest.raises(ConnectionError, match='STOP failed'):
            backend.close()
    assert not backend.input.connected
    assert not backend.output._thread.is_alive()


def test_arena_setup_confirm_and_manual_retry_work_despite_wled_failure(hardware, monkeypatch, tmp_path: Path) -> None:
    from dnd_board_game.ui.routes import create_app
    from dnd_board_game.ui.training_arena import start_training_trial
    from tests.unit.test_recruitment_arena import arena

    connection, _, _, _ = hardware
    failed, recovered = threading.Event(), threading.Event()

    def failing_leds(*args, **kwargs):
        failed.set()
        return recovered.is_set()

    monkeypatch.setattr(connection._backend.wled, 'set_leds', failing_leds)
    session = arena(tmp_path)
    start_training_trial(session, 'garran', 'tutorial', 'humanoid')
    session.attach_board_connection(connection, backend='hardware')
    connection._backend.input.selected = (19, 1)
    app = create_app(session)
    workers = []
    try:
        for automatic in (True, False):
            before = session.encounter_setup_flow.current_index
            responses = []

            def confirm():
                with app.test_client() as client:
                    responses.append(client.post('/api/board/scan', json={'automatic': automatic}))

            worker = threading.Thread(target=confirm)
            workers.append(worker)
            worker.start()
            worker.join(1)
            assert not worker.is_alive(), 'Arena confirmation blocked on failed LED delivery'
            assert responses[0].status_code == 200
            assert session.encounter_setup_flow.current_index == before + 1
            assert failed.wait(1)
            assert responses[0].json['board']['led_output']['pending']
            assert connection.connected
    finally:
        recovered.set()
        for worker in workers:
            worker.join(3)


def test_usb_cancellation_and_new_mask_work_while_wled_waits(hardware, monkeypatch) -> None:
    connection, sending, release, _ = hardware
    release.clear()
    connection.set_leds([(19, 1)], [0, 80, 220], replace=True)
    assert sending.wait(1)
    armed, cancelled = threading.Event(), threading.Event()
    contracts = []

    def prepare(positions, **contract):
        contracts.append((positions, contract))
        armed.set()

        def wait(timeout_s=None):
            assert cancelled.wait(2)
            return None
        return wait

    with monkeypatch.context() as patch:
        patch.setattr(connection._backend.input, 'prepare_input', prepare)
        patch.setattr(connection._backend.input, 'cancel', cancelled.set)
        old = connection.prepare_scan([(19, 1)], context_key='old', mode='single', finish_positions=())
        worker = threading.Thread(target=old)
        worker.start()
        try:
            assert armed.wait(1)
            connection.cancel_scan()
            worker.join(1)
            assert not worker.is_alive()
        finally:
            cancelled.set()
            release.set()
            worker.join(2)
    connection._backend.input.selected = (19, 29)
    new = connection.prepare_scan([(19, 29)], context_key='new', mode='single', finish_positions=())
    assert new() == (19, 29)
    assert connection._backend.input.contracts[-1] == (
        [(19, 29)], {'context_key': 'new', 'mode': 'single', 'finish_positions': ()})
