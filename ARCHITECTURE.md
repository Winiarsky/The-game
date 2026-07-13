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
  application/                 # Use-case orchestration and explicit flow transitions
  core/                        # Shared primitives and errors
  rules/                       # D&D 5e mechanics
  world/                       # Grid, topology, terrain, pathfinding, line of sight
  actors/                      # Actor state, PCs, monsters, NPCs
  actions/                     # Action definitions and action resolution entry points
  combat/                      # Initiative, turns, attacks, damage, conditions
  inventory/                   # Items, equipment, inventory rules
  scenarios/                   # Scenario loading and runtime encounter setup
  hardware/                    # Adapter from game events to board.Connection
  ui/                          # Application session, Flask transport, views, templates, and static assets
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

`BoardSessionAdapter` is the application-facing boundary for board scans, scan reset,
and LED feedback. UI sessions may depend on this adapter, but should not construct or
invoke `board.Connection` directly.

LED colors are centralized in `src/dnd_board_game/hardware/led_palette.py`.
Runtime and combat code should use semantic names like `LedColor.LEGAL_ATTACK_TARGET`,
`LedColor.INTERACTIVE_OBJECT` or `LedColor.ENEMY_MOVEMENT_PATH` instead of local RGB tuples.
This keeps board communication consistent when one tile can represent multiple intentions.

## Web UI Boundary

The exploration web surface is split into explicit responsibilities:

- `application/exploration_flow.py` owns deterministic exploration flow transitions,
- `application/combat_movement_flow.py` owns player movement planning, movement application,
  and opportunity-attack threat detection before reactions are resolved,
- `application/combat_reaction_flow.py` owns opportunity-attack reaction consumption,
  manual hero reaction attacks, Ready trigger detection, attack and damage resolution,
  and the final movement decision,
- `application/combat_turn_action_flow.py` owns common player turn actions and their
  deterministic combat effects (`Dash`, `Dodge`, `Disengage`, `Help`, and Ready preparation),
- `application/enemy_turn_flow.py` owns enemy-turn validation, intent planning, automatic
  resolution orchestration, and classification into Ready, opportunity, movement, attack,
  or immediate-finish transitions,
- `application/combat_turn_finalization.py` owns enemy-result commits, turn advancement,
  turn-boundary effect expiration, and the observation payloads for completed turns,
- `application/player_combat_action_flow.py` owns combat source selection and the
  single-target player attack flow from target preview through attack and damage resolution,
- `application/player_area_healing_flow.py` owns player healing and area-spell targeting,
  resource consumption, saving throws, multi-target damage, and cancellation transitions,
- `application/player_combat_resource_flow.py` owns consumable combat actions and the
  concentration lifecycle, including damage-triggered checks and effect removal,
- `application/combat_scene_interaction_flow.py` owns combat scene-object selection,
  interaction resolution, saving throws, and position-bound effect expiration,
- `ui/exploration_app.py` owns the current application session and compatibility entry point,
- `ui/routes.py` owns Flask request/response transport,
- `ui/session_state.py` groups transient pending choices with explicit flow-owned types,
- `ui/session_view.py` defines the top-level `/api/state` payload contract,
- `ui/templates/` and `ui/static/` own HTML, CSS, and JavaScript.

`ExplorationUiSession` applies the returned transition, then performs edge effects in the
existing order: message/log recording, LED synchronization, and payload rendering. The
planned combat-flow extraction is complete; future feature work should preserve the same API
and session-observation contracts instead of reopening the coordinator boundary without a
concrete need.
Random rolls are injected into combat application services so deterministic tests can provide
explicit outcomes while the UI runtime may retain its seeded random source.

## First Implementation Milestones

1. Create core coordinate/grid primitives.
2. Implement pathfinding and movement budget.
3. Implement actor state and simple encounter state.
4. Implement D&D 5e dice/check/attack primitives.
5. Implement initiative and turn order.
6. Implement board LED adapter for movement/selection feedback.
7. Add minimal UI/runtime loop.
