from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from queue import Queue
from threading import Lock
from typing import Any

from flask import Flask, jsonify, render_template, request

BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = BASE_DIR / "config.json"
LED_POSITIONS_PATH = BASE_DIR / "led_positions.json"
SCENARIOS_DIR = BASE_DIR.parent / "scenarios"
SRC_DIR = BASE_DIR.parent / "src"
GAME_OBJECTS_DIR = SRC_DIR / "GameObjects"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder="static", template_folder="templates")


def _load_board_config() -> tuple[int, int]:
    if not CONFIG_PATH.exists():
        logger.warning("Nie znaleziono pliku config.json, uzywam wartosci domyslnych 15x20.")
        return 15, 20
    with CONFIG_PATH.open("r", encoding="utf-8") as cfg_file:
        config_data = json.load(cfg_file)
    return config_data.get("n_rows", 15), config_data.get("n_cols", 20)


def _load_led_mapping(rows: int, cols: int) -> dict[int, tuple[int, int]]:
    """Zamien mapowanie (row, col) -> led na odwrotne."""
    with LED_POSITIONS_PATH.open("r", encoding="utf-8") as led_file:
        led_positions: dict[str, dict[str, int]] = json.load(led_file)

    outer_count = len(led_positions)
    inner_count = len(next(iter(led_positions.values())))

    if outer_count == rows and inner_count == cols:
        logger.info("LED mapping dopasowano bez transponowania (%s x %s).", rows, cols)

        def to_cell(outer_key: str, inner_key: str) -> tuple[int, int]:
            return int(outer_key), int(inner_key)

    elif outer_count == cols and inner_count == rows:
        logger.info("LED mapping wymaga transpozycji (%s x %s).", rows, cols)

        def to_cell(outer_key: str, inner_key: str) -> tuple[int, int]:
            # Obsługa niezgodności kolejności wymiarów w pliku konfiguracyjnym.
            return int(inner_key), int(outer_key)

    else:
        raise ValueError(
            f"Nieoczekiwany rozmiar mapowania LED ({outer_count} x {inner_count}) "
            f"dla planszy {rows} x {cols}."
        )

    led_to_cell: dict[int, tuple[int, int]] = {}
    for outer_key, inner_values in led_positions.items():
        for inner_key, led_index in inner_values.items():
            led_to_cell[int(led_index)] = to_cell(outer_key, inner_key)

    return led_to_cell


def _scenario_path(name: str) -> Path:
    safe_name = Path(name).stem  # usuń rozszerzenia / ścieżki
    if not safe_name:
        raise ValueError("Nazwa scenariusza jest wymagana.")
    if "/" in name or "\\" in name:
        raise ValueError("Nazwa scenariusza nie może zawierać separatorów katalogów.")
    SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)
    return SCENARIOS_DIR / f"{safe_name}.json"


if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
try:
    from game_objects_loader import scan_game_objects, serialize_meta
except Exception as exc:  # pragma: no cover - zabezpieczenie gdy pakiet nie istnieje
    logger.warning("Nie udało się zaimportować game_objects_loader: %s", exc)
    scan_game_objects = None  # type: ignore
    serialize_meta = None  # type: ignore


BOARD_ROWS, BOARD_COLS = _load_board_config()
LED_TO_CELL = _load_led_mapping(BOARD_ROWS, BOARD_COLS)

board_state: list[list[list[int] | None]] = [
    [None for _ in range(BOARD_COLS)] for _ in range(BOARD_ROWS)
]
state_lock = Lock()
state_version = 0
pending_scans = 0
pending_lock = Lock()
click_queue: "Queue[dict[str, int]]" = Queue()


def _set_cell_color(row: int, col: int, rgb: list[int] | None) -> None:
    board_state[row][col] = rgb[:] if rgb is not None else None


@app.route("/")
def index():
    return render_template("index.html", rows=BOARD_ROWS, cols=BOARD_COLS)


@app.route("/scenario-editor")
def scenario_editor():
    return render_template("scenario_editor.html", rows=BOARD_ROWS, cols=BOARD_COLS)


@app.get("/api/scenarios")
def list_scenarios():
    scenarios = sorted(path.stem for path in SCENARIOS_DIR.glob("*.json")) if SCENARIOS_DIR.exists() else []
    return jsonify({"scenarios": scenarios})


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
