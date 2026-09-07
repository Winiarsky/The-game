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
    from .exploration_app import ExplorationUiSession


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
    session: ExplorationUiSession, hero_id: str, mode: str, creature_type: str
) -> dict[str, object]:
    if session.exploration.scenario_id != ARENA_ID:
        raise ValueError("Próby są dostępne wyłącznie na arenie rekrutacyjnej.")
    if (
        session.combat_state is not None
        and session.combat_state.status.value != "finished"
    ):
        raise ValueError("Najpierw zakończ pokaz u Nessy albo pokonaj kukłę.")
    if session.pending_encounter is not None and session.combat_state is None:
        raise ValueError("Najpierw ukończ przygotowanie bieżącej próby.")
    config = TrainingConfig(mode, creature_type)
    hero = training_hero(hero_id)
    remember_training_result(session)
    completed = tuple(
        (key, value)
        for key, value in session.state.flags.values
        if key.startswith("training_completed_")
    )
    if mode == "support":
        hero = replace(hero, hp=max(1, hero.max_hp - 8))
    session.configure_custom_party((hero,))
    flags = session.state.flags
    for key, value in (
        *completed,
        ("training_mode", config.mode),
        ("training_creature_type", config.creature_type),
        ("training_requested", True),
    ):
        flags = set_scene_flag(flags, key, value)
    session.state = replace(session.state, flags=flags)
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session._refresh_pending_encounter()
    if session.pending_encounter is not None:
        session.pending_encounter = replace(
            session.pending_encounter, precombat_stealth_completed=True
        )
    session._add_message(
        "Nessa: zapraszam na arenę",
        f"{hero.name}, pokaż swoje umiejętności. Pokonaj kukłę albo podejdź do mnie i zakończ pokaz. Przygotuj świeżą talię many: 20 kart, rynek 5, start 3 karty.",
    )
    session._record(
        "training_trial_started",
        {"hero_id": hero_id, "mode": mode, "creature_type": creature_type},
    )
    return session.start_encounter_setup()


def can_talk_to_nessa(session: ExplorationUiSession) -> bool:
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
    current_id = str(session.custom_party[0].id) if session.custom_party else "garran"
    completed = [
        hero_id
        for hero_id in HERO_ORDER
        if scene_flag(session.state.flags, f"training_completed_{hero_id}", False)
        or (hero_id == current_id and trial_won(session))
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
    config = TrainingConfig.from_flags(session.state.flags)
    return {
        "current_hero_id": current_id,
        "completed": completed,
        "heroes": [
            {"id": hero_id, "name": training_hero(hero_id).name}
            for hero_id in HERO_ORDER
        ],
        "can_start": not busy,
        "can_talk": can_talk_to_nessa(session),
        "finished": finished,
        "mode": config.mode,
        "creature_type": config.creature_type,
        "map_url": "/game-assets/maps/recruitment_arena/arena.svg",
    }
