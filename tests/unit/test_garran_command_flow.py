"""Native command controls, unavailable targets, and Strength-based Bastion."""
from dataclasses import replace
from pathlib import Path

import pytest

from dnd_board_game.combat import current_actor
from dnd_board_game.combat.targets import combat_armor_class
from dnd_board_game.hardware.board_panel import panel_position
from dnd_board_game.rules.shared_mana import SharedMana
from dnd_board_game.ui import shared_command
from dnd_board_game.ui.routes import create_app
from dnd_board_game.ui.exploration_app import ExplorationUiSession
from dnd_board_game.world import Coordinate
from tests.unit.test_garran_training_regressions import lesson, guided, send
from tests.unit.test_initiative_panel import Board


@pytest.mark.parametrize('strength,bonus', [(18, 4), (14, 2), (8, -1)])
def test_bastion_uses_casters_strength_for_owner_and_ally(tmp_path: Path, strength: int, bonus: int) -> None:
    session, _ = lesson(tmp_path, 'iron_bastion')
    session.combat_state = replace(session.combat_state, actors=tuple(
        replace(a, ability_scores=replace(a.ability_scores, strength=strength)) if str(a.id) == 'garran' else a
        for a in session.combat_state.actors))
    before = {str(a.id): combat_armor_class(a, session.active_combat_effects) for a in session.combat_state.actors}
    guided.acknowledge(session, guided.notice_id(session))
    session.use_combat_class_feature('iron_bastion')
    send(session, 'pay')
    assert next(e.value for e in session.active_combat_effects if e.kind == 'iron_bastion') == bonus
    for actor in session.combat_state.actors:
        if str(actor.id) in {'garran', 'recruitment_helper'}:
            assert combat_armor_class(actor, session.active_combat_effects) == before[str(actor.id)] + bonus


def start(tmp_path: Path) -> tuple[ExplorationUiSession, Board]:
    session, board = lesson(tmp_path, 'counterattack_command')
    guided.acknowledge(session, guided.notice_id(session))
    session.use_combat_class_feature('counterattack_command', target_id='recruitment_helper')
    send(session, 'pay')
    return session, board


def test_no_targets_finishes_paid_command_but_retries_lesson(tmp_path: Path) -> None:
    session, _ = start(tmp_path)
    session.combat_state = replace(session.combat_state, actors=tuple(
        replace(a, position=Coordinate(1, 1)) if str(a.id) == 'recruitment_dummy' else a
        for a in session.combat_state.actors))
    for actor in ('garran', 'recruitment_helper'):
        assert str(current_actor(session.combat_state).id) == actor
        shared_command.select(session, panel_position(28))
        assert shared_command.stage(session) == 'no_target'
        assert session._current_board_scan_target().positions == (panel_position(28),)
        assert 'Brak legalnego celu' in session.state_payload()['combat']['shared_mana']['command']['instruction']
        shared_command.select(session, panel_position(28))
    assert session.combat_state.shared_mana.command_step == 0
    assert session.combat_state.shared_mana.market == 1
    assert str(current_actor(session.combat_state).id) == 'garran'
    assert guided.flag(session, 'phase') == 'retry'


def test_back_clears_field_and_target_without_refunding_or_reopening_menu(tmp_path: Path) -> None:
    session, _ = start(tmp_path)
    origin = current_actor(session.combat_state).position
    shared_command.select(session, Coordinate(10, 18))
    shared_command.select(session, Coordinate(10, 18))
    assert current_actor(session.combat_state).position == origin  # Only ✓ moves.
    shared_command.select(session, panel_position(29))
    assert session.selected_combat_movement_path is None
    shared_command.select(session, panel_position(28))
    enemy = next(a for a in session.combat_state.actors if str(a.id) == 'recruitment_dummy')
    shared_command.select(session, enemy.position)
    assert shared_command.stage(session) == 'confirm_attack'
    shared_command.select(session, panel_position(29))
    assert session.pending_player_attack is None
    assert shared_command.stage(session) == 'attack'
    assert session.state_payload()['combat']['turn_action_menu'] is None
    assert session.combat_state.shared_mana.market == 1


def test_stale_confirm_does_not_skip_next_stage_and_phase_survives_serialization(tmp_path: Path) -> None:
    session, _ = start(tmp_path)
    client = create_app(session).test_client()
    revision = session._board_selection_payload()['revision']
    response = client.post('/api/combat/command', json={'revision': revision})
    assert response.status_code == 200
    assert shared_command.stage(session) == 'attack'
    second = client.post('/api/combat/command', json={'revision': revision})
    assert second.status_code == 200
    assert session.pending_player_attack is None
    assert SharedMana.from_payload(session.combat_state.shared_mana.as_payload()) == session.combat_state.shared_mana
    with pytest.raises(ValueError, match='automatycznie'):
        session.confirm_combat_turn_action('turn:move')


def test_command_automatically_uses_equipped_crossbow_instead_of_stored_sword(tmp_path: Path) -> None:
    session, _ = start(tmp_path)
    owner = current_actor(session.combat_state)
    equipped = replace(owner, inventory=tuple(
        replace(item, equipped=item.id == 'crossbow', held_in=()) if item.id in {'longsword', 'shield', 'crossbow'} else item
        for item in owner.inventory))
    session.combat_state = replace(session.combat_state, actors=tuple(
        equipped if a.id == owner.id else a for a in session.combat_state.actors))
    shared_command.select(session, panel_position(28))
    source = session._selected_attack_source(equipped)
    assert source.id == 'counterattack_command'
    assert source.source_item_id == 'crossbow'
    assert shared_command.stage(session) == 'attack'


def test_no_movement_available_can_still_confirm_and_attack(tmp_path: Path) -> None:
    session, _ = start(tmp_path)
    owner = current_actor(session.combat_state)
    session.combat_state = replace(session.combat_state, actors=tuple(
        replace(a, speed_feet=0) if a.id == owner.id else a for a in session.combat_state.actors))
    assert set(session._current_board_scan_target().positions) == {owner.position, panel_position(28)}
    shared_command.select(session, panel_position(28))
    assert shared_command.stage(session) == 'attack'
