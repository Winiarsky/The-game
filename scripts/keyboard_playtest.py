"""Run an isolated keyboard + LED session, with the real game and optional WLED."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from tempfile import mkdtemp
from threading import Thread

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from werkzeug.serving import make_server

from dnd_board_game.character_creation import PLAYABLE_HERO_IDS
from dnd_board_game.ui import mission_zero
from dnd_board_game.ui.exploration_app import ExplorationUiSession
from dnd_board_game.ui.routes import create_app
from dnd_board_game.ui.training_arena import training_hero
from scripts.install_default_roster import install_default_roster
from scripts.resonance_playtest import prepare_session as prepare_battle


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--heroes", nargs="+", choices=PLAYABLE_HERO_IDS,
                        default=["garran", "brakka", "nimra"])
    parser.add_argument("--arena", action="store_true", help="Zacznij od walki Misji 0 zamiast początku misji.")
    parser.add_argument("--skip-setup", action="store_true", help="Tylko --arena z symulatorem: automatyczny setup i inicjatywa.")
    parser.add_argument("--wled-url", default="", help="Adres prawdziwych LED-ów; pusty uruchamia podgląd symulatora.")
    parser.add_argument("--port", type=int, default=5202)
    parser.add_argument("--board-port", type=int, default=5002)
    parser.add_argument("--runtime", type=Path, help="Osobny katalog testu; domyślnie nowy /tmp/keyboard-led-…")
    parser.add_argument("--check", action="store_true", help="Sprawdź przygotowanie bez serwerów i połączeń sprzętowych.")
    return parser


def prepare_session(folder: Path, heroes: tuple[str, ...], *, arena: bool = False,
                    skip_setup: bool = False) -> ExplorationUiSession:
    if not 3 <= len(heroes) <= 6 or len(set(heroes)) != len(heroes):
        raise ValueError("Wybierz od 3 do 6 różnych bohaterów.")
    if set(heroes) - set(PLAYABLE_HERO_IDS):
        raise ValueError("Wybierz bohaterów z katalogu siedmiu postaci.")
    if skip_setup and not arena:
        raise ValueError("Automatyczny setup jest dostępny tylko w trybie --arena.")
    if arena:
        game = prepare_battle(folder, heroes, skip_setup=skip_setup)
    else:
        game = ExplorationUiSession(
            ROOT / "content/scenarios/misja_0_dzwon/scenario.json",
            save_dir=folder / "saves", observation_dir=folder / "observations",
            automatic_checkpoints=True,
        )
        game.configure_custom_party(tuple(training_hero(hero) for hero in heroes))
        mission_zero.initialize(game)
    game.configured_board_backend = "none"
    game.configure_input_mode("keyboard")
    return game


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.skip_setup and (not args.arena or args.wled_url):
        parser.error("--skip-setup wymaga --arena i symulatora; prawdziwą planszę rozstaw ręcznie.")
    if not 1 <= args.port <= 65535 or not 1 <= args.board_port <= 65535:
        parser.error("Porty muszą mieścić się w zakresie 1–65535.")
    if not args.wled_url and args.port == args.board_port:
        parser.error("Gra i symulator muszą używać różnych portów.")
    folder = args.runtime or Path(mkdtemp(prefix="keyboard-led-"))
    try:
        game = prepare_session(folder, tuple(args.heroes), arena=args.arena, skip_setup=args.skip_setup)
    except ValueError as error:
        parser.error(str(error))
    if args.check:
        print(f"OK: klawiatura + LED, {len(args.heroes)} bohaterów, "
              f"{'walka' if args.arena else 'pełna Misja 0'}. Dane testu: {folder}")
        return 0
    simulator = server = worker = None
    try:
        install_default_roster(folder / "characters", ROOT / "assets/character_portraits/default_roster_v2")
        if args.wled_url:
            game.configured_board_backend = "wled"
            game.configure_board(backend="wled", wled_url=args.wled_url)
        else:
            from board.simulator.app import app as board_app
            simulator = make_server("127.0.0.1", args.board_port, board_app, threaded=True)
            worker = Thread(target=simulator.serve_forever, daemon=True)
            worker.start()
            game.configured_board_backend = "simulator"
            game.configure_board(backend="simulator", board_url=f"http://127.0.0.1:{args.board_port}")
            print(f"Podgląd LED: http://127.0.0.1:{args.board_port}", flush=True)
        server = make_server("127.0.0.1", args.port,
                             create_app(game, character_dir=folder / "characters"), threaded=True)
        print(f"Gra: http://127.0.0.1:{args.port}/play\n"
              f"Menu: http://127.0.0.1:{args.port}/\n"
              f"Dane testu: {folder.resolve()}\n"
              "M: ruch · strzałki: podgląd · Enter: zatwierdź · Esc: wróć · I: ekwipunek · R: runy\n"
              "Ctrl+C zamyka test i wygasza LED-y.", flush=True)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        game.shutdown_board()
        if server:
            server.server_close()
        if simulator:
            simulator.shutdown()
            simulator.server_close()
        if worker:
            worker.join(timeout=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
