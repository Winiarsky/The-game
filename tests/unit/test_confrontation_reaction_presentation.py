"""The end-of-round response belongs to the scene, not its last hero."""
from dataclasses import replace
from pathlib import Path

import pytest

from dnd_board_game.rules import confrontation as r
from dnd_board_game.ui import confrontation as c, mission_zero as mission
from dnd_board_game.ui.exploration_app import ExplorationUiSession
from dnd_board_game.ui.training_arena import training_hero
from tests.unit.test_confrontation import charged
from tests.unit.test_confrontation_presentation import choose_approaches, command
from tests.unit.test_mission_zero import session, stage, send


def reaction_session(tmp_path: Path, scene_name: str = 'nessa', round_number: int = 1) -> ExplorationUiSession:
    s = session(tmp_path)
    s.configure_custom_party(tuple(training_hero(h) for h in ('brakka', 'garran', 'nimra')))
    mission.initialize(s)
    stage(s, 'road' if scene_name == 'cart' else 'brief')
    send(s, 'cart' if scene_name == 'cart' else 'negotiate')
    command(s, 'acknowledge')
    choose_approaches(s)
    command(s, 'acknowledge')
    store = c.read_store(s)
    state = charged(r.Confrontation.from_data(store['current']['state']), {'nimra': ('B',)})
    state = replace(state, turn=2, stage='after_action', round=round_number,
                    mana=replace(state.mana, actor='nimra'), last='Nimra: zakończony test.')
    store['current']['state'] = state.to_data()
    c.write(s, store)
    return s


@pytest.mark.parametrize('scene_name', ['nessa', 'cart'])
@pytest.mark.parametrize('round_number', [1, 2, 3])
def test_reaction_identity_survives_cost_reload_and_clears_on_next_round(
    tmp_path: Path, scene_name: str, round_number: int,
) -> None:
    s = reaction_session(tmp_path, scene_name, round_number)
    assert not c.payload(s)['reaction_view']['active']
    command(s, 'advance')
    p = c.payload(s)
    assert p['actor'] == 'nimra'  # Engine order is retained; the UI uses scene identity.
    assert p['reaction_view']['active'] and p['reaction_view']['preview_burn'] == 3
    assert p['reaction'] in p['reaction_view']['title']
    assert ('Nessa używa:' in p['reaction_view']['title']) == (scene_name == 'nessa')
    command(s, 'react')
    p = c.payload(s)
    assert p['phase'] == 'after_reaction' and p['mana']['pending'] == 3
    title = p['reaction_view']['title']
    store = c.read_store(s)
    store['current']['state'] = r.Confrontation.from_data(store['current']['state']).to_data()
    c.write(s, store)
    for remaining in (2, 1, 0):
        state = r.Confrontation.from_data(c.read_store(s)['current']['state'])
        command(s, 'color', color=state.mana.deck[0])
        p = c.payload(s)
        assert p['reaction_view']['active'] and p['reaction_view']['title'] == title
        assert p['mana']['pending'] == remaining
    command(s, 'advance')
    p = c.payload(s)
    assert not p['reaction_view']['active'] and p['actor'] == 'brakka'
    assert p['round'] == round_number + 1


def test_reaction_preview_uses_actual_pressure_with_garrans_protection(tmp_path: Path) -> None:
    s = reaction_session(tmp_path)
    store = c.read_store(s)
    state = charged(r.Confrontation.from_data(store['current']['state']),
                    {'garran': ('Z', 'C', 'C', 'F', 'N', 'B')})
    store['current']['state'] = replace(state, stage='reaction').to_data()
    c.write(s, store)
    assert c.payload(s)['reaction_view']['preview_burn'] == 2
    command(s, 'react')
    assert c.payload(s)['mana']['pending'] == 2


def test_reaction_that_drains_deck_keeps_scene_identity(tmp_path: Path) -> None:
    s = reaction_session(tmp_path)
    store = c.read_store(s)
    state = charged(r.Confrontation.from_data(store['current']['state']), {}, deck_size=1)
    store['current']['state'] = replace(state, stage='reaction').to_data()
    c.write(s, store)
    command(s, 'react')
    p = c.payload(s)
    assert p['phase'] == 'result' and p['outcome'] == 'failure'
    assert p['reaction_view']['active'] and p['reaction_view']['source'] == 'Nessa'
