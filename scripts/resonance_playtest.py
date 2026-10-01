"""Isolated manual charge-combat test; skips story, keeps physical board setup."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from tempfile import mkdtemp
from threading import Thread

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from werkzeug.serving import make_server
from dnd_board_game.ui.exploration_app import ExplorationUiSession
from dnd_board_game.ui.routes import create_app
from dnd_board_game.ui.training_arena import training_hero
from dnd_board_game.ui import mission_zero


def prepare_session(folder: Path, heroes: tuple[str, ...], *, skip_setup: bool = False) -> ExplorationUiSession:
    if not 3 <= len(heroes) <= 6 or len(set(heroes)) != len(heroes):
        raise ValueError("Wybierz od 3 do 6 różnych bohaterów.")
    game = ExplorationUiSession(ROOT / "content/scenarios/misja_0_dzwon/scenario.json",
                               save_dir=folder / "saves", observation_dir=folder / "observations")
    game.configure_custom_party(tuple(training_hero(hero) for hero in heroes))
    mission_zero.initialize(game)
    mission = mission_zero.read(game)
    mission.update(stage="arrival", fatigue=0)
    mission_zero.write(game, mission)
    mission_zero.command(game, dict(action="battle", revision=mission_zero.read(game)["revision"]))
    if skip_setup:
        while not game.encounter_setup_flow.completed:
            flow = game.encounter_setup_flow
            if flow.is_player_start_step:
                game.assign_encounter_player_start_position(flow.remaining_player_start_positions()[0])
            else:
                game.confirm_encounter_setup_step()
        game.start_encounter_initiative()
        for i in range(len(heroes)):
            game.submit_encounter_initiative_roll(20-i)
    return game


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--heroes", nargs="+", default=["garran", "brakka", "mira", "dagna", "lorian", "nimra"])
    parser.add_argument("--port", type=int, default=5201)
    parser.add_argument("--board-port", type=int, default=5001)
    parser.add_argument("--runtime", type=Path, help="Opcjonalny osobny katalog zapisów testu; domyślnie nowy katalog /tmp.")
    parser.add_argument("--hardware", action="store_true", help="Zamiast lokalnego symulatora połącz wskazaną planszę.")
    parser.add_argument("--serial-port", default="")
    parser.add_argument("--wled-url", default="")
    parser.add_argument("--skip-setup", action="store_true", help="Tylko symulator: automatyczne ustawienie i inicjatywa.")
    parser.add_argument("--check", action="store_true", help="Sprawdź przygotowanie bez uruchamiania serwerów i sprzętu.")
    args = parser.parse_args()
    if args.hardware and (not args.serial_port or not args.wled_url or args.skip_setup):
        parser.error("Sprzęt wymaga --serial-port i --wled-url oraz ręcznego setupu.")
    folder = args.runtime or Path(mkdtemp(prefix="resonance-playtest-"))
    game = prepare_session(folder, tuple(args.heroes), skip_setup=args.skip_setup or args.check)
    if args.check:
        assert game.combat_state and game.combat_state.resonance
        print(f"OK: {len(args.heroes)} bohaterów, profil Ładunki i Rezonans. Dane testu: {folder}")
        return
    simulator = worker = server = None
    try:
        if args.hardware:
            game.configure_board(backend="hardware", board_serial_port=args.serial_port, wled_url=args.wled_url)
        else:
            from board.simulator.app import app as board_app
            simulator = make_server("127.0.0.1", args.board_port, board_app, threaded=True)
            worker = Thread(target=simulator.serve_forever, daemon=True)
            worker.start()
            game.configure_board(backend="simulator", board_url=f"http://127.0.0.1:{args.board_port}")
            print(f"Plansza: http://127.0.0.1:{args.board_port}", flush=True)
        server = make_server("127.0.0.1", args.port, create_app(game, character_dir=folder / "characters"), threaded=True)
        print(f"Gra: http://127.0.0.1:{args.port}/play\nZapisy testu: {folder}\nCtrl+C kończy test. Zwykłe zapisy gry pozostają nietknięte.", flush=True)
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


if __name__ == "__main__":
    main()
