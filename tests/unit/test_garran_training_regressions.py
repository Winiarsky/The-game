"""Full Garran lessons: interception, aura LEDs and both command participants."""
from pathlib import Path
from dataclasses import replace
from random import Random

import pytest

from dnd_board_game.application.training_walkthrough import steps
from dnd_board_game.combat import current_actor
from dnd_board_game.hardware.board_panel import panel_position
from dnd_board_game.hardware.led_palette import LedColor
from dnd_board_game.ui import training_walkthrough as guided
from dnd_board_game.ui.board_panel_symbols import ability_panel_slot
from dnd_board_game.ui.exploration_app import ExplorationUiSession
from dnd_board_game.world import Coordinate
from tests.unit.test_initiative_panel import Board
from tests.unit.test_shared_mana_runtime import send
from tests.unit.test_training_walkthrough import prepared


def lesson(tmp_path: Path, ability: str) -> tuple[ExplorationUiSession, Board]:
    index = next(i for i, step in enumerate(steps('garran')) if step.id == ability)
    session = prepared(tmp_path, index=index)
    board = Board()
    session.attach_board_connection(board, backend='simulator')
    session._sync_board_leds()
    return session, board


def test_guard_redirects_out_of_reach_attack_and_preserves_payment(tmp_path: Path) -> None:
    session, board = lesson(tmp_path, 'garran_guard_companion')
    before = {str(a.id): a.hp for a in session.combat_state.actors}
    guided.acknowledge(session, guided.notice_id(session))
    assert session.pending_enemy_turn_intent.target.id == 'recruitment_helper'
    assert 'pomocnik' in session.state_payload()['combat']['shared_mana']['declaration']['description'].lower()
    send(session, 'pay')
    result = session.pending_enemy_turn_result
    assert result.target.id == 'garran'
    assert result.attack_resolution.hit
    assert 'przejmuje' in result.message
    assert result.state.shared_mana.market == 4
    assert 'garran' in result.state.spent_reaction_actor_ids
    assert not guided.notice_id(session)  # Resolve the attack before teaching the outcome.
    session._commit_pending_enemy_turn()
    if session.pending_enemy_turn_ack_result:
        session.confirm_enemy_turn_result()
    after = {str(a.id): a.hp for a in session.combat_state.actors}
    assert after['garran'] == before['garran'] - 6
    assert after['recruitment_helper'] == before['recruitment_helper']
    assert session.combat_state.shared_mana.market == 4
    assert guided.flag(session, 'phase') == 'success'
    assert guided.notice_id(session)


def test_interception_can_miss_outside_lesson_and_is_consumed_once(tmp_path: Path) -> None:
    session, _ = lesson(tmp_path, 'garran_guard_companion')
    guided.acknowledge(session, guided.notice_id(session))
    from dnd_board_game.combat.scene import set_scene_flag
    session.state = replace(session.state, flags=set_scene_flag(session.state.flags, 'training_mode', 'basic'))
    session.encounter_rng = Random(31)  # Natural 1, an ordinary miss despite interception.
    send(session, 'pay')
    assert session.pending_enemy_turn_result.target.id == 'garran'
    assert not session.pending_enemy_turn_result.attack_resolution.hit
    assert not any(e.kind == 'garran_guard_companion' for e in session.active_combat_effects)


@pytest.mark.parametrize('natural_roll', [1, 10])
@pytest.mark.parametrize('with_movement', [False, True])
def test_command_automatically_moves_then_attacks_with_both_participants(tmp_path: Path, natural_roll: int, with_movement: bool) -> None:
    session, board = lesson(tmp_path, 'counterattack_command')
    guided.acknowledge(session, guided.notice_id(session))
    session.use_combat_class_feature('counterattack_command', target_id='recruitment_helper')
    send(session, 'pay')
    from dnd_board_game.ui.routes import create_app
    client = create_app(session).test_client()

    def scan(position: Coordinate) -> dict[str, object]:
        board.selected = position.as_tuple()
        response = client.post('/api/board/scan', json={
            'revision': session._board_selection_payload()['revision'], 'automatic': True})
        assert response.status_code == 200, response.json
        return response.json
    rune = panel_position(ability_panel_slot('garran', 'counterattack_command'))
    enemy = next(a for a in session.combat_state.actors if str(a.id) == 'recruitment_dummy')
    for index, actor in enumerate(('garran', 'recruitment_helper'), 1):
        view = session.state_payload()
        assert current_actor(session.combat_state).id == actor
        assert view['combat']['shared_mana']['command']['step'] == index
        assert session.combat_state.shared_mana.market == 1
        assert view['combat']['turn_action_menu'] is None
        assert board.leds[panel_position(28).as_tuple()] == LedColor.PANEL_ACCEPT
        assert board.leds[current_actor(session.combat_state).position.as_tuple()] == LedColor.ACTIVE_ACTOR
        assert rune not in session._current_board_scan_target().positions
        assert panel_position(0) not in session._current_board_scan_target().positions
        assert panel_position(5) not in session._current_board_scan_target().positions
        with pytest.raises(ValueError, match='Dokończ Kontratak'):
            session.finish_combat_turn()
        mana = session.combat_state.shared_mana
        origin = current_actor(session.combat_state).position
        from dnd_board_game.combat.spells import grid_distance_feet
        assert all(grid_distance_feet(origin, p) <= 10 for p in session._current_board_scan_target().positions if p.col != 19)
        destination = Coordinate(10, 18) if actor == 'garran' else Coordinate(9, 18)
        if with_movement:
            assert list(destination.as_tuple()) in view['board_selection']['legal_positions']
            scan(destination)
            assert session.combat_state.shared_mana == mana
            assert current_actor(session.combat_state).position == origin
        confirmation = scan(panel_position(28))
        assert 'panel_event' not in confirmation
        assert session.combat_state.shared_mana.command_stage == 'attack'
        assert session.combat_state.shared_mana.market == mana.market
        assert session.pending_opportunity_movement is None
        assert current_actor(session.combat_state).position == (destination if with_movement else origin)
        assert enemy.position in session._current_board_scan_target().positions
        assert rune not in session._current_board_scan_target().positions
        scan(enemy.position)
        scan(panel_position(28))
        session.submit_player_attack_roll(natural_roll=natural_roll)
        if session.pending_player_attack:
            session.submit_player_damage_roll(damage=4)
    assert session.combat_state.shared_mana.command_step == 0
    assert current_actor(session.combat_state).id == 'garran'
    assert session.combat_state.shared_mana.market == 1
    assert len(session.combat_state.initiative_order.entries) == 2
    assert guided.flag(session, 'phase') == 'success'


@pytest.mark.parametrize('ability,radius', [('garran_shield_wall', 1), ('garran_shield_wall:ward', 1), ('iron_bastion', 2)])
def test_aura_range_members_and_payment_share_leds_without_extra_inputs(tmp_path: Path, ability: str, radius: int) -> None:
    session, board = lesson(tmp_path, ability)
    owner = current_actor(session.combat_state)
    edge = (owner.position.col - radius, owner.position.row)
    assert board.leds[edge] == LedColor.AURA_HEALING_DIM
    assert board.leds[(9, 17)] == LedColor.SELECTED_ABILITY_TARGET
    assert session._current_board_scan_target().positions == (panel_position(28),)
    guided.acknowledge(session, guided.notice_id(session))
    session.use_combat_class_feature(ability.split(':')[0])
    if ':' in ability:
        send(session, 'boost', boost_id='ward', count=1)
    session._sync_board_leds()
    assert edge in board.leds
    assert not any(p.col != 19 for p in session._current_board_scan_target().positions)
    send(session, 'pay')
    if session.shared_mana_declaration:
        send(session, 'target', target_id='recruitment_helper')
        send(session, 'bonus')
    session._sync_board_leds()
    assert guided.flag(session, 'phase') == 'success'
    assert board.leds[edge] == LedColor.AURA_HEALING_DIM
    assert board.leds[(9, 17)] == LedColor.SELECTED_ABILITY_TARGET
    assert session._current_board_scan_target().positions == (panel_position(28),)
    assert 'zasięg' in guided.payload(session)['notice']['narration']


@pytest.mark.parametrize('ability,includes_owner', [('garran_shield_wall', False), ('iron_bastion', True)])
def test_aura_preview_matches_membership_and_updates_after_moving_ally(tmp_path: Path, ability: str, includes_owner: bool) -> None:
    from dnd_board_game.combat.shared_mana_features import support_aura_preview
    session, board = lesson(tmp_path, ability)
    before, effects = session.combat_state, session.active_combat_effects
    preview = support_aura_preview(before.actors, effects, ability, 'garran')
    assert ('garran' in preview.affected_actor_ids) == includes_owner
    assert 'recruitment_helper' in preview.affected_actor_ids
    assert session.combat_state == before and session.active_combat_effects == effects
    session.combat_state = replace(before, actors=tuple(
        replace(actor, position=Coordinate(1, 1)) if str(actor.id) == 'recruitment_helper' else actor
        for actor in before.actors))
    session._sync_board_leds()
    assert board.leds[(9, 17)] == LedColor.AURA_HEALING_DIM
    assert (1, 1) not in board.leds
    assert board.leds[(9, 18)] == LedColor.ACTIVE_ACTOR
