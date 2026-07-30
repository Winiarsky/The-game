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
src/dnd_board_game/
  application/                 # Use-case orchestration and explicit flow transitions
  core/                        # Shared primitives and errors
  rules/                       # D&D 5e mechanics
  world/                       # Grid, topology, terrain, pathfinding, line of sight
  actors/                      # Actor state, PCs, monsters, NPCs
  character_creation/          # Drafts, catalogues, validation, and saved-character construction
  actions/                     # Action definitions and action resolution entry points
  combat/                      # Initiative, turns, attacks, damage, conditions
  inventory/                   # Items, equipment, attunement, charges, loot, currency, and trade
  physical_cards/              # Stable decision-card payloads and printable QR generation
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
- `physical_cards/qr_payload.py` owns the transport-neutral, versioned decision-card
  payload. `physical_cards/qr_generation.py` is the file-generation edge and uses
  the small pure-Python `segno` dependency to emit PNG or SVG without coupling card
  declarations to the web UI, scanner hardware, or `board/`.
- `physical_cards/universal_actions.py` validates the first scanner-facing control
  cards (`accept` and `decline`). A Flask route resolves the payload but does not
  mutate game state; the browser keyboard-wedge adapter maps the resolved control
  to the same primary/secondary dispatcher used by Enter, Escape and visible
  fallback controls. `physical_cards/universal_card_sheet.py` uses Pillow and Segno
  to generate the two-page A4 duplex print sheet.
- `core/migrations.py` owns schema-neutral, sequential pure-data migrations.
  Snapshot and content loaders register explicit `vN -> vN+1` transforms and
  never silently skip an unknown version.
- `scenarios/content_contract.py` owns content headers, stable-id syntax and
  source-pack metadata, while `scenarios/content_audit.py` validates the whole
  repository catalog through the same scenario loader used by runtime.
- `character_creation/` owns deterministic, single-class character drafts,
  choice validation and construction of the shared `Actor` model. File-backed
  catalog loading is an adapter in that package; the builder itself does not
  depend on Flask, board hardware, Gemini, files or real time. Saved-character
  documents persist source choices and rebuild derived statistics instead of
  storing a second mutable copy of them. Caster drafts keep learned/spellbook
  spells separate from prepared spells, and subclass definitions contribute
  proficiencies, runtime feature grants and always-prepared spells without
  branching in the UI. `character_creation/roster.py` is the file-backed edge:
  it performs atomic record writes, rejects unsafe or duplicate ids, rebuilds
  actors while scanning, isolates incompatible records, and uses a recoverable
  local trash directory. Flask routes translate form fields to `CharacterDraft`
  but never calculate derived character rules.

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

- the web root is an application launcher rather than an implicit game start.
  `/new-game`, `/load-game` and `/characters` are separate player flows, while
  `/play` hosts the existing board-first scenario runtime. Starting a new game
  resets the active scenario before entering `/play`; loading delegates to the
  versioned snapshot reader before redirecting there. The character entry
  screen reads the versioned character catalogue and never duplicates its
  species, class or background lists in presentation code,
- `application/exploration_flow.py` owns deterministic exploration flow transitions,
- `application/exploration_action_sources.py` projects party resources, inventory,
  weapons, tools and spell metadata into one capability-tagged source contract.
  Authored goals filter that contract before the free-form method description; the
  engine remains authoritative for ownership, availability, modifiers, spell costs
  and consequence tags. Persistent preparations are scene flags and guarded flow
  nodes (the reference implementation is the watchtower climbing rope).
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
- `application/effect_boundary_flow.py` owns condition transitions across exploration,
  combat, rest and scenario boundaries. Encounter entry filters exploration conditions
  through `start_combat`; encounter exit expires local durations, removes invalid grapples,
  and returns every still-valid condition for persistent party actors. Rest and scenario
  events use the same `EffectEvent` lifecycle instead of UI-specific cleanup,
- `exploration/traps.py` owns pure trap-state transitions and action outcomes; detection
  may come from an authored observation or the shared awareness evaluator, while
  activation delegates to the hazard flow,
- `exploration/awareness.py` owns active zone Search, passive trap detection and
  persistent zone-scoped Hide totals. UI gathers physical d20 input and applies
  light-based roll modes; encounter setup translates stored Hide totals into the
  existing per-observer precombat stealth contract,
- `exploration/fixture_actions.py` owns persistent doors, locks, containers and
  destructible scene fixtures. It resolves authored state transitions, HP and
  damage thresholds, releases contained items, and projects the current
  exploration state into combat `SceneObject`s for movement and cover,
- `exploration/travel.py` owns deterministic overland pace, navigation and
  forced-march resolution. It consumes explicit physical d20 input and returns
  updated actors plus timing metadata; UI only gathers choices and rolls,
- `application/spell_preparation_flow.py` owns the pre-scenario confirmation sequence for
  actors with generic prepared-spell profiles,
- `application/short_rest_flow.py` owns content-driven short-rest preview, completion,
  exploration consequences, and sequential Hit Dice spending,
- `application/scenario_continuation_flow.py` validates content-authored exits between
  scenarios from deterministic flags and the current departure zone. The UI advances
  the pace-adjusted travel duration and navigation delay, resolves forced march, then
  selects an ordered success/partial-success/fail-forward outcome from the final flags
  and navigation result. The verified handoff contains source objective results,
  explicitly propagated flags and validated target effects. The UI expires
  scenario-scoped effects and saves the complete source snapshot before exposing the
  target. The current local runtime can immediately start that target and merges
  same-id party actors through `merge_handoff_actor`: target content owns static
  capabilities, proficiencies, spells and canonical loadout, while mutable HP,
  currency, counters, preparation and acquired inventory come from the source.
  A future campaign save may replace this bridge with canonical character records,
- `application/combat_movement_flow.py` owns player movement planning, movement application,
  and opportunity-attack threat detection before reactions are resolved,
- `combat/attack_flow.py` owns the explicit melee-reach versus ranged-range contract;
  targeting, opportunity threats, enemy positioning, and UI payloads consume that contract,
- `combat/class_features.py` owns executable level-1 class mechanics shared by
  authored and custom actors. Second Wind spends the existing bonus-action and
  short-rest resource contracts; Sneak Attack produces an independently typed
  damage component and an until-next-turn usage marker. `combat/fighting_styles.py`
  applies style-specific attack transformations, while Defense and Two-Weapon
  Fighting reuse their existing armor and off-hand rule boundaries,
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
  state. The LLM classifies and may narrate an interaction, while content permissions
  select success/failure state updates. Guarded NPC prompts contain only the active
  goal and permission; a critical goal can additionally define a hidden
  `grounded_response`, which replaces the model's visible narration after validation.
  It may contain approved equivalent variants; the LLM selects only a variant id
  and the validator copies its complete authored text, falling back to the base
  response for a missing or unknown id.
  This keeps quest facts, rewards, items and currency transfers content-authoritative;
  guarded routes omit private GM context, hidden key issues and still-locked
  information from the model prompt. If an interaction reveals authored information,
  runtime replaces generated prose with the exact authorized facts so semantic
  spoilers cannot bypass id validation.
  conversation history and NPC state remain separate persisted concerns.
  `exploration/social_interactions.py` maps current
  NPC attitude and content-classified request risk to the deterministic 2014
  conversation reaction threshold; the LLM cannot choose this DC. Both are
  separate persisted inputs to later interactions. `exploration/npc_state.py`
  also plans content-limited NPC attempts from persisted relationship events
  and current scene flags; the UI cannot consume an attempt before a roll.
- exploration zones may reference a `PaperMap` stored under the shared game
  assets. Initial setup and every zone change pause in `PARTY_SETUP` until the
  players confirm that the 50×75 cm printed map is physically placed. Only then
  does the UI queue NPC placement, passive traps and other zone setup.
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
- `actors/senses.py` owns typed creature sense ranges, while
  `exploration/visibility.py` combines them with zone ambient light and active
  party light. The evaluator is deterministic and returns sight availability,
  Perception roll mode and passive-Perception adjustment; UI and scenario content
  consume that result instead of inferring visibility from narration,
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
Feature-driven d20 behavior lives in `rules/d20_traits.py`. Callers provide the
actor, roll kind and semantic save tags; the rule returns a transformed request.
Halfling Lucky is represented as an explicit natural-one reroll contract, so a
physical roll remains player input and the result preserves both the original
and replacement dice.
Background features grant stable permission IDs through ordinary `FeatureGrant`
action IDs. `rules/background_features.py` requires both an owned grant and an
authored scene opportunity; the GM classifier can select a permission only when
both sides of that contract are present. It cannot invent rank, contacts,
shelter or research access.

Prepared-spell membership is deterministic actor domain state in
`actors/spell_preparation.py`. Scenario content supplies the available list and preparation
limit; neither the actor model nor the application flow infers a character class. Combat and
exploration resolvers consult the same profile before consuming a spell slot.
Versioned definitions under `content/spells/` are the single source for spell metadata and
their attack, healing or combat-action effect. `rules/spellcasting.py` owns the content-neutral
schema, prepared/known/spellbook access profiles, cast-level selection and V/S/M validation;
`scenarios/loader.py` adapts the effect to the existing combat pipeline.
Per-slot and cantrip-tier scaling remain data in `SpellDefinition` and are applied by generic
attack/healing source transformers before prompting for physical dice. Actor `level` is
authoritative for the cantrip thresholds 5/11/17; healing definitions may bind a caster
ability modifier instead of storing a character-specific constant. `application/ritual_casting_flow.py`
owns exploration ritual execution: access and components are validated through the same
casting rules, normal casting time gains ten minutes, and no spell slot is consumed.
`exploration/magic_effects.py` owns the shared minute-based lifecycle for persistent
exploration magic. Rituals register typed effects there, while crafting, rests and armor
changes advance the same clock; expiry removes the effect and clears its authoritative flag.
The same pure transition evaluates ordered `ScenarioClockPolicy` thresholds and applies each
authored effect once, using a persisted internal marker flag. UI call sites only present the
returned event notices and never decide which consequence occurs.
`exploration/downtime.py` owns formal, location-bound crafting performed over full workdays.
It validates the recipe, actor tool proficiency, owned tools and material budget, then returns
a permanent inventory result and an explicit time cost. Scenario content chooses available
recipes and workshops; the UI advances the existing scenario clock rather than maintaining a
second downtime calendar. This is intentionally separate from temporary, property-based scene
crafting.
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
