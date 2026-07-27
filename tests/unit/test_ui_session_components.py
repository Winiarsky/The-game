from dnd_board_game.ui.session_state import UiPendingState
from dnd_board_game.ui.session_view import UiSessionView


def test_pending_state_clears_only_player_choice_flow() -> None:
    state = UiPendingState(
        encounter="encounter",
        enemy_turn_result="enemy-result",
        enemy_saving_throw="enemy-save",
        player_attack="attack",
        player_healing="healing",
        combat_help="help",
        opportunity_movement="movement",
    )

    state.clear_player_choices()

    assert state.encounter == "encounter"
    assert state.enemy_turn_result == "enemy-result"
    assert state.enemy_saving_throw == "enemy-save"
    assert state.player_attack is None
    assert state.player_healing is None
    assert state.combat_help is None
    assert state.opportunity_movement is None


def test_ui_session_view_preserves_api_state_contract() -> None:
    payload = UiSessionView(
        scenario={"id": "scene"},
        session_log={"session_id": "test"},
        snapshot={"can_save": True},
        flow={"stage": "location_active"},
        spell_preparation=None,
        short_rest=None,
        current_zone={"id": "gate"},
        available_zones=[],
        visible_environment=[],
        travel_options=[],
        visible_points=[],
        current_zone_points=[],
        active_challenge=None,
        active_point=None,
        trade=None,
        resources=[],
        discovered_sources=[],
        actors=[],
        active_effects=[],
        scene_status=[],
        flags=[],
        messages=[],
        conversation={"messages": []},
        pending=None,
        pending_npc_transition=None,
        selected_lead_actor_id="hero",
        selected_helper_actor_id=None,
        allowed_mechanics=[],
        pending_encounter=None,
        exploration_setup=None,
        encounter_setup=None,
        encounter_stealth=None,
        encounter_initiative=None,
        combat=None,
        board={"backend": "none"},
        required_rolls=[],
    ).as_payload()

    assert payload["scenario"] == {"id": "scene"}
    assert payload["flow"] == {"stage": "location_active"}
    assert payload["selected_lead_actor_id"] == "hero"
    assert payload["board"] == {"backend": "none"}
    assert payload["combat"] is None
    assert payload["active_effects"] == []
