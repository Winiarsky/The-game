from pathlib import Path

import pytest

from dnd_board_game.ui.exploration_mana import command, payload, read_store
from dnd_board_game.ui.training_arena import training_hero
from dnd_board_game.ui.routes import create_app
from dnd_board_game.rules.exploration_mana_catalog import HEROES
from tests.unit.test_recruitment_arena import arena


def send(s, action, **extra):
    return command(s, dict(action=action, revision=read_store(s)['revision'], **extra))


def prepared(s, hero='brakka', lesson='npc'):
    send(s, 'open', hero=hero, lesson=lesson)
    assert s.combat_state is None and s.pending_encounter is None
    assert payload(s)['phase'] == 'introduction'
    send(s, 'acknowledge')
    while payload(s)['phase'] == 'setup':
        send(s, 'acknowledge')
    assert payload(s)['phase'] == 'scene'
    option = next(o for o in payload(s)['options'] if o['enabled'] and o['hero'] == hero)
    send(s, 'start', method=option['id'])
    return s


@pytest.mark.parametrize('hero', HEROES)
@pytest.mark.parametrize('kind', ['npc', 'object'])
def test_every_hero_can_really_talk_and_use_object(tmp_path: Path, hero: str, kind: str):
    s = prepared(arena(tmp_path), hero, kind)
    assert payload(s)['attempt']['actor'] == training_hero(hero).name
    s.save_snapshot()
    s.load_snapshot()
    send(s, 'resume', stacks_preserved=True)
    send(s, 'choose', color='C')
    send(s, 'stand')
    send(s, 'roll', rolls=[20])
    a = payload(s)['attempt']
    assert a['success'] and a['phase'] == 'result' and a['lesson_completed']
    assert f'{hero}:{kind}' in read_store(s)['completed']
    assert len(read_store(s)['outcomes']) == 1
    with pytest.raises(ValueError):
        send(s, 'roll', rolls=[20])
    assert len(read_store(s)['outcomes']) == 1
    send(s, 'leave')
    assert not payload(s)['active'] and s.state_payload()['training_arena']['can_start']


def test_hidden_profile_locked_method_and_stale_messages(tmp_path):
    s = arena(tmp_path)
    send(s, 'open', hero='brakka', lesson='npc')
    old = read_store(s)['revision']
    send(s, 'acknowledge')
    with pytest.raises(ValueError, match='nieaktualne'):
        command(s, dict(action='acknowledge', revision=old))
    while payload(s)['phase'] == 'setup':
        send(s, 'acknowledge')
    assert all('values' not in o and 'profile' not in o for o in payload(s)['options'])
    with pytest.raises(ValueError):
        send(s, 'start', method='empathy')
    send(s, 'start', method='intimidation')
    assert len(payload(s)['attempt']['values']) == 5
    with pytest.raises(ValueError):
        send(s, 'start', method='intimidation')


def test_bust_lesson_uses_physical_disadvantage_and_persists(tmp_path):
    s = prepared(arena(tmp_path), 'brakka', 'bust')
    for i, color in enumerate('CCNF'):
        if i:
            send(s, 'draw')
        send(s, 'choose', color=color)
    a = payload(s)['attempt']
    assert a['dice_count'] == 2 and a['bonus'] == 0
    s.save_snapshot()
    s.load_snapshot()
    assert payload(s)['attempt']['phase'] == 'roll'
    with pytest.raises(ValueError):
        send(s, 'roll', rolls=[20])
    send(s, 'roll', rolls=[20, 1])
    a = payload(s)['attempt']
    assert not a['success'] and a['lesson_completed']
    assert a['roll_total'] == 7  # Brakka force: STR +4, Athletics +2, lower die 1.


def test_practice_has_three_present_actors_and_resolves_chosen_actor(tmp_path):
    s = arena(tmp_path)
    send(s, 'open', hero='erynd', lesson='practice_npc')
    send(s, 'acknowledge')
    while payload(s)['phase'] == 'setup':
        send(s, 'acknowledge')
    choices = [o for o in payload(s)['options'] if o['enabled']]
    assert len(choices) == 3 and len(s.custom_party) == 3
    chosen = next(o for o in choices if o['hero'] == 'brakka')
    send(s, 'start', method=chosen['id'])
    assert payload(s)['attempt']['actor'] == 'Brakka'


def test_board_acknowledgment_and_api_block_unrelated_actions(tmp_path):
    s = arena(tmp_path)
    client = create_app(s).test_client()
    response = client.post('/api/exploration-mana', json=dict(action='open', hero='mira', lesson='object', revision=0))
    assert response.status_code == 200, response.json
    from dnd_board_game.world import Coordinate
    s._handle_board_position(Coordinate(19, 1))
    assert payload(s)['phase'] == 'setup'
    response = client.post('/api/training/start', json=dict(hero_id='garran'))
    assert response.status_code == 400


def test_progress_survives_combat_course_launch_and_leave(tmp_path):
    s = prepared(arena(tmp_path), 'garran', 'exact')
    for i in range(3):
        if i:
            send(s, 'draw')
        send(s, 'choose', color='C')
    send(s, 'leave')
    from dnd_board_game.ui import training_walkthrough as combat
    combat.launch(s, 'mira', 0)
    assert 'garran:exact' in read_store(s)['completed']
    combat.leave(s)
    assert 'garran:exact' in read_store(s)['completed']


def test_basics_are_shared_and_resuming_saved_cards_needs_confirmation(tmp_path):
    s = prepared(arena(tmp_path), 'garran', 'exact')
    for i in range(3):
        if i:
            send(s, 'draw')
        send(s, 'choose', color='C')
    send(s, 'leave')
    hero = next(h for h in payload(s)['heroes'] if h['id'] == 'mira')
    assert next(l for l in hero['lessons'] if l['id'] == 'exact')['completed']
    assert not next(l for l in hero['lessons'] if l['id'] == 'npc')['completed']
    prepared(s, 'mira', 'npc')
    send(s, 'choose', color='C')
    s.save_snapshot()
    s.load_snapshot()
    assert payload(s)['attempt']['needs_resume']
    with pytest.raises(ValueError, match='stosów'):
        send(s, 'draw')
    send(s, 'resume', stacks_preserved=True)
    assert payload(s)['attempt']['total'] == 7
