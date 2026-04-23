from pathlib import Path
import sys

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from board.connection import _WledClient


class _ResponseStub:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_wled_client_validate_can_fail_without_raising(monkeypatch):
    client = _WledClient(
        {
            "base_url": "http://192.168.0.165",
            "led_count": 10,
            "request_timeout_s": 0.01,
            "retry_cooldown_s": 0,
        }
    )

    monkeypatch.setattr(
        "board.connection.requests.get",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(requests.exceptions.ConnectTimeout("timeout")),
    )

    ok = client.validate(raise_on_failure=False)

    assert ok is False
    assert client.available is False
    assert client.last_error is not None


def test_wled_client_retries_after_failure_and_recovers(monkeypatch):
    client = _WledClient(
        {
            "base_url": "http://192.168.0.165",
            "led_count": 10,
            "request_timeout_s": 0.01,
            "retry_cooldown_s": 0,
        }
    )

    state = {"online": False, "post_calls": 0}

    def _fake_get(*_args, **_kwargs):
        if not state["online"]:
            raise requests.exceptions.ConnectTimeout("timeout")
        return _ResponseStub({"leds": {"count": 20}})

    def _fake_post(*_args, **_kwargs):
        state["post_calls"] += 1
        return _ResponseStub({"ok": True})

    monkeypatch.setattr("board.connection.requests.get", _fake_get)
    monkeypatch.setattr("board.connection.requests.post", _fake_post)

    assert client.set_leds([(1, [255, 0, 0])]) is False
    assert client.available is False

    state["online"] = True

    assert client.set_leds([(1, [255, 0, 0])]) is True
    assert client.available is True
    assert state["post_calls"] == 1
