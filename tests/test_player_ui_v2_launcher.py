import itertools
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import future.player_ui_v2.app as player_ui_v2_app_module  # noqa: E402


class _ProcStub:
    def __init__(self):
        self.terminated = False
        self.killed = False
        self._poll = None

    def poll(self):
        return self._poll

    def terminate(self):
        self.terminated = True
        self._poll = 0

    def wait(self, timeout=None):  # noqa: ARG002
        self._poll = 0
        return 0

    def kill(self):
        self.killed = True
        self._poll = -9


@pytest.fixture()
def ui_client(monkeypatch):
    monkeypatch.setattr(player_ui_v2_app_module, "events_history", [])
    monkeypatch.setattr(player_ui_v2_app_module, "prompts", {})
    monkeypatch.setattr(player_ui_v2_app_module, "subscribers", set())
    monkeypatch.setattr(player_ui_v2_app_module, "event_ids", itertools.count(1))
    monkeypatch.setattr(player_ui_v2_app_module, "prompt_ids", itertools.count(1))
    monkeypatch.setattr(player_ui_v2_app_module, "session_ids", itertools.count(2))
    monkeypatch.setattr(player_ui_v2_app_module, "current_session_id", "ui-session-1")
    monkeypatch.setattr(
        player_ui_v2_app_module,
        "runtime_state",
        {
            "process": None,
            "state": "idle",
            "scenario_id": None,
            "hero_ids": [],
            "session_id": "ui-session-1",
            "started_at": None,
            "stopped_at": None,
            "returncode": None,
            "command": [],
            "base_url": None,
            "error": None,
        },
    )
    with player_ui_v2_app_module.app.test_client() as client:
        yield client


def test_runtime_start_resets_session_and_tracks_process(ui_client, monkeypatch):
    proc = _ProcStub()
    popen_calls = []

    def _fake_popen(cmd, cwd=None, env=None):  # noqa: ARG001
        popen_calls.append({"cmd": cmd, "cwd": cwd, "env": env})
        return proc

    monkeypatch.setattr(player_ui_v2_app_module.subprocess, "Popen", _fake_popen)
    monkeypatch.setattr(
        player_ui_v2_app_module,
        "_resolve_runtime_board_settings",
        lambda: {
            "backend": "simulator",
            "board_url": "http://127.0.0.1:5000",
            "serial_port": None,
            "wled_url": None,
        },
    )

    response = ui_client.post(
        "/api/runtime/start",
        json={"scenario_id": "bandit_cave", "hero_ids": ["cedric", "freya"]},
        base_url="http://127.0.0.1:5200",
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["session_id"] == "ui-session-2"
    assert payload["runtime_status"]["scenario_id"] == "bandit_cave"
    assert payload["runtime_status"]["hero_ids"] == ["cedric", "freya"]
    assert payload["runtime_status"]["state"] in {"starting", "running"}
    assert popen_calls
    cmd = popen_calls[0]["cmd"]
    assert "main.py" in cmd
    assert "--scenario" in cmd
    assert "bandit_cave" in cmd
    assert "--hero-id" in cmd
    assert "--board-backend" in cmd
    assert "simulator" in cmd
    assert "--board-url" in cmd
    assert "http://127.0.0.1:5000" in cmd
    assert popen_calls[0]["env"]["PLAYER_UI_URL"] == "http://127.0.0.1:5200"


def test_runtime_board_settings_fall_back_to_simulator_when_hardware_has_no_serial(monkeypatch):
    monkeypatch.delenv("PLAYER_UI_V2_BOARD_BACKEND", raising=False)
    monkeypatch.delenv("PLAYER_UI_V2_BOARD_URL", raising=False)
    monkeypatch.delenv("PLAYER_UI_V2_BOARD_SERIAL_PORT", raising=False)
    monkeypatch.delenv("PLAYER_UI_V2_WLED_URL", raising=False)
    monkeypatch.setattr(
        player_ui_v2_app_module,
        "load_board_config",
        lambda: {
            "connection": {"backend": "hardware", "simulator_url": "http://127.0.0.1:5000"},
            "hardware": {"serial_port": ""},
        },
    )
    monkeypatch.setattr(player_ui_v2_app_module, "connection_backend", lambda config: "hardware")
    monkeypatch.setattr(player_ui_v2_app_module, "simulator_url", lambda config: "http://127.0.0.1:5000")
    monkeypatch.setattr(player_ui_v2_app_module, "hardware_scan_config", lambda config: {"serial_port": ""})

    resolved = player_ui_v2_app_module._resolve_runtime_board_settings()

    assert resolved["backend"] == "simulator"
    assert resolved["board_url"] == "http://127.0.0.1:5000"


def test_runtime_start_requires_at_least_one_hero(ui_client):
    response = ui_client.post(
        "/api/runtime/start",
        json={"scenario_id": "bandit_cave", "hero_ids": []},
        base_url="http://127.0.0.1:5200",
    )
    assert response.status_code == 400
    assert "hero_id" in response.get_json()["error"].lower()


def test_runtime_stop_terminates_running_process(ui_client, monkeypatch):
    proc = _ProcStub()
    monkeypatch.setattr(
        player_ui_v2_app_module,
        "runtime_state",
        {
            "process": proc,
            "state": "running",
            "scenario_id": "bandit_cave",
            "hero_ids": ["cedric"],
            "session_id": "ui-session-1",
            "started_at": 1.0,
            "stopped_at": None,
            "returncode": None,
            "command": ["python", "main.py"],
            "base_url": "http://127.0.0.1:5200",
            "error": None,
        },
    )
    response = ui_client.post("/api/runtime/stop", json={})
    assert response.status_code == 200
    payload = response.get_json()["runtime_status"]
    assert payload["state"] == "stopped"
    assert proc.terminated is True


def test_runtime_retry_reuses_previous_configuration(ui_client, monkeypatch):
    proc = _ProcStub()
    popen_calls = []

    def _fake_popen(cmd, cwd=None, env=None):  # noqa: ARG001
        popen_calls.append({"cmd": cmd, "cwd": cwd, "env": env})
        return proc

    monkeypatch.setattr(player_ui_v2_app_module.subprocess, "Popen", _fake_popen)
    monkeypatch.setattr(
        player_ui_v2_app_module,
        "_resolve_runtime_board_settings",
        lambda: {
            "backend": "hardware",
            "board_url": None,
            "serial_port": "/dev/ttyUSB0",
            "wled_url": "http://192.168.0.165",
        },
    )
    monkeypatch.setattr(
        player_ui_v2_app_module,
        "runtime_state",
        {
            "process": None,
            "state": "error",
            "scenario_id": "bandit_cave",
            "hero_ids": ["cedric"],
            "session_id": "ui-session-1",
            "started_at": 1.0,
            "stopped_at": 2.0,
            "returncode": 1,
            "command": ["python", "main.py"],
            "base_url": "http://127.0.0.1:5200",
            "error": "Connection timed out",
            "board_backend": "hardware",
            "board_url": None,
        },
    )

    response = ui_client.post("/api/runtime/retry", json={}, base_url="http://127.0.0.1:5200")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["runtime_status"]["scenario_id"] == "bandit_cave"
    assert payload["runtime_status"]["hero_ids"] == ["cedric"]
    assert payload["runtime_status"]["state"] in {"starting", "running"}
    assert popen_calls
    cmd = popen_calls[0]["cmd"]
    assert "--hero-id" in cmd
    assert "cedric" in cmd
    assert "--board-backend" in cmd
    assert "hardware" in cmd
