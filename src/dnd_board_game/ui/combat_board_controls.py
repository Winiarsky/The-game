"""One confirmation contract for the screen, scan mask and physical LEDs."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .exploration_app import ExplorationUiSession


def preview_confirmation(session: ExplorationUiSession) -> bool | None:
    """None leaves an interrupt/dice wizard in charge of its own confirmation."""
    if session.combat_targeting_item_action_id:
        return session.combat_selected_item_target_id is not None
    pending = session.pending_player_attack
    if pending is not None:
        return True if pending.stage == "confirm_attack" else None
    if session._board_panel_feature_preview_active():
        if session.brakka_shoulder_check_rolls:
            return session.brakka_shoulder_check_destination is not None
        return bool(session.combat_selected_class_feature_target_id
                    or session.combat_selected_class_feature_target_ids)
    option_id = session.combat_turn_preview_option_id
    if option_id:
        from dnd_board_game.combat.context_menu import CombatMenuAction
        option = next((item for item in session._combat_turn_action_options()
                       if item.id == option_id), None)
        if option is None or session._combat_turn_option_unavailable_reason(option):
            return False
        if option.action == CombatMenuAction.MOVE:
            path = session.selected_combat_movement_path
            return bool(path and path.valid)
        if option.action in {CombatMenuAction.SELECT_ATTACK_SOURCE,
                             CombatMenuAction.SELECT_HEALING_SOURCE}:
            return False
        if option.provider == "turn_maneuver":
            return False
        return True
    if session.combat_targeting_attack_source_id or session.combat_targeting_healing_source_id:
        return False
    state = session.combat_state
    if state is not None and state.status.value == "active":
        from dnd_board_game.combat import current_actor
        if (current_actor(state).faction.value == "enemy"
                and not session._combat_has_pending_resolution(ignore_enemy_confirmation=True)):
            # Starting the enemy action, accepting its intent and acknowledging
            # its result use ✓. Physical destinations and interrupts keep their
            # own controls and must be resolved first.
            return True
    return None


def information_available(session: ExplorationUiSession) -> bool:
    if (session.combat_state is None or session.combat_state.status.value != "active"
            or not session._board_panel_enabled()):
        return False
    if session.board_panel_context and session.board_panel_context[0].startswith("combat-inspect:"):
        return True
    return (not session._combat_has_pending_resolution()
            or session._board_panel_feature_preview_active()
            or bool(session.pending_player_attack and session.pending_player_attack.stage == "confirm_attack"))
