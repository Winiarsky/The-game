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
  inventory/                   # Items, equipment, attunement, charges, loot, currency, and trade
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
- `core/migrations.py` owns schema-neutral, sequential pure-data migrations.
  Snapshot and content loaders register explicit `vN -> vN+1` transforms and
  never silently skip an unknown version.
- `scenarios/content_contract.py` owns content headers, stable-id syntax and
  source-pack metadata, while `scenarios/content_audit.py` validates the whole
  repository catalog through the same scenario loader used by runtime.

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
- `exploration/flow_graph.py` owns pure state-derived exploration graph nodes,
  conditions and route references, while
  `application/exploration_interaction_flow.py` selects the available authored
  goal route and `application/exploration_goal_execution.py` validates the
  player-selected participant model, actor eligibility, authored observation
  scope and procedural source actions before the UI creates pending state.
  `application/npc_goal_execution.py` applies the same boundary to NPC goals:
  it derives visible cards, locks the authored NPC intent, and validates the
  selected leader/helper before LLM narration.
  Flow graphs orchestrate content but never resolve D&D checks or mutate state;
  see `docs/EXPLORATION_FLOW_GRAPHS.md`,
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
- `combat/conditions.py` owns condition definitions, immunities, roll consequences,
  movement restrictions, timed expiry, and repeated saving throws; application services
  provide dice/input policy but do not duplicate condition rules,
- `actors/auras.py` defines serializable actor aura data, while `combat/auras.py`
  derives live coverage and roll modifiers from actor positions, factions, and life state;
  aura membership is never stored as mutable combat state,
- `actors/triggers.py` defines serializable feature triggers without importing the rules
  package; `combat/triggers.py` matches stable event ids to runtime `EffectEvent`s and
  applies deterministic ordered outcomes to combat or standalone actor collections.
  Application flows emit events only after the corresponding attack, damage, movement,
  rest, or encounter transition has been committed; the UI presents and logs activations,
- `actors/features.py` owns source-neutral `FeatureDefinition` metadata and runtime
  `FeatureGrant` provenance. Scenario loading expands feature content into the existing
  resource, attack, action, trigger, and aura models; feature execution never bypasses
  their deterministic resolvers,
- `exploration/npc_state.py` owns deterministic updates of persistent NPC runtime
  state. The LLM classifies and narrates an interaction, while content permissions
  select success/failure state updates; conversation history and NPC state remain
  separate persisted concerns. `exploration/social_interactions.py` maps current
  NPC attitude and content-classified request risk to the deterministic 2014
  conversation reaction threshold; the LLM cannot choose this DC. Both are
  separate persisted inputs to later interactions. `exploration/npc_state.py`
  also plans content-limited NPC attempts from persisted relationship events
  and current scene flags; the UI cannot consume an attempt before a roll.
  `exploration/npc_outcomes.py` validates structured intent targets, selects one
  of four check-result branches, and applies its effects through the shared
  exploration effect executor. `exploration/npc_transitions.py` resolves the
  optional content-authored stage between an NPC outcome and its next scene;
  ordered variants inspect only deterministic flags/encounter history, while
  explicit player reactions resume dialogue, close it, or start a named trigger,
  and `exploration/effects.py::validate_policy_exploration_effect` is the shared
  authorization boundary used by both LLM proposal validation and scenario
  load-time validation. Content errors retain the full NPC/branch/reaction path,
- `combat/attack_positioning.py` owns cover geometry shared by attack AC and Dexterity
  saves; area flows provide the effect's actual point of origin,
- `combat/spells.py` owns deterministic radius, line-width and cone geometry,
  line-of-effect filtering, and data-driven area target modes; UI only previews
  and confirms the returned positions and affected actors,
- `application/combat_shove_flow.py` and `application/combat_grapple_flow.py` own the
  visible opposed-check previews and deterministic results of special melee maneuvers,
- `combat/reactions.py` owns the transport-neutral ordered `ReactionWindow` contract:
  one interrupted actor, stable reaction options, the current roll stage, advancement,
  and skipping reactors whose reaction resource is no longer available.
  `application/combat_reaction_flow.py` consumes that queue for automatic and manual
  opportunity attacks, post-hit defensive spell reactions and pre-resolution
  Counterspell reactions, while Ready detection contributes options to the same
  window. A defensive spell re-evaluates the already rolled attack before damage is
  committed; Counterspell either clears the pending spell result or records its
  ability-check stage. The UI resumes the interrupted enemy action only after the
  window closes,
- `combat/long_casting.py` owns persisted, transport-neutral progress for casting
  times measured in minutes or hours. `application/long_casting_flow.py` spends one
  action per caster turn, uses the shared concentration effect/check lifecycle,
  defers slots and components until completion, and removes interrupted casts
  without charging their spell resource,
- `combat/summoning.py` owns data-driven summoned-creature statistics, legal
  placement and initiative insertion/removal. `application/summoning_flow.py`
  consumes the caster's action and slot, binds the dynamic actor to the shared
  concentration lifecycle, and removes it when that concentration disappears,
- `combat/magic_movement.py` owns free-tile validation for teleportation and
  obstacle-aware straight-line push/pull destinations. The application flow
  consumes the spell resource, resolves an optional save and emits ordinary
  actor-moved events without spending movement or opening opportunity attacks,
- `application/spell_debuff_flow.py` owns save-first hostile spell targeting,
  resource consumption and condition application. It delegates the condition
  itself and repeated turn-timed saves to the shared combat condition lifecycle,
- `combat/dispelling.py` groups spell-authored active effects and conditions by
  target, source and cast level. `application/spell_dispel_flow.py` owns target
  selection, automatic same/lower-level removal, physical ability checks for
  stronger spells and summon cleanup after their concentration effect disappears,
- `combat/scene.py` owns transport-neutral scene objectives and typed encounter
  conclusions. Victory/defeat can come from combat state, interaction objectives can
  finish an active encounter, and retreat/surrender are explicit declarations rather
  than synthetic HP changes. The exploration trigger selects the matching authored
  outcome and applies its effects only after the result is confirmed,
- `application/combat_turn_action_flow.py` owns common player turn actions and their
  deterministic combat effects (`Dash`, `Dodge`, `Disengage`, `Help`, and Ready preparation),
- `combat/action_economy.py` defines shared action costs, while `combat/session.py`
  consumes action, individual attacks within the Attack action, bonus action, reaction
  and free object-interaction resources; movement remains available between attacks,
  and Shove or Grapple can replace one attack,
  content and UI only declare or display those costs,
- `inventory/armor.py` owns body-armor AC formulas, Strength-based speed penalties,
  Stealth disadvantage and exploration don/doff transitions; combat movement and
  roll flows consume these derived rules without mutating base actor statistics,
- `inventory/charges.py` owns generic item-use spending and deterministic rest
  recovery. Application flows supply action costs and injected dice; UI and content
  do not mutate charge counters directly,
- `inventory/attunement.py` owns the three-item limit, item-power availability and
  deterministic attune/unattune transitions. `application/short_rest_flow.py`
  limits each actor to one such transition during a completed short rest,
- `inventory/magic_items.py` owns typed passive item effects and their shared
  availability/equipment/attunement gate. Existing AC, speed and d20 modifier
  builders consume its contributions instead of implementing item-specific rules,
- `inventory/weapons.py` owns stable weapon-category/property/special-rule enums.
  Item content uses one nested `weapon` contract; the scenario loader expands it
  into typed melee, ranged, finesse and thrown attack sources. Combat owns binding
  actor ability damage, long-range disadvantage, heavy/Small handling and physical
  thrown-weapon placement,
- `inventory/adventuring_gear.py` owns typed mundane categories, spellcasting-focus
  metadata, container capacities, light/fuel lifecycles, utility check modifiers,
  object durability and equipment-pack expansion. The loader resolves standalone
  item files and stable IDs from the unified adventuring-gear catalog,
- `application/enemy_turn_flow.py` owns enemy-turn validation, data-driven Multiattack
  source sequencing, intent planning, automatic
  resolution orchestration, and classification into Ready, opportunity, movement, attack,
  or immediate-finish transitions,
- `application/combat_turn_finalization.py` owns enemy-result commits, turn advancement,
  turn-boundary effect expiration, injected deterministic resource recharge rolls, and
  the observation payloads for completed turns,
- `application/player_combat_action_flow.py` owns combat source selection and the
  single-target player attack flow from target preview through attack and damage resolution,
- `application/player_area_healing_flow.py` owns player healing and area-spell targeting,
  resource consumption, saving throws, multi-target damage, and cancellation transitions,
- `application/player_combat_resource_flow.py` owns consumable combat actions and the
  concentration lifecycle, including cast-level target-count scaling, bounded
  multi-target selection, grouped target effects, damage-triggered checks and
  all-at-once effect removal,
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
Versioned definitions under `content/spells/` are the single source for spell metadata and
their attack, healing or combat-action effect. `rules/spellcasting.py` owns the content-neutral
schema, prepared/known/spellbook access profiles, cast-level selection and V/S/M validation;
`scenarios/loader.py` adapts the effect to the existing combat pipeline.
Per-slot scaling remains data in `SpellDefinition` and is applied by generic attack/healing
source transformers before prompting for physical dice. `application/ritual_casting_flow.py`
owns exploration ritual execution: access and components are validated through the same
casting rules, normal casting time gains ten minutes, and no spell slot is consumed.
`exploration/magic_effects.py` owns the shared minute-based lifecycle for persistent
exploration magic. Rituals register typed effects there, while crafting, rests and armor
changes advance the same clock; expiry removes the effect and clears its authoritative flag.
Combat-duration spell effects use the shared `ActiveEffect` lifecycle. In particular,
Shield contributes to the common effective-AC calculation for the triggering attack and
later attacks, then expires at the protected actor's next turn start.

Rest data is actor domain state in `actors/resources.py`; D&D recovery decisions live in
`rules/resting.py`. Scenario zones may provide a `ShortRestPolicy`, but they do not implement
healing or resource recovery themselves. Starting an exploration session automatically applies
a long rest to allied actors before the spell-preparation stage. Limited attacks reference the
same actor resource pools; optional recharge rules are resolved at turn start and never create a
parallel counter inside attack or monster definitions.

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
