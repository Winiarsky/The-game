"""Board-driven command: move, confirm, attack, then the next participant."""
from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from dnd_board_game.combat import current_actor
from dnd_board_game.hardware.board_panel import panel_feedback, panel_position
from dnd_board_game.hardware.led_feedback import LedFeedback, LedFrame, LedRole, movement_led_feedback
from dnd_board_game.hardware.led_palette import LedColor
from dnd_board_game.rules.shared_mana import finish_mana_action
from dnd_board_game.world import Coordinate

if TYPE_CHECKING:
    from .exploration_app import BoardScanTarget, ExplorationUiSession


def stage(session: ExplorationUiSession) -> str:
    state = session.combat_state
    if state is None or state.shared_mana is None or not state.shared_mana.command_step or session.shared_mana_declaration:
        return ''
    pending = session.pending_player_attack
    if pending is not None:
        return 'confirm_attack' if pending.stage == 'confirm_attack' else ''
    if session._combat_has_pending_resolution():
        return ''
    return state.shared_mana.command_stage or 'movement'


def targets(session: ExplorationUiSession) -> tuple:
    from .exploration_app import _legal_combat_targets
    actor = current_actor(session.combat_state)
    source = session._attack_source_by_id(actor, 'counterattack_command')
    if source is None or not session._actor_can_use_attack_source(actor, source):
        return ()
    return _legal_combat_targets(session._active_encounter(), session.combat_state, actor,
        session._effective_attack_source(actor, source))


def advance(session: ExplorationUiSession, *, skipped: bool = False) -> None:
    from dnd_board_game.combat.shared_command import advance_command
    from .training_tutorial import record_ability
    state = session.combat_state
    if skipped:
        state = replace(state, shared_mana=replace(state.shared_mana, command_skipped=True))
    session._clear_player_pending_choices()
    session.selected_combat_movement_path = None
    session.combat_state, session.active_combat_effects = advance_command(state, session.active_combat_effects)
    mana = session.combat_state.shared_mana
    if not mana.command_step:
        session.combat_state = replace(session.combat_state, shared_mana=finish_mana_action(mana, revision=mana.revision))
        record_ability(session, mana.pending_ability, mana.pending_actor)
    session.board_selection_revision += 1


def prepare(session: ExplorationUiSession) -> None:
    state = session.combat_state
    changed = False
    if state.turn_action.attacks_used:
        advance(session)
        changed = True
    if stage(session) == 'attack':
        actor = current_actor(session.combat_state)
        if targets(session):
            session.selected_attack_source_ids[str(actor.id)] = 'counterattack_command'
            session.combat_targeting_attack_source_id = 'counterattack_command'
        else:
            session.combat_state = replace(session.combat_state,
                shared_mana=replace(session.combat_state.shared_mana, command_stage='no_target'))
            changed = True
    if changed:
        session._sync_board_leds()


def instruction(session: ExplorationUiSession) -> str:
    phase = stage(session)
    path = session.selected_combat_movement_path
    if phase == 'movement':
        if path is not None and path.valid:
            return f'Ustaw figurkę na polu ({path.destination.col}, {path.destination.row}). ✓ kończy ruch i przechodzi do ataku. ↩ czyści wybór pola.'
        return 'Wskaż podświetlone pole ruchu (do 10 ft, bez ataków okazyjnych). ✓ bez wyboru pola pomija ruch i przechodzi do ataku.'
    if phase == 'attack':
        return 'Wybierz podświetlonego przeciwnika. Atak wyposażoną bronią jest już gotowy — nie wybieraj runy akcji.'
    if phase == 'confirm_attack':
        target = session._actor_by_string_id(session.pending_player_attack.target_id)
        return f'Wybrany cel: {target.name}. ✓ potwierdza i przechodzi do rzutu ataku. ↩ pozwala zmienić cel.'
    if phase == 'no_target':
        from .training_walkthrough import exercising
        return ('Brak legalnego celu dla wyposażonej broni. ✓ przechodzi dalej bez ataku tej figurki.'
            + (' Trzeba będzie ponowić ćwiczenie.' if exercising(session) else ''))
    return ''


def scan_target(session: ExplorationUiSession) -> BoardScanTarget | None:
    from .exploration_app import BoardScanTarget, _remaining_movement_range
    phase = stage(session)
    if not phase:
        return None
    actor = current_actor(session.combat_state)
    feedback = LedFeedback((LedFrame((actor.position,), LedColor.ACTIVE_ACTOR, LedRole.ACTIVE_ACTOR),))
    positions: tuple[Coordinate, ...] = ()
    controls = (28,)
    if phase == 'movement':
        movement = _remaining_movement_range(session._active_encounter().board, session.combat_state, actor, session.active_combat_effects)
        positions = tuple(sorted(movement.reachable_tiles | {actor.position}))
        feedback = movement_led_feedback(movement, session.selected_combat_movement_path)
        controls = (28, 29) if session.selected_combat_movement_path is not None else (28,)
    elif phase == 'attack':
        positions = tuple(t.position for t in targets(session))
        feedback = LedFeedback((*feedback.frames, LedFrame(positions, LedColor.ENEMY, LedRole.ENEMY)))
        controls = ()
    elif phase == 'confirm_attack':
        target = session._actor_by_string_id(session.pending_player_attack.target_id)
        feedback = LedFeedback((*feedback.frames, LedFrame((target.position,), LedColor.ENEMY, LedRole.ENEMY)))
        controls = (28, 29)
    return BoardScanTarget(positions=(*positions, *(panel_position(s) for s in controls)),
        feedback=panel_feedback((), control_slots=controls, base=feedback), empty_message=instruction(session))


def select(session: ExplorationUiSession, position: Coordinate) -> dict[str, object]:
    phase = stage(session)
    target = scan_target(session)
    if target is None or position not in target.positions:
        raise ValueError('Wybierz podświetlone pole albo dostępny przycisk Kontrataku.')
    session.board_selection_revision += 1
    if phase == 'movement':
        if position == panel_position(29):
            session.selected_combat_movement_path = None
        elif position == panel_position(28):
            path = session.selected_combat_movement_path
            if path is not None and path.valid:
                # submit renders the resulting state; prepare opens the attack there.
                previous = session.combat_state.shared_mana
                session.combat_state = replace(session.combat_state, shared_mana=replace(previous, command_stage='attack'))
                try:
                    return session.submit_combat_movement(col=path.destination.col, row=path.destination.row)
                except ValueError:
                    session.combat_state = replace(session.combat_state, shared_mana=previous)
                    raise
            session.combat_state = replace(session.combat_state,
                shared_mana=replace(session.combat_state.shared_mana, command_stage='attack'))
        else:
            session.preview_combat_movement(col=position.col, row=position.row)
    elif phase == 'attack':
        return session.select_player_attack_target_at_position(position)
    elif phase == 'confirm_attack':
        if position == panel_position(28):
            return session.confirm_player_attack_target()
        session._clear_player_pending_choices()
    elif phase == 'no_target':
        advance(session, skipped=True)
    if session.combat_state.shared_mana.command_step:
        prepare(session)
    session.board_message = instruction(session)
    session._sync_board_leds()
    return session.state_payload()
