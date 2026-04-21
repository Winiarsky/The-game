from __future__ import annotations

import json
import logging
import socket
import subprocess
import sys
import time
from pathlib import Path
from queue import Empty, Queue
from threading import Lock
from typing import Any

from flask import Flask, jsonify, render_template, request

from board.led_mapping import invert_led_mapping, load_led_mapping
from board.settings import board_dimensions, load_board_config

BASE_DIR = Path(__file__).resolve().parents[1]
SCENARIOS_DIR = BASE_DIR.parent / "scenarios"
SRC_DIR = BASE_DIR.parent / "src"
GAME_OBJECTS_DIR = SRC_DIR / "GameObjects"
HEROES_DIR = BASE_DIR.parent / "data" / "heroes"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder="static", template_folder="templates")

def _scenario_path(name: str) -> Path:
    safe_name = Path(name).stem  # usuń rozszerzenia / ścieżki
    if not safe_name:
        raise ValueError("Nazwa scenariusza jest wymagana.")
    if "/" in name or "\\" in name:
        raise ValueError("Nazwa scenariusza nie może zawierać separatorów katalogów.")
    SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)
    return SCENARIOS_DIR / f"{safe_name}.json"


def _scenario_flow_path(name: str) -> Path:
    safe_name = Path(name).stem
    if not safe_name:
        raise ValueError("Nazwa flow scenariusza jest wymagana.")
    if "/" in name or "\\" in name:
        raise ValueError("Nazwa flow scenariusza nie może zawierać separatorów katalogów.")
    if scenario_flow_path is None:
        raise RuntimeError("Obsługa scenario flow jest niedostępna.")
    path = scenario_flow_path(safe_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
try:
    from game_objects_loader import scan_game_objects, serialize_meta
    from character_creation.repository import CharacterRepository
    from encounters import EncounterDirectives, EncounterRequest, generate_encounter, preset_directives
    from scenario_flow import (
        list_scenario_flow_names,
        map_catalog,
        load_scenario_flow,
        scenario_flow_path,
        validate_scenario_flow,
    )
except Exception as exc:  # pragma: no cover - zabezpieczenie gdy pakiet nie istnieje
    logger.warning("Nie udało się zaimportować game_objects_loader: %s", exc)
    scan_game_objects = None  # type: ignore
    serialize_meta = None  # type: ignore
    CharacterRepository = None  # type: ignore
    EncounterDirectives = None  # type: ignore
    EncounterRequest = None  # type: ignore
    generate_encounter = None  # type: ignore
    preset_directives = None  # type: ignore
    list_scenario_flow_names = None  # type: ignore
    map_catalog = None  # type: ignore
    load_scenario_flow = None  # type: ignore
    scenario_flow_path = None  # type: ignore
    validate_scenario_flow = None  # type: ignore


BOARD_CONFIG = load_board_config()
BOARD_ROWS, BOARD_COLS = board_dimensions(BOARD_CONFIG)
LED_TO_CELL = invert_led_mapping(load_led_mapping(rows=BOARD_ROWS, cols=BOARD_COLS))

board_state: list[list[list[int] | None]] = [
    [None for _ in range(BOARD_COLS)] for _ in range(BOARD_ROWS)
]
state_lock = Lock()
state_version = 0
pending_scans = 0
pending_lock = Lock()
click_queue: "Queue[dict[str, int]]" = Queue()
runtime_process: subprocess.Popen | None = None
runtime_info: dict[str, Any] = {}
runtime_lock = Lock()


def _set_cell_color(row: int, col: int, rgb: list[int] | None) -> None:
    board_state[row][col] = rgb[:] if rgb is not None else None


def _clear_click_queue() -> int:
    cleared = 0
    while True:
        try:
            click_queue.get_nowait()
            cleared += 1
        except Empty:
            break
    return cleared


def _reset_board_state() -> dict[str, int]:
    global state_version
    with state_lock:
        for row in range(BOARD_ROWS):
            for col in range(BOARD_COLS):
                _set_cell_color(row, col, None)
        state_version += 1
    cleared_clicks = _clear_click_queue()
    return {"state_version": state_version, "cleared_clicks": cleared_clicks}


def _find_free_port(host: str, preferred: int, attempts: int = 10) -> int:
    for offset in range(attempts):
        candidate = preferred + offset
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((host, candidate))
                return candidate
        except PermissionError:
            return preferred
        except OSError:
            continue
    return preferred


def _resolve_encounter_request(payload: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
    if EncounterRequest is None or preset_directives is None or EncounterDirectives is None:
        raise RuntimeError("Generator encounterów niedostępny.")
    biome = str(payload.get("biome") or "forest").strip().lower()
    threat = str(payload.get("threat") or "moderate").strip().lower()
    preset = str(payload.get("preset") or "losowy").strip().lower()
    layout = str(payload.get("layout") or "").strip().lower()
    formation_pack = str(payload.get("formation_pack") or "losowy").strip().lower()
    seed_raw = payload.get("seed")
    try:
        seed = int(seed_raw) if str(seed_raw or "").strip() else 0
    except Exception:
        seed = 0
    if seed <= 0:
        seed = int(time.time()) % 100000
    if preset == "commando_ambush" and threat in {"trivial", "low", "moderate"}:
        threat = "severe"
    directives = preset_directives(preset)
    if layout and layout not in {"losowy", "random"}:
        directives = EncounterDirectives(
            must_include=tuple(getattr(directives, "must_include", ()) or ()),
            fixed_enemies=tuple(getattr(directives, "fixed_enemies", ()) or ()),
            forbidden_cells=tuple(getattr(directives, "forbidden_cells", ()) or ()),
            preferred_layout=layout,
            preset_id=getattr(directives, "preset_id", None),
        )
    request_payload = EncounterRequest(
        biome=biome,
        threat=threat,
        seed=seed,
        party_level=1,
        party_size=4,
        enemy_family="goblin",
        directives=directives,
        formation_pack=formation_pack,
    )
    return request_payload, {
        "biome": biome,
        "threat": threat,
        "preset": preset,
        "layout": layout or "losowy",
        "formation_pack": formation_pack,
        "seed": seed,
    }


def _build_encounter_response(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    if generate_encounter is None:
        raise RuntimeError("Generator encounterów niedostępny.")
    request_payload, normalized = _resolve_encounter_request(payload)
    resolved = generate_encounter(request_payload)
    scenario = dict(resolved.scenario_payload)
    metadata = dict(resolved.metadata)
    setup_plan = scenario.get("setup_plan") or []
    return scenario, metadata, setup_plan, normalized


def _runtime_status_payload() -> dict[str, Any]:
    with runtime_lock:
        proc = runtime_process
        info = dict(runtime_info)
    returncode = proc.poll() if proc is not None else None
    return {
        "ok": True,
        "running": bool(proc is not None and returncode is None),
        "pid": getattr(proc, "pid", None),
        "returncode": returncode,
        **info,
    }


def _stop_runtime_process() -> bool:
    global runtime_process, runtime_info
    with runtime_lock:
        proc = runtime_process
        if proc is None:
            runtime_info = {}
            return False
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except Exception:
                proc.kill()
                try:
                    proc.wait(timeout=1)
                except Exception:
                    pass
        runtime_process = None
        runtime_info = {}
        return True


@app.route("/")
def index():
    return render_template("index.html", rows=BOARD_ROWS, cols=BOARD_COLS)


@app.route("/scenario-editor")
def scenario_editor():
    return render_template("scenario_editor.html", rows=BOARD_ROWS, cols=BOARD_COLS)


@app.route("/scenario-flow-editor")
def scenario_flow_editor():
    return render_template("scenario_flow_editor.html", rows=BOARD_ROWS, cols=BOARD_COLS)


@app.get("/api/scenarios")
def list_scenarios():
    scenarios = sorted(path.stem for path in SCENARIOS_DIR.glob("*.json")) if SCENARIOS_DIR.exists() else []
    return jsonify({"scenarios": scenarios})


@app.get("/api/scenario-map-catalog")
def scenario_map_catalog():
    if map_catalog is None:
        return jsonify({"ok": False, "error": "Katalog map scenariuszy niedostępny."}), 500
    return jsonify({"ok": True, "catalog": map_catalog()})


@app.get("/api/scenario-flows")
def list_scenario_flows():
    if list_scenario_flow_names is None:
        return jsonify({"ok": False, "error": "Obsługa scenario flow jest niedostępna."}), 500
    return jsonify({"ok": True, "scenario_flows": list_scenario_flow_names()})


@app.get("/api/heroes")
def list_heroes():
    if CharacterRepository is None:
        return jsonify({"ok": False, "error": "Brak repozytorium bohaterów."}), 500
    repo = CharacterRepository(HEROES_DIR)
    heroes = repo.list_characters()
    return jsonify({"ok": True, "heroes": heroes})


@app.post("/api/reset")
def reset_simulator():
    snapshot = _reset_board_state()
    logger.info("Zresetowano symulator planszy.")
    return jsonify({"ok": True, **snapshot})


@app.post("/api/encounters/generate")
def generate_encounter_api():
    if EncounterRequest is None or generate_encounter is None or preset_directives is None or EncounterDirectives is None:
        return jsonify({"ok": False, "error": "Generator encounterów niedostępny."}), 500
    payload: dict[str, Any] = request.get_json(force=True, silent=True) or {}
    try:
        scenario, metadata, setup_plan, _normalized = _build_encounter_response(payload)
    except Exception as exc:
        logger.exception("Błąd generowania encounteru")
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify(
        {
            "ok": True,
            "scenario": scenario,
            "metadata": metadata,
            "setup_plan": setup_plan,
        }
    )


@app.get("/api/runtime/status")
def runtime_status():
    return jsonify(_runtime_status_payload())


@app.post("/api/runtime/start")
def runtime_start():
    global runtime_process, runtime_info
    payload: dict[str, Any] = request.get_json(force=True, silent=True) or {}
    hero_ids_raw = payload.get("hero_ids") or []
    if not isinstance(hero_ids_raw, list):
        return jsonify({"ok": False, "error": "hero_ids musi być listą."}), 400
    hero_ids = [str(item or "").strip().lower() for item in hero_ids_raw if str(item or "").strip()]
    if not hero_ids:
        return jsonify({"ok": False, "error": "Wybierz co najmniej jednego bohatera."}), 400
    with runtime_lock:
        already_running = runtime_process is not None and runtime_process.poll() is None
    if already_running:
        return jsonify({"ok": False, "error": "Runtime gry już działa.", "runtime": _runtime_status_payload()}), 409
    try:
        scenario, metadata, setup_plan, normalized = _build_encounter_response(payload)
    except Exception as exc:
        logger.exception("Błąd przygotowania runtime encounteru")
        return jsonify({"ok": False, "error": str(exc)}), 400

    ui_host = "127.0.0.1"
    ui_port = _find_free_port(ui_host, int(payload.get("ui_port") or 5100))
    board_url = request.host_url.rstrip("/")
    cmd = [
        sys.executable,
        "main.py",
        "--start-ui",
        "--ui-host",
        ui_host,
        "--ui-port",
        str(ui_port),
        "--board-backend",
        "simulator",
        "--board-url",
        board_url,
        "--encounter-biome",
        normalized["biome"],
        "--encounter-threat",
        normalized["threat"],
        "--encounter-layout",
        normalized["layout"],
        "--encounter-formation-pack",
        normalized["formation_pack"],
        "--encounter-preset",
        normalized["preset"],
        "--encounter-seed",
        str(normalized["seed"]),
    ]
    for hero_id in hero_ids:
        cmd.extend(["--hero-id", hero_id])
    try:
        proc = subprocess.Popen(cmd, cwd=str(BASE_DIR.parent))
    except Exception as exc:
        logger.exception("Nie udało się uruchomić runtime gry")
        return jsonify({"ok": False, "error": str(exc)}), 500
    ui_url = f"http://{ui_host}:{ui_port}"
    with runtime_lock:
        runtime_process = proc
        runtime_info = {
            "ui_url": ui_url,
            "board_backend": "simulator",
            "board_url": board_url,
            "hero_ids": hero_ids,
            "encounter": normalized,
            "metadata": metadata,
        }
    logger.info("Uruchomiono runtime encounteru PID=%s UI=%s", proc.pid, ui_url)
    return jsonify(
        {
            "ok": True,
            "scenario": scenario,
            "metadata": metadata,
            "setup_plan": setup_plan,
            "runtime": _runtime_status_payload(),
        }
    )


@app.post("/api/runtime/start-scenario")
def runtime_start_scenario():
    global runtime_process, runtime_info
    payload: dict[str, Any] = request.get_json(force=True, silent=True) or {}
    scenario_name = str(payload.get("scenario") or "").strip()
    if not scenario_name:
        return jsonify({"ok": False, "error": "Pole 'scenario' jest wymagane."}), 400
    hero_ids_raw = payload.get("hero_ids") or []
    if not isinstance(hero_ids_raw, list):
        return jsonify({"ok": False, "error": "hero_ids musi być listą."}), 400
    hero_ids = [str(item or "").strip().lower() for item in hero_ids_raw if str(item or "").strip()]
    if not hero_ids:
        return jsonify({"ok": False, "error": "Wybierz co najmniej jednego bohatera."}), 400
    with runtime_lock:
        already_running = runtime_process is not None and runtime_process.poll() is None
    if already_running:
        return jsonify({"ok": False, "error": "Runtime gry już działa.", "runtime": _runtime_status_payload()}), 409

    ui_host = "127.0.0.1"
    ui_port = _find_free_port(ui_host, int(payload.get("ui_port") or 5100))
    board_url = request.host_url.rstrip("/")
    cmd = [
        sys.executable,
        "main.py",
        "--start-ui",
        "--ui-host",
        ui_host,
        "--ui-port",
        str(ui_port),
        "--board-backend",
        "simulator",
        "--board-url",
        board_url,
        "--scenario",
        scenario_name,
    ]
    for hero_id in hero_ids:
        cmd.extend(["--hero-id", hero_id])
    try:
        proc = subprocess.Popen(cmd, cwd=str(BASE_DIR.parent))
    except Exception as exc:
        logger.exception("Nie udało się uruchomić runtime scenariusza")
        return jsonify({"ok": False, "error": str(exc)}), 500

    ui_url = f"http://{ui_host}:{ui_port}"
    with runtime_lock:
        runtime_process = proc
        runtime_info = {
            "ui_url": ui_url,
            "board_backend": "simulator",
            "board_url": board_url,
            "hero_ids": hero_ids,
            "scenario": scenario_name,
            "scenario_kind": "flow_or_runtime",
        }
    logger.info("Uruchomiono runtime scenariusza %s PID=%s UI=%s", scenario_name, proc.pid, ui_url)
    return jsonify({"ok": True, "runtime": _runtime_status_payload()})


@app.post("/api/runtime/stop")
def runtime_stop():
    stopped = _stop_runtime_process()
    return jsonify({"ok": True, "stopped": stopped, "runtime": _runtime_status_payload()})


@app.get("/api/game-objects")
def list_game_objects():
    if scan_game_objects is None or serialize_meta is None:
        return jsonify({"ok": False, "error": "Brak loadera GameObjects."}), 500
    definitions = scan_game_objects(GAME_OBJECTS_DIR)
    metas = serialize_meta(definitions)
    categories: dict[str, list[dict[str, object]]] = {}
    for meta in metas:
        categories.setdefault(meta["category"], []).append(meta)
    grouped = [
        {"category": name, "objects": sorted(items, key=lambda obj: obj["label"] or "")}
        for name, items in sorted(categories.items(), key=lambda pair: pair[0])
    ]
    return jsonify({"ok": True, "categories": grouped})


@app.get("/api/scenarios/<name>")
def load_scenario(name: str):
    try:
        path = _scenario_path(name)
        if not path.exists():
            return jsonify({"ok": False, "error": "Scenariusz nie istnieje."}), 404
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return jsonify({"ok": True, "scenario": data})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:  # pragma: no cover - zabezpieczenie
        logger.exception("Błąd podczas wczytywania scenariusza")
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.get("/api/scenario-flows/<name>")
def load_scenario_flow_api(name: str):
    if load_scenario_flow is None:
        return jsonify({"ok": False, "error": "Obsługa scenario flow jest niedostępna."}), 500
    try:
        path = _scenario_flow_path(name)
        if not path.exists():
            return jsonify({"ok": False, "error": "Scenario flow nie istnieje."}), 404
        data = load_scenario_flow(path)
        return jsonify({"ok": True, "scenario_flow": data})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:  # pragma: no cover - zabezpieczenie
        logger.exception("Błąd podczas wczytywania scenario flow")
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.post("/api/scenarios/<name>")
def save_scenario(name: str):
    try:
        scenario_data = request.get_json(force=True, silent=True)
        if not isinstance(scenario_data, dict):
            return jsonify({"ok": False, "error": "Brak danych scenariusza."}), 400
        path = _scenario_path(name)
        with path.open("w", encoding="utf-8") as file:
            json.dump(scenario_data, file, ensure_ascii=False, indent=4)
        logger.info("Zapisano scenariusz do %s", path)
        return jsonify({"ok": True, "path": str(path)}), 201
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:  # pragma: no cover - zabezpieczenie
        logger.exception("Błąd podczas zapisu scenariusza")
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.post("/api/scenario-flows/<name>")
def save_scenario_flow_api(name: str):
    if load_scenario_flow is None or validate_scenario_flow is None:
        return jsonify({"ok": False, "error": "Obsługa scenario flow jest niedostępna."}), 500
    try:
        flow_data = request.get_json(force=True, silent=True)
        if not isinstance(flow_data, dict):
            return jsonify({"ok": False, "error": "Brak danych scenario flow."}), 400
        validated = validate_scenario_flow(flow_data)
        path = _scenario_flow_path(name)
        with path.open("w", encoding="utf-8") as file:
            json.dump(flow_data, file, ensure_ascii=False, indent=4)
        validated["_source_path"] = str(path)
        logger.info("Zapisano scenario flow do %s", path)
        return jsonify({"ok": True, "path": str(path), "scenario_flow": validated}), 201
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:  # pragma: no cover - zabezpieczenie
        logger.exception("Błąd podczas zapisu scenario flow")
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.get("/state")
def get_state():
    with state_lock:
        snapshot = [row[:] for row in board_state]
        version = state_version
    with pending_lock:
        waiting = pending_scans
    return jsonify(
        {
            "rows": BOARD_ROWS,
            "cols": BOARD_COLS,
            "state": snapshot,
            "version": version,
            "pending_scans": waiting,
        }
    )


@app.post("/simulate/click")
def simulate_click():
    payload: dict[str, Any] = request.get_json(force=True, silent=True) or {}
    try:
        row = int(payload["row"])
        col = int(payload["col"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"ok": False, "error": "row i col musza byc liczbami"}), 400

    if not (0 <= row < BOARD_ROWS and 0 <= col < BOARD_COLS):
        return (
            jsonify({"ok": False, "error": f"Pozycja ({row}, {col}) poza plansza."}),
            400,
        )

    click_queue.put({"row": row, "col": col})
    logger.info("Dodano klikniecie (%s, %s) do kolejki.", row, col)
    return jsonify({"ok": True})


@app.get("/scan_board")
def scan_board():
    global pending_scans
    with pending_lock:
        pending_scans += 1
    try:
        click = click_queue.get()
    finally:
        with pending_lock:
            pending_scans -= 1

    response = {
        "ok": True,
        "type": "key",
        "row": click["row"] + 1,
        "col": click["col"] + 1,
    }
    logger.info("Zwracam klikniecie: %s", response)
    return jsonify(response)


@app.post("/set")
def set_leds():
    global state_version
    payload: dict[str, Any] = request.get_json(force=True, silent=True) or {}
    leds = payload.get("leds", [])
    if not isinstance(leds, list):
        return jsonify({"ok": False, "error": "Brak listy leds."}), 400

    applied = 0
    with state_lock:
        for led in leds:
            if not isinstance(led, dict):
                continue
            try:
                idx1 = int(led["i"])
                rgb = list(led["rgb"])
            except (KeyError, TypeError, ValueError):
                continue

            led_index = idx1 - 1
            cell = LED_TO_CELL.get(led_index)
            if cell is None:
                continue

            row, col = cell
            if not (0 <= row < BOARD_ROWS and 0 <= col < BOARD_COLS):
                continue
            # Przycinamy kolory do zakresu 0-255 i tylko 3 pierwsze wartosci.
            rgb = [max(0, min(255, int(component))) for component in rgb[:3]]
            _set_cell_color(row, col, rgb)
            applied += 1

        if applied:
            state_version += 1

    logger.info("Zaktualizowano %s pol LED.", applied)
    return jsonify({"ok": True, "applied": applied})


@app.get("/off")
def leds_off():
    global state_version
    with state_lock:
        for row in range(BOARD_ROWS):
            for col in range(BOARD_COLS):
                _set_cell_color(row, col, None)
        state_version += 1

    logger.info("Wylaczono wszystkie pola.")
    return jsonify({"ok": True, "message": "all off"})


if __name__ == "__main__":
    logger.info(
        "Uruchamiam symulator planszy (%sx%s). Odwiedz http://127.0.0.1:5000", BOARD_ROWS, BOARD_COLS
    )
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
