"""Recruitment trials exercise normal combat while isolating the seven heroes."""

from dataclasses import replace
from pathlib import Path
import random

import pytest

from dnd_board_game.application.recruitment_arena import HERO_ORDER, HELPER_ID
from dnd_board_game.actors import Faction
from dnd_board_game.actors.resources import uses_physical_mana
from dnd_board_game.combat import current_actor, replace_actor
from dnd_board_game.combat.enemy_ai import plan_enemy_turn, resolve_planned_enemy_turn
from dnd_board_game.combat.physical_mana import resolve_mana_support
from dnd_board_game.ui.exploration_app import ExplorationUiSession
from dnd_board_game.ui.training_arena import training_hero, start_training_trial
from dnd_board_game.world import Coordinate


def arena(tmp_path: Path) -> ExplorationUiSession:
    s = ExplorationUiSession(
        "content/scenarios/recruitment_arena.json",
        save_dir=tmp_path / "saves",
        observation_dir=tmp_path / "observations",
    )
    s.configure_custom_party((training_hero("garran"),))
    return s


def begin(
    s: ExplorationUiSession,
    hero: str,
    mode: str = "basic",
    creature_type: str = "humanoid",
) -> None:
    start_training_trial(s, hero, mode, creature_type)
    for _ in range(20):
        if s.encounter_setup_flow.completed:
            break
        s.confirm_encounter_setup_step()
    assert s.encounter_setup_flow.completed
    s.start_encounter_initiative()
    assert len(s.encounter_initiative_flow.prompts) == 1
    s.submit_encounter_initiative_roll(20)
    assert s.combat_state is not None
    # Keep the tests independent of tied initiative and random enemy rolls.
    index = next(
        i
        for i, e in enumerate(s.combat_state.initiative_order.entries)
        if str(e.actor.id) == hero
    )
    s.combat_state = replace(
        s.combat_state,
        initiative_order=replace(s.combat_state.initiative_order, current_index=index),
    )


@pytest.mark.parametrize("hero", HERO_ORDER)
def test_each_hero_has_individual_trial_and_normal_abilities(
    hero: str, tmp_path: Path
) -> None:
    s = arena(tmp_path)
    begin(s, hero)
    actor = current_actor(s.combat_state)
    assert str(actor.id) == hero and uses_physical_mana(actor)
    assert actor.hp == training_hero(hero).hp
    assert len(s.combat_state.actors) == 2
    payload = s.state_payload()
    assert payload["combat"]["physical_mana"]["abilities"]
    assert not payload["training_arena"]["can_start"]
    assert len(payload["training_arena"]["heroes"]) == 7
    with pytest.raises(ValueError, match="Najpierw zakończ"):
        start_training_trial(s, "garran", "basic", "humanoid")


def test_dummy_approaches_and_hits_without_damage(tmp_path: Path) -> None:
    s = arena(tmp_path)
    begin(s, "garran")
    enemy_index = next(
        i
        for i, e in enumerate(s.combat_state.initiative_order.entries)
        if e.actor.faction == Faction.ENEMY
    )
    s.combat_state = replace(
        s.combat_state,
        initiative_order=replace(
            s.combat_state.initiative_order, current_index=enemy_index
        ),
    )
    e = s._active_encounter()
    dummy = next(a for a in s.combat_state.actors if a.faction == Faction.ENEMY)
    source = e.attack_sources_by_actor[dummy.id]
    assert dummy.ac == 10 and dummy.hp == 50
    assert sum(m.value for m in source.attack_roll_request.modifiers) == 5
    plan = plan_enemy_turn(e.board, s.combat_state, dummy, source)
    assert plan.movement_path is not None and plan.movement_path.valid
    dummy = replace(dummy, position=Coordinate(9, 17))
    state = replace_actor(s.combat_state, dummy)
    plan = plan_enemy_turn(e.board, state, dummy, source)
    result = resolve_planned_enemy_turn(e.board, plan, source, random.Random(5))
    assert result.attack_roll is not None
    assert result.attack_resolution.hit
    assert result.damage.total_applied == 0
    assert result.applied_damage.hp_before == result.applied_damage.hp_after


def test_talking_to_nessa_requires_approach_and_completes_trial(tmp_path: Path) -> None:
    s = arena(tmp_path)
    begin(s, "mira")
    with pytest.raises(ValueError):
        s.select_combat_interaction_at_position(Coordinate(3, 18))
    actor = replace(current_actor(s.combat_state), position=Coordinate(4, 18))
    s.combat_state = replace_actor(s.combat_state, actor)
    s.select_combat_interaction_at_position(Coordinate(3, 18))
    payload = s.confirm_combat_interaction("finish_recruitment")
    assert payload["training_arena"]["finished"]
    assert "mira" in payload["training_arena"]["completed"]
    start_training_trial(s, "brakka", "basic", "humanoid")
    assert "mira" in s.state_payload()["training_arena"]["completed"]
    assert s.custom_party[0].id == "brakka"
    assert not s.active_combat_effects


def test_defeating_dummy_allows_replay_and_persists_progress(tmp_path: Path) -> None:
    s = arena(tmp_path)
    begin(s, "erynd")
    dummy = next(a for a in s.combat_state.actors if a.faction == Faction.ENEMY)
    s.combat_state = replace_actor(s.combat_state, replace(dummy, hp=0))
    assert s.state_payload()["training_arena"]["can_start"]
    s.save_snapshot()
    s.load_snapshot()
    assert "erynd" in s.state_payload()["training_arena"]["completed"]
    start_training_trial(s, "erynd", "basic", "humanoid")
    assert s.custom_party[0].hp == training_hero("erynd").hp
    assert (
        next(
            a
            for a in s.encounter_setup_flow.encounter.actors
            if a.faction == Faction.ENEMY
        ).hp
        == 50
    )


def test_support_has_passive_wounded_recipient_for_lorian_and_survives_save(
    tmp_path: Path,
) -> None:
    s = arena(tmp_path)
    begin(s, "lorian", "support")
    helper = next(a for a in s.combat_state.actors if str(a.id) == HELPER_ID)
    assert helper.hp < helper.max_hp and uses_physical_mana(helper)
    assert HELPER_ID not in {
        str(e.actor.id) for e in s.combat_state.initiative_order.entries
    }
    assert current_actor(s.combat_state).hp < current_actor(s.combat_state).max_hp
    resolve_mana_support(s.combat_state, (), "mana_transfer", HELPER_ID)
    s.save_snapshot()
    s.load_snapshot()
    assert len(s.combat_state.actors) == 3
    assert s.state_payload()["combat"]["physical_mana"]["setup"]["deck"] == 20
    source = s._active_encounter().attack_sources_by_actor["recruitment_dummy"]
    assert source.damage_fixed == 1


def test_area_variant_restores_three_targets_and_selected_creature_type(
    tmp_path: Path,
) -> None:
    s = arena(tmp_path)
    begin(s, "nimra", "area", "undead")
    enemies = [a for a in s.combat_state.actors if a.faction == Faction.ENEMY]
    assert len(enemies) == 3 and all(a.creature_type == "undead" for a in enemies)
    s.save_snapshot()
    s.load_snapshot()
    assert len(s._active_encounter().actors) == 4


def test_bad_parameters_do_not_reset_live_state(tmp_path: Path) -> None:
    s = arena(tmp_path)
    before = s.state
    with pytest.raises(ValueError):
        start_training_trial(s, "not_a_hero", "basic", "humanoid")
    with pytest.raises(ValueError):
        start_training_trial(s, "mira", "unknown", "humanoid")
    assert s.state == before and s.combat_state is None


def test_nessa_is_lit_and_board_selection_opens_the_real_interaction(
    tmp_path: Path,
) -> None:
    from dnd_board_game.application.recruitment_arena import NESSA_POSITION
    from dnd_board_game.ui.training_arena import can_talk_to_nessa

    s = arena(tmp_path)
    begin(s, "garran")
    assert not can_talk_to_nessa(s)
    s.combat_state = replace_actor(
        s.combat_state,
        replace(current_actor(s.combat_state), position=Coordinate(4, 18)),
    )
    assert can_talk_to_nessa(s)
    assert NESSA_POSITION in s._current_board_scan_target().positions
    payload = s._handle_board_position(NESSA_POSITION)
    assert payload["combat"]["pending_combat_interaction"]
    s.confirm_combat_interaction("finish_recruitment")
    s.resolve_active_combat()
    assert s.state_payload()["training_arena"]["can_start"]
    assert "garran" in s.state_payload()["training_arena"]["completed"]


def test_support_result_does_not_leak_helper_into_next_trial(tmp_path: Path) -> None:
    s = arena(tmp_path)
    begin(s, "dagna", "support")
    assert any(c.actor_id == HELPER_ID for c in s.combat_state.condition_states)
    dummy = next(a for a in s.combat_state.actors if a.faction == Faction.ENEMY)
    s.combat_state = replace_actor(s.combat_state, replace(dummy, hp=0))
    s.resolve_active_combat()
    s.save_snapshot()
    s.load_snapshot()
    start_training_trial(s, "mira", "basic", "humanoid")
    assert [str(a.id) for a in s.exploration.actors] == ["mira"]
    assert not s.state.condition_states


def test_training_routes_and_launcher(tmp_path: Path) -> None:
    from dnd_board_game.ui.routes import create_app

    s = arena(tmp_path)
    client = create_app(s, character_dir=tmp_path / "characters").test_client()
    assert b"/training/open" in client.get("/").data
    assert client.post("/training/open").status_code == 302
    html = client.get("/play").get_data(as_text=True)
    assert "training_arena.js" in html and "training-arena-panel" in html
    assert client.post("/api/training/nessa", json={}).status_code == 400
    response = client.post("/api/training/start", json={"hero_id": "brakka"})
    assert response.status_code == 200
    assert response.json["training_arena"]["current_hero_id"] == "brakka"
    assert (
        client.post("/api/training/start", json={"hero_id": "mira"}).status_code == 400
    )


@pytest.mark.parametrize("mode,damage", [("basic", 0), ("support", 1), ("area", 0)])
def test_mana_waves_keep_dummy_damage_safe(
    mode: str, damage: int, tmp_path: Path
) -> None:
    from dnd_board_game.combat.physical_mana import report_wave, resolve_waves
    from dnd_board_game.combat.scene_interactions import (
        attack_source_with_combat_effects,
    )

    s = arena(tmp_path)
    begin(s, "garran", mode)
    effects = ()
    for event in (1, 2, 4):
        effects = report_wave(s.combat_state, effects, event)
    effects = resolve_waves(s.combat_state, effects)
    assert any(e.kind == "mana_threat" and e.value == 3 for e in effects)
    for enemy in s.combat_state.actors:
        if enemy.faction != Faction.ENEMY:
            continue
        source = s._active_encounter().attack_sources_by_actor[enemy.id]
        modified = attack_source_with_combat_effects(enemy, source, effects)
        assert modified.damage_fixed == damage
        assert modified.damage_modifier == 0
        assert modified.damage_components == source.damage_components


def test_arena_terrain_changes_movement_and_sight_with_open_detours(
    tmp_path: Path,
) -> None:
    from dnd_board_game.world import find_path
    from dnd_board_game.world.movement import movement_cost
    from dnd_board_game.world.line_of_sight import line_of_sight_clear

    session = arena(tmp_path)
    start_training_trial(session, "mira", "basic", "humanoid")
    encounter = session.encounter_setup_flow.encounter
    board = encounter.board
    hero = next(a for a in encounter.actors if a.faction == Faction.ALLY)
    for row in (14, 15):
        for col in range(8, 12):
            assert movement_cost(board, hero, (), Coordinate(col, row)) == 10
    assert movement_cost(board, hero, (), Coordinate(7, 15)) == 5
    assert movement_cost(board, hero, (), Coordinate(13, 11)) is None
    assert not line_of_sight_clear(board, Coordinate(12, 11), Coordinate(15, 11))
    assert not line_of_sight_clear(board, Coordinate(3, 11), Coordinate(6, 11))
    assert line_of_sight_clear(board, Coordinate(9, 16), Coordinate(9, 13))
    # Both sides of the rubble and the route back to Nessa remain passable.
    walker = replace(hero, speed_feet=100)
    for col in (7, 12):
        for row in range(13, 19):
            assert movement_cost(board, walker, (), Coordinate(col, row)) == 5
        assert find_path(board, walker, (), Coordinate(col, 13)).valid
    assert find_path(board, walker, (), Coordinate(4, 18)).valid
    setup_fields = {
        p for step in session.encounter_setup_flow.steps for p in step.positions
    }
    assert {Coordinate(8, 14), Coordinate(4, 11), Coordinate(13, 11)} <= setup_fields


@pytest.mark.parametrize("mode", ["basic", "support", "area"])
def test_arena_terrain_keeps_all_variant_starts_clear(
    mode: str, tmp_path: Path
) -> None:
    session = arena(tmp_path)
    start_training_trial(session, "nimra", mode, "humanoid")
    encounter = session.encounter_setup_flow.encounter
    for actor in encounter.actors:
        terrain = encounter.board.terrain_at(actor.position)
        assert not terrain.blocks_movement and not terrain.is_difficult


def test_low_cover_setup_never_inherits_blocking_obstacle_rules(tmp_path: Path) -> None:
    session = arena(tmp_path)
    start_training_trial(session, "garran", "basic", "humanoid")
    flow = session.encounter_setup_flow
    low_fields = {Coordinate(13, 15), Coordinate(14, 15)}
    cover_steps = [step for step in flow.steps if low_fields.intersection(step.positions)]
    assert cover_steps
    for step in cover_steps:
        assert "osłony" in step.label
        assert set(step.positions) <= low_fields
        assert "można wejść" in " ".join(step.mechanics)
        assert not any("Pole blokuje ruch" in rule for rule in step.mechanics)
        assert "Kamienny filar" not in step.message
    for step in flow.steps:
        if any("Pole blokuje ruch" in rule for rule in step.mechanics):
            assert not low_fields.intersection(step.positions)
            assert not any("Figurka stojąca" in rule for rule in step.mechanics)
    assert all(not flow.encounter.board.terrain_at(p).blocks_movement for p in low_fields)
