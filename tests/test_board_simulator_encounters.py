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


def test_simulator_api_lists_saved_heroes():
    app = simulator_app_module.app
    with app.test_client() as client:
        response = client.get("/api/heroes")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert isinstance(payload["heroes"], list)
    assert payload["heroes"]
    assert {"character_id", "name", "class_id", "level"} <= set(payload["heroes"][0].keys())


def test_simulator_reset_clears_board_and_click_queue():
    app = simulator_app_module.app
    _reset_simulator_globals()
    simulator_app_module._set_cell_color(0, 0, [255, 10, 10])
    simulator_app_module.click_queue.put({"row": 1, "col": 2})
    simulator_app_module.click_queue.put({"row": 3, "col": 4})

    with app.test_client() as client:
        response = client.post("/api/reset")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["cleared_clicks"] == 2
    assert simulator_app_module.board_state[0][0] is None


def test_simulator_api_generates_procedural_encounter():
    app = simulator_app_module.app
    _reset_simulator_globals()

    with app.test_client() as client:
        response = client.post(
            "/api/encounters/generate",
            json={
                "biome": "forest",
                "threat": "moderate",
                "layout": "split_lanes",
                "formation_pack": "serpentine",
                "preset": "commando_ambush",
                "seed": 4242,
            },
        )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["metadata"]["seed"] == 4242
    assert payload["metadata"]["layout"] == "split_lanes"
    assert payload["metadata"]["threat"] == "severe"
    assert payload["metadata"]["formation_pack"] == "serpentine"
    assert len(payload["metadata"]["formations_used"]) == 2
    assert payload["scenario"]["mode"] == "encounter"
    assert payload["scenario"]["starting_positions"]
    assert isinstance(payload["setup_plan"], list)
    assert payload["setup_plan"]


def test_simulator_runtime_start_and_stop(monkeypatch):
    app = simulator_app_module.app
    _reset_simulator_globals()
    calls: list[dict[str, object]] = []

    class _DummyProc:
        def __init__(self, cmd, cwd=None):
            self.cmd = cmd
            self.cwd = cwd
            self.pid = 43210
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
            "/api/runtime/start",
            json={
                "biome": "forest",
                "threat": "moderate",
                "layout": "split_lanes",
                "formation_pack": "fortifications",
                "preset": "losowy",
                "seed": 12345,
                "hero_ids": ["cedric", "freya"],
            },
        )
        status = client.get("/api/runtime/status")
        stopped = client.post("/api/runtime/stop")

    assert started.status_code == 200
    started_payload = started.get_json()
    assert started_payload["ok"] is True
    assert started_payload["runtime"]["running"] is True
    assert started_payload["runtime"]["ui_url"].startswith("http://127.0.0.1:")
    assert started_payload["metadata"]["formation_pack"] == "fortifications"
    assert calls
    cmd = calls[0]["cmd"]
    assert "--encounter-biome" in cmd
    assert "--encounter-formation-pack" in cmd
    assert "--hero-id" in cmd
    assert "cedric" in cmd and "freya" in cmd

    status_payload = status.get_json()
    assert status_payload["ok"] is True
    assert status_payload["running"] is True

    stopped_payload = stopped.get_json()
    assert stopped_payload["ok"] is True
    assert stopped_payload["stopped"] is True
    assert stopped_payload["runtime"]["running"] is False
