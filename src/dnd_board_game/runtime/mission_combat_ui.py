"""Start the Mission 0 battle with a chosen party and stance, without its prologue."""
from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path
import sys
from tempfile import mkdtemp

from dnd_board_game.application.party_ethos import apply_choice, read as read_ethos
from dnd_board_game.application.recruitment_arena import HERO_ORDER
from dnd_board_game.rules.dice import RollMode
from dnd_board_game.ui import mission_zero
from dnd_board_game.ui.exploration_app import ExplorationUiSession, create_app
from dnd_board_game.ui.training_arena import training_hero

PACK = Path(__file__).resolve().parents[3] / 'content/scenarios/misja_0_dzwon'
STARTS = ('intro', 'setup', 'initiative', 'combat')


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Szybki start walki Misji 0 z wybraną drużyną i postawą.')
    parser.add_argument('--heroes', nargs='+', choices=HERO_ORDER, default=['brakka', 'garran', 'nimra'],
                        help='3–6 różnych bohaterów, w kolejności przygotowania i rzutów.')
    parser.add_argument('--morality', '--ethos', type=int, choices=range(-3, 4), default=0,
                        help='−3…−1: Solidarność; 0: Równowaga; 1…3: Bezwzględność.')
    parser.add_argument('--start-at', choices=STARTS, default='intro',
                        help='intro: przybycie po scenie z wozem (domyślnie); setup: rozstawianie; initiative: rzuty graczy; combat: pierwsza runda.')
    parser.add_argument('--seed', type=int, default=7, help='Ziarno automatycznych rzutów inicjatywy i przeciwników.')
    parser.add_argument('--runtime-dir', type=Path, help='Katalog zapisów i logów; domyślnie nowy /tmp/mission0-combat-…')
    parser.add_argument('--board-backend', choices=('none', 'simulator', 'hardware'), default='none')
    parser.add_argument('--board-url', default='http://127.0.0.1:5000')
    parser.add_argument('--board-serial-port', default='', help='Pusty: automatyczne wyszukiwanie planszy USB.')
    parser.add_argument('--wled-url', default='')
    parser.add_argument('--scan-timeout', type=float, default=30.0)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=5201)
    return parser


def validate_party(heroes: tuple[str, ...]) -> None:
    if not 3 <= len(heroes) <= 6:
        raise ValueError('Walka Misji 0 ma warianty dla 3–6 bohaterów.')
    if len(set(heroes)) != len(heroes):
        raise ValueError('Każdy bohater może wystąpić w drużynie tylko raz.')
    if any(hero not in HERO_ORDER for hero in heroes):
        raise ValueError('Nieznany bohater. Dostępni: ' + ', '.join(HERO_ORDER))


def create_session(*, heroes: tuple[str, ...], morality: int, start_at: str,
                   runtime_dir: Path, seed: int = 7) -> ExplorationUiSession:
    validate_party(heroes)
    if type(morality) is not int or not -3 <= morality <= 3:
        raise ValueError('Postawa musi być liczbą całkowitą od −3 do 3.')
    if start_at not in STARTS:
        raise ValueError('Wybierz etap intro, setup, initiative albo combat.')
    session = ExplorationUiSession(
        PACK / 'scenario.json', save_dir=runtime_dir / 'saves',
        observation_dir=runtime_dir / 'observations', automatic_checkpoints=True,
    )
    # A headless debug launch must not reconnect hardware from the normal UI's defaults.
    session.configure_custom_party(tuple(training_hero(hero) for hero in heroes))
    session.configured_board_backend = 'none'
    mission_zero.initialize(session)
    session.encounter_rng.seed(seed)
    for index in range(abs(morality)):
        session.state = replace(session.state, flags=apply_choice(
            session.state.flags, f'debug_battle_stance:{index}',
            'ruthlessness' if morality > 0 else 'solidarity',
        ))
    mission = mission_zero.read(session)
    mission.update(stage='arrival', equipment_locked=True)
    mission_zero.write(session, mission)
    mission_zero.checkpoint(session, mission)
    if start_at != 'intro':
        mission_zero.command(session, {'action': 'battle', 'revision': mission['revision']})
    if start_at in ('initiative', 'combat'):
        flow = session.encounter_setup_flow
        assert flow is not None
        while not flow.completed:
            if flow.is_player_start_step:
                session.assign_encounter_player_start_position(flow.remaining_player_start_positions()[0])
            else:
                session.confirm_encounter_setup_step()
        session.start_encounter_initiative()
        if start_at == 'combat':
            initiative = session.encounter_initiative_flow
            assert initiative is not None
            while (prompt := initiative.current_prompt) is not None:
                first = session.encounter_rng.randint(1, 20)
                second = session.encounter_rng.randint(1, 20) if prompt.request.mode != RollMode.NORMAL else None
                session.submit_encounter_initiative_roll(first, second)
    session._record('debug_mission_battle_started', dict(
        heroes=list(heroes), morality=morality, start_at=start_at, seed=seed,
    ))
    if start_at == 'combat':
        session.save_snapshot()
    return session


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        validate_party(tuple(args.heroes))
    except ValueError as error:
        parser.error(str(error))
    runtime_dir = args.runtime_dir or Path(mkdtemp(prefix='mission0-combat-'))
    session = create_session(heroes=tuple(args.heroes), morality=args.morality,
                             start_at=args.start_at, runtime_dir=runtime_dir, seed=args.seed)
    try:
        session.configured_board_backend = args.board_backend
        if args.board_backend != 'none':
            session.configure_board(backend=args.board_backend, board_url=args.board_url,
                                    board_serial_port=args.board_serial_port, wled_url=args.wled_url,
                                    scan_timeout_s=args.scan_timeout)
        app = create_app(session, character_dir=runtime_dir / 'characters')
        ethos = read_ethos(session.state.flags)
        print(f"Drużyna: {', '.join(args.heroes)} | {ethos.label} {abs(args.morality)}/3 | etap: {args.start_at}")
        print(f'Zapisy i logi: {runtime_dir.resolve()}')
        if args.start_at in ('initiative', 'combat'):
            encounter = session.encounter_setup_flow.encounter
            print('Automatyczne ustawienie figurek (kolumna, wiersz): ' + '; '.join(
                f'{actor.name}: {actor.position.as_tuple()}' for actor in encounter.actors))
        print(f'Walka Misji 0: http://{args.host}:{args.port}/play', flush=True)
        app.run(host=args.host, port=args.port, debug=False, use_reloader=False)
    finally:
        try:
            session.shutdown_board()
        except Exception as error:  # pragma: no cover - physical transport failure
            print(f'Nie udało się rozłączyć planszy: {error}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
