"""Critical results reach the live NPC/object payload and physical burn choices."""
from dataclasses import replace
from pathlib import Path

import pytest

from dnd_board_game.rules import confrontation as r
from dnd_board_game.ui import confrontation as c
from dnd_board_game.ui.exploration_app import ExplorationUiSession
from tests.unit.test_confrontation import charged
from tests.unit.test_confrontation_presentation import start, choose_approaches, command


def critical_session(tmp_path: Path, natural: int, scene_name: str = 'nessa') -> ExplorationUiSession:
    session = start(tmp_path, scene_name=scene_name)
    command(session, 'acknowledge')
    choose_approaches(session)
    command(session, 'acknowledge')
    store = c.read_store(session)
    state = r.Confrontation.from_data(store['current']['state'])
    state = charged(state, {})
    actor = replace(state.actor, test_modifier=-30 if natural == 20 else 30, impact_modifier=2, die=8)
    state = replace(state, participants=(actor, *state.participants[1:]), maximum=100, resistance=100)
    store['current']['state'] = r.declare(state, 0).to_data()
    c.write(session, store)
    return session


@pytest.mark.parametrize('scene_name,effect', [('nessa', 'Wpływ'), ('cart', 'Postęp')])
@pytest.mark.parametrize('natural', [1, 20])
def test_critical_payload_skips_second_die_and_keeps_cost_on_reload(
    tmp_path: Path, natural: int, scene_name: str, effect: str,
) -> None:
    session = critical_session(tmp_path, natural, scene_name)
    command(session, 'roll', rolls=[natural])
    payload = c.payload(session)
    assert payload['phase'] == 'after_action' and payload['attempt'] == {}
    assert payload['effect_name'] == effect
    assert payload['critical'] == ('success' if natural == 20 else 'failure')
    assert payload['last_impact'] == (10 if natural == 20 else 0)
    assert payload['action_cost'] == payload['mana']['pending'] == (1 if natural == 20 else 2)
    assert all(choice['action'] != 'roll' for choice in payload['board_choices'])
    with pytest.raises(ValueError):
        command(session, 'roll', rolls=[8])
    store = c.read_store(session)
    store['current']['state'] = r.Confrontation.from_data(store['current']['state']).to_data()
    c.write(session, store)
    assert c.payload(session)['critical'] == payload['critical']
    while c.payload(session)['mana']['phase'] == 'burn':
        state = r.Confrontation.from_data(c.read_store(session)['current']['state'])
        command(session, 'color', color=state.mana.deck[0])
    command(session, 'advance')
    assert c.payload(session)['critical'] == ''
