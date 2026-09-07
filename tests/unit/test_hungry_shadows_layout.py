"""Playable geography, directional cover and player briefings for Map 1."""

from dataclasses import replace
import json
from pathlib import Path

import pytest

from dnd_board_game.application.battle_setup import battle_briefing
from dnd_board_game.combat.attack_positioning import evaluate_cover_from_origin
from dnd_board_game.scenarios import (
    build_encounter_from_scenario,
    encounter_for_party_size,
    load_scenario,
    LoadedEncounter,
)
from dnd_board_game.world import Coordinate, find_path

SCENARIO = Path("content/scenarios/ostatni_transport_01_glodne_cienie.json")


def encounter() -> LoadedEncounter:
    return build_encounter_from_scenario(load_scenario(SCENARIO))


@pytest.mark.parametrize("size", [1, 2, 3, 4, 5])
def test_all_starts_and_enemy_positions_are_legal_and_disjoint(size: int) -> None:
    scene = encounter_for_party_size(encounter(), size)
    starts = set(scene.player_start_zones[0])
    enemies = [a for a in scene.actors if a.faction.value == "enemy"]
    assert len({a.position for a in enemies}) == size
    assert all(a.position not in starts for a in enemies)
    assert all(not scene.board.terrain_at(p).blocks_movement for p in starts)
    assert all(not scene.board.terrain_at(p).is_difficult for p in starts)
    hero = next(a for a in scene.actors if a.faction.value == "ally")
    # Formation extremes and center connect to every enemy within two dashes.
    for start in (
        Coordinate(5, 19),
        Coordinate(14, 19),
        Coordinate(5, 22),
        Coordinate(14, 22),
        Coordinate(10, 21),
    ):
        walker = replace(hero, position=start, speed_feet=200)
        for enemy in enemies:
            path = find_path(scene.board, walker, (), enemy.position)
            assert path.valid
            assert path.cost_feet <= 90


@pytest.mark.parametrize(
    "origin,destination",
    [
        ((5, 19), (5, 10)),
        ((14, 19), (14, 9)),
        ((14, 14), (18, 14)),
        ((14, 9), (18, 9)),
    ],
)
def test_dry_approaches_and_both_ridge_connections(
    origin: tuple[int, int], destination: tuple[int, int],
) -> None:
    scene = encounter()
    hero = replace(scene.actors[0], position=Coordinate(*origin), speed_feet=200)
    path = find_path(scene.board, hero, (), Coordinate(*destination))
    assert path.valid
    assert all(not scene.board.terrain_at(p).is_difficult for p in path.path)


def test_actual_cargo_gives_cover_only_when_between_origin_and_target() -> None:
    scene = encounter()
    hero = replace(scene.actors[0], position=Coordinate(6, 14))
    protected = evaluate_cover_from_origin(
        scene.board, Coordinate(6, 11), hero, (hero,), scene.scene_objects
    )
    exposed = evaluate_cover_from_origin(
        scene.board, Coordinate(6, 17), hero, (hero,), scene.scene_objects
    )
    on_cover = replace(hero, position=Coordinate(6, 13))
    standing = evaluate_cover_from_origin(
        scene.board, Coordinate(6, 11), on_cover, (on_cover,), scene.scene_objects
    )
    assert protected.cover_bonus == 2
    assert exposed.cover_bonus == standing.cover_bonus == 0
    assert all(obj.cover_bonus == 0 for obj in scene.scene_objects)


def test_solo_briefing_explains_actual_opponent_and_mana_stays_physical() -> None:
    scene = encounter()
    solo = " ".join(battle_briefing(scene.environment, solo=True)).lower()
    party = " ".join(battle_briefing(scene.environment)).lower()
    assert "osłabionego" in solo
    assert "przewodnic" not in solo
    assert "przewodnic" in party
    assert "man" in solo and "man" in party


def test_environment_has_no_duplicate_cells_or_automatic_ac_bonuses() -> None:
    data = json.loads(SCENARIO.read_text())
    for entry in data["environment"]:
        positions = entry.get("positions", [])
        assert len(positions) == len(set(map(tuple, positions)))
        assert not entry.get("cover_bonus", 0)


def test_aftermath_landmarks_match_wreck_and_accessible_shelter() -> None:
    scene = encounter()
    data = json.loads(
        Path("content/scenarios/ostatni_transport_01_zawalona_droga.json").read_text()
    )
    zones = {zone["id"]: zone for zone in data["exploration"]["zones"]}
    points = {point["id"]: point for point in data["exploration"]["points"]}
    assert data["encounter_map_asset"] == scene.map_asset
    assert scene.board.terrain_at(
        Coordinate(*zones["overturned_wagon"]["anchor_position"])
    ).blocks_movement
    assert points["teren"]["positions"][0] == zones["teren_shelter"]["anchor_position"]
    for zone_id in ("blocked_road", "overturned_wagon", "teren_shelter"):
        for position in zones[zone_id]["interaction_pad_positions"]:
            assert not scene.board.terrain_at(Coordinate(*position)).blocks_movement
