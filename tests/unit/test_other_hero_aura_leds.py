"""Other hero auras retain the same physical preview contract as Garran."""
from dataclasses import replace
from pathlib import Path

import pytest

from dnd_board_game.application.training_walkthrough import steps
from dnd_board_game.combat import current_actor
from dnd_board_game.combat.auras import active_spell_auras
from dnd_board_game.combat.shared_mana_features import support_aura_preview
from dnd_board_game.hardware.board_panel import panel_position
from dnd_board_game.hardware.led_palette import LedColor
from dnd_board_game.ui import training_walkthrough as guided
from dnd_board_game.ui.exploration_app import ExplorationUiSession
from dnd_board_game.world import Coordinate
from tests.unit.test_initiative_panel import Board
from tests.unit.test_shared_mana_runtime import send
from tests.unit.test_training_walkthrough import prepared


CASES = [('dagna', 'bless', 10), ('dagna', 'divine_care_aura', 5),
         ('dagna', 'divine_care_aura:radius', 10), ('dagna', 'divine_care_aura:reduction', 5),
         ('lorian', 'victory_hymn', 30)]


def aura_lesson(tmp_path: Path, hero: str, step_id: str) -> tuple[ExplorationUiSession, Board]:
    index = next(i for i, step in enumerate(steps(hero)) if step.id == step_id)
    session = prepared(tmp_path, hero=hero, index=index)
    board = Board()
    session.attach_board_connection(board, backend='simulator')
    session._sync_board_leds()
    return session, board


def cast(session: ExplorationUiSession, ability: str) -> None:
    if ability == 'victory_hymn':
        session.use_combat_class_feature(ability)
    else:
        session.start_combat_concentration_action(ability)


@pytest.mark.parametrize('hero,step_id,radius', CASES)
def test_briefing_payment_and_active_aura_have_correct_range_and_targets(tmp_path: Path, hero: str, step_id: str, radius: int) -> None:
    session, board = aura_lesson(tmp_path, hero, step_id)
    owner = current_actor(session.combat_state)
    ability, _, boost = step_id.partition(':')
    hostile = ability == 'divine_care_aura'
    dim = LedColor.AURA_DIVINE_CARE_DIM if hostile else LedColor.AURA_HEALING_DIM
    bright = LedColor.AURA_DIVINE_CARE_ACTIVE if hostile else LedColor.SELECTED_ABILITY_TARGET
    recipient = next(a for a in session.combat_state.actors if str(a.id) == ('recruitment_dummy' if hostile else 'recruitment_helper'))
    edge = (owner.position.col-radius//5, owner.position.row)
    assert board.leds[edge] == dim
    assert board.leds[recipient.position.as_tuple()] == bright
    assert board.leds[owner.position.as_tuple()] == LedColor.ACTIVE_ACTOR
    assert session._current_board_scan_target().positions == (panel_position(28),)
    assert not session.active_combat_effects
    guided.acknowledge(session, guided.notice_id(session))
    cast(session, ability)
    if boost:
        send(session, 'boost', boost_id=boost, count=1)
    session._sync_board_leds()
    assert board.leds[edge] == dim
    assert all(p.col == 19 for p in session._current_board_scan_target().positions)
    send(session, 'pay')
    session._sync_board_leds()
    assert guided.flag(session, 'phase') == 'success'
    preview = support_aura_preview(session.combat_state.actors, session.active_combat_effects, ability, hero, active_only=True)
    assert preview.radius_feet == radius
    assert str(recipient.id) in preview.affected_actor_ids
    assert (hero in preview.affected_actor_ids) != hostile
    assert board.leds[edge] == dim
    assert board.leds[recipient.position.as_tuple()] == bright
    if hostile:
        assert active_spell_auras(session.combat_state.actors, session.active_combat_effects)[0].affected_actor_ids == preview.affected_actor_ids


def test_radius_boost_changes_live_payment_preview_without_applying_effect(tmp_path: Path) -> None:
    session, board = aura_lesson(tmp_path, 'dagna', 'divine_care_aura:radius')
    guided.acknowledge(session, guided.notice_id(session))
    cast(session, 'divine_care_aura')
    edge = (7, 18)
    assert edge not in board.leds
    send(session, 'boost', boost_id='radius', count=1)
    assert board.leds[edge] == LedColor.AURA_DIVINE_CARE_DIM
    send(session, 'boost', boost_id='radius', count=0)
    assert edge not in board.leds
    assert not session.active_combat_effects


@pytest.mark.parametrize('hero,ability', [('dagna', 'bless'), ('dagna', 'divine_care_aura'), ('lorian', 'victory_hymn')])
def test_active_aura_updates_members_after_move_and_disappears_with_concentration(tmp_path: Path, hero: str, ability: str) -> None:
    session, board = aura_lesson(tmp_path, hero, ability)
    guided.acknowledge(session, guided.notice_id(session))
    cast(session, ability)
    send(session, 'pay')
    target_id = 'recruitment_dummy' if ability == 'divine_care_aura' else 'recruitment_helper'
    original = next(a.position for a in session.combat_state.actors if str(a.id) == target_id)
    session.combat_state = replace(session.combat_state, actors=tuple(
        replace(a, position=Coordinate(0, 0)) if str(a.id) == target_id else a for a in session.combat_state.actors))
    session.state_payload()
    session._sync_board_leds()
    dim = LedColor.AURA_DIVINE_CARE_DIM if ability == 'divine_care_aura' else LedColor.AURA_HEALING_DIM
    assert board.leds[original.as_tuple()] == dim
    assert (0, 0) not in board.leds
    from dnd_board_game.rules import EffectEvent, EffectEventType, expire_active_effects
    session.active_combat_effects = expire_active_effects(session.active_combat_effects,
        EffectEvent(EffectEventType.CONCENTRATION_ENDED, actor_id=hero)).active_effects
    session.state_payload()
    session._sync_board_leds()
    assert board.leds == {(19, 1): LedColor.PANEL_ACCEPT}


def test_hymn_footprint_matches_bonus_rule_and_stays_visible_in_another_turn(tmp_path: Path) -> None:
    from dnd_board_game.combat.session import shared_bonus_action_limit
    from dnd_board_game.combat.scene import set_scene_flag
    session, board = aura_lesson(tmp_path, 'lorian', 'victory_hymn')
    guided.acknowledge(session, guided.notice_id(session))
    cast(session, 'victory_hymn')
    send(session, 'pay')
    session.state = replace(session.state, flags=set_scene_flag(session.state.flags, 'training_mode', 'basic'))
    order = session.combat_state.initiative_order
    session.combat_state = replace(session.combat_state,
        initiative_order=replace(order, current_index=next(i for i,e in enumerate(order.entries) if str(e.actor.id) != 'lorian')))
    for position, expected in ((Coordinate(15,24), 2), (Coordinate(16,24), 1)):
        session.combat_state = replace(session.combat_state, actors=tuple(
            replace(a, position=position) if str(a.id) == 'recruitment_helper' else a for a in session.combat_state.actors))
        helper = next(a for a in session.combat_state.actors if str(a.id) == 'recruitment_helper')
        preview = support_aura_preview(session.combat_state.actors, session.active_combat_effects, 'victory_hymn', 'lorian', active_only=True)
        assert shared_bonus_action_limit(session.combat_state, helper) == expected
        assert ('recruitment_helper' in preview.affected_actor_ids) == (expected == 2)
        session._sync_board_leds()
        assert board.leds[current_actor(session.combat_state).position.as_tuple()] == LedColor.ACTIVE_ACTOR
        if expected == 2:
            assert board.leds[position.as_tuple()] == LedColor.SELECTED_ABILITY_TARGET
        else:
            assert position.as_tuple() not in board.leds
    session.combat_state = replace(session.combat_state, actors=tuple(
        replace(a, position=Coordinate(8,18)) if str(a.id) == 'lorian' else a for a in session.combat_state.actors))
    session._sync_board_leds()
    assert board.leds[(2,18)] == LedColor.AURA_HEALING_DIM
    assert (15,18) not in board.leds
    assert board.leds[(8,18)] == LedColor.ACTIVE_ACTOR


def test_action_preview_supersedes_auras_without_changing_their_effects(tmp_path: Path) -> None:
    from dnd_board_game.combat.scene import set_scene_flag
    from dnd_board_game.ui.aura_preview import context_feedback
    session, _ = aura_lesson(tmp_path, 'dagna', 'bless')
    guided.acknowledge(session, guided.notice_id(session))
    cast(session, 'bless')
    send(session, 'pay')
    session.state = replace(session.state, flags=set_scene_flag(session.state.flags, 'training_mode', 'basic'))
    assert context_feedback(session).frames
    move = next(o for o in session._combat_turn_action_options() if o.id == 'turn:move')
    session.confirm_combat_turn_action(move.id)
    assert not context_feedback(session).frames
    assert active_spell_auras(session.combat_state.actors, session.active_combat_effects)
