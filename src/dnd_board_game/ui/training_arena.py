"""Recruitment UI orchestration; campaign saves and roster characters stay separate."""

from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from dnd_board_game.actors import Actor, Faction
from dnd_board_game.application.recruitment_arena import (
    ARENA_ID,
    HERO_ORDER,
    NESSA_POSITION,
    TrainingConfig,
)
from dnd_board_game.character_creation import (
    apply_boardgame_archetype,
    build_character,
    default_character_drafts,
    load_character_catalog,
    load_character_resources,
)
from dnd_board_game.character_creation.physical_mana import apply_physical_mana_profile
from dnd_board_game.combat.scene import scene_flag, set_scene_flag
from dnd_board_game.combat.session import combat_winner, current_actor
from dnd_board_game.application.exploration_flow import (
    ExplorationFlowStage as UiFlowStage,
)

if TYPE_CHECKING:
    from .exploration_app import ExplorationUiSession, BoardScanTarget
    from dnd_board_game.world import Coordinate


def roster_active(session: ExplorationUiSession) -> bool:
    return session.exploration.scenario_id == ARENA_ID and not scene_flag(session.state.flags, 'training_requested', False)


def roster_target(session: ExplorationUiSession) -> BoardScanTarget:
    from .training_menu import board_target
    return board_target(session)


def select_roster(session: ExplorationUiSession, position: Coordinate) -> dict[str, object]:
    from .training_menu import select_position
    return select_position(session, position)


@lru_cache(maxsize=7)
def training_hero(hero_id: str) -> Actor:
    if hero_id not in HERO_ORDER:
        raise ValueError("Wybierz jednego z siedmiu bohaterów.")
    root = Path(__file__).resolve().parents[3]
    catalog = load_character_catalog(root / "content/character_creation/catalog.json")
    resources = load_character_resources(catalog, root / "content")
    draft = next(d for d in default_character_drafts() if d.id == hero_id)
    actor = apply_boardgame_archetype(
        build_character(draft, catalog, resources).actor,
        spell_definitions=tuple(s for _, s in resources.spells),
    )
    return apply_physical_mana_profile(actor)


def trial_won(session: ExplorationUiSession) -> bool:
    from .training_walkthrough import enabled as guided, current_step
    if guided(session):
        return bool(current_step(session) is None and session.combat_state and session.combat_state.status.value == "finished" and combat_winner(session.combat_state) == Faction.ALLY)
    from .training_tutorial import enabled, completed, abilities
    if enabled(session):
        hero_id = str(session.custom_party[0].id) if session.custom_party else ""
        return bool(hero_id and len(completed(session, hero_id)) == len(abilities(hero_id)))
    combat = session.combat_state
    return bool(
        combat is not None
        and combat.status.value == "finished"
        and (
            combat_winner(combat) == Faction.ALLY
            or (
                session.pending_encounter_result is not None
                and session.pending_encounter_result.conclusion.value
                == "objective_completed"
            )
        )
    )


def remember_training_result(session: ExplorationUiSession) -> None:
    if (
        session.exploration.scenario_id == ARENA_ID
        and trial_won(session)
        and session.custom_party
    ):
        session.state = replace(
            session.state,
            flags=set_scene_flag(
                session.state.flags,
                f"training_completed_{session.custom_party[0].id}",
                True,
            ),
        )


def start_training_trial(
    session: ExplorationUiSession, hero_id: str, mode: str, creature_type: str, *, reset_progress: bool = False, case_id: str | None = None
) -> dict[str, object]:
    if mode == "walkthrough":
        from .training_walkthrough import start
        return start(session, hero_id, reset_progress=reset_progress, case_id=case_id)
    if session.exploration.scenario_id != ARENA_ID:
        raise ValueError("Próby są dostępne wyłącznie na arenie rekrutacyjnej.")
    if (
        session.combat_state is not None
        and session.combat_state.status.value != "finished"
    ):
        raise ValueError("Najpierw zakończ pokaz u Nessy albo pokonaj kukłę.")
    if session.pending_encounter is not None and session.combat_state is None:
        raise ValueError("Najpierw ukończ przygotowanie bieżącej próby.")
    config = TrainingConfig(mode, creature_type, hero_id)
    hero = training_hero(hero_id)
    remember_training_result(session)
    completed = tuple(
        (key, value)
        for key, value in session.state.flags.values
        if key.startswith(("training_completed_", "walkthrough_", "exploration_mana_", "trap_lesson_done_")) or (
            key.startswith("training_tutorial_done_")
            and not (reset_progress and key.startswith(f"training_tutorial_done_{hero_id}_")))
    )
    if mode == "support" or (mode == "tutorial" and hero_id in {"garran", "dagna"}):
        hero = replace(hero, hp=max(1, hero.max_hp - 8))
    session.configure_custom_party((hero,))
    flags = session.state.flags
    for key, value in (
        *completed,
        ("training_mode", config.mode),
        ("training_creature_type", config.creature_type),
        ("training_hero", hero_id),
        ("training_requested", True),
    ):
        flags = set_scene_flag(flags, key, value)
    session.state = replace(session.state, flags=flags)
    if mode == "traps":
        from .simple_traps import initialize
        initialize(session)
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session._refresh_pending_encounter()
    if session.pending_encounter is not None:
        session.pending_encounter = replace(
            session.pending_encounter, precombat_stealth_completed=True
        )
    session._add_message(
        "Nessa: zapraszam na arenę",
        (f"{hero.name}, wykonaj wszystkie ćwiczenia z listy samouczka. Kolejność jest dowolna; "
         "zaliczamy rozstrzygnięcie zdolności, również przy pudle lub udanej obronie celu. "
         "Rozmowa z Nessą pozwala przerwać próbę bez zaliczenia brakujących ćwiczeń. "
         if mode == "tutorial" else f"{hero.name}, pokonaj kukłę albo podejdź do mnie i zakończ pokaz. ")
        + "Przygotuj 25 kart many: po 5 każdego koloru. Wyłóż rynek 5 kart; pozostałe 20 tworzy talię. Nie ma prywatnej ręki.",
    )
    session._record(
        "training_trial_started",
        {"hero_id": hero_id, "mode": mode, "creature_type": creature_type},
    )
    return session.start_encounter_setup()


def can_talk_to_nessa(session: ExplorationUiSession) -> bool:
    from .training_walkthrough import enabled as guided
    if guided(session):
        return False
    if session.exploration.scenario_id != ARENA_ID or session.combat_state is None:
        return False
    if (
        session.combat_state.status.value != "active"
        or session._combat_has_pending_resolution()
    ):
        return False
    if session.combat_turn_preview_option_id is not None:
        return False
    actor = current_actor(session.combat_state)
    return (
        str(actor.id) in HERO_ORDER
        and max(
            abs(actor.position.col - NESSA_POSITION.col),
            abs(actor.position.row - NESSA_POSITION.row),
        )
        <= 1
    )


def training_payload(session: ExplorationUiSession) -> dict[str, object] | None:
    if session.exploration.scenario_id != ARENA_ID:
        return None
    from .exploration_mana import active as exploration_active
    if exploration_active(session):
        return dict(mode="exploration", can_start=False, tutorial=None, heroes=[], completed=[],
                    current_hero_id=str(scene_flag(session.state.flags, "training_hero", "garran")), finished=False)
    from .simple_traps import enabled as trap_enabled, notice as trap_notice, payload as trap_payload
    if trap_enabled(session):
        return dict(mode="traps", can_start=False, tutorial=dict(notice=trap_notice(session)),
                    trap=trap_payload(session), heroes=[], completed=[], current_hero_id=str(scene_flag(session.state.flags, "training_hero", "garran")))
    from . import training_walkthrough as guided
    from .board_panel_symbols import panel_icon
    from dnd_board_game.application.training_walkthrough import steps
    if guided.enabled(session) or not scene_flag(session.state.flags, "training_requested", False):
        active = guided.enabled(session)
        finished = bool(session.combat_state and session.combat_state.status.value == "finished")
        from .training_menu import payload as menu_payload
        done = [h for h in HERO_ORDER if scene_flag(session.state.flags, f"walkthrough_charge_completed_{h}", False) or (active and not guided.single_case(session) and h == guided.hero_id(session) and trial_won(session))]
        return dict(current_hero_id=guided.hero_id(session), completed=done, menu=menu_payload(session) if not active else None,
            heroes=[dict(id=h, name=training_hero(h).name, panel_slot=6+i, icon=panel_icon(6+i), tutorial_count=int(scene_flag(session.state.flags, f"walkthrough_charge_progress_{h}", 0)), tutorial_total=len(steps(h)), completed=h in done) for i,h in enumerate(HERO_ORDER)],
            can_start=not active, can_talk=False, finished=finished, mode="walkthrough",
            tutorial=guided.payload(session) if active else None, creature_type="humanoid",
            won=trial_won(session) if active else False, map_url="/game-assets/maps/recruitment_arena/arena.svg")
    current_id = str(session.custom_party[0].id) if session.custom_party else "garran"
    from .training_tutorial import completed as skills_completed, abilities, payload as tutorial_payload
    config = TrainingConfig.from_flags(session.state.flags)
    is_tutorial = config.mode == "tutorial" or not scene_flag(session.state.flags, "training_requested", False)
    completed = [
        hero_id
        for hero_id in HERO_ORDER
        if (len(skills_completed(session, hero_id)) == len(abilities(hero_id)) if is_tutorial else (
            scene_flag(session.state.flags, f"training_completed_{hero_id}", False)
            or (hero_id == current_id and trial_won(session))))
    ]
    finished = bool(
        session.combat_state and session.combat_state.status.value == "finished"
    )
    busy = (
        bool(
            session.pending_encounter
            or session.encounter_setup_flow
            or session.combat_state
        )
        and not finished
    )
    return {
        "current_hero_id": current_id,
        "completed": completed,
        "heroes": [
            {"id": hero_id, "name": training_hero(hero_id).name,
             "tutorial_count": len(skills_completed(session, hero_id)), "tutorial_total": len(abilities(hero_id))}
            for hero_id in HERO_ORDER
        ],
        "can_start": not busy,
        "can_talk": can_talk_to_nessa(session),
        "finished": finished,
        "mode": "tutorial" if is_tutorial else config.mode,
        "tutorial": tutorial_payload(session, current_id) if is_tutorial else None,
        "creature_type": config.creature_type,
        "map_url": "/game-assets/maps/recruitment_arena/arena.svg",
    }
