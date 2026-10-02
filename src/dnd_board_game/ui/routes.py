from __future__ import annotations

from .shield_bash import submit_shield_bash, confirm_shield_bash
from dnd_board_game.physical_cards.mana_symbols import mana_text
from dnd_board_game.physical_cards.mana_print_html import chips

from dnd_board_game.application.recruitment_arena import ARENA_ID, NESSA_POSITION
from dnd_board_game.ui.training_arena import training_hero, start_training_trial, can_talk_to_nessa

from dataclasses import replace
from pathlib import Path
import hashlib
import time
from typing import TYPE_CHECKING
from uuid import uuid4

from flask import (
    Flask,
    Response,
    abort,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)

from dnd_board_game.character_creation.runes import apply_rune_profile
from dnd_board_game.actions import slash_commands_payload
from dnd_board_game.actors import AbilityScores, FeatureGrant
from dnd_board_game.character_creation import (
    ABILITY_IDS,
    CLASS_CHOICE_GROUP_HELP,
    FIGHTING_STYLE_HELP,
    POINT_BUY_BUDGET,
    POINT_BUY_COSTS,
    SKILL_CHOICE_HELP,
    CharacterDraft,
    CharacterRoster,
    CharacterRosterScan,
    LevelUpChoices,
    build_character,
    class_feature_help,
    character_record_payload,
    load_character_catalog,
    load_character_resources,
    level_up_character,
    origin_feature_help,
    validate_character_draft,
    HERO_ARCHETYPES_BY_ID,
    PLAYABLE_HERO_IDS,
    apply_boardgame_archetype,
)
from dnd_board_game.combat.archetype_flaws import FLAW_FEATURE_IDS
from dnd_board_game.core.player_labels_pl import PLAYER_LABELS_PL, player_label
from dnd_board_game.inventory import effective_armor_class
from dnd_board_game.physical_cards import (
    DecisionCardActionKind,
    normalize_decision_card_scanner_text,
    parse_actor_card_qr_payload,
    parse_decision_card_qr_payload,
    resolve_universal_card_scan,
)
from dnd_board_game.rules import experience_progress
from dnd_board_game.scenarios import discover_scenarios
from dnd_board_game.world import Coordinate

from .hero_selection import HERO_SELECTION_GUIDES, physical_mana_guides
from dnd_board_game.rules.physical_mana import mana_ability, hero_abilities, FLAWS, MANA_PASSIVES, turn_supply
from dnd_board_game.character_creation.physical_mana_help import physical_mana_passives, visible_character_features
from dnd_board_game.combat.physical_mana import WAVES
from dnd_board_game.character_creation.boardgame_help import ACTIVE_FEATURE_HELP, FLAW_HELP, HERO_FLAWS, PASSIVE_HELP

if TYPE_CHECKING:
    from .exploration_app import ExplorationUiSession


PLAYER_SCENARIO_IDS = ("misja_0_dzwon", "ostatni_transport_00_gildia")


def create_app(
    session: ExplorationUiSession,
    *,
    character_dir: str | Path = "data/characters",
    scenario_dir: str | Path = "content/scenarios",
) -> Flask:
    app = Flask(__name__)

    def static_asset_url(filename: str) -> str:
        """An edited UI asset gets a new URL even when its name stays the same."""
        digest = hashlib.sha256((Path(app.static_folder) / filename).read_bytes()).hexdigest()[:12]
        return url_for("static", filename=filename, v=digest)

    app.jinja_env.globals["static_asset_url"] = static_asset_url
    from .board_panel_symbols import panel_icon
    from . import launcher_board
    app.jinja_env.globals['panel_icon'] = panel_icon

    @app.context_processor
    def launcher_context():
        from .session_copy import load_ui_copy, render_ui_text
        copy = load_ui_copy()
        return {'launcher_token': getattr(g, 'launcher_token', ''), 'ui_copy': copy,
                'ui_text': lambda key, **values: render_ui_text(copy, key, **values)}
    character_catalog = load_character_catalog(
        Path("content/character_creation/catalog.json")
    )
    character_resources = load_character_resources(character_catalog, "content")
    character_roster = CharacterRoster(
        character_dir,
        character_catalog,
        character_resources,
    )
    character_portrait_dir = Path(character_dir) / "portraits"
    character_class_names = {
        character_class.id: character_class.name
        for character_class in character_catalog.classes
    }
    app.jinja_env.globals["character_portrait_url"] = _character_portrait_url

    def persist_character_progress(actors) -> None:
        if session.exploration.scenario_id == ARENA_ID:
            return
        for actor in actors:
            character_roster.update_experience(
                str(actor.id),
                actor.experience_points,
            )

    session.character_progress_sink = persist_character_progress

    def scenario_choices():
        discovered = {
            scenario.id: scenario
            for scenario in discover_scenarios(scenario_dir)
        }
        return tuple(
            discovered[scenario_id]
            for scenario_id in PLAYER_SCENARIO_IDS
            if scenario_id in discovered
        )

    def new_game_context(**extra):
        choices = scenario_choices()
        roster_scan = character_roster.scan()
        roster = CharacterRosterScan(
            tuple(
            character
            for character in roster_scan.characters
            if str(character.actor.id) in PLAYABLE_HERO_IDS
            ),
            roster_scan.errors,
        )
        return {
            "scenarios": choices,
            "active_scenario_id": session.exploration.scenario_id,
            "selected_scenario_id": choices[0].id if len(choices) == 1 else "",
            "roster": roster,
            "class_names": character_class_names,
            "hero_guides": physical_mana_guides(),
            "hero_flaws": FLAW_FEATURE_IDS,
            **extra,
        }

    @app.get("/rules/physical-mana")
    def physical_mana_rules():
        from dnd_board_game.physical_cards.mana_print import build_print_hero
        from dnd_board_game.scenarios.confrontation import reminder, condition_help
        from dnd_board_game.scenarios.pooled_mana_catalog import hero_profile
        from dnd_board_game.physical_cards.mana_print import turn_reminders, mana_passive_reminder
        names = {"garran": "Garran", "brakka": "Brakka", "mira": "Mira", "dagna": "Dagna", "lorian": "Lorian", "nimra": "Nimra", "erynd": "Erynd"}
        return render_template("physical_mana.html", waves=WAVES, mana_text=mana_text, mana_chips=chips, exploration_reminder=reminder(), exploration_conditions=condition_help(), pool_rules=turn_reminders(), mana_passive_reminder=mana_passive_reminder(),
            heroes=[{"id": hero_id, "name": name, "abilities": build_print_hero(hero_id).cards, "values": hero_profile(hero_id)["values"],
                     "flaw": ("", hero_profile(hero_id)["flaw_name"], hero_profile(hero_id)["flaw"]), "passive": ("", hero_profile(hero_id)["passive_name"], hero_profile(hero_id)["passive"]), "notes": "\n".join(f"{note.name}: {note.body}" for note in physical_mana_passives(hero_id)[:-1]), "supply": turn_supply(hero_id), "exploration": build_print_hero(hero_id).exploration, "exploration_passives": build_print_hero(hero_id).exploration_passives, "mana_passives": build_print_hero(hero_id).mana_passives}
                    for hero_id,name in names.items()])

    @app.get("/")
    def index():
        return render_template(
            "main_menu.html",
            scenario_name=session.exploration.scenario_name,
            save_exists=session.snapshot_path.exists() or (session.save_dir/"misja_0_dzwon.snapshot.json").exists(),
        )

    @app.post("/training/open")
    def open_training_arena():
        session.configure_scenario(Path("content/scenarios/recruitment_arena.json"))
        session.configure_custom_party((training_hero("garran"),))
        return redirect(url_for("play"))

    @app.post("/api/training/nessa")
    def talk_to_training_nessa():
        if not can_talk_to_nessa(session):
            return jsonify(error="Podejdź do Nessy w swojej turze i zakończ bieżącą akcję.", state=session.state_payload()), 400
        return jsonify(session.select_combat_interaction_at_position(NESSA_POSITION))

    @app.post("/api/training/start")
    def start_training():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(start_training_trial(session, str(data.get("hero_id", "")),
                           str(data.get("mode", "walkthrough")), str(data.get("creature_type", "humanoid")),
                           reset_progress=bool(data.get("reset_progress", False)),
                           case_id=str(data["case_id"]) if "case_id" in data else None))
        except ValueError as error:
            return jsonify(error=str(error), state=session.state_payload()), 400

    @app.post("/api/training/menu")
    def training_menu_action():
        from .training_menu import command
        try:
            return jsonify(command(session, request.get_json(silent=True) or {}))
        except (ValueError, TypeError) as error:
            return jsonify(error=str(error), state=session.state_payload()), 400

    @app.post("/api/exploration-mana")
    def exploration_mana_action():
        from .exploration_mana import command
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(command(session, data))
        except (ValueError, TypeError) as error:
            return jsonify(error=str(error), state=session.state_payload()), 400

    @app.post("/api/simple-trap")
    def simple_trap_action():
        from .simple_traps import command
        try:
            return jsonify(command(session, request.get_json(silent=True) or {}))
        except (ValueError, TypeError) as error:
            return jsonify(error=str(error), state=session.state_payload()), 400

    def guard_exploration_lesson():
        from .exploration_mana import active
        from .simple_traps import enabled as trap_enabled, read as trap_read
        if (request.method == "POST" and request.path.startswith("/api/")
                and not request.path.startswith("/api/board/") and trap_enabled(session)
                and trap_read(session)['pending'] and request.path not in
                {"/api/simple-trap", "/api/snapshot/save", "/api/snapshot/load"}):
            return jsonify(error="Najpierw rozstrzygnij test pułapki.", state=session.state_payload()), 400
        if (request.method == "POST" and request.path.startswith("/api/") and not request.path.startswith("/api/board/") and active(session)
                and request.path not in {"/api/exploration-mana", "/api/snapshot/save", "/api/snapshot/load",
                                         "/api/board/scan", "/api/board/reset-scan"}):
            return jsonify(error="Najpierw zakończ lub opuść aktywną konfrontację.", state=session.state_payload()), 400

    @app.post("/api/training/leave")
    def leave_training():
        from .training_walkthrough import leave
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(leave(session, retry=data.get("retry") is True, choose_case=data.get("choose_case") is True))
        except ValueError as error:
            return jsonify(error=str(error), state=session.state_payload()), 400

    @app.post("/api/training/acknowledge")
    def acknowledge_training():
        from .training_tutorial import acknowledge
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(acknowledge(session, str(data.get("ability_id", ""))))
        except ValueError as error:
            return jsonify(error=str(error), state=session.state_payload()), 400

    @app.get("/play")
    def play():
        launcher_board.leave(session)
        return render_template("exploration.html", slash_commands=slash_commands_payload())

    @app.get("/session-materials")
    def session_materials():
        from dnd_board_game.physical_cards import handout_files
        materials = []
        for spec in handout_files.HANDOUT_FILES:
            try:
                exists = handout_files.handout_path(
                    spec.filename, root=handout_files.HANDOUTS_ROOT,
                ).is_file()
            except ValueError:
                exists = False
            materials.append(dict(filename=spec.filename, label=spec.label_key,
                                  title=spec.title, exists=exists))
        return render_template("session_materials.html", materials=materials)

    @app.get("/session-materials/<path:filename>")
    def session_material_file(filename: str):
        from dnd_board_game.physical_cards import handout_files
        try:
            path = handout_files.handout_path(filename, root=handout_files.HANDOUTS_ROOT)
        except ValueError:
            abort(404)
        if not path.is_file():
            abort(404)
        return send_from_directory(handout_files.HANDOUTS_ROOT, filename)

    @app.get("/new-game")
    def new_game():
        return render_template("new_game.html", **new_game_context())

    @app.post("/new-game/start")
    def start_new_game():
        selected_actor_ids = tuple(
            str(actor_id).strip()
            for actor_id in request.form.getlist("character_ids")
            if str(actor_id).strip()
        )
        scenario_id = str(request.form.get("scenario_id", "")).strip()

        def selection_error(message: str):
            return render_template(
                "new_game.html",
                **new_game_context(
                    selected_character_ids=selected_actor_ids,
                    selected_scenario_id=scenario_id,
                    initial_stage="scenario" if selected_actor_ids else "party",
                ),
                error=message,
            ), 400

        if not 1 <= len(selected_actor_ids) <= 6:
            return selection_error("Wybierz od 1 do 6 bohaterów.")
        if len(set(selected_actor_ids)) != len(selected_actor_ids):
            return selection_error("Każdego bohatera można wybrać tylko raz.")
        if any(actor_id not in PLAYABLE_HERO_IDS for actor_id in selected_actor_ids):
            return selection_error("Wybrano bohatera spoza dostępnego zestawu.")

        if scenario_id == "misja_0_dzwon" and len(selected_actor_ids) < 3:
            return selection_error("Misja 0 wymaga 3–6 bohaterów.")
        if scenario_id != "misja_0_dzwon" and len(selected_actor_ids) > 5:
            return selection_error("Ten starszy scenariusz obsługuje do 5 bohaterów.")
        scenarios_by_id = {entry.id: entry for entry in scenario_choices()}
        selected_scenario = scenarios_by_id.get(scenario_id)
        if selected_scenario is None:
            return selection_error("Wybierz dostępny scenariusz.")

        try:
            party = tuple(
                apply_boardgame_archetype(
                    character_roster.load(actor_id).actor,
                    spell_definitions=tuple(
                        spell for _, spell in character_resources.spells
                    ),
                )
                for actor_id in selected_actor_ids
            )
        except (FileNotFoundError, TypeError, ValueError):
            return selection_error("Nie udało się wczytać wybranego bohatera.")

        session.configure_scenario(selected_scenario.path)
        session.configure_custom_party(tuple(apply_rune_profile(actor) for actor in party))
        if scenario_id == "misja_0_dzwon":
            from .mission_zero import initialize
            initialize(session)
        return redirect(url_for("play"))

    @app.post("/api/mission/action")
    def mission_action():
        from .mission_zero import command
        try:
            return jsonify(command(session, request.get_json(silent=True) or {}))
        except (ValueError, KeyError, TypeError) as exc:
            return jsonify(error=str(exc)), 400

    @app.get("/load-game")
    def load_game():
        return render_template(
            "load_game.html",
            mission_save=(session.save_dir/"misja_0_dzwon.snapshot.json").exists() and session.exploration.scenario_id != "misja_0_dzwon",
            save={
                "exists": session.snapshot_path.exists(),
                "scenario_name": session.exploration.scenario_name,
                "path": str(session.snapshot_path),
            },
        )

    @app.post("/load-game/mission-zero")
    def load_mission_zero():
        path=session.save_dir/"misja_0_dzwon.snapshot.json"
        if not path.exists():
            return redirect(url_for("load_game"))
        session.configure_scenario(Path("content/scenarios/misja_0_dzwon/scenario.json"))
        session.load_snapshot()
        return redirect(url_for("play"))

    @app.post("/load-game/current")
    def load_current_game():
        if not session.snapshot_path.exists():
            return render_template(
                "load_game.html",
                save={
                    "exists": False,
                    "scenario_name": session.exploration.scenario_name,
                    "path": str(session.snapshot_path),
                },
                error="Nie znaleziono kompatybilnego zapisu gry.",
            ), 404
        session.load_snapshot()
        return redirect(url_for("play"))

    @app.get("/characters")
    def characters():
        return render_template(
            "character_creator.html",
            roster=character_roster.scan(),
        )

    @app.get("/characters/new")
    def new_character():
        return _render_character_form(
            character_catalog,
            character_resources,
            form={},
            issues=(),
        )

    @app.post("/characters")
    def create_character():
        draft = _character_draft_from_request(
            character_roster.next_character_id(
                str(request.form.get("name", "")).strip()
            )
        )
        validation = validate_character_draft(draft, character_catalog)
        if not validation.valid:
            return _render_character_form(
                character_catalog,
                character_resources,
                form=request.form,
                issues=validation.issues,
            ), 400
        uploaded_portrait_path: Path | None = None
        try:
            portrait_file = request.files.get("portrait_file")
            if portrait_file is not None and portrait_file.filename:
                portrait, uploaded_portrait_path = _store_character_portrait(
                    portrait_file,
                    character_id=draft.id,
                    portrait_dir=character_portrait_dir,
                )
                draft = replace(draft, portrait=portrait)
            character = build_character(
                draft,
                character_catalog,
                character_resources,
            )
            character_roster.save(character)
        except ValueError as exc:
            if uploaded_portrait_path is not None and uploaded_portrait_path.exists():
                uploaded_portrait_path.unlink()
            return _render_character_form(
                character_catalog,
                character_resources,
                form=request.form,
                issues=({"field": "portrait", "message": str(exc)},),
            ), 400
        return redirect(url_for("character_detail", character_id=str(character.actor.id)))

    @app.get("/characters/<character_id>")
    def character_detail(character_id: str):
        try:
            character = character_roster.load(character_id)
        except ValueError as exc:
            return render_template(
                "character_not_found.html",
                message=str(exc),
            ), 404
        character = replace(character, actor=apply_rune_profile(character.actor))
        return render_template(
            "character_detail.html",
            character=character,
            archetype=_physical_mana_archetype(str(character.actor.id)),
            mana_profile=turn_supply(str(character.actor.id)) if hero_abilities(str(character.actor.id)) else None,
            payload=character_record_payload(character),
            effective_ac=effective_armor_class(character.actor),
            experience=experience_progress(character.actor),
            species=character_catalog.species_by_id(character.species_id),
            character_class=character_catalog.class_by_id(character.class_id),
            background=character_catalog.background_by_id(character.background_id),
            labels=_PLAYER_LABELS,
            feature_entries=_character_sheet_feature_entries(
                visible_character_features(character.actor), actor_id=str(character.actor.id)
            ),
        )

    @app.get("/characters/<character_id>/copy")
    def copy_character(character_id: str):
        try:
            character = character_roster.load(character_id)
        except ValueError as exc:
            return render_template(
                "character_not_found.html",
                message=str(exc),
            ), 404
        return _render_character_form(
            character_catalog,
            character_resources,
            form=_copy_character_form(character),
            issues=(),
            copy_source=character.actor.name,
        )

    @app.get("/characters/<character_id>/level-up")
    def character_level_up(character_id: str):
        try:
            character = character_roster.load(character_id)
        except ValueError as exc:
            return render_template(
                "character_not_found.html",
                message=str(exc),
            ), 404
        return render_template(
            "character_level_up.html",
            **_level_up_context(
                character,
                character_catalog,
                character_resources,
            ),
        )

    @app.post("/characters/<character_id>/level-up")
    def apply_character_level_up(character_id: str):
        try:
            character = character_roster.load(character_id)
            result = level_up_character(
                character,
                character_catalog,
                character_resources,
                choices=LevelUpChoices(
                    selected_cantrip_ids=tuple(
                        request.form.getlist("selected_cantrip_ids")
                    ),
                    selected_spell_ids=tuple(
                        request.form.getlist("selected_spell_ids")
                    ),
                    selected_prepared_spell_ids=tuple(
                        request.form.getlist("selected_prepared_spell_ids")
                    ),
                    selected_subclass_id=str(
                        request.form.get("selected_subclass_id", "")
                    ),
                    selected_expertise_ids=tuple(
                        request.form.getlist("selected_expertise_ids")
                    ),
                    selected_fighting_style_id=str(
                        request.form.get("selected_fighting_style_id", "")
                    ),
                    selected_class_option_ids=tuple(
                        request.form.getlist("selected_class_option_ids")
                    ),
                ),
            )
            character_roster.save(
                replace(
                    result.character_after,
                    actor=apply_boardgame_archetype(
                        result.character_after.actor,
                        spell_definitions=tuple(
                            spell for _, spell in character_resources.spells
                        ),
                    ),
                ),
                overwrite=True,
            )
        except ValueError as exc:
            try:
                character = character_roster.load(character_id)
            except ValueError:
                return render_template(
                    "character_not_found.html",
                    message=str(exc),
                ), 404
            return render_template(
                "character_level_up.html",
                **_level_up_context(
                    character,
                    character_catalog,
                    character_resources,
                    form=request.form,
                    error=str(exc),
                ),
            ), 400
        return redirect(
            url_for("character_detail", character_id=character_id)
        )

    @app.post("/characters/<character_id>/delete")
    def delete_character(character_id: str):
        try:
            character_roster.delete(character_id)
        except ValueError as exc:
            return render_template(
                "character_not_found.html",
                message=str(exc),
            ), 404
        return redirect(url_for("characters", deleted=character_id))

    @app.get("/equipment-art/<name>.png")
    def equipment_art_asset(name: str):
        from dnd_board_game.physical_cards.equipment_art import artwork_path
        try:
            path = artwork_path(name)
        except ValueError:
            abort(404)
        return send_from_directory(path.parent, path.name, conditional=True)

    @app.get("/scenario-assets/<path:filename>")
    def scenario_assets(filename: str):
        return send_from_directory(session._scenario_asset_root().resolve(), filename)

    @app.get("/game-assets/<path:filename>")
    def game_assets(filename: str):
        return send_from_directory(session._game_asset_root().resolve(), filename)

    @app.get("/character-portraits/<path:filename>")
    def character_portraits(filename: str):
        return send_from_directory(character_portrait_dir.resolve(), filename)

    @app.get("/api/state")
    def api_state():
        return jsonify(session.state_payload())

    @app.get("/api/session-log")
    def api_session_log():
        return jsonify(_session_log_payload(session))

    @app.post("/api/physical-cards/scan")
    def api_physical_card_scan():
        data = request.get_json(silent=True) or {}
        payload = data.get("payload")
        if not isinstance(payload, str) or not payload or len(payload) > 256:
            return jsonify({"error": "Nieprawidłowy payload karty decyzji."}), 400
        normalized = normalize_decision_card_scanner_text(payload)
        if ":actor:" in normalized:
            try:
                actor_card = parse_actor_card_qr_payload(normalized)
                context = data.get("context")
                if (
                    isinstance(context, dict)
                    and context.get("continuation_stage") == "navigator"
                ):
                    navigator = session.declare_continuation_navigator(
                        actor_card.actor_id
                    )
                    return jsonify(
                        {
                            "applied": False,
                            "effect": "select_continuation_navigator",
                            "label": navigator["actor_name"],
                            "payload": normalized,
                            **navigator,
                            "feedback": {
                                "status": "waiting",
                                "next_step": "enter_navigation_roll",
                                "message": (
                                    f"{navigator['actor_name']} prowadzi drużynę. "
                                    "Wpisz naturalny wynik rzutu na nawigację."
                                ),
                            },
                        }
                    )
                selection = session.board_actor_selection
                if selection is None:
                    zone_option_id = (
                        str(context.get("zone_option_id", ""))
                        if isinstance(context, dict)
                        else ""
                    )
                    state = session.state_payload()
                    zone_option = next(
                        (
                            option
                            for option in state.get("flow", {}).get(
                                "zone_options",
                                [],
                            )
                            if str(option.get("id")) == zone_option_id
                            and option.get("check") is not None
                        ),
                        None,
                    )
                    actor = next(
                        (
                            candidate
                            for candidate in state.get("actors", [])
                            if str(candidate.get("id")) == actor_card.actor_id
                            and candidate.get("faction") == "ally"
                            and not candidate.get("defeated", False)
                        ),
                        None,
                    )
                    if zone_option is None:
                        raise ValueError(
                            "Aplikacja nie oczekuje teraz wyboru bohatera."
                        )
                    assigned_actor_id = zone_option.get("assigned_actor_id")
                    if assigned_actor_id:
                        assigned_actor = zone_option.get("assigned_actor")
                        assigned_actor_name = (
                            str(assigned_actor.get("name", assigned_actor_id))
                            if isinstance(assigned_actor, dict)
                            else str(assigned_actor_id)
                        )
                        raise ValueError(
                            "Ta scena ma już przypisanego wykonawcę: "
                            f"{assigned_actor_name}."
                        )
                    if actor is None:
                        raise ValueError("Ta postać nie może teraz zostać wybrana.")
                    session._record(
                        "ui_actor_card_zone_option_declared",
                        {
                            "actor_id": actor_card.actor_id,
                            "zone_option_id": zone_option_id,
                        },
                    )
                    return jsonify(
                        {
                            "applied": False,
                            "effect": "select_zone_option_actor",
                            "actor_id": actor_card.actor_id,
                            "label": str(actor.get("name", actor_card.actor_id)),
                            "payload": normalized,
                        }
                    )
                if actor_card.actor_id not in selection.eligible_actor_ids:
                    raise ValueError("Ta postać nie może teraz zostać wybrana.")
                state = session.select_exploration_actor(
                    goal_id=selection.goal_id,
                    actor_id=actor_card.actor_id,
                    role=selection.role,
                )
                session._record(
                    "ui_actor_card_selected",
                    {
                        "actor_id": actor_card.actor_id,
                        "goal_id": selection.goal_id,
                        "role": selection.role,
                    },
                )
                return jsonify(
                    {
                        "applied": True,
                        "effect": "select_actor",
                        "actor_id": actor_card.actor_id,
                        "label": actor_card.actor_id.upper(),
                        "payload": normalized,
                        "state": state,
                    }
                )
            except (TypeError, ValueError) as exc:
                return jsonify({"error": str(exc), "state": session.state_payload()}), 400
        try:
            action_card = parse_decision_card_qr_payload(normalized)
        except (TypeError, ValueError) as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400
        if (
            action_card.action_kind is DecisionCardActionKind.SPELL
            and session.ui_flow_stage.value == "spell_preparation"
        ):
            context = data.get("context")
            if (
                not isinstance(context, dict)
                or context.get("spell_preparation_mode") != "custom"
            ):
                return jsonify(
                    {
                        "error": (
                            "Najpierw zeskanuj ODRZUĆ, aby rozpocząć własne "
                            "przygotowywanie czarów."
                        ),
                        "state": session.state_payload(),
                    }
                ), 400
            current_preparation = session.state_payload().get(
                "spell_preparation",
                {},
            )
            current_actor_id = (
                str(current_preparation.get("current_actor_id", ""))
                if isinstance(current_preparation, dict)
                else ""
            )
            if str(context.get("spell_preparation_actor_id", "")) != current_actor_id:
                return jsonify(
                    {
                        "error": "Zmieniła się postać przygotowująca czary. Zeskanuj kartę ponownie.",
                        "state": session.state_payload(),
                    }
                ), 409
            try:
                selection = session.declare_spell_preparation_card(
                    action_card.source_id
                )
            except (TypeError, ValueError) as exc:
                return jsonify(
                    {"error": str(exc), "state": session.state_payload()}
                ), 400
            return jsonify(
                {
                    "applied": False,
                    "effect": "select_preparation_spell",
                    "label": selection["spell_label"],
                    "payload": normalized,
                    **selection,
                    "feedback": {
                        "status": "waiting",
                        "next_step": "scan_preparation_spell",
                        "message": (
                            f"Dodano {selection['spell_label']} do przygotowań "
                            f"postaci {selection['actor_name']}."
                        ),
                    },
                }
            )
        if (
            action_card.action_kind is DecisionCardActionKind.UNIVERSAL
            and action_card.source_id in {"maneuvers", "equipment"}
        ):
            try:
                state = session.open_physical_combat_menu(action_card.source_id)
            except (TypeError, ValueError) as exc:
                return jsonify({"error": str(exc), "state": session.state_payload()}), 400
            return jsonify(
                {
                    "applied": True,
                    "effect": f"open_{action_card.source_id}_menu",
                    "label": (
                        "MANEWRY"
                        if action_card.source_id == "maneuvers"
                        else "EKWIPUNEK"
                    ),
                    "payload": normalized,
                    "feedback": {
                        "status": "waiting",
                        "next_step": "select_menu_option",
                        "message": session.board_message,
                    },
                    "state": state,
                }
            )
        if action_card.action_kind is not DecisionCardActionKind.UNIVERSAL:
            declared_stage = session.ui_flow_stage.value
            session._record(
                "ui_physical_action_card_declared",
                {
                    "action_kind": action_card.action_kind.value,
                    "source_id": action_card.source_id,
                    "payload": normalized,
                    "flow_stage": declared_stage,
                },
            )
            try:
                state = session.use_physical_action_card(
                    action_card.action_kind,
                    action_card.source_id,
                    owner_actor_id=action_card.actor_id,
                )
            except Exception as exc:
                session._record(
                    "ui_physical_action_card_resolved",
                    {
                        "action_kind": action_card.action_kind.value,
                        "source_id": action_card.source_id,
                        "applied": False,
                        "error": str(exc),
                        "declared_flow_stage": declared_stage,
                    },
                )
                return jsonify({"error": str(exc), "state": session.state_payload()}), 400
            session._record(
                "ui_physical_action_card_resolved",
                {
                    "action_kind": action_card.action_kind.value,
                    "source_id": action_card.source_id,
                    "applied": True,
                    "declared_flow_stage": declared_stage,
                    "result_flow_stage": session.ui_flow_stage.value,
                },
            )
            combat = state.get("combat") if isinstance(state, dict) else None
            combat = combat if isinstance(combat, dict) else {}
            next_step = "resolved"
            stabilization = combat.get("stabilization")
            if combat.get("physical_feature_prompt"):
                next_step = "enter_feature_value"
            elif (
                combat.get("targeting")
                or combat.get("class_feature_targeting")
                or (
                    isinstance(stabilization, dict)
                    and stabilization.get("targeting_method")
                )
            ):
                next_step = "select_board_target"
            elif any(
                combat.get(key)
                for key in (
                    "pending_area_spell",
                    "pending_magic_movement",
                    "pending_multi_target_damage_spell",
                    "pending_spell_debuff",
                    "pending_summon",
                )
            ):
                next_step = "select_board_target"
            elif combat.get("pending_concentration_action"):
                pending_concentration = combat["pending_concentration_action"]
                selected_ids = (
                    pending_concentration.get("selected_target_ids", [])
                    if isinstance(pending_concentration, dict)
                    else []
                )
                next_step = (
                    "confirm_action" if selected_ids else "select_board_target"
                )
            elif combat.get("reaction_window"):
                next_step = "enter_reaction_roll"
            elif (
                isinstance(state.get("board_selection"), dict)
                and state["board_selection"].get("mode") == "spell_area"
                and state["board_selection"].get("legal_position_count", 0) > 0
            ):
                next_step = "select_board_target"
            feedback = {
                "status": "waiting" if next_step != "resolved" else "resolved",
                "next_step": next_step,
                "message": session.board_message,
            }
            current_actor = combat.get("current_actor")
            if isinstance(current_actor, dict):
                resources = [
                    {
                        "id": str(pool.get("id", "")),
                        "label": str(pool.get("label", pool.get("id", ""))),
                        "current": int(pool.get("current", 0)),
                        "maximum": int(pool.get("maximum", 0)),
                    }
                    for pool in current_actor.get("resource_pools", [])
                    if isinstance(pool, dict) and int(pool.get("maximum", 0)) > 0
                ]
                resources.extend(
                    {
                        "id": f"spell_slot_{int(slot.get('level', 0))}",
                        "label": f"Slot {int(slot.get('level', 0))}. poziomu",
                        "current": int(slot.get("remaining", 0)),
                        "maximum": int(slot.get("maximum", 0)),
                    }
                    for slot in current_actor.get("spell_slots", [])
                    if isinstance(slot, dict) and int(slot.get("maximum", 0)) > 0
                )
                feedback["resources"] = resources
            return jsonify(
                {
                    "applied": True,
                    "effect": "action_card",
                    "action": action_card.source_id,
                    "label": player_label(action_card.source_id),
                    "payload": normalized,
                    "feedback": feedback,
                    "state": state,
                }
            )
        try:
            card = resolve_universal_card_scan(normalized)
        except (TypeError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 400
        declared_stage = session.ui_flow_stage.value
        session._record(
            "ui_physical_card_declared",
            {
                "action": card.action.value,
                "label": card.player_label,
                "payload": card.payload,
                "flow_stage": declared_stage,
            },
        )
        response: dict[str, object] = {
            "action": card.action.value,
            "label": card.player_label,
            "payload": card.payload,
            "applied": False,
        }
        try:
            if session.exploration_card_state.pending is not None:
                state = session.resolve_exploration_card(
                    accept=card.action.value == "accept",
                )
                response.update(
                    applied=True,
                    effect=(
                        "accept_exploration_card"
                        if card.action.value == "accept"
                        else "decline_exploration_card"
                    ),
                    state=state,
                    feedback={
                        "status": "resolved",
                        "next_step": "resume_prompt",
                        "message": session.board_message,
                    },
                )
                return jsonify(response)
            if (
                card.action.value == "accept"
                and session.board_actor_selection is not None
                and session.board_actor_selection.role == "helper"
                and session.board_selected_actor_id
            ):
                session.board_actor_selection = None
                session.board_selection_revision += 1
                session.board_message = (
                    "Wybrano test bez pomocnika. Karta prowadzącego pozostaje aktywna."
                )
                session._sync_board_leds()
                response.update(
                    applied=True,
                    effect="skip_optional_helper",
                    state=session.state_payload(),
                )
            elif card.action.value == "accept" and declared_stage == "ready_to_start":
                response.update(
                    applied=True,
                    effect="start_session",
                    state=session.start_session(),
                )
            elif card.action.value == "accept" and declared_stage == "party_setup":
                setup = session.exploration_setup_flow
                if (
                    setup is not None
                    and setup.current_step is not None
                    and not (
                        setup.assignment_point_id
                        and setup.assigned_position is None
                    )
                ):
                    response.update(
                        applied=True,
                        effect="confirm_exploration_setup",
                        state=session.confirm_exploration_setup_step(),
                    )
        except Exception as exc:
            session._record(
                "ui_physical_card_resolved",
                {
                    "action": card.action.value,
                    "applied": False,
                    "error": str(exc),
                    "declared_flow_stage": declared_stage,
                    "result_flow_stage": session.ui_flow_stage.value,
                },
            )
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400
        session._record(
            "ui_physical_card_resolved",
            {
                "action": card.action.value,
                "applied": bool(response["applied"]),
                "effect": response.get("effect", ""),
                "declared_flow_stage": declared_stage,
                "result_flow_stage": session.ui_flow_stage.value,
            },
        )
        return jsonify(response)

    @app.post("/api/npc-transition/resolve")
    def api_npc_transition_resolve():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.resolve_npc_transition(str(data.get("reaction_id", ""))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/trade/buy")
    def api_trade_buy():
        data = request.get_json(silent=True) or {}
        try:
            quantity = _trade_quantity(data.get("quantity"))
            return jsonify(
                session.buy_merchant_item(
                    merchant_id=str(data.get("merchant_id", "")),
                    actor_id=str(data.get("actor_id", "")),
                    item_id=str(data.get("item_id", "")),
                    quantity=quantity,
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/trade/sell")
    def api_trade_sell():
        data = request.get_json(silent=True) or {}
        try:
            quantity = _trade_quantity(data.get("quantity"))
            return jsonify(
                session.sell_merchant_item(
                    merchant_id=str(data.get("merchant_id", "")),
                    actor_id=str(data.get("actor_id", "")),
                    item_id=str(data.get("item_id", "")),
                    quantity=quantity,
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/downtime/crafting/complete")
    def api_downtime_crafting_complete():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.complete_downtime_crafting(
                    actor_id=str(data.get("actor_id", "")),
                    recipe_id=str(data.get("recipe_id", "")),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/equipment/armor")
    def api_equipment_armor():
        data = request.get_json(silent=True) or {}
        try:
            equip = data.get("equip")
            if not isinstance(equip, bool):
                raise ValueError("Pole equip musi mieć wartość true albo false.")
            return jsonify(
                session.change_actor_armor(
                    actor_id=str(data.get("actor_id", "")),
                    armor_id=str(data.get("armor_id", "")),
                    equip=equip,
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/equipment/light")
    def api_equipment_light():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.change_actor_light(
                    actor_id=str(data.get("actor_id", "")),
                    item_id=str(data.get("item_id", "")),
                    action=str(data.get("action", "")),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/exploration/search/start")
    def api_exploration_search_start():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.start_exploration_search(
                    str(data.get("actor_id", "")),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/exploration/option")
    def api_exploration_option():
        data = request.get_json(silent=True) or {}
        actor_id = data.get("actor_id")
        try:
            return jsonify(
                session.select_exploration_option(
                    str(data.get("option_id", "")),
                    actor_id=str(actor_id) if actor_id else None,
                    player_description=str(data.get("player_description", "")),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/exploration/hide/start")
    def api_exploration_hide_start():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.start_exploration_hide(
                    str(data.get("actor_id", "")),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/exploration/fixture/action")
    def api_exploration_fixture_action():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.start_exploration_fixture_action(
                    actor_id=str(data.get("actor_id", "")),
                    fixture_id=str(data.get("fixture_id", "")),
                    operation=str(data.get("operation", "")),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/exploration/fixture/damage")
    def api_exploration_fixture_damage():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.damage_exploration_fixture(
                    actor_id=str(data.get("actor_id", "")),
                    fixture_id=str(data.get("fixture_id", "")),
                    attack_total=int(data.get("attack_total", 0)),
                    damage=int(data.get("damage", 0)),
                )
            )
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

    @app.post("/api/rest/long/complete")
    def api_long_rest_complete():
        try:
            return jsonify(session.complete_long_rest())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/rest/short/confirm")
    def api_short_rest_confirm():
        data = request.get_json(silent=True) or {}
        raw_choices = data.get("attunement_choices", [])
        if not isinstance(raw_choices, list):
            return jsonify({"error": "Pole attunement_choices musi być listą.", "state": session.state_payload()}), 400
        try:
            return jsonify(session.confirm_short_rest(attunement_choices=raw_choices))
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
                    song_of_rest_roll=(
                        int(data["song_of_rest_roll"])
                        if data.get("song_of_rest_roll") not in (None, "", 0, "0")
                        else None
                    ),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/rest/short/spell-recovery")
    def api_short_rest_spell_recovery():
        data = request.get_json(silent=True) or {}
        try:
            raw_levels = data.get("slot_levels", [])
            if not isinstance(raw_levels, list):
                raise ValueError("slot_levels musi być listą.")
            return jsonify(
                session.recover_short_rest_spell_slots(
                    actor_id=str(data.get("actor_id", "")),
                    slot_levels=tuple(int(level) for level in raw_levels),
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
                    selected_social_skill=(
                        str(data["selected_social_skill"])
                        if data.get("selected_social_skill") is not None
                        else None
                    ),
                    selected_action_source_id=(
                        str(data["selected_action_source_id"])
                        if data.get("selected_action_source_id") is not None
                        else None
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

    @app.post("/api/point/leave")
    def api_point_leave():
        try:
            return jsonify(session.select_point(""))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/exploration/board-selection")
    def api_exploration_board_selection():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.set_exploration_board_selection(bool(data.get("enabled", False))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/board/clear-selection")
    def api_board_clear_selection():
        try:
            return jsonify(session.clear_board_interaction_selection())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/exploration/lead-actor")
    def api_exploration_lead_actor():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.set_exploration_lead_actor(
                    str(data.get("actor_id", "")),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/exploration/actor-selection/start")
    def api_exploration_actor_selection_start():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.start_exploration_actor_selection(
                    goal_id=str(data.get("goal_id", "")),
                    role=str(data.get("role", "lead")),
                    excluded_actor_ids=tuple(
                        str(actor_id)
                        for actor_id in data.get("excluded_actor_ids", ())
                    ),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/exploration/actor-selection/select")
    def api_exploration_actor_selection_select():
        return jsonify(
            {
                "error": (
                    "Wybór bohatera jest dostępny wyłącznie przez fizyczną "
                    "kartę postaci."
                ),
                "state": session.state_payload(),
            }
        ), 409

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

    @app.before_request
    def clear_browser_panel_on_game_command():
        g.request_started_at = time.monotonic()
        launcher_pages = {'index', 'new_game', 'load_game', 'characters', 'character_detail', 'start_new_game', 'load_current_game', 'session_materials'}
        if (request.path.startswith("/api/") or request.endpoint in launcher_pages | {'play', 'open_training_arena'}) and request.path not in {"/api/board/scan", "/api/board/reset-scan"}:
            session._board_state_lock.acquire()
            g.board_state_locked = True
        if request.endpoint in launcher_pages:
            g.launcher_token = launcher_board.begin(session)
        # A dice overlay belongs to one decision; a game command invalidates it.
        if request.method == "POST" and request.path.startswith("/api/") and not request.path.startswith("/api/board/"):
            session.board_panel_context = None
        if (session.combat_state and session.combat_state.resonance and request.method == "POST"
                and request.path.startswith("/api/combat/") and request.path != "/api/combat/resonance"):
            return jsonify({"error": "Ta walka korzysta z panelu Ładunki i Rezonans."}), 409
        return guard_exploration_lesson()

    @app.teardown_request
    def release_board_state_lock(error):
        if getattr(g, "board_state_locked", False):
            g.board_state_locked = False
            session._board_state_lock.release()

    @app.after_request
    def record_slow_game_request(response):
        if getattr(g, "board_state_locked", False) and request.method == "POST":
            try:
                session._cancel_obsolete_board_input()
            except (ConnectionError, TimeoutError) as exc:
                session.board_message = str(exc)

        elapsed_ms = round((time.monotonic() - g.request_started_at) * 1000)
        # Board scans wait for the player and report their preparation separately.
        if elapsed_ms >= 250 and request.path.startswith("/api/") and request.path != "/api/board/scan":
            session._record("ui_request_slow", {
                "path": request.path, "method": request.method,
                "elapsed_ms": elapsed_ms, "status": response.status_code,
            })
        return response

    @app.post('/api/board/navigation')
    def api_board_navigation():
        try:
            return jsonify(launcher_board.configure(session, request.get_json(silent=True) or {}))
        except ValueError as exc:
            return jsonify(error=str(exc)), 409
        except Exception as exc:
            return jsonify(error=str(exc)), 400

    @app.post('/api/board/navigation/release')
    def api_board_navigation_release():
        data = request.get_json(silent=True) or {}
        launcher_board.release(session, str(data.get('token', '')))
        return jsonify(ok=True)

    @app.post("/api/board/panel")
    def api_board_panel():
        data = request.get_json(silent=True) or {}
        try:
            if 'release_context' in data:
                return jsonify(session.release_board_panel(str(data['release_context'])))
            return jsonify(session.configure_board_panel(
                str(data.get("context", "")), data.get("slots", []), bool(data.get("exclusive", False)),
                expected_revision=str(data.get("revision", "")),
            ))
        except (ValueError, TypeError) as exc:
            return jsonify({"error": str(exc)}), 400

    @app.post("/api/board/scan")
    def api_board_scan():
        from .exploration_app import BoardCommandRejected
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.scan_board_selection(
                    expected_revision=str(data.get("revision", "")),
                    automatic=bool(data.get("automatic", False)),
                )
            )
        except BoardCommandRejected as exc:
            return jsonify({"error": str(exc), "error_kind": "command_rejected", "state": session.state_payload()}), 400
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

    @app.post("/api/encounter/setup/back")
    def api_encounter_setup_back() -> Response | tuple[Response, int]:
        try:
            return jsonify(session.back_encounter_setup_step())
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
            natural_roll_2 = data.get("natural_roll_2")
            return jsonify(
                session.submit_precombat_stealth_roll(
                    actor_id=str(data.get("actor_id", "")),
                    natural_roll=int(data.get("natural_roll", 0)),
                    natural_roll_2=(
                        int(natural_roll_2)
                        if natural_roll_2 not in (None, "")
                        else None
                    ),
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

    @app.post("/api/encounter/initiative/panel")
    def api_encounter_initiative_panel():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.update_initiative_panel(
                str(data.get("command", "")), value=data.get("value"),
                expected_revision=str(data.get("revision", "")),
            ))
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
                    _natural_rerolls(data),
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
                    natural_rerolls=_natural_rerolls(data),
                    bardic_inspiration_roll=(
                        int(data["bardic_inspiration_roll"])
                        if data.get("bardic_inspiration_roll") not in (None, "", 0, "0")
                        else None
                    ),
                    bless_roll=(
                        int(data["bless_roll"])
                        if data.get("bless_roll") not in (None, "", 0, "0")
                        else None
                    ),
                    mirror_image_roll=(
                        int(data["mirror_image_roll"])
                        if data.get("mirror_image_roll") not in (None, "")
                        else None
                    ),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/resonance")
    def resonance_command():
        from .resonance import command
        try:
            return jsonify(command(session, request.get_json() or {}))
        except (ValueError, TypeError, KeyError) as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/shared-mana")
    def shared_mana_command():
        from .shared_mana import command
        try:
            return jsonify(command(session, request.get_json() or {}))
        except (ValueError, TypeError) as exc:
            return jsonify({"error": str(exc)}), 400

    @app.post("/api/combat/mana-wave")
    def api_combat_mana_wave():
        data = request.get_json(silent=True) or {}
        try:
            event = data.get("event")
            if isinstance(event, bool) or not isinstance(event, int):
                raise ValueError("Podaj numer wydarzenia 1–6.")
            return jsonify(session.report_physical_mana_wave(event))
        except (TypeError, ValueError) as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/mana-damage-bonus/skip")
    def api_combat_mana_damage_bonus_skip():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.skip_physical_damage_bonus(str(data.get("bonus_id", ""))))
        except ValueError as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/mana-weapon")
    def api_combat_mana_weapon():
        try:
            return jsonify(session.activate_mana_weapon())
        except ValueError as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/mana-loan")
    def api_combat_mana_loan():
        try:
            return jsonify(session.use_mana_loan())
        except ValueError as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/mana-blue-movement")
    def api_combat_mana_blue_movement():
        try:
            return jsonify(session.declare_blue_movement())
        except ValueError as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/attack-series")
    def api_combat_attack_series():
        data = request.get_json(silent=True) or {}
        try:
            count = data.get("count")
            if isinstance(count, bool) or not isinstance(count, int):
                raise ValueError("Podaj całkowitą liczbę ataków.")
            return jsonify(session.declare_physical_attack_series(count))
        except (TypeError, ValueError) as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/attack-source")
    def api_combat_attack_source():
        data = request.get_json(silent=True) or {}
        try:
            cast_level = data.get("cast_level")
            return jsonify(
                session.select_combat_attack_source(
                    str(data.get("source_id", "")),
                    int(cast_level) if cast_level not in (None, "") else None,
                    tuple(str(value) for value in data.get("metamagic_ids", ())),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/exploration/ritual")
    def api_exploration_ritual():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.cast_exploration_ritual(
                    str(data.get("actor_id", "")),
                    str(data.get("spell_id", "")),
                    str(data.get("target_id", "")),
                    message=str(data.get("message", "")),
                    trigger_description=str(data.get("trigger_description", "")),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/exploration/hazard/feather-fall")
    def api_exploration_hazard_feather_fall():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.cast_feather_fall_for_pending_hazard(
                    str(data.get("caster_id", "")),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/exploration/spell")
    def api_exploration_spell():
        data = request.get_json(silent=True) or {}
        try:
            cast_level = data.get("cast_level")
            raw_target_ids = data.get("target_ids", [])
            if not isinstance(raw_target_ids, list):
                raise ValueError("target_ids musi być listą.")
            healing_roll = data.get("healing_roll")
            rope_length_feet = data.get("rope_length_feet", 60)
            return jsonify(
                session.cast_exploration_spell(
                    str(data.get("actor_id", "")),
                    str(data.get("spell_id", "")),
                    cast_level=(
                        int(cast_level)
                        if cast_level not in (None, "")
                        else None
                    ),
                    target_id=str(data.get("target_id", "")),
                    target_ids=tuple(str(value) for value in raw_target_ids),
                    healing_roll=(
                        int(healing_roll)
                        if healing_roll not in (None, "")
                        else None
                    ),
                    rope_length_feet=int(rope_length_feet),
                    message=str(data.get("message", "")),
                    trigger_description=str(data.get("trigger_description", "")),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/exploration/rope-trick/enter")
    def api_exploration_rope_trick_enter():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.enter_rope_trick_space(
                    str(data.get("effect_id", "")),
                    str(data.get("actor_id", "")),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/exploration/rope-trick/exit")
    def api_exploration_rope_trick_exit():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.exit_rope_trick_space(
                    str(data.get("effect_id", "")),
                    str(data.get("actor_id", "")),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/healing-source")
    def api_combat_healing_source():
        data = request.get_json(silent=True) or {}
        try:
            cast_level = data.get("cast_level")
            return jsonify(
                session.select_combat_healing_source(
                    str(data.get("source_id", "")),
                    int(cast_level) if cast_level not in (None, "") else None,
                    tuple(str(value) for value in data.get("metamagic_ids", ())),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/player-attack-confirm")
    def api_combat_player_attack_confirm():
        try:
            return jsonify(session.confirm_player_attack_target())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/twinned-attack-target")
    def api_combat_twinned_attack_target():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.select_twinned_attack_target(
                    str(data.get("target_id", "")),
                )
            )
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
            return jsonify(
                session.submit_player_damage_roll(
                    **_damage_submission(data),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/divine-smite")
    def api_combat_divine_smite():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.select_combat_divine_smite(
                    slot_level=int(data.get("slot_level", 0)),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/open-hand-technique")
    def api_combat_open_hand_technique():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.resolve_combat_open_hand_technique(
                    mode=str(data.get("mode", "")),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/open-hand-technique/skip")
    def api_combat_open_hand_technique_skip():
        try:
            return jsonify(session.skip_combat_open_hand_technique())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/repelling-blast")
    def api_combat_repelling_blast():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.resolve_repelling_blast(
                    push=bool(data.get("push", True)),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/player-healing")
    def api_combat_player_healing():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(session.submit_player_healing_roll(healing=int(data.get("healing", 0))))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/twinned-healing-target")
    def api_combat_twinned_healing_target():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.select_twinned_healing_target(
                    str(data.get("target_id", "")),
                )
            )
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

    @app.post("/api/combat/area-spell/sculpt")
    def api_combat_area_spell_sculpt():
        data = request.get_json(silent=True) or {}
        try:
            raw_ids = data.get("target_ids", [])
            if not isinstance(raw_ids, list):
                raise ValueError("target_ids musi być listą.")
            return jsonify(
                session.select_sculpt_spells_targets(
                    tuple(str(target_id) for target_id in raw_ids),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/area-spell/metamagic-targets")
    def api_combat_area_spell_metamagic_targets():
        data = request.get_json(silent=True) or {}
        try:
            heightened = data.get("heightened_target_id")
            return jsonify(
                session.select_area_spell_metamagic_targets(
                    careful_target_ids=tuple(
                        str(value) for value in data.get("careful_target_ids", ())
                    ),
                    heightened_target_id=(
                        str(heightened)
                        if heightened not in (None, "")
                        else None
                    ),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/metamagic/empowered")
    def api_combat_metamagic_empowered():
        try:
            return jsonify(session.activate_empowered_spell())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/area-spell/volley-roll")
    def api_shared_volley_roll():
        from .shared_volley import submit_volley_roll
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(submit_volley_roll(session, data.get("natural_roll"), data.get("natural_roll_2")))
        except (ValueError, TypeError) as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/area-spell/damage")
    def api_combat_area_spell_damage():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.submit_player_area_spell_damage(
                    **_damage_submission(data),
                )
            )
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

    @app.post("/api/combat/assisted-spell")
    def api_combat_assisted_spell():
        data = request.get_json(silent=True) or {}
        try:
            cast_level = data.get("cast_level")
            return jsonify(
                session.use_assisted_combat_spell(
                    str(data.get("action_id", "")),
                    cast_level=(
                        int(cast_level)
                        if cast_level not in (None, "")
                        else None
                    ),
                    metamagic_ids=tuple(
                        str(value) for value in data.get("metamagic_ids", ())
                    ),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/multi-target-spell/start")
    def api_combat_multi_target_spell_start():
        data = request.get_json(silent=True) or {}
        try:
            cast_level = data.get("cast_level")
            return jsonify(
                session.start_multi_target_damage_spell(
                    str(data.get("action_id", "")),
                    cast_level=(
                        int(cast_level)
                        if cast_level not in (None, "")
                        else None
                    ),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/multi-target-spell/target")
    def api_combat_multi_target_spell_target():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.select_multi_target_spell_target(
                    str(data.get("target_id", ""))
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/multi-target-spell/clear")
    def api_combat_multi_target_spell_clear():
        try:
            return jsonify(session.clear_multi_target_spell_targets())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/multi-target-spell/confirm")
    def api_combat_multi_target_spell_confirm():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.confirm_multi_target_damage_spell(
                    tuple(int(value) for value in data.get("die_rolls", ())),
                    tuple(int(value) for value in data.get("natural_rolls", ())),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/multi-target-spell/cancel")
    def api_combat_multi_target_spell_cancel():
        try:
            return jsonify(session.cancel_multi_target_damage_spell())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/class-feature")
    def api_combat_class_feature():
        data = request.get_json(silent=True) or {}
        try:
            raw_allocations = data.get("allocations", [])
            allocations = tuple(
                (str(entry.get("target_id", "")), int(entry.get("points", 0)))
                for entry in raw_allocations
                if isinstance(entry, dict)
            )
            saving_rolls = tuple(
                (str(entry.get("target_id", "")), int(entry.get("natural_roll", 0)))
                for entry in data.get("saving_rolls", [])
                if isinstance(entry, dict)
            )
            natural_roll = data.get("natural_roll")
            return jsonify(
                session.use_combat_class_feature(
                    str(data.get("action_id", "")),
                    natural_roll=(
                        int(natural_roll)
                        if natural_roll not in (None, "")
                        else None
                    ),
                    target_id=str(data.get("target_id", "")),
                    points=int(data.get("points", 0)),
                    mode=str(data.get("mode", "")),
                    slot_level=int(data.get("slot_level", 0)),
                    source_item_id=str(data.get("source_item_id", "")),
                    form_id=str(data.get("form_id", "")),
                    saving_rolls=saving_rolls,
                    allocations=allocations,
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/shield-bash/rolls")
    def api_shield_bash_rolls():
        try:
            return jsonify(submit_shield_bash(session, request.get_json(silent=True) or {}))
        except ValueError as exc:
            return jsonify(error=str(exc), state=session.state_payload()), 400

    @app.post("/api/combat/shield-bash/confirm")
    def api_shield_bash_confirm():
        try:
            return jsonify(confirm_shield_bash(session))
        except ValueError as exc:
            return jsonify(error=str(exc), state=session.state_payload()), 400

    @app.post("/api/combat/class-feature/targeting")
    def api_combat_class_feature_targeting():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.start_combat_class_feature_targeting(
                    str(data.get("action_id", "")),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/physical-feature/cancel")
    def api_combat_physical_feature_cancel():
        try:
            return jsonify(session.cancel_physical_feature_prompt())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/class-feature/targeting/cancel")
    def api_combat_class_feature_targeting_cancel():
        try:
            return jsonify(session.cancel_combat_class_feature_targeting())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/class-feature/targeting/confirm")
    def api_combat_class_feature_targeting_confirm():
        try:
            return jsonify(session.confirm_combat_class_feature_targeting())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/aux-targeting/start")
    def api_combat_aux_targeting_start():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.start_combat_aux_targeting(
                    str(data.get("mode", "")),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/aux-targeting/finish")
    def api_combat_aux_targeting_finish():
        try:
            return jsonify(session.finish_combat_aux_targeting())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/concentration/start")
    def api_combat_concentration_start():
        data = request.get_json(silent=True) or {}
        try:
            cast_level = data.get("cast_level")
            return jsonify(
                session.start_combat_concentration_action(
                    str(data.get("action_id", "")),
                    None if cast_level is None else int(cast_level),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/concentration/confirm")
    def api_combat_concentration_confirm():
        data = request.get_json(silent=True) or {}
        try:
            raw_target_ids = data.get("target_ids", [])
            if not isinstance(raw_target_ids, list):
                raise ValueError("target_ids musi być listą.")
            target_ids = tuple(str(target_id) for target_id in raw_target_ids)
            confirmation_kwargs: dict[str, object] = {
                "target_id": (
                        str(data["target_id"])
                        if "target_id" in data
                        else None
                    ),
                "target_ids": target_ids,
            }
            if data.get("roll_total") not in (None, ""):
                confirmation_kwargs["roll_total"] = int(data["roll_total"])
            if data.get("effect_option") not in (None, ""):
                confirmation_kwargs["effect_option"] = str(data["effect_option"])
            return jsonify(
                session.confirm_combat_concentration_action(
                    **confirmation_kwargs
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/concentration/cancel")
    def api_combat_concentration_cancel():
        try:
            return jsonify(session.cancel_combat_concentration_action())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/timed-cast/complete")
    def api_combat_timed_cast_complete():
        try:
            return jsonify(session.complete_timed_combat_spell())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/concentration-check")
    def api_combat_concentration_check():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.submit_concentration_check(
                    natural_roll=int(data.get("natural_roll", 0)),
                    natural_roll_2=(
                        int(data["natural_roll_2"])
                        if data.get("natural_roll_2") is not None
                        else None
                    ),
                )
            )
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

    @app.post("/api/combat/turn-actions/select")
    def api_combat_turn_actions_select():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.move_combat_turn_action_selection(int(data.get("delta", 0)))
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/command")
    def api_combat_command():
        from .shared_command import select
        from dnd_board_game.hardware.board_panel import panel_position
        data = request.get_json(silent=True) or {}
        if data.get("revision") != session._board_selection_payload()["revision"]:
            return jsonify(session.state_payload())
        try:
            return jsonify(select(session, panel_position(29 if data.get("back") else 28)))
        except ValueError as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/turn-actions/confirm")
    def api_combat_turn_actions_confirm():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.confirm_combat_turn_action(str(data.get("option_id", "")))
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/turn-actions/cancel-preview")
    def api_combat_turn_actions_cancel_preview():
        try:
            return jsonify(session.cancel_combat_turn_action_preview())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/item-target/confirm")
    def api_combat_item_target_confirm():
        try:
            return jsonify(session.confirm_combat_item_target())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/item-target/cancel")
    def api_combat_item_target_cancel():
        try:
            return jsonify(session.cancel_combat_item_targeting())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/pending-board-selection/confirm")
    def api_combat_pending_board_selection_confirm():
        try:
            return jsonify(session.confirm_combat_pending_board_selection())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/aura-preview")
    def api_combat_aura_preview():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.set_combat_aura_preview(str(data.get("aura_id", "")))
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/context-menu/confirm")
    def api_combat_context_menu_confirm():
        data = request.get_json(silent=True) or {}
        try:
            raw_quantity = data.get("quantity")
            if raw_quantity is not None and (
                isinstance(raw_quantity, bool)
                or not isinstance(raw_quantity, int)
            ):
                raise ValueError("Liczba zabieranych sztuk musi być liczbą całkowitą.")
            return jsonify(
                session.confirm_combat_context_menu(
                    str(data.get("option_id", "")),
                    quantity=raw_quantity,
                )
            )
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
            natural_roll_2 = data.get("natural_roll_2")
            return jsonify(
                session.submit_combat_skill_check(
                    natural_roll=int(data.get("natural_roll", 0)),
                    natural_roll_2=(
                        int(natural_roll_2)
                        if natural_roll_2 not in (None, "")
                        else None
                    ),
                )
            )
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

    @app.post("/api/combat/instinctive-dodge/use")
    def api_combat_instinctive_dodge_use():
        try:
            return jsonify(session.use_instinctive_dodge_reaction())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/instinctive-dodge/skip")
    def api_combat_instinctive_dodge_skip():
        try:
            return jsonify(session.skip_instinctive_dodge_reaction())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/reaction/choose")
    def api_combat_reaction_choose():
        from .reaction_choices import choose, confirm
        data = request.get_json(silent=True) or {}
        try:
            if data.get("confirm"):
                return jsonify(confirm(session, revision=data.get("revision")))
            return jsonify(choose(session, str(data.get("option_id", "")), revision=data.get("revision")))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/defensive-spell/cast")
    def api_combat_defensive_spell_cast():
        try:
            return jsonify(session.cast_defensive_spell_reaction())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/retaliation-spell/cast")
    def api_combat_retaliation_spell_cast():
        try:
            return jsonify(session.cast_retaliation_spell_reaction())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/retaliation-spell/skip")
    def api_combat_retaliation_spell_skip():
        try:
            return jsonify(session.skip_retaliation_spell_reaction())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/cutting-words/roll")
    def api_combat_cutting_words_roll():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.resolve_cutting_words_reaction(
                    die_roll=int(data.get("die_roll", 0)),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/cutting-words/skip")
    def api_combat_cutting_words_skip():
        try:
            return jsonify(session.skip_cutting_words_reaction())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/distracting-shout/roll")
    def api_combat_distracting_shout_roll():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.resolve_distracting_shout_reaction(
                    die_roll=int(data.get("die_roll", 0)),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/distracting-shout/skip")
    def api_combat_distracting_shout_skip():
        try:
            return jsonify(session.skip_distracting_shout_reaction())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/deflect-missiles/roll")
    def api_combat_deflect_missiles_roll():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.resolve_deflect_missiles_reaction(
                    die_roll=int(data.get("die_roll", 0)),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/deflect-missiles/skip")
    def api_combat_deflect_missiles_skip():
        try:
            return jsonify(session.skip_deflect_missiles_reaction())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/deflect-missiles/return")
    def api_combat_deflect_missiles_return():
        data = request.get_json(silent=True) or {}
        try:
            second = data.get("natural_roll_2")
            return jsonify(
                session.return_deflected_missile(
                    natural_roll=int(data.get("natural_roll", 0)),
                    natural_roll_2=(
                        int(second)
                        if second not in (None, "")
                        else None
                    ),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/deflect-missiles/damage")
    def api_combat_deflect_missiles_damage():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.submit_deflected_missile_damage(
                    damage=int(data.get("damage", 0)),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/long-cast/start")
    def api_combat_long_cast_start():
        data = request.get_json(silent=True) or {}
        try:
            cast_level = data.get("cast_level")
            return jsonify(
                session.start_long_cast(
                    str(data.get("action_id", "")),
                    cast_level=(
                        int(cast_level)
                        if cast_level not in (None, "")
                        else None
                    ),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/long-cast/continue")
    def api_combat_long_cast_continue():
        try:
            return jsonify(session.continue_long_cast())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/long-cast/cancel")
    def api_combat_long_cast_cancel():
        try:
            return jsonify(session.cancel_long_cast())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/summon/start")
    def api_combat_summon_start():
        data = request.get_json(silent=True) or {}
        try:
            cast_level = data.get("cast_level")
            return jsonify(
                session.start_summon(
                    str(data.get("action_id", "")),
                    cast_level=(
                        int(cast_level)
                        if cast_level not in (None, "")
                        else None
                    ),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/summon/confirm")
    def api_combat_summon_confirm():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.confirm_summon(
                    col=int(data.get("col")),
                    row=int(data.get("row")),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/summon/cancel")
    def api_combat_summon_cancel():
        try:
            return jsonify(session.cancel_summon())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/magic-movement/start")
    def api_combat_magic_movement_start():
        data = request.get_json(silent=True) or {}
        try:
            cast_level = data.get("cast_level")
            return jsonify(
                session.start_magic_movement(
                    str(data.get("action_id", "")),
                    cast_level=(
                        int(cast_level)
                        if cast_level not in (None, "")
                        else None
                    ),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/magic-movement/confirm")
    def api_combat_magic_movement_confirm():
        data = request.get_json(silent=True) or {}
        try:
            col = data.get("col")
            row = data.get("row")
            return jsonify(
                session.confirm_magic_movement(
                    col=int(col) if col not in (None, "") else None,
                    row=int(row) if row not in (None, "") else None,
                    target_id=(
                        str(data["target_id"])
                        if data.get("target_id") not in (None, "")
                        else None
                    ),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/magic-movement/cancel")
    def api_combat_magic_movement_cancel():
        try:
            return jsonify(session.cancel_magic_movement())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/moonbeam/move/start")
    def api_combat_moonbeam_move_start():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.start_moonbeam_move(str(data.get("effect_id", "")))
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/spell-debuff/start")
    def api_combat_spell_debuff_start():
        data = request.get_json(silent=True) or {}
        try:
            cast_level = data.get("cast_level")
            return jsonify(
                session.start_spell_debuff(
                    str(data.get("action_id", "")),
                    cast_level=(
                        int(cast_level)
                        if cast_level not in (None, "")
                        else None
                    ),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/spell-debuff/confirm")
    def api_combat_spell_debuff_confirm():
        data = request.get_json(silent=True) or {}
        try:
            confirmation_kwargs = {
                "target_id": str(data.get("target_id", "")),
            }
            if data.get("condition") not in (None, ""):
                confirmation_kwargs["condition"] = str(data["condition"])
            return jsonify(session.confirm_spell_debuff(**confirmation_kwargs))
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/spell-debuff/condition")
    def api_combat_spell_debuff_condition():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.select_spell_debuff_condition(
                    str(data.get("condition", "")),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/spell-debuff/cancel")
    def api_combat_spell_debuff_cancel():
        try:
            return jsonify(session.cancel_spell_debuff())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/spell-dispel/start")
    def api_combat_spell_dispel_start():
        data = request.get_json(silent=True) or {}
        try:
            cast_level = data.get("cast_level")
            return jsonify(
                session.start_spell_dispel(
                    str(data.get("action_id", "")),
                    cast_level=(
                        int(cast_level)
                        if cast_level not in (None, "")
                        else None
                    ),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/spell-dispel/confirm")
    def api_combat_spell_dispel_confirm():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.confirm_spell_dispel(
                    target_id=str(data.get("target_id", "")),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/spell-dispel/check")
    def api_combat_spell_dispel_check():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.resolve_spell_dispel_check(
                    natural_roll=int(data.get("natural_roll", 0)),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/spell-dispel/cancel")
    def api_combat_spell_dispel_cancel():
        try:
            return jsonify(session.cancel_spell_dispel())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/counterspell/cast")
    def api_combat_counterspell_cast():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.cast_counterspell_reaction(
                    cast_level=int(data.get("cast_level", 0)),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/counterspell/roll")
    def api_combat_counterspell_roll():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.submit_counterspell_check(
                    natural_roll=int(data.get("natural_roll", 0)),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/counterspell/skip")
    def api_combat_counterspell_skip():
        try:
            return jsonify(session.skip_counterspell_reaction())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/defensive-spell/skip")
    def api_combat_defensive_spell_skip():
        try:
            return jsonify(session.skip_defensive_spell_reaction())
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
            return jsonify(
                session.submit_enemy_opportunity_damage_roll(
                    **_damage_submission(data),
                )
            )
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
            return jsonify(
                session.submit_ready_damage_roll(
                    **_damage_submission(data),
                )
            )
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
                    natural_rerolls=_natural_rerolls(data),
                    bardic_inspiration_roll=(
                        int(data["bardic_inspiration_roll"])
                        if data.get("bardic_inspiration_roll") not in (None, "", 0, "0")
                        else None
                    ),
                    bless_roll=(
                        int(data["bless_roll"])
                        if data.get("bless_roll") not in (None, "", 0, "0")
                        else None
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

    @app.post("/api/combat/retreat")
    def api_combat_retreat():
        try:
            return jsonify(session.retreat_from_combat())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/combat/surrender")
    def api_combat_surrender():
        try:
            return jsonify(session.surrender_combat())
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
                    bardic_inspiration_roll=(
                        int(data["bardic_inspiration_roll"])
                        if data.get("bardic_inspiration_roll") not in (None, "", 0, "0")
                        else None
                    ),
                    bless_roll=(
                        int(data["bless_roll"])
                        if data.get("bless_roll") not in (None, "", 0, "0")
                        else None
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

    @app.post("/api/combat/stabilize/targeting")
    def api_combat_stabilize_targeting():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.start_combat_stabilization_targeting(
                    str(data.get("method", "")),
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

    @app.post("/api/encounter/retry")
    def api_encounter_retry():
        try:
            return jsonify(session.retry_encounter())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/reset")
    def api_reset():
        session.reset()
        return jsonify(session.state_payload())

    @app.post("/api/playground/configure")
    def api_playground_configure():
        data = request.get_json(silent=True) or {}
        try:
            return jsonify(
                session.configure_playground_trial(
                    dummy_count=int(data.get("dummy_count", 3)),
                    armor_class=int(data.get("armor_class", 12)),
                    hit_points=int(data.get("hit_points", 20)),
                    speed_feet=int(data.get("speed_feet", 10)),
                    ability_score=int(data.get("ability_score", 10)),
                    creature_type=str(data.get("creature_type", "construct")),
                    affinity=str(data.get("affinity", "none")),
                    damage_type=str(data.get("damage_type", "fire")),
                    condition_immunity=str(data.get("condition_immunity", "")),
                )
            )
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/playground/reset")
    def api_playground_reset():
        try:
            return jsonify(session.reset_playground_trial())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/scenario/finish")
    def api_scenario_finish():
        try:
            return jsonify(session.finish_scenario())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/scenario/continue")
    def api_scenario_continue():
        try:
            return jsonify(session.continue_scenario())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    @app.post("/api/scenario/handoff/start")
    def api_scenario_handoff_start():
        try:
            return jsonify(session.start_scenario_handoff())
        except Exception as exc:
            return jsonify({"error": str(exc), "state": session.state_payload()}), 400

    return app


def _damage_submission(data: object) -> dict[str, object]:
    if not isinstance(data, dict):
        data = {}
    raw_components = data.get("components")
    if isinstance(raw_components, dict):
        return {
            "damage": None,
            "component_totals": {
                str(component_id): int(amount)
                for component_id, amount in raw_components.items()
            },
        }
    return {
        "damage": int(data.get("damage", 0)),
        "component_totals": None,
    }


def _natural_rerolls(data: object) -> tuple[int, ...]:
    if not isinstance(data, dict):
        return ()
    raw = data.get("natural_rerolls", [])
    if not isinstance(raw, list):
        raise ValueError("natural_rerolls musi być listą wyników d20.")
    return tuple(int(value) for value in raw)


def _trade_quantity(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("Liczba przedmiotów musi być liczbą całkowitą.")
    if value < 1:
        raise ValueError("Liczba przedmiotów musi być dodatnia.")
    return value


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


_PLAYER_LABELS = PLAYER_LABELS_PL
_PLAYER_LANGUAGE_IDS = (
    "dwarvish", "elvish", "giant", "gnomish", "goblin", "halfling", "orc",
    "abyssal", "celestial", "deep_speech", "draconic", "infernal",
    "primordial", "sylvan", "undercommon",
)


def _render_character_form(
    catalog,
    resources,
    *,
    form: object,
    issues: tuple[object, ...],
    copy_source: str = "",
):
    values = _character_form_values(form)
    portrait_reference = str(values["portrait"]).strip().lstrip("/")
    portrait_url = (
        url_for(
            "character_portraits",
            filename=portrait_reference.removeprefix("character_uploads/"),
        )
        if portrait_reference.startswith("character_uploads/")
        else url_for("game_assets", filename=portrait_reference)
        if portrait_reference
        else ""
    )
    skill_ids = sorted(
        {
            skill_id
            for character_class in catalog.classes
            for skill_id in character_class.skill_choices
        }
        | {
            skill_id
            for species in catalog.species
            for skill_id in species.skill_proficiencies
        }
        | {
            skill_id
            for background in catalog.backgrounds
            for skill_id in background.skill_proficiencies
        }
    )
    species_mechanics = {
        species.id: _species_mechanics(species)
        for species in catalog.species
    }
    species_ability_bonuses = {
        species.id: {
            "fixed": {
                ability_id: getattr(species.ability_bonuses, ability_id)
                for ability_id in ABILITY_IDS
            },
            "choice_value": species.ability_bonus_choice_value,
        }
        for species in catalog.species
    }
    species_feature_help = {
        species.id: tuple(
            help_entry
            for feature_id in species.trait_ids
            if (help_entry := origin_feature_help(feature_id)) is not None
        )
        for species in catalog.species
    }
    species_variant_feature_help = {
        variant.id: tuple(
            help_entry
            for feature_id in variant.trait_ids
            if (help_entry := origin_feature_help(feature_id)) is not None
        )
        for species in catalog.species
        for variant in species.variant_choices
    }
    background_mechanics = {
        background.id: _background_mechanics(background)
        for background in catalog.backgrounds
    }
    background_feature_help = {
        background.id: tuple(
            help_entry
            for feature_id in background.feature_ids
            if (help_entry := origin_feature_help(feature_id)) is not None
        )
        for background in catalog.backgrounds
    }
    species_tool_prompts = {
        species.id: _tool_choice_prompt(
            species.tool_choices,
            species.tool_choice_count,
        )
        for species in catalog.species
    }
    background_tool_prompts = {
        background.id: _tool_choice_prompt(
            background.tool_choices,
            background.tool_choice_count,
        )
        for background in catalog.backgrounds
    }
    class_mechanics = {
        character_class.id: _class_mechanics(character_class)
        for character_class in catalog.classes
    }
    class_feature_help_entries = {
        character_class.id: tuple(
            help_entry
            for feature_id in character_class.feature_ids
            if (help_entry := class_feature_help(feature_id)) is not None
        )
        for character_class in catalog.classes
    }
    equipment_package_views = {
        package.id: _equipment_package_view(package, resources)
        for character_class in catalog.classes
        for package in character_class.equipment_packages
    }
    species_skill_grants = {
        species.id: species.skill_proficiencies
        for species in catalog.species
    }
    background_skill_grants = {
        background.id: background.skill_proficiencies
        for background in catalog.backgrounds
    }
    initial_step = _character_issue_step(issues[0]) if issues else 0
    return render_template(
        "character_form.html",
        catalog=catalog,
        values=values,
        issues=issues,
        ability_ids=ABILITY_IDS,
        point_buy_budget=POINT_BUY_BUDGET,
        point_buy_costs=POINT_BUY_COSTS,
        skill_ids=skill_ids,
        labels=_PLAYER_LABELS,
        language_ids=_PLAYER_LANGUAGE_IDS,
        copy_source=copy_source,
        portrait_url=portrait_url,
        species_mechanics=species_mechanics,
        species_ability_bonuses=species_ability_bonuses,
        species_feature_help=species_feature_help,
        species_variant_feature_help=species_variant_feature_help,
        background_mechanics=background_mechanics,
        background_feature_help=background_feature_help,
        species_tool_prompts=species_tool_prompts,
        background_tool_prompts=background_tool_prompts,
        class_mechanics=class_mechanics,
        class_feature_help=class_feature_help_entries,
        skill_choice_help=SKILL_CHOICE_HELP,
        skill_labels={
            skill_id: _PLAYER_LABELS.get(skill_id, skill_id)
            for skill_id in SKILL_CHOICE_HELP
        },
        fighting_style_help=FIGHTING_STYLE_HELP,
        class_choice_group_help=CLASS_CHOICE_GROUP_HELP,
        equipment_package_views=equipment_package_views,
        species_skill_grants=species_skill_grants,
        background_skill_grants=background_skill_grants,
        initial_step=initial_step,
    )


_CHARACTER_FEATURE_LABELS = {
    "artificers_lore": "Wiedza rzemieślnicza",
    "brave": "Odważny",
    "by_popular_demand": "Popularny artysta",
    "city_secrets": "Sekrety miasta",
    "criminal_contact": "Kontakt w półświatku",
    "darkvision": "Widzenie w ciemności",
    "discovery": "Odkrycie",
    "dwarven_resilience": "Krasnoludzka odporność",
    "dwarven_speed": "Nieograniczona szybkość w ciężkim pancerzu",
    "dwarven_toughness": "Krasnoludzka wytrzymałość",
    "elf_weapon_training": "Elfie wyszkolenie bronią",
    "false_identity": "Fałszywa tożsamość",
    "fey_ancestry": "Fey Ancestry",
    "gnome_cunning": "Gnomi spryt",
    "guild_membership": "Członkostwo w gildii",
    "halfling_nimbleness": "Niziołcza zwinność",
    "mira_shadow_stealth": "Mistrzyni ukrycia",
    "mira_shadow_killer": "Atak z cienia",
    "mira_opportunity_evasion": "Zwinny odskok",
    "flaw_exposed_panic": "Skaza: Panika po zdemaskowaniu",
    "hellish_resistance": "Odporność na ogień",
    "high_elf_cantrip": "Elficki cantrip",
    "human_versatility": "Ludzka wszechstronność",
    "infernal_legacy": "Piekielne dziedzictwo",
    "lucky": "Szczęście",
    "military_rank": "Stopień wojskowy",
    "naturally_stealthy": "Naturalna skrytość",
    "position_of_privilege": "Uprzywilejowana pozycja",
    "relentless_endurance": "Nieustępliwa wytrzymałość",
    "researcher": "Badacz",
    "rustic_hospitality": "Wiejska gościnność",
    "savage_attacks": "Brutalne ataki",
    "shelter_of_the_faithful": "Opieka współwyznawców",
    "ships_passage": "Przejazd statkiem",
    "skill_versatility": "Wszechstronność umiejętności",
    "stonecunning": "Znajomość kamienia",
    "tinker": "Majsterkowicz",
    "trance": "Trans",
    "wanderer": "Wędrowiec",
}

_SUBCLASS_FEATURE_HELP = {
    "life_domain": (
        "Domena Życia",
        "Zapewnia biegłość w ciężkich pancerzach oraz zawsze przygotowane czary domenowe.",
        "Biegłość i czary są automatycznie dodane do postaci.",
    ),
    "disciple_of_life": (
        "Uczeń życia",
        "Czary przywracające PW leczą dodatkowo o 2 + poziom użytego czaru.",
        "Silnik automatycznie dodaje premię do leczenia.",
    ),
    "dragon_ancestor": (
        "Smoczy przodek",
        "Magia postaci pochodzi od smoczego przodka i określa jej fabularne dziedzictwo.",
        "Cecha jest zapisana na karcie; jej znaczenie wykorzystują sceny i dalszy rozwój postaci.",
    ),
    "draconic_resilience": (
        "Smocza odporność",
        "Maksymalne PW rosną o 1 na poziom, a bez pancerza bazowa KP wynosi 13 + modyfikator Zręczności.",
        "Premie do PW i KP są wyliczane automatycznie.",
    ),
    "dark_ones_blessing": (
        "Błogosławieństwo Mrocznego",
        "Gdy sprowadzasz wrogą istotę do 0 PW, zyskujesz tymczasowe PW równe poziomowi czarnoksiężnika + modyfikator Charyzmy.",
        "Silnik walki wykrywa pokonanie celu i automatycznie przyznaje tymczasowe PW.",
    ),
}

_CHARACTER_CONTENT_LABELS = {
    "battleaxe": "topór bojowy",
    "blanket": "koc",
    "club": "pałka",
    "common_clothes": "zwykłe ubranie",
    "common": "wspólny",
    "costume_clothes": "kostium",
    "crowbar": "łom",
    "dice_set": "kości do gry",
    "disguise_kit": "zestaw do charakteryzacji",
    "dragonchess_set": "zestaw do dragonchess",
    "draconic": "smoczy",
    "dwarvish": "krasnoludzki",
    "fine_clothes": "eleganckie ubranie",
    "forgery_kit": "zestaw fałszerski",
    "herbalism_kit": "zestaw zielarski",
    "halfling": "niziołczy",
    "handaxe": "toporek",
    "holy_symbol_amulet": "święty symbol",
    "hunting_trap": "pułapka myśliwska",
    "ink": "atrament",
    "ink_pen": "pióro",
    "infernal": "piekielny",
    "iron_pot": "żelazny garnek",
    "land_vehicles": "pojazdy lądowe",
    "light_hammer": "lekki młot",
    "longbow": "długi łuk",
    "longsword": "długi miecz",
    "map_scroll_case": "tuba na mapę lub zwój",
    "navigators_tools": "narzędzia nawigatora",
    "playing_card_set": "talia kart",
    "pouch": "sakiewka",
    "quarterstaff": "kostur",
    "shortbow": "krótki łuk",
    "shortsword": "krótki miecz",
    "shovel": "łopata",
    "signet_ring": "sygnet",
    "silk_rope": "jedwabna lina",
    "small_knife": "mały nóż",
    "three_dragon_ante_set": "zestaw Three-Dragon Ante",
    "thieves_tools": "narzędzia złodziejskie",
    "travelers_clothes": "ubranie podróżne",
    "vestments": "szaty liturgiczne",
    "water_vehicles": "pojazdy wodne",
    "elvish": "elficki",
    "gnomish": "gnomi",
    "orc": "orkowy",
}


_GAMING_SET_IDS = frozenset(
    {"dice_set", "playing_card_set", "dragonchess_set", "three_dragon_ante_set"}
)
_MUSICAL_INSTRUMENT_IDS = frozenset(
    {
        "bagpipes", "drum", "dulcimer", "flute", "horn",
        "lute", "lyre", "pan_flute", "shawm", "viol",
    }
)
_ARTISAN_TOOL_IDS = frozenset(
    {
        "alchemists_supplies", "brewers_supplies", "calligraphers_supplies",
        "carpenters_tools", "cartographers_tools", "cobblers_tools",
        "cooks_utensils", "glassblowers_tools", "jewelers_tools",
        "leatherworkers_tools", "masons_tools", "painters_supplies",
        "potters_tools", "smiths_tools", "tinkers_tools", "weavers_tools",
        "woodcarvers_tools",
    }
)


def _tool_choice_prompt(
    tool_ids: tuple[str, ...],
    choice_count: int,
) -> dict[str, str]:
    choices = frozenset(tool_ids)
    suffix = f"wybierz {choice_count}"
    if choices and choices <= _GAMING_SET_IDS:
        category = "Zestaw do gry"
        explanation = (
            "Wybierasz biegłość w jednej grze oraz jej fizyczny zestaw. "
            "Gdy test wykorzystuje tę grę, postać dodaje premię z biegłości."
        )
    elif choices and choices <= _MUSICAL_INSTRUMENT_IDS:
        category = "Instrument muzyczny"
        explanation = (
            "Wybierasz biegłość w jednym instrumencie oraz otrzymujesz ten "
            "instrument. Odpowiednie występy mogą korzystać z premii z biegłości."
        )
    elif choices and choices <= _ARTISAN_TOOL_IDS:
        category = "Narzędzia rzemieślnicze"
        explanation = (
            "Wybierasz biegłość i komplet narzędzi. Odpowiednie testy oraz "
            "receptury rzemieślnicze mogą korzystać z premii z biegłości."
        )
    else:
        category = "Biegłość narzędziowa"
        explanation = (
            "Jeśli test wykorzystuje wybrane narzędzie, postać dodaje premię "
            "z biegłości. Do użycia potrzebny jest również właściwy przedmiot."
        )
    return {
        "legend": f"{category} — {suffix}",
        "explanation": explanation,
    }


def _content_label(content_id: str) -> str:
    return _CHARACTER_CONTENT_LABELS.get(
        content_id,
        player_label(content_id),
    )


def _feature_labels(feature_ids: tuple[str, ...]) -> str:
    return ", ".join(
        _CHARACTER_FEATURE_LABELS.get(
            feature_id,
            feature_id.replace("_", " ").title(),
        )
        for feature_id in feature_ids
    )


def _character_sheet_feature_entries(
    features: tuple[FeatureGrant, ...], *, actor_id: str | None = None,
) -> tuple[dict[str, str], ...]:
    entries: list[dict[str, str]] = []
    for feature in features:
        if feature.source_ref == "physical_mana:v02":
            flaw = FLAWS.get(actor_id or "")
            name, text = (flaw[1], flaw[2]) if flaw and feature.feature_id == flaw[0] else (feature.label, feature.description)
            ability = mana_ability(actor_id or "", feature.feature_id)
            if ability is not None:
                name, text = ability.name, feature.description
            from dnd_board_game.scenarios.character_text import feature_copy
            current_copy = feature_copy(actor_id or '', feature.feature_id)
            if current_copy is not None:
                name, text = current_copy
            entries.append({"name": name, "rule_text": text, "game_text": "", "use_mode": ""})
            continue
        note = FLAW_HELP.get(feature.feature_id) or PASSIVE_HELP.get(feature.feature_id)
        if note is None and actor_id in HERO_FLAWS:
            note = ACTIVE_FEATURE_HELP.get(feature.feature_id)
        if note is not None:
            entries.append({"name": note.name, "rule_text": note.body,
                            "game_text": "", "use_mode": ""})
            continue
        help_entry = (
            origin_feature_help(feature.feature_id)
            or class_feature_help(feature.feature_id)
        )
        if help_entry is not None:
            entries.append(
                {
                    "name": help_entry.name,
                    "rule_text": help_entry.rule_text,
                    "game_text": help_entry.game_text,
                    "use_mode": help_entry.use_mode_label,
                }
            )
            continue
        fighting_style_id = feature.feature_id.removeprefix("fighting_style_")
        fighting_style = (
            FIGHTING_STYLE_HELP.get(fighting_style_id)
            if fighting_style_id != feature.feature_id
            else None
        )
        if fighting_style is not None:
            entries.append(
                {
                    "name": f"Styl walki: {fighting_style.name}",
                    "rule_text": fighting_style.rule_text,
                    "game_text": fighting_style.play_text,
                    "use_mode": "Działa automatycznie",
                }
            )
            continue
        subclass_help = _SUBCLASS_FEATURE_HELP.get(feature.feature_id)
        if subclass_help is not None:
            name, rule_text, game_text = subclass_help
            entries.append(
                {
                    "name": name,
                    "rule_text": rule_text,
                    "game_text": game_text,
                    "use_mode": "Działa automatycznie",
                }
            )
            continue
        if feature.feature_id.startswith("favored_enemy_"):
            entries.append(
                {
                    "name": f"Ulubiony wróg: {player_label(feature.feature_id)}",
                    "rule_text": (
                        "Masz przewagę w testach Przetrwania podczas tropienia "
                        "wybranego typu oraz w testach Inteligencji dotyczących go."
                    ),
                    "game_text": (
                        "Premia pojawia się automatycznie, gdy scena i cel mają "
                        "pasujące oznaczenie."
                    ),
                    "use_mode": "Działa w pasującej scenie",
                }
            )
            continue
        if feature.feature_id.startswith("natural_explorer_"):
            entries.append(
                {
                    "name": f"Naturalny odkrywca: {player_label(feature.feature_id)}",
                    "rule_text": (
                        "Podczas podróży po wybranym terenie zyskujesz korzyści "
                        "w nawigacji, tropieniu i zdobywaniu pożywienia."
                    ),
                    "game_text": (
                        "Profil podróży stosuje korzyści w scenach oznaczonych "
                        "tym rodzajem terenu."
                    ),
                    "use_mode": "Działa w pasującej scenie",
                }
            )
            continue
        entries.append(
            {
                "name": player_label(feature.feature_id, feature.label),
                "rule_text": feature.description or "Cecha postaci.",
                "game_text": "Jej efekt jest uwzględniany przez zasady gry.",
                "use_mode": "",
            }
        )
    return tuple(entries)


def _species_mechanics(species) -> tuple[str, ...]:
    bonuses = [
        f"{_PLAYER_LABELS[ability_id]} +{getattr(species.ability_bonuses, ability_id)}"
        for ability_id in ABILITY_IDS
        if getattr(species.ability_bonuses, ability_id)
    ]
    if species.ability_bonus_choice_count:
        bonuses.append(
            f"{species.ability_bonus_choice_count} wybrane cechy "
            f"+{species.ability_bonus_choice_value}"
        )
    result = [
        f"Cechy: {', '.join(bonuses) or 'bez premii'}",
        f"Szybkość: {species.speed_feet} ft · rozmiar: "
        f"{'średni' if species.size == 'medium' else 'mały' if species.size == 'small' else species.size}",
    ]
    if species.darkvision_feet:
        result.append(f"Widzenie w ciemności: {species.darkvision_feet} ft")
    if species.skill_proficiencies:
        result.append(
            "Biegłości: "
            + ", ".join(_content_label(skill_id) for skill_id in species.skill_proficiencies)
        )
    if species.weapon_proficiencies:
        result.append(
            "Bronie: "
            + ", ".join(_content_label(item_id) for item_id in species.weapon_proficiencies)
        )
    if species.tool_proficiencies:
        result.append(
            "Biegłości narzędziowe: "
            + ", ".join(_content_label(tool_id) for tool_id in species.tool_proficiencies)
        )
    if species.languages:
        result.append(
            "Języki: " + ", ".join(_content_label(language_id) for language_id in species.languages)
        )
    if species.language_choice_count:
        result.append(f"Dodatkowe języki: wybierz {species.language_choice_count}")
    return tuple(result)


def _background_mechanics(background) -> tuple[str, ...]:
    result = [
        "Umiejętności: "
        + ", ".join(_content_label(skill_id) for skill_id in background.skill_proficiencies)
    ]
    tools = (*background.tool_proficiencies,)
    if tools:
        result.append(
            "Biegłości narzędziowe: "
            + ", ".join(_content_label(tool_id) for tool_id in tools)
        )
    if background.tool_choice_count:
        category = _tool_choice_prompt(
            background.tool_choices,
            background.tool_choice_count,
        )["legend"].split(" — ", maxsplit=1)[0]
        result.append(
            f"{category}: wybierz {background.tool_choice_count}"
        )
    if background.language_choice_count:
        result.append(f"Języki: wybierz {background.language_choice_count}")
    if background.equipment:
        result.append(
            "Wyposażenie: "
            + ", ".join(_content_label(grant.item_id) for grant in background.equipment)
        )
    result.append(f"Startowe złoto: {background.starting_gp} gp")
    return tuple(result)


def _class_mechanics(character_class) -> tuple[str, ...]:
    result = [
        f"Kość Wytrzymałości: k{character_class.hit_die}",
        "Rzuty obronne: "
        + ", ".join(
            _PLAYER_LABELS.get(ability_id, ability_id)
            for ability_id in character_class.saving_throw_proficiencies
        ),
        f"Umiejętności: wybierz {character_class.skill_choice_count}",
    ]
    if character_class.armor_proficiencies:
        result.append(
            "Pancerze: "
            + ", ".join(character_class.armor_proficiencies)
        )
    if character_class.spellcasting_ability:
        result.append(
            "Magia: "
            + _PLAYER_LABELS.get(
                character_class.spellcasting_ability,
                character_class.spellcasting_ability,
            )
        )
    return tuple(result)


def _equipment_package_view(package, resources) -> dict[str, object]:
    items: list[dict[str, object]] = []
    for grant in package.items:
        item = resources.inventory_item(grant.item_id)
        if item is None:
            continue
        contents = tuple(
            {
                "name": (
                    nested.name
                    if (nested := resources.inventory_item(entry.item_id))
                    is not None
                    else player_label(entry.item_id)
                ),
                "quantity": entry.quantity,
            }
            for entry in item.bundle_contents
        )
        items.append(
            {
                "name": item.name,
                "quantity": grant.quantity,
                "description": item.description,
                "equipped": grant.equipped,
                "contents": contents,
            }
        )
    return {
        "id": package.id,
        "label": package.label,
        "items": tuple(items),
    }


def _character_issue_step(issue: object) -> int:
    field = (
        str(issue.get("field", ""))
        if isinstance(issue, dict)
        else str(getattr(issue, "field", ""))
    )
    if field == "species_id":
        return 0
    if field.startswith("selected_species_"):
        return 1
    if field == "background_id":
        return 2
    if field.startswith("selected_background_"):
        return 3
    if field == "class_id":
        return 4
    if field in ABILITY_IDS or field == "base_ability_scores":
        return 5
    if field in {"name", "portrait"}:
        return 7
    return 6


def _character_draft_from_request(character_id: str) -> CharacterDraft:
    return CharacterDraft(
        id=character_id,
        name=str(request.form.get("name", "")).strip(),
        species_id=str(request.form.get("species_id", "")).strip(),
        class_id=str(request.form.get("class_id", "")).strip(),
        background_id=str(request.form.get("background_id", "")).strip(),
        base_ability_scores=AbilityScores(
            **{
                ability_id: _form_integer(request.form.get(ability_id))
                for ability_id in ABILITY_IDS
            }
        ),
        selected_skill_ids=tuple(request.form.getlist("selected_skill_ids")),
        selected_expertise_ids=tuple(
            request.form.getlist("selected_expertise_ids")
        ),
        selected_fighting_style_id=str(
            request.form.get("selected_fighting_style_id", "")
        ).strip(),
        equipment_package_id=str(
            request.form.get("equipment_package_id", "")
        ).strip(),
        selected_cantrip_ids=tuple(request.form.getlist("selected_cantrip_ids")),
        selected_spell_ids=tuple(request.form.getlist("selected_spell_ids")),
        selected_prepared_spell_ids=tuple(
            request.form.getlist("selected_prepared_spell_ids")
        ),
        selected_subclass_id=str(
            request.form.get("selected_subclass_id", "")
        ).strip(),
        selected_species_bonus_ability_ids=tuple(
            request.form.getlist("selected_species_bonus_ability_ids")
        ),
        selected_species_skill_ids=tuple(
            request.form.getlist("selected_species_skill_ids")
        ),
        selected_species_tool_ids=tuple(
            request.form.getlist("selected_species_tool_ids")
        ),
        selected_species_language_ids=tuple(
            request.form.getlist("selected_species_language_ids")
        ),
        selected_species_variant_id=str(
            request.form.get("selected_species_variant_id", "")
        ).strip(),
        selected_species_cantrip_ids=tuple(
            request.form.getlist("selected_species_cantrip_ids")
        ),
        selected_class_option_ids=tuple(
            request.form.getlist("selected_class_option_ids")
        ),
        selected_background_tool_ids=tuple(
            request.form.getlist("selected_background_tool_ids")
        ),
        selected_background_language_ids=tuple(
            request.form.getlist("selected_background_language_ids")
        ),
        portrait=str(request.form.get("portrait", "")).strip(),
    )


def _store_character_portrait(
    portrait_file,
    *,
    character_id: str,
    portrait_dir: Path,
) -> tuple[str, Path]:
    maximum_bytes = 5 * 1024 * 1024
    payload = portrait_file.stream.read(maximum_bytes + 1)
    if len(payload) > maximum_bytes:
        raise ValueError("Portret może mieć maksymalnie 5 MB.")
    extension = _portrait_extension(payload)
    if extension is None:
        raise ValueError("Portret musi być obrazem PNG, JPEG albo WEBP.")
    portrait_dir.mkdir(parents=True, exist_ok=True)
    destination = portrait_dir / f"{character_id}.{extension}"
    temporary = portrait_dir / f".{character_id}.{uuid4().hex}.tmp"
    try:
        temporary.write_bytes(payload)
        temporary.replace(destination)
    finally:
        if temporary.exists():
            temporary.unlink()
    return f"character_uploads/{destination.name}", destination


def _character_portrait_url(reference: str) -> str:
    normalized = str(reference).strip().lstrip("/")
    if normalized.startswith("character_uploads/"):
        return url_for(
            "character_portraits",
            filename=normalized.removeprefix("character_uploads/"),
        )
    return url_for("game_assets", filename=normalized) if normalized else ""


def _portrait_extension(payload: bytes) -> str | None:
    if payload.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if payload.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if (
        len(payload) >= 12
        and payload[:4] == b"RIFF"
        and payload[8:12] == b"WEBP"
    ):
        return "webp"
    return None


def _character_form_values(form: object) -> dict[str, object]:
    def value(key: str, default: str = "") -> str:
        getter = getattr(form, "get", None)
        if getter is None:
            return default
        raw = getter(key, default)
        return str(raw) if raw is not None else default

    def values(key: str) -> tuple[str, ...]:
        getlist = getattr(form, "getlist", None)
        if getlist is not None:
            return tuple(str(item) for item in getlist(key))
        if isinstance(form, dict):
            raw = form.get(key, ())
            if isinstance(raw, (list, tuple)):
                return tuple(str(item) for item in raw)
            if raw:
                return (str(raw),)
        return ()

    result: dict[str, object] = {
        "name": value("name"),
        "species_id": value("species_id", "human"),
        "class_id": value("class_id", "fighter"),
        "background_id": value("background_id", "soldier"),
        "portrait": value("portrait"),
        "selected_fighting_style_id": value("selected_fighting_style_id"),
        "equipment_package_id": value("equipment_package_id"),
        "selected_subclass_id": value("selected_subclass_id"),
        "selected_skill_ids": values("selected_skill_ids"),
        "selected_expertise_ids": values("selected_expertise_ids"),
        "selected_cantrip_ids": values("selected_cantrip_ids"),
        "selected_spell_ids": values("selected_spell_ids"),
        "selected_prepared_spell_ids": values("selected_prepared_spell_ids"),
        "selected_species_bonus_ability_ids": values(
            "selected_species_bonus_ability_ids"
        ),
        "selected_species_skill_ids": values("selected_species_skill_ids"),
        "selected_species_tool_ids": values("selected_species_tool_ids"),
        "selected_species_language_ids": values(
            "selected_species_language_ids"
        ),
        "selected_species_variant_id": value("selected_species_variant_id"),
        "selected_species_cantrip_ids": values("selected_species_cantrip_ids"),
        "selected_class_option_ids": values("selected_class_option_ids"),
        "selected_background_tool_ids": values(
            "selected_background_tool_ids"
        ),
        "selected_background_language_ids": values(
            "selected_background_language_ids"
        ),
    }
    for index, ability_id in enumerate(ABILITY_IDS):
        result[ability_id] = value(ability_id, str((15, 14, 13, 12, 10, 8)[index]))
    return result


def _copy_character_form(character) -> dict[str, object]:
    actor = character.actor
    return {
        "name": f"{actor.name} — kopia",
        "species_id": character.species_id,
        "class_id": character.class_id,
        "background_id": character.background_id,
        **{
            ability_id: str(getattr(character.base_ability_scores, ability_id))
            for ability_id in ABILITY_IDS
        },
        "selected_skill_ids": character.selected_skill_ids,
        "selected_expertise_ids": character.selected_expertise_ids,
        "selected_fighting_style_id": character.selected_fighting_style_id,
        "equipment_package_id": character.equipment_package_id,
        "selected_cantrip_ids": character.selected_cantrip_ids,
        "selected_spell_ids": character.selected_spell_ids,
        "selected_prepared_spell_ids": character.selected_prepared_spell_ids,
        "selected_subclass_id": character.selected_subclass_id,
        "selected_species_bonus_ability_ids": (
            character.selected_species_bonus_ability_ids
        ),
        "selected_species_skill_ids": character.selected_species_skill_ids,
        "selected_species_tool_ids": character.selected_species_tool_ids,
        "selected_species_language_ids": (
            character.selected_species_language_ids
        ),
        "selected_species_variant_id": character.selected_species_variant_id,
        "selected_species_cantrip_ids": character.selected_species_cantrip_ids,
        "selected_class_option_ids": character.selected_class_option_ids,
        "selected_background_tool_ids": character.selected_background_tool_ids,
        "selected_background_language_ids": (
            character.selected_background_language_ids
        ),
        "portrait": actor.portrait,
    }


def _level_up_context(
    character,
    catalog,
    resources,
    *,
    form: object | None = None,
    error: str = "",
) -> dict[str, object]:
    character_class = catalog.class_by_id(character.class_id)
    if character_class is None:
        raise ValueError("Klasa zapisanej postaci nie istnieje w katalogu.")
    target_level = character.actor.level + 1

    def form_values(key: str, fallback: tuple[str, ...]) -> tuple[str, ...]:
        if form is None:
            return fallback
        getlist = getattr(form, "getlist", None)
        return (
            tuple(str(value) for value in getlist(key))
            if getlist is not None
            else fallback
        )

    def form_value(key: str, fallback: str) -> str:
        if form is None:
            return fallback
        getter = getattr(form, "get", None)
        value = getter(key, fallback) if getter is not None else fallback
        return str(value or "")

    values = {
        "selected_cantrip_ids": form_values(
            "selected_cantrip_ids",
            character.selected_cantrip_ids,
        ),
        "selected_spell_ids": form_values(
            "selected_spell_ids",
            character.selected_spell_ids,
        ),
        "selected_prepared_spell_ids": form_values(
            "selected_prepared_spell_ids",
            character.selected_prepared_spell_ids,
        ),
        "selected_expertise_ids": form_values(
            "selected_expertise_ids",
            character.selected_expertise_ids,
        ),
        "selected_class_option_ids": form_values(
            "selected_class_option_ids",
            character.selected_class_option_ids,
        ),
        "selected_subclass_id": form_value(
            "selected_subclass_id",
            character.selected_subclass_id,
        ),
        "selected_fighting_style_id": form_value(
            "selected_fighting_style_id",
            character.selected_fighting_style_id,
        ),
    }

    def progression_count(field: str, default: int) -> int:
        value = default
        for entry in character_class.level_progression:
            candidate = getattr(entry, field)
            if entry.level <= target_level and candidate is not None:
                value = candidate
        return value

    slots = dict(character_class.spell_slots)
    for entry in character_class.level_progression:
        if entry.level <= target_level and entry.spell_slots:
            slots = dict(entry.spell_slots)
    maximum_spell_level = max(slots, default=0)
    selected_class_options = tuple(
        option
        for group in character_class.choice_groups
        if group.level <= target_level
        for option in group.options
        if option.id in values["selected_class_option_ids"]
    )
    optional_cantrip_ids = tuple(
        cantrip_id
        for group in character_class.choice_groups
        if group.level <= target_level
        for option in group.options
        for cantrip_id in option.cantrip_choices
    )
    cantrip_choices = tuple(
        spell
        for spell_id in dict.fromkeys(
            (*character_class.cantrip_choices, *optional_cantrip_ids)
        )
        for spell in (resources.spell(spell_id),)
        if spell is not None
    )
    selected_subclass = next(
        (
            subclass
            for subclass in character_class.subclass_choices
            if subclass.id == values["selected_subclass_id"]
        ),
        None,
    )
    subclass_spell_choices = (
        (
            *selected_subclass.additional_spell_choice_ids,
            *(
                spell_id
                for entry in selected_subclass.level_progression
                if entry.level <= target_level
                for spell_id in entry.additional_spell_choice_ids
            ),
        )
        if selected_subclass is not None
        else ()
    )
    spell_choices = tuple(
        spell
        for spell_id in dict.fromkeys(
            (*character_class.spell_choices, *subclass_spell_choices)
        )
        for spell in (resources.spell(spell_id),)
        if spell is not None and spell.level <= maximum_spell_level
    )
    always_prepared = set(
        (
            *selected_subclass.always_prepared_spell_ids,
            *(
                spell_id
                for entry in selected_subclass.level_progression
                if entry.level <= target_level
                for spell_id in entry.always_prepared_spell_ids
            ),
        )
        if selected_subclass is not None
        else ()
    )
    preparation_choices = tuple(
        spell for spell in spell_choices if spell.id not in always_prepared
    )
    prepared_count = 0
    if (
        character_class.preparation_formula
        and target_level >= character_class.spellcasting_level
    ):
        ability = character_class.spellcasting_ability
        assert ability is not None
        ability_score = getattr(character.actor.ability_scores, ability)
        class_level = (
            target_level // 2
            if character_class.preparation_formula
            == "ability_modifier_plus_half_level"
            else target_level
        )
        prepared_count = max(1, (ability_score - 10) // 2 + class_level)
        prepared_count = min(prepared_count, len(preparation_choices))
    return {
        "character": character,
        "character_class": character_class,
        "target_level": target_level,
        "values": values,
        "error": error,
        "cantrip_count": (
            progression_count(
                "cantrip_choice_count",
                character_class.cantrip_choice_count,
            )
            + sum(
                option.cantrip_choice_count
                for option in selected_class_options
            )
        ),
        "cantrip_choices": cantrip_choices,
        "spell_count": progression_count(
            "spell_choice_count",
            character_class.spell_choice_count,
        ),
        "spell_choices": spell_choices,
        "prepared_count": prepared_count,
        "preparation_choices": preparation_choices,
        "expertise_count": (
            character_class.expertise_choice_count
            if target_level >= character_class.expertise_choice_level
            else 0
        ),
        "expertise_choices": tuple(
            dict.fromkeys(
                (
                    *character.actor.proficiencies.skills,
                    *(
                        skill_id
                        for group in character_class.choice_groups
                        if group.level <= target_level
                        for option in group.options
                        for skill_id in option.skill_proficiencies
                    ),
                )
            )
        ),
        "option_groups": tuple(
            group
            for group in character_class.choice_groups
            if group.level <= target_level
        ),
        "labels": _PLAYER_LABELS,
    }


def _form_integer(value: object) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def _physical_mana_archetype(hero_id: str):
    archetype = HERO_ARCHETYPES_BY_ID.get(hero_id)
    if archetype is None or not hero_abilities(hero_id):
        return archetype
    from dnd_board_game.scenarios.pooled_mana_catalog import hero_profile
    from dnd_board_game.scenarios.character_text import hero_text
    profile = hero_profile(hero_id)
    copy = hero_text(hero_id)
    return replace(archetype,
        history=copy["history"], motivation=copy["motivation"], personal_goal=copy["personal_goal"], role=copy["role"],
        turn_plan=("Mając mniej niż 6 kart, wybierz jedną z dwóch odkrytych kart many.",
                   "Zaplanuj ruch, akcję główną i dodatkową. Test: k20 + cecha + naładowanie + inne premie.",
                   "Zachowaj pulę. Zwykły atak nie spala kart; spalanie zdolności rozlicz po jej efekcie."),
        resources=("Naładowanie: +1 do testów za fizyczną kartę, maks. +6. Atut daje 2 ładunku zdolności; progi 2/4/6.",
                   "Kolory many uruchamiają osobne pasywy. Premie trwają do mana draina.",
                   profile["passive"]),
        pitfalls=(profile["flaw"], "Spalanie wspólnej talii przybliża mana drain."))
