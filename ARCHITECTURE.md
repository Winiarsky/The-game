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
- `application/exploration_hazard_flow.py` owns hazard saving throws, typed damage,
  save-dependent effects, and actor-condition consequences,
- `exploration/traps.py` owns pure trap-state transitions and action outcomes; detection
  remains an exploration observation and activation delegates to the hazard flow,
- `application/spell_preparation_flow.py` owns the pre-scenario confirmation sequence for
  actors with generic prepared-spell profiles,
- `application/short_rest_flow.py` owns content-driven short-rest preview, completion,
  exploration consequences, and sequential Hit Dice spending,
- `application/combat_movement_flow.py` owns player movement planning, movement application,
  and opportunity-attack threat detection before reactions are resolved,
- `combat/attack_flow.py` owns the explicit melee-reach versus ranged-range contract;
  targeting, opportunity threats, enemy positioning, and UI payloads consume that contract,
- `combat/attack_positioning.py` owns cover geometry shared by attack AC and Dexterity
  saves; area flows provide the effect's actual point of origin,
- `combat/spells.py` owns deterministic radius, line-width and cone geometry,
  line-of-effect filtering, and data-driven area target modes; UI only previews
  and confirms the returned positions and affected actors,
- `application/combat_shove_flow.py` and `application/combat_grapple_flow.py` own the
  visible opposed-check previews and deterministic results of special melee maneuvers,
- `application/combat_reaction_flow.py` owns opportunity-attack reaction consumption,
  manual hero reaction attacks, Ready trigger detection, attack and damage resolution,
  and the final movement decision,
- `application/combat_turn_action_flow.py` owns common player turn actions and their
  deterministic combat effects (`Dash`, `Dodge`, `Disengage`, `Help`, and Ready preparation),
- `combat/action_economy.py` defines shared action costs, while `combat/session.py`
  consumes action, individual attacks within the Attack action, bonus action, reaction
  and free object-interaction resources; movement remains available between attacks,
  and Shove or Grapple can replace one attack,
  content and UI only declare or display those costs,
- `application/enemy_turn_flow.py` owns enemy-turn validation, data-driven Multiattack
  source sequencing, intent planning, automatic
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
The exploration presentation is fiction-first: the normal player surface renders zone
description, optional image and freeform input. `active_challenge.player_hints` contains only
non-mechanical inspiration, while exact options, DCs, progress and risks remain in the
collapsed GM/debug view. Questions reuse the declaration analyzer and are recorded as visible
player/GM exchanges without entering the roll resolver.
Random rolls are injected into combat application services so deterministic tests can provide
explicit outcomes while the UI runtime may retain its seeded random source.

Prepared-spell membership is deterministic actor domain state in
`actors/spell_preparation.py`. Scenario content supplies the available list and preparation
limit; neither the actor model nor the application flow infers a character class. Combat and
exploration resolvers consult the same profile before consuming a spell slot.

Rest data is actor domain state in `actors/resources.py`; D&D recovery decisions live in
`rules/resting.py`. Scenario zones may provide a `ShortRestPolicy`, but they do not implement
healing or resource recovery themselves. Starting an exploration session automatically applies
a long rest to allied actors before the spell-preparation stage.

Runtime effects use the transport-neutral `rules/effects.py` contract. `ActiveEffect` carries
its mechanical source, duration, stacking policy/key and optional secondary expiration points.
Application and combat services may interpret the effect `kind`, but they apply, replace and
expire instances through `apply_active_effect` and `expire_active_effects`. Lifecycle events
cover turn/round boundaries, attacks, movement, concentration, encounter end, rests and scenario
end. `ActiveCombatEffect` remains a compatibility export of this shared type while older call
sites are migrated incrementally. The UI exposes source and expiration but does not decide them.

## First Implementation Milestones

1. Create core coordinate/grid primitives.
2. Implement pathfinding and movement budget.
3. Implement actor state and simple encounter state.
4. Implement D&D 5e dice/check/attack primitives.
5. Implement initiative and turn order.
6. Implement board LED adapter for movement/selection feedback.
7. Add minimal UI/runtime loop.
