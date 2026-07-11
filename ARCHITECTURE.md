# Architecture

The rebuild should separate deterministic game logic from adapters.

## Directory Layout

```text
board/                         # Existing low-level board, serial, WLED, simulator backend
content/                       # Data-driven game content
  items/
  monsters/
  scenarios/
docs/                          # Design and engineering notes
legacy/                        # Archived previous application
src/dnd_board_game/
  core/                        # Shared primitives and errors
  rules/                       # D&D 5e mechanics
  world/                       # Grid, topology, terrain, pathfinding, line of sight
  actors/                      # Actor state, PCs, monsters, NPCs
  actions/                     # Action definitions and action resolution entry points
  combat/                      # Initiative, turns, attacks, damage, conditions
  inventory/                   # Items, equipment, inventory rules
  scenarios/                   # Scenario loading and runtime encounter setup
  hardware/                    # Adapter from game events to board.Connection
  ui/                          # Presentation and input adapters
  save/                        # Save/load snapshots
tests/
  unit/
  integration/
  hardware/
```

## Dependency Direction

Rules and world modules must not depend on UI or hardware.

Preferred direction:

```text
ui -> application orchestration -> rules/world/actors/combat
hardware -> board.Connection
application orchestration -> hardware adapter
content loaders -> rules/world/actors
```

Forbidden direction:

```text
rules -> ui
rules -> board
world -> board
actors -> flask/requests/serial
combat -> WLED
```

## Core Design Principles

- Deterministic domain code first.
- Adapters at the edges.
- Explicit events or result objects between modules.
- Small APIs with tests before adding feature breadth.
- Data-driven content after the core behavior is stable.
- Combat/exploration features should map to the action-mechanics hierarchy in `docs/MECHANICS_ARCHITECTURE.md` before UI-specific flow is added.

## Hardware Boundary

Existing `board.Connection` provides:

- `scan_board(...)`
- `set_leds(...)`
- `leds_off()`
- `cancel_scan()`
- `rearm_scan()`
- `reset_connection()`

New code should wrap it in `src/dnd_board_game/hardware/` rather than calling it from rules modules.

LED colors are centralized in `src/dnd_board_game/hardware/led_palette.py`.
Runtime and combat code should use semantic names like `LedColor.LEGAL_ATTACK_TARGET`,
`LedColor.INTERACTIVE_OBJECT` or `LedColor.ENEMY_MOVEMENT_PATH` instead of local RGB tuples.
This keeps board communication consistent when one tile can represent multiple intentions.

## First Implementation Milestones

1. Create core coordinate/grid primitives.
2. Implement pathfinding and movement budget.
3. Implement actor state and simple encounter state.
4. Implement D&D 5e dice/check/attack primitives.
5. Implement initiative and turn order.
6. Implement board LED adapter for movement/selection feedback.
7. Add minimal UI/runtime loop.
