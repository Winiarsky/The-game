# Legacy Description

Current status: the previous gameplay/application stage has been archived in `legacy/previous_app/`.

The root project now keeps only the low-level board and LED layer that should survive the rebuild. The archived code is a reference, not a foundation to keep extending directly.

## Kept Low-Level Hardware Layer

- `board/connection.py`
  - `Connection` is the primary hardware boundary.
  - Supports `simulator` backend through HTTP endpoints: `scan_board`, `set`, `off`, and `simulate/cancel_scan`.
  - Supports `hardware` backend through USB serial scan input plus WLED HTTP LED output.
  - Serial detection probes candidate USB ports and waits for the `board_scan_usb_v1` protocol.
  - WLED control uses `/json/state` and `/json/info`, validates LED count, clears ranges, and sends sparse LED updates.

- `board/settings.py`
  - Loads `board/config.json`.
  - Allows environment overrides for backend, board dimensions, serial port, WLED URL, segment, offset, count, and brightness.

- `board/led_mapping.py`
  - Converts board cells `(col, row)` to LED indexes.
  - Default mapping is serpentine by column with one turnaround LED per column.
  - For the 20x30 board the total strip is 620 LEDs: 600 cell LEDs plus 20 turnaround LEDs.
  - Formula:
    - even column: `led = col * (rows + 1) + row`
    - odd column: `led = col * (rows + 1) + (rows - 1 - row)`
    - turnaround after column: `led = col * (rows + 1) + rows`

- `board/simulator/`
  - Simulator backend for clicking board cells and previewing LED output.
  - It also contains older scenario/editor surfaces; use those as reference only if needed.

- `future/board_20x30_usb_wled_test/`
  - ESP32 sketch and standalone USB/WLED test utility.
  - Useful for validating physical board scans independently from the new app.

## Useful Legacy Algorithms

These are candidates to reimplement cleanly in the new app, not modules to copy wholesale.

### Grid and Movement

Reference files:

- `legacy/previous_app/src/board_grid.py`
- `legacy/previous_app/src/actions/move_utils.py`

Important behavior:

- Board positions are `(col, row)`.
- Grid bounds check against configured `cols` and `rows`.
- Neighbor search supports orthogonal and diagonal movement.
- Diagonal movement was guarded so diagonal traversal only worked when at least one legal two-step corner route existed.
- Movement blocked on walls, blocked terrain, obstacles, blocking interactables, and occupied cells unless explicitly allowed.
- Older movement cost logic included speed in feet, 5 ft per square, difficult terrain, armor penalties, and status-based overrides.
- Pathfinding used heap-based search in the movement utilities; keep that idea, but rebuild it behind a smaller, tested pathfinding API.

Recommended rebuild standard:

- Make a small `Grid`/`BoardTopology` module with no game-rule imports.
- Put pathfinding in a pure function that accepts passability/cost callbacks.
- Keep hardware coordinates identical to LED coordinates: `(col, row)`.

### LED Effects

Reference file:

- `legacy/previous_app/src/led_fx.py`

Important behavior:

- Projectile animation used Bresenham-style line rasterization between two board cells.
- Area animation grouped cells by Chebyshev distance from an origin, then lit expanding rings.
- Effects used `conn.set_leds(positions, colors)` and ended with `conn.leds_off()`.
- Effects gracefully returned `False` when the connection did not support LEDs.

Recommended rebuild standard:

- Keep effects pure where possible: generate frames first, then pass frames to the board adapter.
- Add a single effect runner responsible for sleep timing and cleanup.
- Keep `board.Connection` as the only object that talks to real hardware.

### Runtime/UI Boundary

Reference files:

- `legacy/previous_app/main.py`
- `legacy/previous_app/player_ui/`
- `legacy/previous_app/src/ui_client.py`

Important lesson:

- The old runtime mixed game state, prompts, UI transport, board scans, LED effects, and scenario transitions too tightly.

Recommended rebuild standard:

- Treat board hardware, UI, game rules, and scenario content as separate adapters/modules.
- Use explicit event objects between layers.
- Keep deterministic game rules testable without Flask, WLED, serial devices, or filesystem content.

## Do Not Carry Forward By Default

- PF2-heavy status/class/feat modules.
- Old scenario content and generated assets.
- Old player UI state machine.
- Debug session logs except when investigating a specific old issue.
- Broad runtime tests that depend on old module layout.

## Suggested New App Starting Point

1. Define a small domain model for board cells, actors, turns, and actions.
2. Build a pure movement/pathfinding module.
3. Add a board adapter around `board.Connection`.
4. Add minimal UI only after the domain loop is stable.
5. Add hardware tests around `board/` separately from gameplay tests.
