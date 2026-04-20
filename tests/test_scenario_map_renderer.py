from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scenario_map_renderer import (
    CELL_SIZE_CM,
    load_board_dimensions,
    load_scenario_data,
    render_scenario_files,
)


def test_load_scenario_data_collects_goblin_features():
    rows, cols = load_board_dimensions()
    data = load_scenario_data(PROJECT_ROOT / "scenarios" / "goblin_skirmish.json", rows=rows, cols=cols)

    assert data.cols == 20
    assert data.rows == 30
    assert len(data.starting_positions) == 6
    assert data.terrains[(6, 5)] == "blocked_field"
    assert (4, 6) in data.obstacles
    assert any(enemy.object_id == "goblin_commando" and enemy.position == (14, 3) for enemy in data.enemies)
    assert any(set((a, b)) == set(((5, 6), (6, 6))) for a, b in data.walls)


def test_load_scenario_data_handles_dense_ruins_variant():
    rows, cols = load_board_dimensions()
    data = load_scenario_data(PROJECT_ROOT / "scenarios" / "goblin_skirmish_dense_ruins.json", rows=rows, cols=cols)

    assert data.terrains[(4, 4)] == "blocked_field"
    assert data.terrains[(16, 10)] == "bushes_field"
    assert (11, 5) in data.obstacles
    assert any(enemy.object_id == "goblin_dog" and enemy.position == (18, 10) for enemy in data.enemies)
    assert any(set((a, b)) == set(((16, 3), (16, 4))) for a, b in data.walls)


def test_render_scenario_files_write_clean_map_and_separate_legend(tmp_path):
    map_path, legend_path = render_scenario_files(
        PROJECT_ROOT / "scenarios" / "goblin_skirmish_flank_lab.json",
        output_dir=tmp_path,
    )

    map_text = map_path.read_text(encoding="utf-8")
    legend_text = legend_path.read_text(encoding="utf-8")

    assert map_path.name == "goblin_skirmish_flank_lab.svg"
    assert legend_path.name == "goblin_skirmish_flank_lab_legend.svg"
    assert "<svg" in map_text
    assert "<svg" in legend_text
    assert "Goblin Skirmish Flank Lab" not in map_text
    assert "Starting position" not in map_text
    assert "paper-bg" in map_text
    assert "stone-speck" in map_text
    assert "ground-wash" in map_text
    assert "GW" not in map_text
    assert "GC" not in map_text
    assert "GD" not in map_text
    assert f"1 kratka = {CELL_SIZE_CM:.2f} cm" in legend_text
    assert "Legenda" in legend_text
    assert "Enemy positions" not in legend_text
