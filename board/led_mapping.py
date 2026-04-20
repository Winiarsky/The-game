from __future__ import annotations

import json
from pathlib import Path


LED_POSITIONS_PATH = Path(__file__).resolve().parent / "led_positions.json"


def board_cell_to_led_index(col: int, row: int, *, rows: int, turnaround_per_column: int = 1) -> int:
    if col < 0:
        raise ValueError(f"Column out of range: {col}.")
    if not 0 <= row < rows:
        raise ValueError(f"Row out of range: {row}. Expected 0..{rows - 1}.")
    leds_per_column = rows + turnaround_per_column
    base = col * leds_per_column
    if col % 2 == 0:
        return base + row
    return base + (rows - 1 - row)


def turnaround_led_index_after_column(col: int, *, rows: int, turnaround_per_column: int = 1) -> int:
    if col < 0:
        raise ValueError(f"Column out of range: {col}.")
    leds_per_column = rows + turnaround_per_column
    return (col * leds_per_column) + rows


def build_serpentine_led_mapping(
    rows: int,
    cols: int,
    *,
    turnaround_per_column: int = 1,
) -> dict[str, dict[str, int]]:
    mapping: dict[str, dict[str, int]] = {}
    for col in range(cols):
        mapping[str(col)] = {}
        for row in range(rows):
            mapping[str(col)][str(row)] = board_cell_to_led_index(
                col,
                row,
                rows=rows,
                turnaround_per_column=turnaround_per_column,
            )
    return mapping


def load_led_mapping(
    *,
    rows: int,
    cols: int,
    mapping_path: str | Path | None = None,
) -> dict[str, dict[str, int]]:
    path = Path(mapping_path) if mapping_path is not None else LED_POSITIONS_PATH
    if not path.exists():
        return build_serpentine_led_mapping(rows, cols)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("LED mapping must be a dictionary.")
    if len(payload) != cols:
        raise ValueError(f"LED mapping has {len(payload)} outer keys, expected {cols}.")
    for outer in payload.values():
        if not isinstance(outer, dict):
            raise ValueError("LED mapping inner values must be dictionaries.")
        if len(outer) != rows:
            raise ValueError(f"LED mapping inner size {len(outer)} does not match rows={rows}.")
    return payload


def invert_led_mapping(mapping: dict[str, dict[str, int]]) -> dict[int, tuple[int, int]]:
    led_to_cell: dict[int, tuple[int, int]] = {}
    for col_key, rows in mapping.items():
        for row_key, led_index in rows.items():
            led_to_cell[int(led_index)] = (int(row_key), int(col_key))
    return led_to_cell
