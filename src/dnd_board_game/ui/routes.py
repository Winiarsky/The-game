from __future__ import annotations

from typing import TYPE_CHECKING

from flask import Flask, jsonify, render_template, request, send_from_directory

from dnd_board_game.actions import slash_commands_payload
from dnd_board_game.world import Coordinate

if TYPE_CHECKING:
    from .exploration_app import ExplorationUiSession


def create_app(session: ExplorationUiSession) -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        return render_template("exploration.html", slash_commands=slash_commands_payload())

    @app.get("/scenario-assets/<path:filename>")
    def scenario_assets(filename: str):
        return send_from_directory(session._scenario_asset_root().resolve(), filename)

    @app.get("/game-assets/<path:filename>")
    def game_assets(filename: str):
        return send_from_directory(session._game_asset_root().resolve(), filename)

    @app.get("/api/state")
    def api_state():
        return jsonify(session.state_payload())

    @app.get("/api/session-log")
    def api_session_log():
        return jsonify(_session_log_payload(session))

    @app.post("/api/npc-transition/resolve")
    def api_npc_transition_resolve():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.resolve_npc_transition(str(data.get("reaction_id", ""))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/snapshot/save")
    def api_snapshot_save():
        try:
            return jsonify(session.save_snapshot())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/snapshot/load")
    def api_snapshot_load():
        try:
            return jsonify(session.load_snapshot())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/start")
    def api_start():
        try:
            return jsonify(session.start_session())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/spell-preparation/confirm")
    def api_spell_preparation_confirm():
        data = request.get_json(silent=True) or {}
        raw_spell_ids = data.get("spell_ids", [])
        if not isinstance(raw_spell_ids, list):
            return jsonify({"error": "Pole spell_ids musi być listą.", "state": session.state_payload()}), 400
        try:
            return jsonify(
                session.confirm_spell_preparation(
                    actor_id=str(data.get("actor_id", "")),
                    spell_ids=tuple(str(spell_id) for spell_id in raw_spell_ids),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/rest/short/start")
    def api_short_rest_start():
        try:
            return jsonify(session.start_short_rest())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/rest/short/confirm")
    def api_short_rest_confirm():
        try:
            return jsonify(session.confirm_short_rest())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/rest/short/hit-die")
    def api_short_rest_hit_die():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.spend_short_rest_hit_die(
                    actor_id=str(data.get("actor_id", "")),
                    die_sides=int(data.get("die_sides", 0)),
                    natural_roll=int(data.get("natural_roll", 0)),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/rest/short/cancel")
    def api_short_rest_cancel():
        try:
            return jsonify(session.cancel_short_rest())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/rest/short/finish")
    def api_short_rest_finish():
        try:
            return jsonify(session.finish_short_rest())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/exploration/condition/recover")
    def api_exploration_condition_recover():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.recover_exploration_condition(
                    actor_id=str(data.get("actor_id", "")),
                    condition=str(data.get("condition", "")),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/action")
    def api_action():
        data = request.get_json(silent=True) or {}
        try:
            selected_goal_id = data.get("selected_goal_id")
            raw_participant_ids = data.get("participant_actor_ids", [])
            if not isinstance(raw_participant_ids, list):
                raise ValueError("participant_actor_ids musi być listą.")
            return jsonify(
                session.submit_action(
                    str(data.get("text", "")),
                    selected_goal_id=(
                        str(selected_goal_id)
                        if selected_goal_id is not None
                        else None
                    ),
                    selected_check_participants=(
                        str(data["check_participants"])
                        if data.get("check_participants") is not None
                        else None
                    ),
                    participant_actor_ids=tuple(
                        str(actor_id) for actor_id in raw_participant_ids
                    ),
                    conversation_only=bool(data.get("conversation_only", False)),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/decision")
    def api_decision():
        data = request.get_json(silent=True) or {}
        try:
            lead_actor_id = data.get("lead_actor_id")
            source_id = data.get("source_id")
            quantity = data.get("quantity")
            return jsonify(
                session.decide(
                    str(data.get("decision", "")),
                    lead_actor_id=str(lead_actor_id) if lead_actor_id else None,
                    source_id=str(source_id) if source_id else None,
                    quantity=int(quantity) if quantity is not None else None,
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/decision/correction")
    def api_decision_correction():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.update_pending_challenge_decision(data))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/crafting/dismantle")
    def api_crafting_dismantle():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.dismantle_temporary_item(str(data.get("item_id", ""))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/rolls")
    def api_rolls():
        data = request.get_json(silent=True) or {}
        rolls = data.get("rolls", {})
        if not isinstance(rolls, dict):
            return jsonify({"error": "Pole rolls musi być obiektem.", "state": session.state_payload()}), 400
        try:
            return jsonify(session.resolve_rolls(rolls))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/interaction/finish")
    def api_interaction_finish():
        try:
            return jsonify(session.finish_interaction_result())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/location/cancel-preview")
    def api_location_cancel_preview():
        try:
            return jsonify(session.cancel_location_preview())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/location/confirm-preview")
    def api_location_confirm_preview():
        try:
            return jsonify(session.confirm_location_preview())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/exploration/setup/confirm")
    def api_exploration_setup_confirm():
        try:
            return jsonify(session.confirm_exploration_setup_step())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/travel")
    def api_travel():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.travel_to(str(data.get("zone_id", ""))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/point")
    def api_point():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.select_point(str(data.get("point_id", ""))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/exploration/board-selection")
    def api_exploration_board_selection():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.set_exploration_board_selection(bool(data.get("enabled", False))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/board/configure")
    def api_board_configure():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.configure_board(
                    backend=str(data.get("backend", "none")),
                    board_url=str(data.get("board_url", "")),
                    board_serial_port=str(data.get("board_serial_port", "")),
                    wled_url=str(data.get("wled_url", "")),
                    scan_timeout_s=float(data["scan_timeout_s"]) if data.get("scan_timeout_s") not in {None, ""} else None,
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/board/scan")
    def api_board_scan():
        try:
            return jsonify(session.scan_board_selection())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/board/select")
    def api_board_select():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.select_board_position(Coordinate(int(data.get("col", 0)), int(data.get("row", 0)))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/board/reset-scan")
    def api_board_reset_scan():
        try:
            return jsonify(session.reset_board_scan())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/encounter/setup/start")
    def api_encounter_setup_start():
        try:
            return jsonify(session.start_encounter_setup())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/encounter/opening/resolve")
    def api_encounter_opening_resolve():
        try:
            return jsonify(session.resolve_encounter_opening())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/encounter/setup/confirm")
    def api_encounter_setup_confirm():
        try:
            return jsonify(session.confirm_encounter_setup_step())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/encounter/initiative/start")
    def api_encounter_initiative_start():
        try:
            return jsonify(session.start_encounter_initiative())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/encounter/stealth/roll")
    def api_encounter_stealth_roll():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.submit_precombat_stealth_roll(
                    actor_id=str(data.get("actor_id", "")),
                    natural_roll=int(data.get("natural_roll", 0)),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/encounter/stealth/finish")
    def api_encounter_stealth_finish():
        try:
            return jsonify(session.finish_precombat_stealth())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/encounter/initiative/roll")
    def api_encounter_initiative_roll():
        data = request.get_json(silent=True) or {}
        try:
            natural_roll_2 = data.get("natural_roll_2")
            return jsonify(
                session.submit_encounter_initiative_roll(
                    int(data.get("natural_roll", 0)),
                    int(natural_roll_2) if natural_roll_2 not in (None, "") else None,
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/player-attack-roll")
    def api_combat_player_attack_roll():
        data = request.get_json(silent=True) or {}
        try:
            natural_roll_2 = data.get("natural_roll_2")
            return jsonify(
                session.submit_player_attack_roll(
                    natural_roll=int(data.get("natural_roll", 0)),
                    natural_roll_2=int(natural_roll_2) if natural_roll_2 not in (None, "") else None,
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/attack-source")
    def api_combat_attack_source():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.select_combat_attack_source(str(data.get("source_id", ""))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/healing-source")
    def api_combat_healing_source():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.select_combat_healing_source(str(data.get("source_id", ""))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/player-attack-confirm")
    def api_combat_player_attack_confirm():
        try:
            return jsonify(session.confirm_player_attack_target())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/player-attack-cancel")
    def api_combat_player_attack_cancel():
        try:
            return jsonify(session.cancel_player_attack_target())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/player-damage")
    def api_combat_player_damage():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.submit_player_damage_roll(damage=int(data.get("damage", 0))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/player-healing")
    def api_combat_player_healing():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.submit_player_healing_roll(healing=int(data.get("healing", 0))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/player-healing-cancel")
    def api_combat_player_healing_cancel():
        try:
            return jsonify(session.cancel_player_healing())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/area-spell/confirm")
    def api_combat_area_spell_confirm():
        try:
            return jsonify(session.confirm_player_area_spell())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/area-spell/damage")
    def api_combat_area_spell_damage():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.submit_player_area_spell_damage(damage=int(data.get("damage", 0))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/area-spell/cancel")
    def api_combat_area_spell_cancel():
        try:
            return jsonify(session.cancel_player_area_spell())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/strength-potion")
    def api_combat_strength_potion():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.use_combat_strength_potion(str(data.get("action_id", ""))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/concentration/start")
    def api_combat_concentration_start():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.start_combat_concentration_action(str(data.get("action_id", ""))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/concentration/confirm")
    def api_combat_concentration_confirm():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.confirm_combat_concentration_action(target_id=str(data.get("target_id", ""))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/concentration/cancel")
    def api_combat_concentration_cancel():
        try:
            return jsonify(session.cancel_combat_concentration_action())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/concentration-check")
    def api_combat_concentration_check():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.submit_concentration_check(natural_roll=int(data.get("natural_roll", 0))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/interaction/confirm")
    def api_combat_interaction_confirm():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.confirm_combat_interaction(str(data.get("interaction_id", ""))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/interaction/cancel")
    def api_combat_interaction_cancel():
        try:
            return jsonify(session.cancel_combat_interaction())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/context-menu/select")
    def api_combat_context_menu_select():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.move_combat_context_menu_selection(int(data.get("delta", 0))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/context-menu/confirm")
    def api_combat_context_menu_confirm():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.confirm_combat_context_menu(str(data.get("option_id", ""))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/context-menu/cancel")
    def api_combat_context_menu_cancel():
        try:
            return jsonify(session.cancel_combat_context_menu())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/move")
    def api_combat_move():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.submit_combat_movement(col=int(data.get("col", 0)), row=int(data.get("row", 0))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/opportunity-movement/confirm")
    def api_combat_opportunity_movement_confirm():
        try:
            return jsonify(session.confirm_opportunity_movement())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/opportunity-movement/cancel")
    def api_combat_opportunity_movement_cancel():
        try:
            return jsonify(session.cancel_opportunity_movement())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/dash")
    def api_combat_dash():
        try:
            return jsonify(session.use_combat_dash())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/dodge")
    def api_combat_dodge():
        try:
            return jsonify(session.use_combat_dodge())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/disengage")
    def api_combat_disengage():
        try:
            return jsonify(session.use_combat_disengage())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/hide/start")
    def api_combat_hide_start():
        try:
            return jsonify(session.start_combat_hide())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/search/start")
    def api_combat_search_start():
        try:
            return jsonify(session.start_combat_search())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/skill-check")
    def api_combat_skill_check():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.submit_combat_skill_check(natural_roll=int(data.get("natural_roll", 0))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/skill-check/cancel")
    def api_combat_skill_check_cancel():
        try:
            return jsonify(session.cancel_combat_skill_check())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/shove/start")
    def api_combat_shove_start():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.start_combat_shove(
                    target_id=str(data.get("target_id", "")),
                    mode=str(data.get("mode", "")),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/shove/resolve")
    def api_combat_shove_resolve():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.submit_combat_shove(
                    attacker_natural_roll=int(data.get("natural_roll", 0)),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/shove/cancel")
    def api_combat_shove_cancel():
        try:
            return jsonify(session.cancel_combat_shove())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/grapple/start")
    def api_combat_grapple_start():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.start_combat_grapple(
                    target_id=str(data.get("target_id", "")),
                    mode=str(data.get("mode", "")),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/grapple/resolve")
    def api_combat_grapple_resolve():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.submit_combat_grapple(
                    actor_natural_roll=int(data.get("natural_roll", 0)),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/grapple/cancel")
    def api_combat_grapple_cancel():
        try:
            return jsonify(session.cancel_combat_grapple())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/help/start")
    def api_combat_help_start():
        try:
            return jsonify(session.start_combat_help())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/help/confirm")
    def api_combat_help_confirm():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.confirm_combat_help(ally_id=str(data.get("ally_id", "")), target_id=str(data.get("target_id", ""))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/help/cancel")
    def api_combat_help_cancel():
        try:
            return jsonify(session.cancel_combat_help())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/ready/start")
    def api_combat_ready_start():
        try:
            return jsonify(session.start_combat_ready())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/ready/confirm")
    def api_combat_ready_confirm():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.confirm_combat_ready(trigger=str(data.get("trigger", ""))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/ready/cancel")
    def api_combat_ready_cancel():
        try:
            return jsonify(session.cancel_combat_ready())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/enemy-turn")
    def api_combat_enemy_turn():
        try:
            return jsonify(session.resolve_enemy_turn())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/enemy-opportunity/start")
    def api_combat_enemy_opportunity_start():
        try:
            return jsonify(session.start_enemy_opportunity_attack())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/enemy-opportunity/skip")
    def api_combat_enemy_opportunity_skip():
        try:
            return jsonify(session.skip_enemy_opportunity_attack())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/enemy-opportunity/roll")
    def api_combat_enemy_opportunity_roll():
        data = request.get_json(silent=True) or {}
        try:
            natural_roll_2 = data.get("natural_roll_2")
            return jsonify(
                session.submit_enemy_opportunity_attack_roll(
                    natural_roll=int(data.get("natural_roll", 0)),
                    natural_roll_2=int(natural_roll_2) if natural_roll_2 not in (None, "") else None,
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/enemy-opportunity/damage")
    def api_combat_enemy_opportunity_damage():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.submit_enemy_opportunity_damage_roll(damage=int(data.get("damage", 0))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/ready-attack/start")
    def api_combat_ready_attack_start():
        try:
            return jsonify(session.start_ready_attack())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/ready-attack/skip")
    def api_combat_ready_attack_skip():
        try:
            return jsonify(session.skip_ready_attack())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/ready-attack/roll")
    def api_combat_ready_attack_roll():
        data = request.get_json(silent=True) or {}
        try:
            natural_roll_2 = data.get("natural_roll_2")
            return jsonify(
                session.submit_ready_attack_roll(
                    natural_roll=int(data.get("natural_roll", 0)),
                    natural_roll_2=int(natural_roll_2) if natural_roll_2 not in (None, "") else None,
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/ready-attack/damage")
    def api_combat_ready_attack_damage():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.submit_ready_damage_roll(damage=int(data.get("damage", 0))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/enemy-turn/confirm")
    def api_combat_enemy_turn_confirm():
        try:
            return jsonify(session.confirm_enemy_turn_result())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/enemy-saving-throw")
    def api_combat_enemy_saving_throw():
        data = request.get_json(silent=True) or {}
        try:
            natural_roll_2 = data.get("natural_roll_2")
            return jsonify(
                session.submit_enemy_saving_throw(
                    natural_roll=int(data.get("natural_roll", 0)),
                    natural_roll_2=(
                        int(natural_roll_2) if natural_roll_2 not in (None, "") else None
                    ),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/end-turn")
    def api_combat_end_turn():
        try:
            return jsonify(session.finish_combat_turn())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/death-save")
    def api_combat_death_save():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.submit_death_save(int(data.get("natural_roll", 0))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/condition-save")
    def api_combat_condition_save():
        data = request.get_json(silent=True) or {}
        try:
            natural_roll_2 = data.get("natural_roll_2")
            return jsonify(
                session.submit_combat_condition_save(
                    condition=str(data.get("condition", "")),
                    natural_roll=int(data.get("natural_roll", 0)),
                    natural_roll_2=(
                        int(natural_roll_2) if natural_roll_2 not in (None, "") else None
                    ),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/stabilize")
    def api_combat_stabilize():
        data = request.get_json(silent=True) or {}
        try:
            natural_roll = data.get("natural_roll")
            return jsonify(
                session.stabilize_combat_actor(
                    target_id=str(data.get("target_id", "")),
                    method=str(data.get("method", "medicine")),
                    natural_roll=int(natural_roll) if natural_roll not in (None, "") else None,
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/encounter/combat/resolve")
    def api_encounter_combat_resolve():
        try:
            return jsonify(session.resolve_active_combat())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/reset")
    def api_reset():
        session.reset()
        return jsonify(session.state_payload())

    @app.post("/api/scenario/finish")
    def api_scenario_finish():
        try:
            return jsonify(session.finish_scenario())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    return app


def _session_log_payload(session: ExplorationUiSession, *, limit: int = 200) -> dict[str, object]:
    path = session.observer.path
    events: list[dict[str, object]] = []
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()[-limit:]
        import json

        for line in lines:
            if not line.strip():
                continue
            events.append(json.loads(line))
    return {
        "session_id": session.observer.session_id,
        "path": str(path),
        "events": events,
    }
