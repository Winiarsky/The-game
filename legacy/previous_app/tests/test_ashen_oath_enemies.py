from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from game_objects_loader import scan_game_objects
from src.game import Game


class DummyConnection:
    def set_leds(self, *_args, **_kwargs):
        return None

    def leds_off(self, *_args, **_kwargs):
        return None

    def scan_board(self, *_args, **_kwargs):
        return (0, 0)

    def read_card(self, *_args, **_kwargs):
        return "DECLINE"


def _enemy_defs_by_id():
    definitions = scan_game_objects(SRC_ROOT / "GameObjects")
    return {definition.meta.object_id: definition for definition in definitions if definition.meta.category == "Enemies"}


def test_ashen_oath_enemy_definitions_are_registered_with_pf2e_levels():
    definitions = _enemy_defs_by_id()

    expected_levels = {
        "ashen_watcher": -1,
        "ash_cinder": -1,
        "vale_guard": 0,
        "mill_enforcer": 1,
        "ashen_knight": 1,
        "charred_deacon": 2,
        "odrans_champion": 2,
    }
    for object_id, level in expected_levels.items():
        definition = definitions[object_id]
        assert definition.logic_cls is not None
        assert definition.meta.default_config["level"] == level


def test_ashen_oath_maps_load_campaign_specific_enemy_classes():
    expected_by_map = {
        "ashen_oath_old_mill": {"ValeGuard", "MillEnforcer"},
        "ashen_oath_hill_ruins": {"AshenKnight"},
        "ashen_oath_oath_crypt": {"OdransChampion", "AshenWatcher"},
    }

    for scenario_id, expected_classes in expected_by_map.items():
        game = Game(conn=DummyConnection(), scenario=scenario_id)
        class_names = {enemy.__class__.__name__ for enemy in game.enemies}
        assert expected_classes <= class_names


def test_burned_chapel_spawns_charred_deacon_from_altar_trigger():
    from burned_chapel_encounter import trigger_altar

    game = Game(conn=DummyConnection(), scenario="ashen_oath_burned_chapel")
    assert game.enemies == []

    trigger_altar(game)

    assert {enemy.__class__.__name__ for enemy in game.enemies} == {"CharredDeacon"}


def test_ashen_oath_enemy_numbers_follow_level_one_party_budget():
    definitions = _enemy_defs_by_id()
    encounter_xp_by_map = {
        "burned_chapel": ["charred_deacon"],
        "old_mill": ["vale_guard", "vale_guard", "mill_enforcer"],
        "hill_ruins": ["ashen_knight", "ashen_watcher", "ashen_watcher"],
        "oath_crypt": ["odrans_champion", "ashen_knight", "ashen_watcher", "ashen_watcher"],
    }
    xp_by_delta = {-4: 10, -3: 15, -2: 20, -1: 30, 0: 40, 1: 60, 2: 80, 3: 120, 4: 160}

    totals = {}
    for map_id, enemy_ids in encounter_xp_by_map.items():
        total = 0
        for enemy_id in enemy_ids:
            level = int(definitions[enemy_id].meta.default_config["level"])
            total += xp_by_delta[max(-4, min(4, level - 1))]
        totals[map_id] = total

    assert totals == {
        "burned_chapel": 60,
        "old_mill": 100,
        "hill_ruins": 80,
        "oath_crypt": 140,
    }
