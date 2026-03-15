from __future__ import annotations

import argparse
import logging
import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

import requests

# Ensure project `src/` is on sys.path so imports like `actions.*` work even
# when running the script directly (python main.py).
ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
for path in (ROOT_DIR, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from board import Connection
from src.game import Game
from src import ui_client
from src.character_creation import CharacterRepository, create_character
from src.ui_client import UIClient, UndoRequested, get_ui_client
from src.ui_payloads import build_active_actor_payload, build_hero_snapshot


logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def list_scenarios(directory: Path) -> list[str]:
    """Zwróć listę dostępnych scenariuszy (nazwy plików bez .json)."""
    if not directory.exists():
        logger.error("Katalog ze scenariuszami nie istnieje: %s", directory)
        return []
    return sorted(p.stem for p in directory.glob("*.json"))


def choose_scenario(scenarios: Iterable[str], ui: UIClient | None = None) -> str:
    """Wybierz scenariusz – najpierw przez UI, w razie braku fallback do CLI."""
    options = list(scenarios)
    if not options:
        raise SystemExit("Brak scenariuszy do wyboru.")

    # UI prompt (jeśli dostępny)
    if ui and ui.enabled:
        answer = ui.prompt_choice("Wybierz scenariusz", options, source="main")
        if answer in options:
            return answer
        logger.info("UI nie zwróciło wyboru, przełączam na wybór w konsoli.")

    # Fallback CLI
    print("Wybierz scenariusz:")
    for idx, name in enumerate(options, start=1):
        print(f"  {idx}) {name}")
    while True:
        raw = input("> ").strip()
        if raw in options:
            return raw
        try:
            num = int(raw)
            if 1 <= num <= len(options):
                return options[num - 1]
        except ValueError:
            pass
        print("Nieprawidłowy wybór, spróbuj ponownie.")


def _decode_menu_choice(raw: str | None, options: list[dict[str, str]]) -> str | None:
    text = str(raw or "").strip()
    if not text:
        return None
    by_id = {str(item["id"]).strip().lower(): str(item["id"]).strip().lower() for item in options}
    by_label = {str(item["label"]).strip().lower(): str(item["id"]).strip().lower() for item in options}
    by_key = {
        str(item.get("key") or "").strip().lower(): str(item["id"]).strip().lower()
        for item in options
        if str(item.get("key") or "").strip()
    }
    low = text.lower()
    if low in by_id:
        return by_id[low]
    if low in by_label:
        return by_label[low]
    if low in by_key:
        return by_key[low]
    if text.isdigit():
        idx = int(text) - 1
        if 0 <= idx < len(options):
            return str(options[idx]["id"]).strip().lower()
    return None


def choose_start_action(ui: UIClient | None = None) -> str:
    options = [
        {"id": "play", "label": "Graj", "desc": "Przejdź do wyboru scenariusza i startu gry."},
        {"id": "create", "label": "Stwórz postać", "desc": "Uruchom pipeline tworzenia postaci."},
    ]
    subtitle = "8/2 nawigacja, Enter potwierdzenie."
    if ui and ui.enabled:
        choice_meta = [
            {
                "raw": item["id"],
                "label": item["label"],
                "desc": item["desc"],
                "key": "",
            }
            for item in options
        ]
        answer = ui.prompt_choice(
            "Start",
            choices=[item["label"] for item in options],
            source="main",
            layout="menu_numpad",
            title="Start",
            subtitle=subtitle,
            choice_meta=choice_meta,
        )
        decoded = _decode_menu_choice(answer, options)
        if decoded in {"play", "create"}:
            return decoded
        logger.info("UI nie zwróciło poprawnego wyboru, domyślnie: Graj.")
        return "play"

    print("Start:")
    print("  1) Graj")
    print("  2) Stwórz postać")
    while True:
        raw = input("> ").strip()
        decoded = _decode_menu_choice(
            raw,
            [
                {"id": "play", "label": "Graj", "key": "1"},
                {"id": "create", "label": "Stwórz postać", "key": "2"},
            ],
        )
        if decoded in {"play", "create"}:
            return decoded
        print("Nieprawidłowy wybór, spróbuj ponownie.")


@dataclass
class _CharacterCreationGame:
    ui: UIClient | None

    def ui_event(self, event_type: str, payload: dict[str, Any]) -> bool:
        if not self.ui or not self.ui.enabled:
            return False
        try:
            return bool(self.ui.send_event(event_type, payload))
        except Exception:
            return False

    def ui_log(self, message: str) -> None:
        text = str(message)
        logger.info(text)
        self.ui_event("log", {"message": text, "source": "character_creation"})

    def ui_hero(self, hero: Any, note: str | None = None) -> None:
        if hero is None:
            return
        self.ui_event("hero_snapshot", build_hero_snapshot(hero, note=note))

    def ui_active_actor(self, actor: Any | None) -> None:
        self.ui_event(
            "active_actor_changed",
            build_active_actor_payload(actor, default_kind="hero"),
        )


def default_game_loop(game: Game) -> None:
    """Prosty loop: setup bohaterów, potem kolejne wybory akcji."""
    game.run_action("set_heroes_starting_positions")
    while True:
        game.run_action("choose_action")


def _find_free_port(host: str, preferred: int, attempts: int = 10) -> int:
    """Znajdź wolny port zaczynając od preferred na wskazanym hoście."""
    for offset in range(attempts):
        candidate = preferred + offset
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, candidate))
                return candidate
            except OSError:
                continue
    return preferred


def start_ui_server(host: str = "127.0.0.1", port: int = 5100) -> tuple[subprocess.Popen, int]:
    """Uruchom Flask UI w tle."""
    env = os.environ.copy()
    env["PLAYER_UI_HOST"] = host
    env["PLAYER_UI_PORT"] = str(port)
    env["PLAYER_UI_URL"] = f"http://{host}:{port}"
    # gdy uruchamiamy z main.py nie otwieraj automatycznie przeglądarki
    env["PLAYER_UI_NO_BROWSER"] = "1"
    # wyłącz debug/reloader żeby nie podnosić dwóch procesów
    env["FLASK_DEBUG"] = "0"
    cmd = [sys.executable, "player_ui/app.py"]
    proc = subprocess.Popen(cmd, env=env)
    return proc, port


def wait_for_ui(url: str, retries: int = 20, delay: float = 0.4) -> bool:
    for _ in range(retries):
        try:
            resp = requests.get(url, timeout=1.5)
            if resp.ok:
                return True
        except Exception:
            pass
        time.sleep(delay)
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Uruchom główną pętlę gry.")
    parser.add_argument("--scenario", help="Nazwa scenariusza (bez .json). Jeśli brak – zapytamy w UI/CLI.")
    parser.add_argument(
        "--scenarios-dir",
        type=Path,
        default=Path("scenarios"),
        help="Katalog z plikami scenariuszy JSON.",
    )
    parser.add_argument(
        "--esp-ip",
        help="Adres HTTP ESP. Jeśli nie podasz, użyjemy domyślnego z board/consts.py.",
    )
    parser.add_argument(
        "--start-ui",
        action="store_true",
        help="Uruchom UI gracza w tle przed startem gry.",
    )
    parser.add_argument(
        "--ui-port",
        type=int,
        default=5100,
        help="Port UI gracza (domyślnie 5100). Przy konflikcie spróbujemy następnych portów.",
    )
    parser.add_argument(
        "--ui-host",
        default="127.0.0.1",
        help="Host UI gracza (domyślnie 127.0.0.1).",
    )
    args = parser.parse_args(argv)
    # Debug trace włączony domyślnie dla aktywnego developmentu/testów.
    os.environ["GAME_DEBUG_TRACE"] = "1"

    ui = get_ui_client()
    ui_proc: subprocess.Popen | None = None
    ui_port = args.ui_port

    if args.start_ui:
        ui_port = _find_free_port(args.ui_host, args.ui_port)
        ui_base = f"http://{args.ui_host}:{ui_port}"
        logger.info("Uruchamiam UI gracza na %s...", ui_base)
        ui_proc, ui_port = start_ui_server(host=args.ui_host, port=ui_port)
        if wait_for_ui(ui_base):
            logger.info("UI dostępne pod %s", ui_base)
        else:
            logger.warning("Nie udało się potwierdzić działania UI pod %s", ui_base)
        # zmień klienta na lokalny UI
        ui = UIClient(base_url=ui_base)
        ui_client.set_default_ui_client(ui)
        # nadpisz też ewentualne stare wartości env, by kolejne instancje używały właściwego adresu
        os.environ["PLAYER_UI_URL"] = ui_base

    scenarios = list_scenarios(args.scenarios_dir)

    if args.scenario:
        scenario_name = args.scenario
    else:
        repo = CharacterRepository(ROOT_DIR / "data" / "heroes")
        creation_game = _CharacterCreationGame(ui=ui)
        while True:
            try:
                action = choose_start_action(ui)
            except UndoRequested:
                logger.info("Cofnij jest dostępne tylko w trakcie aktywnej akcji gry.")
                continue
            if action == "create":
                try:
                    created = create_character(creation_game, repo)
                except UndoRequested:
                    logger.info("Cofnij w kreatorze postaci poza akcją gry zostało zignorowane.")
                    continue
                if created is None:
                    logger.info("Tworzenie postaci przerwane.")
                else:
                    logger.info("Postać zapisana: %s", getattr(created.hero, "name", "Bohater"))
                continue
            try:
                scenario_name = choose_scenario(scenarios, ui)
            except UndoRequested:
                logger.info("Cofnij nie działa na ekranie wyboru scenariusza.")
                continue
            break

    if ui and ui.enabled:
        ui.send_event("info", {"message": f"Start scenariusza: {scenario_name}", "source": "main"})

    conn = Connection(esp_ip=args.esp_ip) if args.esp_ip else None
    game = Game(conn=conn, scenario=scenario_name)
    logger.info("Uruchamiam scenariusz: %s", scenario_name)

    try:
        default_game_loop(game)
    except KeyboardInterrupt:
        logger.info("Przerwano przez użytkownika.")
    finally:
        try:
            game.conn.leds_off()
        except Exception:
            pass
        if ui_proc is not None:
            ui_proc.terminate()
            try:
                ui_proc.wait(timeout=2)
            except Exception:
                ui_proc.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
