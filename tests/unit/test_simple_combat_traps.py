from dataclasses import replace

import pytest

from dnd_board_game.combat import current_actor
from dnd_board_game.combat.simple_traps import SimpleTrap, trap_request, resolve_trap_check, validate_trap_action
from dnd_board_game.combat.session import ActionUse
from dnd_board_game.ui import simple_traps
from dnd_board_game.ui.training_arena import start_training_trial, training_hero
from dnd_board_game.ui.training_tutorial import acknowledge, notice_id
from dnd_board_game.ui.routes import create_app
from dnd_board_game.world import Coordinate
from tests.unit.test_recruitment_arena import arena, begin


def hero_turn(s, hero='mira'):
    index = next(i for i,e in enumerate(s.combat_state.initiative_order.entries) if str(e.actor.id) == hero)
    s.combat_state = replace(s.combat_state, initiative_order=replace(s.combat_state.initiative_order,current_index=index),
        turn_action=replace(s.combat_state.turn_action, action_use=ActionUse.ACTION_AVAILABLE))


def test_trap_detection_and_disarm_consume_real_actions(tmp_path):
    s=arena(tmp_path)
    begin(s,'mira')
    trap=SimpleTrap('t','Pułapka',current_actor(s.combat_state).position)
    with pytest.raises(ValueError):
        resolve_trap_check(s.combat_state,trap,'disarm',20,tools_available=True)
    result=resolve_trap_check(s.combat_state,trap,'detect',20,tools_available=True)
    assert result.trap.status=='revealed'
    assert result.state.turn_action.action_use!=ActionUse.ACTION_AVAILABLE
    with pytest.raises(ValueError):
        resolve_trap_check(result.state,result.trap,'disarm',20,tools_available=True)
    with pytest.raises(ValueError):
        resolve_trap_check(s.combat_state,result.trap,'disarm',20,tools_available=False)
    assert resolve_trap_check(s.combat_state,result.trap,'disarm',20,tools_available=True).trap.status=='disarmed'
    failed=resolve_trap_check(s.combat_state,result.trap,'disarm',1,tools_available=True)
    assert failed.triggered and failed.trap.status=='triggered'


def test_trap_range_and_no_exploration_passive(tmp_path):
    s=arena(tmp_path)
    begin(s,'erynd')
    actor=current_actor(s.combat_state)
    trap=SimpleTrap('t','Pułapka',Coordinate(actor.position.col,actor.position.row-3))
    with pytest.raises(ValueError):
        validate_trap_action(s.combat_state,trap,'detect',tools_available=True)
    request=trap_request(actor,trap,'detect')
    assert not any('Czujność' in m.label or 'Praktyka' in m.label for m in request.modifiers)
    assert sum(m.value for m in request.modifiers)==4


@pytest.mark.parametrize('hero', ('garran','brakka','mira','dagna','lorian','nimra','erynd'))
def test_trap_lesson_intro_pending_roll_save_and_completion(tmp_path, hero):
    s=arena(tmp_path)
    start_training_trial(s,hero,'traps','humanoid')
    assert notice_id(s).startswith('trap:')
    acknowledge(s,notice_id(s))
    for _ in range(30):
        if s.encounter_setup_flow.completed:
            break
        s.confirm_encounter_setup_step()
    s.start_encounter_initiative()
    s.submit_encounter_initiative_roll(20)
    hero_turn(s,hero)
    def send(action,**extra):
        return simple_traps.command(s,dict(action=action,revision=simple_traps.read(s)['revision'],**extra))
    send('detect')
    client=create_app(s).test_client()
    assert client.post('/api/training/start',json={'hero_id':'garran'}).status_code==400
    s.save_snapshot()
    s.load_snapshot()
    assert simple_traps.read(s)['pending']['action']=='detect'
    send('roll',roll=20)
    assert simple_traps.read(s)['status']=='revealed'
    with pytest.raises(ValueError):
        send('disarm')
    hero_turn(s,hero)
    send('disarm')
    send('roll',roll=1)
    assert simple_traps.read(s)['completed'] and simple_traps.read(s)['status']=='triggered'
    send('leave')
    assert s.state_payload()['training_arena']['can_start']
    from dnd_board_game.combat.scene import scene_flag
    assert scene_flag(s.state.flags,'trap_lesson_done_'+hero)
