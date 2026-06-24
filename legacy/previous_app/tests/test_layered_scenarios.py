from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from layered_scenarios import (
    build_layered_setup_plan,
    compile_layered_scenario,
    list_scenario_names,
    load_layered_scenario,
    resolve_scenario_payload,
)
from scenario_map_renderer import load_scenario_data, render_scenario_files
from src.game import Game


LAYERED_PATH = PROJECT_ROOT / "scenarios_layered" / "layered_forest_rooms.json"


class DummyConnection:
    def set_leds(self, *_args, **_kwargs):
        return None

    def leds_off(self, *_args, **_kwargs):
        return None

    def scan_board(self, *_args, **_kwargs):
        return (0, 0)


def test_layered_scenario_is_listed_and_compiles_to_runtime():
    names = list_scenario_names()
    assert "layered_forest_rooms" in names

    layered = load_layered_scenario(LAYERED_PATH)
    compiled = compile_layered_scenario(layered)

    assert compiled["metadata"]["source_format"] == "layered_scenario_v1"
    assert isinstance(compiled["setup_plan"], list) and compiled["setup_plan"]
    room_ids = {room["id"] for room in compiled["rooms"]}
    assert {"biome_forest", "stone_hall", "garden_patch_alpha"}.issubset(room_ids)
    assert any(obj["category"] == "Interactables" and obj["object_id"] == "door" for obj in compiled["objects"])
    assert any(obj["category"] == "Enemies" and obj["object_id"] == "goblin_warrior" for obj in compiled["objects"])


def test_build_layered_setup_plan_returns_room_wall_door_object_enemy_steps():
    layered = load_layered_scenario(LAYERED_PATH)
    plan = build_layered_setup_plan(layered)
    kinds = [step["kind"] for step in plan]

    assert kinds == ["room", "room", "wall", "door", "object", "enemy", "hero_start"]
    assert any(step["edges"] for step in plan if step["kind"] in {"wall", "door"})


def test_game_loads_layered_scenario_and_applies_rooms_edges_and_objects():
    layered = load_layered_scenario(LAYERED_PATH)
    compiled = compile_layered_scenario(layered)
    game = Game(
        conn=DummyConnection(),
        scenario_payload=compiled,
        scenario_label="layered_forest_rooms",
    )

    assert game.state.__class__.__name__ == "EncounterSetupState"
    assert "biome_forest" in game.board.rooms_at((0, 0))
    assert {"biome_forest", "stone_hall"}.issubset(game.board.rooms_at((4, 5)))
    assert {"biome_forest", "garden_patch_alpha"}.issubset(game.board.rooms_at((12, 6)))
    assert game.board.get_wall((7, 4), (8, 4)) is not None
    assert game.board.edge_interactables_between((7, 7), (8, 7))
    assert game.board.occupant_at((5, 6)).__class__.__name__ == "SimpleObstacle"
    assert any(enemy.name == "Garden Goblin" and enemy.position == (13, 7) for enemy in game.enemies)


def test_resolve_scenario_payload_returns_compiled_layered_payload():
    payload, meta = resolve_scenario_payload("layered_forest_rooms")

    assert meta["kind"] == "layered"
    assert payload["metadata"]["source_format"] == "layered_scenario_v1"
    assert payload["name"] == "Layered Forest Rooms"


def test_renderer_supports_layered_scenario_files(tmp_path):
    data = load_scenario_data(LAYERED_PATH, rows=30, cols=20)
    assert data.biome_name == "Forest Biome"
    assert data.doors
    assert any(room["id"] == "stone_hall" for room in data.rooms)

    map_path, legend_path = render_scenario_files(LAYERED_PATH, output_dir=tmp_path, rows=30, cols=20)
    map_text = map_path.read_text(encoding="utf-8")
    legend_text = legend_path.read_text(encoding="utf-8")

    assert "Door / passage edge" in legend_text
    assert "Biome: Forest Biome" in legend_text
    assert "<svg" in map_text
