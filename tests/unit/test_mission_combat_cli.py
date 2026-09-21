"""Quick-start arguments use real mission transitions and isolated storage."""
from pathlib import Path

import pytest

from dnd_board_game.application.party_ethos import read
from dnd_board_game.runtime import mission_combat_ui as cli
from dnd_board_game.ui.exploration_app import create_app


@pytest.mark.parametrize('start_at,heroes,morality', [
    ('intro', ('brakka','nimra','mira'), 1),
    ('setup', ('mira','nimra','garran'), -3),
    ('initiative', ('dagna','lorian','brakka','erynd'), 0),
    ('combat', ('nimra','mira','garran','dagna','lorian','erynd'), 2),
])
def test_cli_start_modes_party_stance_and_deck(tmp_path: Path, start_at: str,
                                             heroes: tuple[str,...], morality: int) -> None:
    game = cli.create_session(heroes=heroes, morality=morality, start_at=start_at, runtime_dir=tmp_path)
    assert tuple(str(actor.id) for actor in game.custom_party) == heroes
    assert read(game.state.flags).position == 3 + morality
    assert game.configured_board_backend == 'none' and game.board_adapter is None
    assert game.save_dir == tmp_path / 'saves'
    assert game.observation_dir == tmp_path / 'observations'
    client = create_app(game, character_dir=tmp_path/'characters').test_client()
    assert client.get('/play').status_code == 200
    view = client.get('/api/state').json
    assert view['party_ethos']['total'] == len(heroes)*10 - 2*abs(morality)
    if start_at == 'intro':
        assert view['mission']['stage'] == 'arrival'
        assert view['mission']['text']['id'] == 'arrival'
        assert view['mission']['reading']
        assert game.encounter_setup_flow is None and game.combat_state is None
        game.load_snapshot()
        assert read(game.state.flags).position == 4
        result = client.post('/api/board/select', json={'col':19,'row':1})
        assert result.status_code == 200
        assert result.json['mission']['stage'] == 'battle'
        assert result.json['encounter_setup']['status'] == 'active'
    elif start_at == 'setup':
        assert view['mission']['stage'] == 'battle'
        assert not game.encounter_setup_flow.completed
        assert game.encounter_initiative_flow is None and game.combat_state is None
    else:
        assert game.encounter_setup_flow.completed
        assigned = game.encounter_setup_flow.player_start_assignments
        assert len(set(assigned.values())) == len(heroes)
        assert {str(actor.id):actor.position for actor in game.encounter_setup_flow.encounter.actors if str(actor.id) in heroes} == assigned
        if start_at == 'initiative':
            assert game.combat_state is None
            assert tuple(str(p.actor.id) for p in game.encounter_initiative_flow.prompts) == heroes
            assert game.encounter_initiative_flow.roll_panel.values == (10,)
            assert view['board_selection']['mode'] == 'initiative_roll'
        else:
            pool = game.combat_state.shared_mana.pooled
            assert pool.phase == 'setup'
            assert pool.excluded == ('B','B','N','N')
            assert pool.total == 56
            assert game.snapshot_path.is_file()
            game.load_snapshot()
            assert game.combat_state.shared_mana.pooled == pool
            assert read(game.state.flags).position == 5


@pytest.mark.parametrize('arguments', [
    ['--morality','4'], ['--morality','-4'], ['--morality','1.5'],
    ['--heroes','garran'], ['--heroes','garran','garran','nimra'],
    ['--heroes','garran','nimra','unknown'],
    ['--heroes','garran','brakka','mira','dagna','lorian','nimra','erynd'],
    ['--start-at','narration'],
])
def test_invalid_cli_arguments_fail_before_creating_session(monkeypatch: pytest.MonkeyPatch, arguments: list[str]) -> None:
    def forbidden(**kwargs: object) -> None:
        pytest.fail('Invalid arguments must not create a session')
    monkeypatch.setattr(cli, 'create_session', forbidden)
    with pytest.raises(SystemExit) as error:
        cli.main(arguments)
    assert error.value.code == 2


def test_main_connects_only_requested_backend_and_shuts_down(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                          capsys: pytest.CaptureFixture[str]) -> None:
    captured: dict = {}
    class App:
        def run(self, **kwargs: object) -> None:
            captured['run'] = kwargs
    def app(game: cli.ExplorationUiSession, **kwargs: object) -> App:
        captured['game'] = game
        captured['app'] = kwargs
        return App()
    monkeypatch.setattr(cli, 'create_app', app)
    monkeypatch.setattr(cli.ExplorationUiSession, 'configure_board', lambda self, **kwargs: captured.update(board=kwargs))
    monkeypatch.setattr(cli.ExplorationUiSession, 'shutdown_board', lambda self: captured.update(closed=True))
    assert cli.main(['--heroes','nimra','garran','mira','--ethos','-1','--start-at','initiative',
                     '--runtime-dir',str(tmp_path),'--board-backend','hardware','--port','5299']) == 0
    assert captured['board']['board_serial_port'] == ''
    assert captured['board']['backend'] == 'hardware'
    assert captured['closed']
    assert captured['run'] == dict(host='127.0.0.1', port=5299, debug=False, use_reloader=False)
    assert captured['app']['character_dir'] == tmp_path/'characters'
    output = capsys.readouterr().out
    assert 'Solidarność 1/3' in output and 'http://127.0.0.1:5299/play' in output
    assert 'Automatyczne ustawienie figurek' in output


def test_seed_reproduces_automatic_initiative(tmp_path: Path) -> None:
    def rolls(folder: str) -> list[tuple[str, int]]:
        game = cli.create_session(heroes=('brakka','nimra','mira'), morality=0,
                                  start_at='combat', runtime_dir=tmp_path/folder, seed=23)
        return [(str(entry.actor.id), entry.roll.natural_roll) for entry in game.encounter_initiative_flow.entries]
    assert rolls('first') == rolls('second')


def test_default_cli_starts_after_cart_scene() -> None:
    args = cli.build_parser().parse_args([])
    assert args.start_at == 'intro'
    assert args.heroes == ['brakka','garran','nimra']
    assert args.morality == 0
