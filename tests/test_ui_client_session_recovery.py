from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from ui_client import UIClient


class _ResponseStub:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = int(status_code)
        self._payload = dict(payload)

    def json(self):
        return dict(self._payload)

    def raise_for_status(self):
        if self.status_code >= 400 and self.status_code != 409:
            raise RuntimeError(f"http {self.status_code}")


def test_ui_client_send_event_refreshes_session_after_409(monkeypatch):
    client = UIClient(base_url="http://127.0.0.1:5200")
    client.session_id = None

    get_responses = iter(
        [
            _ResponseStub(200, {"ok": True, "session": {"id": "ui-session-1"}}),
            _ResponseStub(200, {"ok": True, "session": {"id": "ui-session-2"}}),
        ]
    )
    post_responses = iter(
        [
            _ResponseStub(409, {"ok": False, "error": "session mismatch", "current_session_id": "ui-session-2"}),
            _ResponseStub(200, {"ok": True, "event": {"id": 1}}),
        ]
    )
    sent_payloads: list[dict] = []

    monkeypatch.setattr("ui_client.requests.get", lambda *args, **kwargs: next(get_responses))

    def _post(_url, json=None, **_kwargs):
        sent_payloads.append(dict(json or {}))
        return next(post_responses)

    monkeypatch.setattr("ui_client.requests.post", _post)

    assert client.send_event("log", {"message": "test"}) is True
    assert client.session_id == "ui-session-2"
    assert sent_payloads[0]["session_id"] == "ui-session-1"
    assert sent_payloads[1]["session_id"] == "ui-session-2"


def test_ui_client_create_prompt_refreshes_session_after_409(monkeypatch):
    client = UIClient(base_url="http://127.0.0.1:5200")
    client.session_id = None

    get_responses = iter(
        [
            _ResponseStub(200, {"ok": True, "session": {"id": "ui-session-1"}}),
            _ResponseStub(200, {"ok": True, "session": {"id": "ui-session-2"}}),
        ]
    )
    post_responses = iter(
        [
            _ResponseStub(409, {"ok": False, "error": "session mismatch", "current_session_id": "ui-session-2"}),
            _ResponseStub(200, {"ok": True, "id": "42"}),
        ]
    )
    sent_payloads: list[dict] = []

    monkeypatch.setattr("ui_client.requests.get", lambda *args, **kwargs: next(get_responses))

    def _post(_url, json=None, **_kwargs):
        sent_payloads.append(dict(json or {}))
        return next(post_responses)

    monkeypatch.setattr("ui_client.requests.post", _post)

    prompt_id = client._create_prompt("Ustaw figurke bohatera", kind="info", source="hero_setup_place")

    assert prompt_id == "42"
    assert client.session_id == "ui-session-2"
    assert sent_payloads[0]["session_id"] == "ui-session-1"
    assert sent_payloads[1]["session_id"] == "ui-session-2"
