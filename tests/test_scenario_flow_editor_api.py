from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import board.simulator.app as simulator_app_module  # noqa: E402


def _reset_simulator_globals() -> None:
    simulator_app_module._reset_board_state()
    simulator_app_module._stop_runtime_process()


def test_scenario_flow_api_lists_and_loads_bandit_cave():
    app = simulator_app_module.app
    with app.test_client() as client:
        listed = client.get("/api/scenario-flows")
        loaded = client.get("/api/scenario-flows/bandit_cave")
        catalog = client.get("/api/scenario-map-catalog")

    assert listed.status_code == 200
    listed_payload = listed.get_json()
    assert listed_payload["ok"] is True
    assert "bandit_cave" in listed_payload["scenario_flows"]

    assert loaded.status_code == 200
    loaded_payload = loaded.get_json()
    assert loaded_payload["ok"] is True
    assert loaded_payload["scenario_flow"]["scenario_id"] == "bandit_cave"

    assert catalog.status_code == 200
    catalog_payload = catalog.get_json()
    assert catalog_payload["ok"] is True
    assert "bandit_cave_cave_entrance" in catalog_payload["catalog"]["runtime"]


def test_simulator_runtime_can_start_named_scenario_flow(monkeypatch):
    app = simulator_app_module.app
    _reset_simulator_globals()
    calls: list[dict[str, object]] = []

    class _DummyProc:
        def __init__(self, cmd, cwd=None):
            self.cmd = cmd
            self.cwd = cwd
            self.pid = 54321
            self._returncode = None

        def poll(self):
            return self._returncode

        def terminate(self):
            self._returncode = 0

        def wait(self, timeout=None):
            self._returncode = 0
            return 0

        def kill(self):
            self._returncode = -9

    def _fake_popen(cmd, cwd=None):
        calls.append({"cmd": cmd, "cwd": cwd})
        return _DummyProc(cmd, cwd=cwd)

    monkeypatch.setattr(simulator_app_module.subprocess, "Popen", _fake_popen)

    with app.test_client() as client:
        started = client.post(
            "/api/runtime/start-scenario",
            json={
                "scenario": "bandit_cave",
                "hero_ids": ["cedric", "freya"],
            },
        )
        stopped = client.post("/api/runtime/stop")

    assert started.status_code == 200
    started_payload = started.get_json()
    assert started_payload["ok"] is True
    assert started_payload["runtime"]["running"] is True
    assert calls
    cmd = calls[0]["cmd"]
    assert "--scenario" in cmd
    assert "bandit_cave" in cmd
    assert "--hero-id" in cmd
    assert "cedric" in cmd and "freya" in cmd

    stopped_payload = stopped.get_json()
    assert stopped_payload["ok"] is True
