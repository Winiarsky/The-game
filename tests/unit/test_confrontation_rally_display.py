"""Replay the reported Garran failure without touching the player's saved game."""
from pathlib import Path

import pytest

from dnd_board_game.ui import confrontation as c, mission_zero as mission
from dnd_board_game.ui.exploration_app import ExplorationUiSession
from dnd_board_game.ui.training_arena import training_hero
from tests.unit.test_mission_zero import session, stage, send
from tests.unit.test_confrontation_presentation import command


def rally_session(tmp_path: Path) -> ExplorationUiSession:
    s = session(tmp_path)
    s.configure_custom_party(tuple(training_hero(hero) for hero in ('brakka', 'garran', 'nimra')))
    mission.initialize(s)
    stage(s, 'brief')
    send(s, 'negotiate')
    command(s, 'acknowledge')
    for approach in ('demands', 'empathy', 'logic'):
        command(s, 'approach', approach=approach)
    command(s, 'acknowledge')
    for color in ('Z', 'F'):
        command(s, 'color', color=color)
    command(s, 'take', index=0)
    command(s, 'peek')
    command(s, 'peek_finish', move_top=True)
    command(s, 'advance')
    command(s, 'color', color='B')
    command(s, 'take', index=0)
    command(s, 'test', bonus=1)
    command(s, 'roll', rolls=[11])
    command(s, 'color', color='N')
    command(s, 'advance')
    return s


@pytest.mark.parametrize('natural', [1, 20])
def test_rally_aid_survives_draw_and_is_used_by_next_attempt(tmp_path: Path, natural: int) -> None:
    s = rally_session(tmp_path)
    p = c.payload(s)
    assert p['actor'] == 'nimra' and p['mana']['phase'] == 'reveal'
    assert '11 + (2) = 13, ST 19' in p['last']
    heroes = {hero['id']: hero for hero in p['party']}
    assert heroes['nimra']['roll_bonus'] == 0
    assert heroes['nimra']['aid'] == heroes['brakka']['aid'] == 1
    assert p['test_preview']['modifier_total'] == heroes['nimra']['test_modifier'] + 1
    command(s, 'color', color='N')
    command(s, 'take', index=0)
    p = c.payload(s)
    nimra = next(hero for hero in p['party'] if hero['id'] == 'nimra')
    assert nimra['aid'] == 1 and nimra['roll_bonus'] == 1
    assert sum(item['value'] for item in p['test_preview']['modifiers']
               if item['label'] == 'Otrzymana pomoc') == 1
    modifier = p['test_preview']['modifier_total']
    command(s, 'test', bonus=1)
    assert c.payload(s)['attempt']['modifier_total'] == modifier
    command(s, 'roll', rolls=[natural])
    p = c.payload(s)
    assert p['last_total'] == natural + modifier
    assert next(hero for hero in p['party'] if hero['id'] == 'nimra')['aid'] == 0
    assert next(hero for hero in p['party'] if hero['id'] == 'brakka')['aid'] == 1
