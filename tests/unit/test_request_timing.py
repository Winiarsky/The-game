"""Slow work is observable without treating waiting for a player as a stall."""
from pathlib import Path

from dnd_board_game.ui.routes import create_app
from tests.unit.test_recruitment_arena import arena


def test_slow_request_reports_duration_but_scan_wait_does_not(tmp_path: Path, monkeypatch) -> None:
    import dnd_board_game.ui.routes as routes

    session = arena(tmp_path)
    app = create_app(session)
    now = [0.0]
    events = []
    original = session.state_payload

    def delayed_state():
        result = original()
        now[0] += .6
        return result

    monkeypatch.setattr(routes.time, 'monotonic', lambda: now[0])
    monkeypatch.setattr(session, 'state_payload', delayed_state)
    monkeypatch.setattr(session, '_record', lambda event, payload: events.append((event, payload)))
    client = app.test_client()
    assert client.get('/api/state').status_code == 200
    slow = [(event, payload) for event, payload in events if event == 'ui_request_slow']
    assert slow == [('ui_request_slow', {'path': '/api/state', 'method': 'GET', 'elapsed_ms': 600, 'status': 200})]
    events.clear()
    # The disconnected-board error response also builds state, but scan request
    # duration must not be mistaken for computational work or device latency.
    assert client.post('/api/board/scan', json={}).status_code == 400
    assert not any(event == 'ui_request_slow' for event, _ in events)
