from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from board.led_mapping import build_serpentine_led_mapping, board_cell_to_led_index
from board.settings import board_dimensions, load_board_config


def test_board_config_uses_30x20_dimensions():
    rows, cols = board_dimensions(load_board_config())

    assert rows == 30
    assert cols == 20


def test_serpentine_mapping_matches_key_reference_points():
    mapping = build_serpentine_led_mapping(rows=30, cols=20)

    assert mapping["0"]["0"] == 0
    assert mapping["0"]["29"] == 29
    assert mapping["1"]["29"] == 31
    assert mapping["1"]["0"] == 60
    assert mapping["19"]["0"] == 618


def test_serpentine_mapping_covers_600_unique_board_cells():
    mapping = build_serpentine_led_mapping(rows=30, cols=20)
    led_indexes = {
        int(mapping[str(col)][str(row)])
        for col in range(20)
        for row in range(30)
    }

    assert len(led_indexes) == 600
    assert min(led_indexes) == 0
    assert max(led_indexes) == 618
    assert 30 not in led_indexes


def test_direct_led_index_helper_matches_mapping():
    assert board_cell_to_led_index(0, 0, rows=30) == 0
    assert board_cell_to_led_index(0, 29, rows=30) == 29
    assert board_cell_to_led_index(1, 29, rows=30) == 31
    assert board_cell_to_led_index(1, 0, rows=30) == 60
