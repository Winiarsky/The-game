from __future__ import annotations

BOARD_COLS = 20
BOARD_ROWS = 30
LEDS_PER_COLUMN_WITH_TURN = BOARD_ROWS + 1
BOARD_LED_COUNT = BOARD_COLS * BOARD_ROWS
TURN_LED_COUNT = BOARD_COLS
TOTAL_LED_COUNT = BOARD_COLS * LEDS_PER_COLUMN_WITH_TURN


def validate_cell(col: int, row: int) -> None:
    if not 0 <= col < BOARD_COLS:
        raise ValueError(f"Column out of range: {col}. Expected 0..{BOARD_COLS - 1}.")
    if not 0 <= row < BOARD_ROWS:
        raise ValueError(f"Row out of range: {row}. Expected 0..{BOARD_ROWS - 1}.")


def board_cell_to_led_index(col: int, row: int) -> int:
    validate_cell(col, row)
    base = col * LEDS_PER_COLUMN_WITH_TURN
    if col % 2 == 0:
        return base + row
    return base + (BOARD_ROWS - 1 - row)


def turnaround_led_index_after_column(col: int) -> int:
    if not 0 <= col < BOARD_COLS:
        raise ValueError(f"Column out of range: {col}. Expected 0..{BOARD_COLS - 1}.")
    return (col * LEDS_PER_COLUMN_WITH_TURN) + BOARD_ROWS


def build_mapping() -> dict[str, dict[str, int]]:
    mapping: dict[str, dict[str, int]] = {}
    for col in range(BOARD_COLS):
        mapping[str(col)] = {}
        for row in range(BOARD_ROWS):
            mapping[str(col)][str(row)] = board_cell_to_led_index(col, row)
    return mapping
