# TODO

## Setup

- [x] Remove the obsolete previous application from the active tree after the
  D&D 5e rebuild became self-contained; retain recoverability through Git history.
- [x] Keep low-level board communication in root `board/`.
- [x] Add rebuild documentation and Codex working rules.
- [x] Add package structure for the new D&D 5e application.
- [x] Add local rules decision document for implemented D&D mechanics.
- [x] Add project roadmap with implementation milestones.

## Current Roadmap Focus

Master kolejności znajduje się w `ROADMAP.md`. Aktualny stan rodzin zasad jest
prowadzony w `docs/DND_IMPLEMENTATION_MATRIX.md`. Ta sekcja powinna zawierać tylko
najbliższy horyzont, a nie kopię całej roadmapy.

- [x] Replace the historical milestone roadmap with the mechanics-first master roadmap.
- [x] Add a living D&D implementation matrix separating stable MVP, partial, fixture, and missing systems.
- [x] Lock the first full release rules baseline to D&D 5e 2014.
- [x] Decide and document the SRD 5.1 CC BY 4.0/source-pack strategy for the target 2014 content catalog.
- [x] Define schema versions, stable content ids, sequential migration rules, and a repository content audit.
- [x] Start M6 with coin denominations, item value/weight, Strength-based carrying capacity, generic corpse/container loot bundles, and selective combat looting of whole bundles, item stacks, or currency.
- [x] Add typed ammunition stacks, per-attack consumption for player/AI/reactions, empty-ammo blocking, crossbow `loading`, UI counts, lootable bolts, and snapshot v4 migration.
- [x] Recover half of party-fired ammunition after victory as persistent battlefield loot, with UI collection and snapshot v5 migration.
- [x] Add partial combat-loot selection for item stacks, recovered ammunition, and individual coin denominations, with live mass/capacity preview and atomic transfer validation.
- [x] Add scenario-defined merchants with deterministic partial buy/sell transactions, buyback prices, wallet/carrying-capacity validation, web UI previews, and snapshot v6 persistence.
- [x] Add light, medium, and heavy body armor with 2014 AC formulas, Strength speed penalties, Stealth disadvantage, exploration don/doff time, merchant content, and snapshot v7 persistence.
- [x] Add generic item charges with action costs, depletion blocking, deterministic short/long-rest recovery, UI counts, a reference binding wand, and snapshot v8 persistence.
- [x] Add D&D 5e 2014 item attunement with a three-item limit, one change per actor during short rest, power gating, UI selection, encounter persistence, and snapshot v9.
- [x] Close M6 with composable passive magic-item effects for AC, saves, checks, attacks, and speed; add an attunement-gated reference amulet, UI disclosure, and snapshot v10.
- [x] Add the complete 37-weapon SRD 5.1 catalog under one typed schema, category proficiency, dynamic ability damage, finesse choices, thrown recovery, normal/long range, heavy, reach, loading, ammunition hand requirements, lance/net rules, UI disclosure, content audit, and snapshot v11.
- [x] Complete mundane equipment before M7 with all 12 body armors, 144 SRD adventuring-gear/focus/tool/pack definitions, typed containers, light/fuel, utility checks, durability, pack expansion, merchant/UI integration, content audit, and snapshot v12.
- [x] Start M7 with a versioned `SpellDefinition` schema, spell refs as the single source for existing fixture effects, prepared/known/spellbook access profiles, V/S/M and focus validation, costly/consumed materials, cast-at-level slot selection, casting-time action costs, UI metadata, and snapshot v13.
- [x] Add M7.2 data-driven damage/healing scaling per slot level, an explicit higher-slot UI flow, exploration ritual casting with access/component validation, +10 minute time cost, no slot consumption, a utility ritual fixture, and snapshot v14.
- [x] Add M7.3 shared minute-based lifecycle for exploration magic, automatic expiry through ritual/crafting/rest/armor time advances, refresh semantics, UI disclosure, expiration notices, and snapshot v15.
- [x] Add M7.4 target-count upcasting with explicit slot selection, bounded multi-target selection in UI/board flow, grouped concentration effects, and a three-target Bless fixture gaining one target per higher slot.
- [x] Add M7.5 defensive spell reactions with a post-hit/pre-damage interrupt, shared reaction and slot consumption, persistent AC effects, expiry at the caster's next turn start, and a data-driven Shield fixture.
- [x] Add M7.6 Counterspell with a pre-resolution enemy-spell interrupt, 60-foot line-of-sight eligibility, reaction and selected-slot consumption, automatic same/lower-level interruption, a manual spellcasting-ability check for stronger spells, and shared UI/board resumption.
- [x] Add M7.7 interruptible long casting with one action per turn, transient concentration, damage checks, missed-action/cancel/defeat interruption, deferred slot/component consumption, UI progress, a data-driven reference ward, and snapshot v16.
- [x] Add M7.8 data-driven concentration summons with board/LOS placement, dynamic allied actors, owner-adjacent initiative, independent attacks, automatic dismissal, UI/LED flow, and snapshot v17.
- [x] Add M7.9 data-driven spell movement with visible free-tile teleportation, save-based push/pull, obstacle-aware final positions, no movement-cost/opportunity triggers, UI/LED selection, and project-original fixtures.
- [x] Add M7.10 generic save-first spell debuffs with shared condition state, automatic enemy saves, repeated saves at authored timing, UI/LED target selection, and project-original Poisoned/Restrained fixtures.
- [x] Close M7.11 with generic creature-targeted spell dispelling, automatic same/lower-level removal, physical spellcasting-ability checks for stronger effects, shared ActiveEffect/ConditionState provenance, summon dismissal, UI/LED flow, and snapshot v18.
- [x] Add M7.12's first executable SRD spell-content tranche (Sacred Flame, Healing Word, Fire Bolt, Burning Hands, Cure Wounds, and Inflict Wounds), character-level cantrip scaling at 5/11/17, spell-attack proficiency, caster-ability healing, reference-scenario preparation, and snapshot v19.
- [x] Start M8 by auditing its already-complete foundations and migrating the terminal exploration harness to authoritative guarded flow routes.
- [x] Add M8.2 guarded NPC flow for `village_square_mvp`: explicit information/reward goals, state-gated negotiation, terminal refusal state, shared planner/UI payload, and regression coverage.
- [x] Add M8.3 guarded tavern-keeper flow for `village_square_mvp`: migrate the legacy rumor option to Olan's NPC interaction, apply the authored quest hook, hide the consumed rumor goal, and keep ordinary conversation available.
- [x] Add M8.4 village quest lifecycle and authored scenario continuation: separate hook/acceptance/readiness flags, gate departure by state and location, validate the watchtower target, expose objective progress in UI, and save a source-scene handoff snapshot.
- [x] Add M8.5 scenario time and delay consequences: data-driven clock thresholds, travel/conversation/rest costs, one-shot effects and narration, visible time of day, and timed watchtower handoff metadata.
- [x] Add M8.6 exploration visibility: typed ambient light and actor senses, darkvision/blindsight/truesight evaluation, sight-based observations, dim-light Perception disadvantage/passive -5, darkness blocking, party light ranges and burn time, precombat Stealth integration, UI disclosure, and snapshot v20.
- [x] Add M8.7 exploration awareness: active zone Search with time and light rules, passive trap detection, typed trap detection DC/range, persistent zone Hide totals, reveal-on-light/time/travel, encounter stealth handoff, UI controls, and snapshot v21.
- [x] Add M8.8 interactive exploration fixtures: typed doors, locks and containers; local unlock/open/close/loot flows; object AC, HP and damage thresholds; persistent state, combat movement/cover projection, UI controls, reference content, and snapshot v22.
- [x] Add M8.9 overland travel: fast/normal/slow pace, authored navigation checks and fail-forward delay, forced-march Constitution saves, six exhaustion levels shared by exploration/combat/resting, village-to-watchtower UI handoff, and snapshot v23.
- [x] Audit Brakka's combat identity: apply 60-foot darkvision to nonmagical combat darkness, keep Relentless Endurance as an automatic first-drop long-rest resource, replace the restraint flaw with Rage-time active-equipment blocking, enforce Frenzy's next-turn timing, and regenerate color/toner card sets.
- [x] Close M8.10 social interaction rules: persistent NPC state and attitude, deterministic 2014 reaction thresholds, authored retries/outcomes/transitions, visible stakes, and player-authoritative Persuasion/Deception/Intimidation selection.
- [x] Add M8.11 formal downtime crafting: location-bound data-driven recipes, tool ownership and proficiency, half-price materials, 5 gp workdays, permanent inventory results, shared-clock consequences, and player confirmation.
- [x] Add M8.12 shared condition boundaries: exploration hazards can author persistent Poisoned/Restrained states with source and duration; conditions enter combat, return to exploration, and expire consistently on encounter, rest, long-rest, and scenario events.
- [x] Close M8.13 with ordered continuation outcomes: success, partial success and fail-forward branches can depend on final flags/navigation, carry selected flags, emit validated target effects and summarize source objectives in the verified handoff.
- [x] Harden the M8 village playtest UI: expose authored zone options, show objective milestones, make NPC setup/location messages generic, avoid repeated dialogue intros, and replace continuation prompts/raw ids with an in-page Polish travel form and friendly scenario names.
- [x] Ground generative NPC narration against authored facts and effects: scope prompts to the active goal/permission and let critical routes enforce hidden content-authored narration so Gemini cannot invent quest evidence, rewards, purchases, or currency transfers.
- [x] Add controlled authored paraphrases for guarded NPC routes: Gemini selects an approved variant id matching the player's tone, while validation copies the complete variant and safely falls back to the base response.
- [x] [Spell fidelity] Add creature-type healing exclusions for undead/constructs and an explicit unattended-flammable-object rider for Fire Bolt.
- [x] Replace character-creator standard-array-only input with D&D 5e 2014 27-point buy, show base score/cost/origin bonus/final modifier separately, and add audited Polish tooltips for every level-1 class feature.
- [x] Rebuild class choices as a guided player step with skill use/proficiency explanations, fighting-style rule cards, automatic expanded starting packages, origin-skill conflict prevention, and a final live character-sheet review.
- [ ] [Deferred character creator] Add an optional starting-wealth mode with class-specific wealth generation, a restricted pre-game shop, affordability/carrying-capacity checks, and an explicit choice between wealth and the automatic class package.
- [ ] [Deferred subclass expansion] Add real multi-option subclass branches and
  corresponding level-up card pools only from a registered lawful source pack;
  do not source catalogue text or definitions directly from the Player's
  Handbook. If no additional licensed pack is established, author
  `project_original` subclasses with original names, descriptions and mechanics,
  then cover their grants with runtime resolvers, Polish help, audits and focused
  tests.
- [ ] [Deferred mounted combat] Let a mounted wielder use a lance in one hand; until an explicit mounted actor state exists, the lance correctly uses two hands and retains its close-range disadvantage.
- [ ] [Deferred destructible equipment] Model the net as an AC 10 object with 5 HP that can be cut using slashing damage; Strength DC 10 escape is implemented.
- [ ] [Deferred attunement fidelity] End attunement automatically after the official distance/time, death, prerequisite-loss, or another-creature-attunement conditions.
- [x] Add the versioned material-property catalog and schemas for item definitions, item instances, and scene fixtures.
- [x] Add a unified crafting-source registry for zone items, fixtures, exploration resources, and party inventory.
- [x] Add deterministic property-based crafting drafts, component validation, allocation, dismantling, and engine-owned costs.
- [x] Integrate property-based crafting with the GM classifier and chat confirmation, without a default build roll.
- [x] Close the exploration MVP with a chat-first GM, grounded scene answers, progressive hints, and persisted reveal context.
- [x] Give LLM narration a lively D&D table voice and resolve absurd-but-possible declarations as policy-limited world actions with immediate fictional consequences.
- [x] Drop no-op LLM situational modifiers so descriptive details such as loud actions do not reject otherwise valid declarations.
- [x] Add persistent NpcRuntimeState with attitude, physical/emotional state, revealed information, used attempts, relationship events, content-driven updates, UI, LLM context, and snapshot compatibility.
- [x] Add filterable slash-command intent hints to the exploration chat while preserving automatic intent detection.
- [x] Unify player questions and progressive hint requests under `/pytaj`; infer hint strength from message content.
- [x] Add deterministic graded observations that reveal cumulative scene facts without advancing the active challenge.
- [x] Add goal-scoped contextual searches: semantic no-roll material lookup, graded hidden discoveries, preselected observers, and flag-driven follow-up cards.
- [x] Separate free GM conversation from goal actions and route known scene-item uses through authored procedural source actions.
- [x] Add the first guarded exploration flow-graph vertical slice and migrate the watchtower gate's goal availability and routing.
- [x] Make authored flow options authoritative for check mechanics and accept a reduced LLM method-only contract on migrated routes.
- [x] Add one pre-declaration exploration source contract for resources, tools, items, weapons and spells; filter sources by capability tags, keep ownership/cost/modifier/consequence resolution deterministic, and add the watchtower rope setup-to-persistent-route reference flow.
- [ ] Migrate remaining exploration/NPC scenes to guarded flow graphs and reduce the LLM contract to route selection plus grounded method details.
  - [x] Revalidate the selected goal against its currently active graph transition, with participant choice made before the method description and roll.
  - [x] Extract goal, participant, observation and procedural-source planning from `ExplorationUiSession` into an application service and remove duplicated gate routing fields.
  - [x] Migrate the wounded scout to an NPC-owned flow with authored intent routing and pre-declaration participant selection.
  - [x] Migrate the legacy `demo_exploration_scene` freeform harness from tag-based goal inference to explicit flow routes, then update its watchtower regression cases.
  - [x] Migrate village elder Bren to an NPC-owned flow with quest-state and refusal-state gating.
- [x] Route authored observation intents before generic challenge classification and ground numeric DCs to content tiers.
- [x] Replace the gate's predefined approach/risk lists with structured guidance facts and update the interaction form.
- [x] Give `/szukaj` an exact-first and semantic-fallback flow with player-confirmed substitutes and persisted scene findings.
- [x] Give `/użyj` explicit source resolution, deterministic source binding, and a property/risk preview for scene-item use.
- [x] Normalize actor-inventory source ids selected by `/użyj` before exploration resource validation.
- [x] Add explicit take/collect policies for portable findings, quest items, and treasure without conflating search with inventory transfer.
- [x] Let detachable scene fixtures be acquired during confirmed crafting instead of requiring an unavailable technical detachment command.
- [x] Ground actor-inventory items in generated exploration checks and restrict the test leader to an actor who owns the item.
- [x] Route visible-source searches and immediate improvised use before observation/crafting, with player-facing validation messages.
- [x] Carry exact reconnaissance into a one-use initiative advantage for its observer in the matching encounter.
- [x] Keep the wounded scout hidden until the gate encounter is won instead of revealing it when the gate opens.
- [x] Add a scenario-driven encounter-opening stage with initiative disadvantage for the surprised side.
- [x] Bridge scenario-driven quiet encounter openings into optional per-character Stealth vs passive Perception before initiative.
- [x] Split critical gate openings into independent party-wide initiative advantage and precombat Hide opportunities for force, lock-and-bolt, and wall routes.
- [ ] [Deferred rules fidelity] Replace side-wide initiative disadvantage with the full per-creature D&D 5e 2014 surprised condition when a scenario needs exact rules fidelity.
- [x] Replace text-only exploration materials and predefined temporary-item templates with deterministic property-based crafting.
- [x] Persist component reservations and dynamically crafted temporary items in scenario snapshots.
- [x] Persist runtime fixture state changes once fixture detachment and destruction actions are implemented.
- [x] Migrate the watchtower gate as the reference fixture/crafting interaction after the generic runtime is ready.
- [x] Unify effect source, duration, expiration, stacking, and replacement contracts.
- [x] Add generic actor resources with short-rest and long-rest recovery policies.
- [x] Implement automatic pre-scenario long rest and content-driven short rest independently from classes.
- [x] Extend the duration/recovery model with scenario-end expiration and recovery policies.
- [x] Add a versioned actor/scenario snapshot and deterministic round-trip test.
- [x] Add actor life states at 0 HP, death saves, stabilization, massive damage, and recovery through healing.
- [x] Add unconscious attack consequences and combat stabilization with Medicine or a healer's kit.
- [x] Represent equipped weapons dropped at 0 HP as scene-positioned combat objects persisted in snapshots.
- [x] Add contextual combat field/self-action menus for overlapping field intents with arrow/Enter/Escape control.
- [x] Add compound approach-and-interact plans with path cost, range validation, and opportunity-attack interruption.
- [x] Route the watchtower cart and rubble through contextual combat interactions while keeping the fallen gate non-interactive.
- [x] Implement dropped-weapon pickup as the first inventory interaction using the contextual field menu.
- [x] Add explicit equip/swap/drop weapon actions to the self-action equipment menu.
- [x] Add geometric projectile cover and ranged-attack-in-melee disadvantage with visible combat previews.
- [x] Add D&D 5e 2014 Hide/Search with per-observer detection, passive Perception, movement/attack reveal, and enemy Search.
- [x] Replace Mira's interrogation flaw with session-scoped `Panika po zdemaskowaniu`: visible enemies gain `+2` to attack rolls until Mira ends stealth or every active enemy detects her.
- [x] Add a shared combat condition state and D&D 5e 2014 Prone rules for movement, attacks, AI, UI, and snapshots.
- [x] Complete the actor proficiency-profile vertical slice for skills, expertise, saves, weapons, armor, and tools.
- [x] Add tool proficiency checks and a generic opposed-check resolver as groundwork for Grapple and Shove.
- [x] Implement D&D 5e 2014 Shove with Athletics contest, prone/push modes, forced movement validation, and combat UI.
- [x] Implement D&D 5e 2014 Grapple with sourced condition state, escape action, zero target speed, dragging, snapshots, and combat UI.
- [x] Enable D&D 5e 2014 optional flanking by default for player and enemy melee attacks, with visible advantage context.
- [x] Add creature-size categories with Medium defaults, content/snapshot/UI support, and D&D 5e size eligibility for Grapple and Shove while keeping all actors one-tile.
- [x] Add a grouped contextual combat action catalog with every legal weapon source, maneuvers, spells, support actions, and content-defined targeted item actions.
- [x] Add explicit main/off-hand slots, one- and two-handed equipment plans, visible hand occupancy, and free-hand validation for Grapple.
- [x] Add D&D 5e 2014 two-weapon bonus-action rules with light melee weapon validation, a per-turn trigger, visible contextual UI, bonus-action consumption, and off-hand damage rules.
- [x] Add D&D 5e 2014 versatile-weapon attack variants that require a free second hand and expose the stronger damage die in combat UI.
- [x] Add shields as held equipment with don/doff action cost, proficiency validation, effective AC, hand conflicts, UI, content, and snapshots.
- [x] Add typed damage components with D&D 5e 2014 resistance, immunity, vulnerability, content/snapshot support, and visible damage breakdowns.
- [x] Add compatible `NdM` and multi-component attack damage content, including
  per-component manual player input, automatic enemy rolls, critical dice doubling,
  per-type affinity resolution, area spells, Ready attacks, and opportunity attacks.
- [x] Add a shared ordered reaction window and migrate Ready plus manual/automatic
  opportunity attacks to one pause, advancement, skip, and resume contract.
- [x] Unify saving-throw requests/results and add enemy effects that pause for a physical player d20 before applying save-adjusted typed damage.
- [x] Add data-driven exploration hazards triggered by failed checks, with a visible physical saving throw and save-adjusted typed damage.
- [x] Add save-dependent exploration hazard effects, persistent actor conditions, snapshot support, and an exploration-to-combat condition bridge.
- [x] Add the M5 condition-engine vertical slice with Poisoned, Restrained, condition immunities, timed expiry, repeated turn-boundary saves, UI, content, and snapshots.
- [x] Add data-driven actor auras with dynamic position coverage, non-stacking save modifiers, defeated-source shutdown, UI visibility, and snapshot support.
- [x] Add the first data-driven trigger-engine vertical slice with shared event ids, deterministic turn-boundary activation, `grant_temp_hp`, UI logs, content validation, and snapshots.
- [x] Connect the shared trigger engine to attack-hit, damage-taken, movement, rest, and encounter-end emitters, including reactions, forced movement, and exploration hazards.
- [x] Add resource-backed limited attacks with short/long-rest recovery, deterministic monster Recharge rolls at turn start, UI availability/logs, content validation, and snapshots.
- [x] Close M5 with versioned FeatureDefinition/FeatureGrant composition for resources, actions, triggers, and auras, including provenance, collision validation, UI, snapshots, and two content fixtures.
- [x] Add data-driven exploration traps with detection, disarm/bypass/trigger actions, hazard activation, snapshots, and an alarm-wire reference fixture.
- [x] Close the combat turn-economy MVP with explicit action costs, data-driven Use an Object, separate draw/stow interactions, and visible UI costs.
- [x] Define the board-first player UI direction, target exploration/combat/NPC views, information hierarchy, and edge cases in `docs/PLAYER_UI_DESIGN.md`.
- [x] UI-1: Add the shared player shell and visual tokens; move hardware configuration and debug surfaces out of the normal player flow.
- [x] UI-2: Rework exploration and NPC presentation around one stateful full-screen chat without duplicated trial/result cards.
- [x] Make tall interaction composers scrollable and give every watchtower gate goal a responsive illustrated tile.
- [x] UI-3: Rework encounter setup and combat around a compact turn HUD, board-context menus, and one preview/roll/result flow without a digital map.
- [x] UI-4: Add on-demand character/state/spell/inventory drawers, information-overload priorities, keyboard navigation, and disconnected-board fallback.
- [x] Add the smooth-play runtime contract: revision-safe automatic board listening,
  one active chat step, automatic deterministic advances, non-blocking Gemini
  feedback, redundant-frame suppression, and contextual projectile animation.
- [x] [Hardware scan reliability] Apply idle recovery inside bounded hardware scans,
  reset the listener after a final timeout, and persist the timeout reason in session
  observations instead of leaving an unmatched scan-start event.
- [x] [Hardware scan reliability] Preserve the firmware STOP acknowledgement during a
  soft reset so a cancelled scan releases its lock before the next combat turn, and
  normalize keyboard-wedge `?` underscores in the browser before card validation.
- [x] [Hardware scan reliability] Ignore delayed acknowledgements of the defensive
  pre-scan STOP while still honoring explicit scan cancellation, so a newly armed
  hardware scan cannot terminate before the player presses a field.
- [x] [Hardware scan reliability] Release a cancelled serial scan locally without
  requiring a firmware STOP acknowledgement, and wait for that request to finish
  before the browser arms the next board revision.
- [x] [Combat action preview responsiveness] Debounce Numpad action changes,
  update the highlighted row optimistically, refresh LED previews without waiting
  for the obsolete scan, tint action sections, and keep the 5×4 hero start zone whole.
- [x] [Combat action list stability] Update only the selected action row during
  Numpad preview changes and keep scrolling inside the list, avoiding full-screen
  rerenders and page-level scroll flashes.
- [x] [Enemy attack result acknowledgement] Keep hit, damage, HP and effect results
  visible after board confirmation until the players explicitly acknowledge them.
- [x] [Combat preview scan handoff] Keep Numpad preview changes optimistic, but wait
  for the obsolete hardware scan to release its lock before arming the selected
  movement or ranged-attack revision.
- [x] [Board shutdown safety] Send the all-LEDs-off command and close the board
  transport when the exploration runtime exits, including terminal Ctrl+C.
- [x] [Area preview and scan lifecycle] Limit Spike Growth center placement to
  50 feet, retain dim legal centers under the stronger selected spell area,
  allow repeated repositioning before Enter, and centrally re-arm cancelled scans.
- [x] [Combat action section order] Keep movement first, followed by weapon
  attacks, hero abilities, spells, equipment, maneuvers and basic actions.
- [x] [Black Ford aftermath] Keep the battlemap active after the Hungry Shadows,
  reveal the wagon, tracks, Teren, young beast and route choice, gate departure
  on their fail-forward outcomes, and provide a working Map 2 entry handoff.
- [x] [Simple scenario continuation] Replace pace, navigator and travel-roll
  selection with one fixed-duration handoff confirmation.
- [x] Replace the fixed 2×4 hotspot grid with the visible continuation composer as soon
  as its board tile is selected, instead of hiding the composer below a clipped grid
  while board listening is intentionally paused.
- [x] Show player-visible mechanical rules for every highlighted environment group
  during encounter setup, including difficult terrain, cover, blockers and interactions.
- [x] Make universal ACCEPT trigger the sole visible forward action and replace
  spell hand-juggling restrictions with explicit hands-bound, gagged and Silence states.
- [x] Add passive board focus for physically placed initiative/Stealth actors and exploration objects, without treating exploration party members or NPCs as separate board pieces.
- [x] Move prepared-spell selection to the final initial-setup step before first-location selection.
- [ ] UI-5: Validate the complete board-first UI vertical slice with `abandoned_watchtower` and the manual hardware checklist.
- [ ] [Post-scenario control experiment] After completing the first target
  scenario, playtest an optional LED-only board mode without figurine detection:
  keep LEDs as spatial output, use the numpad/UI for declared positions and
  confirmations, provide fast position correction, and compare reliability,
  pace and player experience against the scanner-driven mode before deciding
  whether detection remains required or becomes an optional enhancement.
- [ ] P1: After the first target scenario, add the physical player-interface vertical
  slice: a player-maintained A4/A5 character sheet updated through level-up, printable
  illustrated decision cards with stable QR ids, a scanner input adapter, shared
  action-catalog validation, and board-based spatial targeting. Hero identity has no
  screen or board fallback; recovery may retry, reconnect, cancel, or return to menu.
  - [x] Add the versioned decision-card QR payload and deterministic PNG/SVG generator
    with printable quiet zones, metadata sidecars, and focused unit tests.
  - [x] Add the first duplex A4 control-card batch (`ACCEPT`/`DECLINE`) with real
    QR payloads, poker-size trim, bleed, crop marks, mirrored backs, and a manifest.
  - [x] Replace the flat control-card art with image-generated heroic dark-fantasy
    front and back backgrounds while keeping text and QR layers deterministic.
  - [x] Add the browser keyboard-wedge scanner adapter and route universal control
    cards through the existing context-sensitive primary/secondary UI actions.
  - [x] Make `ACCEPT` start a ready session and confirm instruction-only setup
    steps before considering an optional board-scan button.
  - [x] Normalize the keyboard-wedge scanner's observed `>` separator output to
    canonical `:` payloads in the shared card input adapter.
  - [x] Remove redundant physical NPC-placement setup from village instances so
    selecting a city location opens its interaction tiles directly.
  - [x] Anchor duplicate physical-card suppression to response completion so one
    slow ACCEPT request cannot spill into and confirm the following UI stage.
  - [x] Replace the player-facing character creator entry with twelve level-1
    archetypes while preserving the dormant creator and player-chosen legal level-up
    choices through level 3.
  - [x] Add player-facing histories, motivations, personal goals, turn guidance,
    resources, strengths, and pitfalls for every starter archetype.
  - [x] Refresh all twelve starter portraits as a versioned, comic dark-fantasy set.
  - [x] Add stable `dndbg:v1:actor:<actor_id>` hero-card payloads and use scans as
    the exclusive party-selection and exploration check-participant input.
  - [x] Generate the twelve-card duplex poker-size A4 hero set with real QR codes,
    bleed, crop marks, mirrored backs, previews, and a machine-readable manifest.
  - [x] Generate the first complete character-specific card sets for Garran and
    Dagna through level 3, with unique themed art treatments, stable QR payloads,
    concise mechanics, level requirements, duplex backs, and narrative dossiers.
  - [x] Extend the class-themed card sets to all twelve starter heroes and add a
    printable level-1 statistics, saves, proficiencies, spell, and equipment page
    to every character PDF.
  - [x] Audit all level 0–2 class spells: keep combat damage/status effects
    executable and record narrative-fidelity follow-ups without disabling combat magic.
  - [ ] Extend hero-card participant declarations to any remaining combat/support
    prompts that still introduce a separate choice of acting hero.
- [x] Fix the pre-combat Stealth transition renderer after encounter setup confirmation.
- [x] Remove physical-card gating from the New Game launcher and restore on-screen party and scenario confirmation.
- [x] Keep exploration numpad actions on stable board-backed numbers and restore readable, uncropped action tiles in the NPC workspace.
- [x] Reserve Numpad 0 as the visible, stable shortcut for leaving an NPC conversation.
- [x] Clarify rubble interaction targets, prioritize movement paths over object LEDs, and require visible acknowledgement of automatic enemy opportunity-attack results.
- [x] Keep combat result acknowledgements inside the combat panel, name ranged-melee threats, clarify compound movement destinations, and surface defeated-enemy results.
- [x] Keep the idle combat panel board-first by moving hero spells, common actions, equipment, and turn ending behind the active hero's board tile menu.
- [x] Render acknowledged combat results once instead of duplicating the same message across prompt, inline summary, and acknowledgement card.
- [x] Scope automatic spell-result acknowledgements to messages created by the current combat request so a previous caster's result cannot reappear during another actor's attack.
- [x] Keep exploration LEDs aligned with actual input mode: passive focus during an open interaction and selectable locations/points only after leaving it.
- [x] Add a courtyard-entry NPC placement setup, persisted selected point positions, location action cards, and passive LED focus for the physically placed wounded scout.
- [x] Add a direct courtyard-entry debug preset (including the legacy `courtyard_search` shortcut), full arrival narration, mandatory wounded-scout miniature placement, and illustrated scout/search action tiles.
- [x] Make wounded-scout intimidation a deterministic Charisma (Intimidation) check with authored outcome branches, without contradictory social-table refusal or a premature NPC response.
- [x] Add strict combat targeting after selecting an attack or spell source so movement tiles cannot steal target/area clicks, with explicit single-target and area labels.
- [x] Replace clear-then-render combat LED updates with atomic fading frames, preserve attacker/target focus during rolls, and keep the acting enemy visible through movement previews.
- [x] Clarify exploration checks by naming the tested skill and separating the rolling leader from a non-rolling helper.
- [x] Give exploration goal cards `must`/`allow` policies for D&D single, optional Help, and whole-party checks, selected before the free-form method.
- [x] Fix watchtower gate board-tile synchronization, restore a persisted hardware selection in the chat UI, log the activated target, and remove the duplicate gate-search card.
- [x] [Combat playtest] Block ending a turn with an unresolved action, expose executable spells and active class features in the board context menu, explain prepared spells from their real resolver contracts, and animate ranged projectiles across LEDs.
- [x] [Progression playtest] Award every player hero 300 XP after the gate-goblin victory, persist custom-character progress, and expose direct level-up actions in the encounter result.
- [x] Add a selectable mechanics playground with configurable training dummies, normal board-first combat setup, spell/area targets, exploration fixtures, a social-test NPC, repeatable short rests, and a one-click trial reset.
- [x] Remove the playground hotspot/location overlap and align its card tests with
  canonical level-3 archetypes, including replacement of inherited spell
  definitions by their resource-powered physical-deck variants.
- [x] Open the guild map directly into widely spaced interaction hotspots after
  paper-map acceptance, remove Nessa miniature setup, and confirm hotspot previews
  with a second click on the same board field.
- [x] Keep map hotspots widely separated while placing an entered point's action
  tiles and exit locally around that point's physical board field.
- [x] Keep automatic board listening armed during hotspot previews and enrich
  character feature lists with player-facing rules text plus runtime mechanics.
- [x] Fit the desktop New Game party/scenario selection flow into one responsive
  viewport while preserving normal document scrolling on narrow screens.
- [x] Split desktop hotspot previews and active conversations into a responsive
  two-pane workspace with a fixed 4-by-2 board-tile grid, independent dialogue
  scrolling, compact portrait/HP party HUD, and content-aware image cropping.
- [x] Execute description-free interaction goals immediately once their required
  participant/source choices are resolved, without a redundant confirmation card.
- [x] Use the compact portrait-and-HP party HUD throughout desktop exploration,
  hiding the campaign title and fitting the full party without horizontal scrolling.
- [x] Normalize the fixed keyboard-wedge scanner's `?` output back to `_` for
  every D&D board-game QR signature, including owned action cards.
- [x] Skip redundant participant selection for actor-assigned interaction tests
  and stage social checks as actor, approach, authored description, then test preview.
- [x] Keep authored setup LEDs passive on instruction-only encounter/map steps,
  preventing false board-scan errors while retaining scans for actual placement choices.

## Completed Work And Deferred Backlog

Ta sekcja zachowuje historię dotychczasowych prac. Nie określa kolejności wykonania;
obowiązują `Current Roadmap Focus` oraz etapy z `ROADMAP.md`.

- [x] Add `.gitignore` entries for local manual test runs and session observations.
- [x] Implement session observation writer for local JSONL metadata.
- [x] Define first debug runtime command shape.
- [ ] Keep `docs/RULES_DECISIONS.md` updated when implementing each D&D mechanic.
- [x] Define `Coordinate`, board dimensions, and grid primitives.
- [x] Implement pure neighbor lookup and bounds checks.
- [x] Implement pathfinding with terrain/passability callbacks.
- [x] Add unit tests for grid and pathfinding.
- [x] Define D&D 5e dice primitives: d20 roll, advantage, disadvantage.
- [x] Define basic actor state: AC, HP, speed, ability scores, position.
- [x] Implement initiative order.
- [x] Implement basic melee/ranged attack resolution.
- [x] Implement first mini-combat turn loop.
- [x] Implement board-first turn intent flow with split movement.
- [x] Add enemy auto movement before melee attack.
- [x] Implement first playable scene with setup, objective, and interaction.
- [x] Implement exploration interactions with ability checks and scene flags.
- [x] Integrate rolled initiative into the playable scene runtime.
- [x] Add multi-option tile preview for overlapping attack and interaction choices.
- [x] Add first scene-object flags for movement, interaction while occupied, and cover.
- [x] Implement exploration mode MVP with zones and shared party position.
- [x] Add abandoned watchtower exploration scenario.
- [x] Replace binary exploration gates with progress-based `ExplorationChallenge` model.
- [x] Add fail-forward outcomes and complications for exploration challenge options.
- [x] Add MVP item/resource tags for exploration option bonuses.
- [x] Replace exploration option cycling with board menu option slots.
- [x] Show only exploration anchors by default and move full-zone LEDs to look-around mode.
- [x] Add first village exploration mini-scene with setup NPC/object points.
- [x] Allow simple exploration message options to set scene flags and complete objectives.
- [x] Add optional Groq LLM GM classifier MVP for free-form exploration declarations.
- [x] Add optional Gemini LLM provider for free-form exploration declarations.
- [x] Add LLM context layers and retry flow for rejected free-form declarations.
- [x] Add LLM declaration analyzer, prompt registry, interpretation acceptance, and challenge attempt history.
- [x] Move LLM classifier MVP policy lists into exploration challenge content.
- [x] Add local declaration thread for freeform corrections inside active exploration challenges.
- [x] Add resource/fact grounding and structured freeform action flow for challenge attempts and preparations.
- [x] Add LLM interpretation explain/reject/reclassify controls before freeform challenge resolution.
- [x] Add content-driven DC policy tiers for freeform challenge proposals.
- [x] Move general LLM vocabularies and freeform grounding terms into `content/llm`.
- [x] Remove obsolete single-step legacy GM classifier prompt.
- [x] Add folder-based scenario manifests and split `abandoned_watchtower` into smaller JSON parts.
- [x] Add interaction/object-level LLM policy when freeform interactions expand beyond challenges.
- [x] Add global LLM intent catalog in `content/llm/intent_catalog.json`.
- [x] Add global LLM effect and condition catalogs for deterministic content-driven outcomes.
- [x] Replace NPC `allowed_actions` with local `intent_permissions` based on the global intent catalog.
- [x] Add hybrid exploration goal cards, authored method tradeoffs, and first NPC key issue vertical slice for the watchtower gate and wounded scout.
- [x] Add inherited instance/goal narrative profiles with heroic D&D defaults and serious-scene overrides.
- [x] Replace the watchtower gate progress track with lock/bolt state flags, repeatable outcome branches, capped goblin alert, and a concrete weaken-structure goal.
- [x] Remove stale progress validation, LLM context, and decision UI from flag-completed gate interactions.
- [x] Keep End Turn beside combat board scanning and require acknowledgement of automatic enemy saves against player spells.
- [ ] Add grounded value/currency requirements and a guard-bribe hard-boundary fixture for NPC key-issue validation.
- [ ] Add semantic LLM key-issue classification beyond authored phrase matching, with deterministic engine validation.
- [x] Route exploration web UI NPC flags and challenge reveals through the effect executor.
- [x] Add content-driven NPC effect fields with legacy flag-change fallback.
- [x] Add per-session web UI JSONL debug logs for actions, LLM proposals, rolls, and effects.
- [x] Add web UI session log panel backed by `/api/session-log`.
- [x] Make exploration presentation fiction-first with freeform questions, optional player inspiration, and separate GM mechanics.
- [x] Integrate the exploration effect executor with NPC runtime and load-time validation for intent parameters, limits, outcome branches, and scene transitions.
- [x] Extend preparation effects with advantage/disadvantage, effect boost, unlock option, and grant resource.
- [x] Show consequence preview before accepted freeform challenge rolls.
- [x] Add second exploration challenge in abandoned watchtower and reveal first hidden NPC hook.
- [x] Add first NPC interaction MVP after exploration point reveal.
- [x] Add persistent visible NPC attitude and deterministic 2014 social reaction thresholds for content-marked intents.
- [x] Add content-driven NPC attempt limits, retry unlock flags, natural blocking, and persisted roll history.
- [x] Add structured NPC intent targets with limits, deterministic checks, four outcome branches, preview, and effect execution.
- [x] Add persisted content-driven NPC escalation stages with state-aware variants and explicit player reactions before dialogue closure or encounter start.
- [x] Add exploration check plans for actor selection, result aggregation, and consequence targets.
- [x] Add simple local web UI for exploration and LLM playtesting.
- [x] Add content-driven exploration encounter triggers and pending encounter UI.
- [x] Add guided pre-combat encounter setup steps to the exploration web UI.
- [x] Start rolled initiative and initial combat state from the exploration web UI.
- [x] Apply combat outcome effects back into exploration after an encounter.
- [x] Add MVP combat actions to the exploration web UI.
- [x] Add player combat movement to the exploration web UI.
- [x] Add Bresenham line-of-sight and MVP ranged attacks.
- [x] Add a small gate skirmish encounter for immediate ranged testing.
- [x] Improve combat UI current-step clarity.
- [x] Close D&D combat core MVP for HP, damage, defeat, and attack results.
- [x] Add explicit combat turn economy placeholders for action, bonus action, reaction, and split movement.
- [x] Add deterministic combat interactions for the broken cart with LED support.
- [x] Add data-driven combat scene interaction conditions and effects.
- [x] Add rubble combat interaction with next-attack penalty and LED support.
- [x] Add enemy Dexterity saving throw for rubble combat interaction.
- [x] Show active combat effects with clear value and expiration in the combat UI.
- [x] Add combat actor status chips for action economy and active effects.
- [x] Add Dash and Dodge player combat actions to the exploration UI.
- [x] Add Disengage player combat action as a turn-end status effect.
- [x] Add opportunity attack reaction tracking and player movement confirmation.
- [x] Add hero opportunity attack choice during enemy movement preview.
- [x] Add explicit melee reach to attack sources, legal targeting, opportunity threats, enemy positioning, UI, and reference content.
- [x] Apply half and three-quarters cover to Dexterity saves for single-target and area spells, using each effect's point of origin.
- [x] Complete area-spell MVP geometry with line width, expanding cones, line of effect, data-driven target modes, and visible friendly fire.
- [x] Add Attack action budgets, Extra Attack-ready actors, attack-replacing Shove/Grapple, split movement between attacks, and data-driven monster Multiattack.
- [x] Add combat Help action with ally advantage against a chosen target.
- [x] Add combat Ready action for prepared attacks triggered during enemy turns.
- [x] Add generic encounter conclusions for victory, defeat, objective completion, party retreat, and surrender with scenario-driven outcomes.
- [x] Add full advantage/disadvantage d20 input and resolution for combat attacks.
- [x] Add combat action sources, cleric healing, and strength potion MVP.
- [x] Add MVP spell slots and area spell targeting for combat.
- [x] Add MVP spell save DC and automatic enemy saving throws.
- [x] Show cantrip vs spell-slot sources in the gate skirmish UI.
- [x] Add MVP concentration spell with a real attack-bonus effect.
- [x] Add concentration saving throws after damage.
- [x] Add actor inventory MVP with item-backed combat actions and consumable quantity.
- [x] Add inventory and spell requirements for exploration challenge options.
- [x] Add action mechanics class hierarchy and extension guide.
- [x] Extract first combat action resolution services from exploration UI.
- [x] Extract Flask routes, frontend assets, pending UI state, session view contract, and board session adapter from exploration UI.
- [x] Extract deterministic exploration start, setup, location, travel, point-selection, and encounter-trigger flow service.
- [x] Extract player combat movement planning, direct movement application, and opportunity-threat detection service.
- [x] Extract player opportunity-attack reaction resolution from the UI session.
- [x] Extract hero opportunity/Ready attack resolution and Ready trigger detection from the UI session.
- [x] Extract Dash, Dodge, Disengage, Help, and Ready preparation flow from the UI session.
- [x] Extract enemy-turn intent planning and result classification from the UI session.
- [x] Extract enemy-result commit and combat-turn finalization from the UI session.
- [x] Extract player attack/healing source selection and single-target player attack flow.
- [x] Extract player healing resolution and area-spell targeting/damage flow.
- [x] Extract strength-potion resources and concentration lifecycle/check resolution.
- [x] Extract combat scene interactions and position-bound effect expiration.
- [x] Extract combat flow services from `ExplorationUiSession` in small contract-preserving slices.
- [x] Complete pending-state typing and remove dead compatibility helpers after combat-flow extraction.
- [x] Fix real enemy-movement Ready detection when `EnemyAutoTurnResult.enemy` already has the destination position.
- [x] Add exploration map environment setup before location selection.
- [x] Consolidate the MVP into two printable black-and-white 20×30 overview maps (village and watchtower), tiled A4 and full-size PDFs; require physical-map confirmation only when the active paper map changes.
- [x] Add authored interaction-pad pools, dynamic numbered/color-coded UI-to-LED bindings, and board-driven point/goal/zone-option selection.
- [x] [Board interaction UX] Keep the entire interaction in one chat stream: one set of actionable tiles with board badges, a compact scan control, then an explicit per-action actor choice, player description, resolution, and result.
- [x] [Board actor identity UX] Assign stable red/blue/green/purple/orange colors by new-game party order and route exploration test-performer selection through matching illuminated board pads, with screen-card fallback.
- [x] [Party decision UX] Distinguish actor-owned actions and group checks from
  `no_actor` party decisions; let automatic information requests, accepting Bren's
  quest, and confirming departure resolve without an artificial hero-selection step.
- [x] [Interaction resolution UX] Add data-driven automatic, deterministic-check, LLM-rubric, and conversation modes with none/optional/required descriptions; migrate every village/watchtower MVP interaction and bypass LLM for fully scripted challenge checks.
- [x] [Board color fidelity] Stop reordering logical RGB values before sending them to the configured WLED API, so physical LEDs, Polish color labels, and UI borders use the same palette.
- [x] [Village playtest regression] Synchronize physical board-pad selections with the chat exactly once per click, clear stale NPC presentation after board-driven transitions, keep navigation inside the chat, and disclose the authored watchtower departure gate.
- [x] Couple exploration web UI with board/simulator backend for LEDs and board clicks.
- [x] Boost LED brightness only while an active board scan is waiting for a physical click.
- [x] Add data-driven actor portraits to party, test selection, rolls, combat order, and actor-linked messages.
- [x] Add inventory/cantrip option bonuses with actor item consumption and breakage checks to exploration rolls.
- [x] Add named exploration mechanic tools for LLM-selected challenge mechanics.
- [x] Add GM correction UI for selected exploration mechanic before rolls.
- [x] Add grounded situational modifiers and advantage/disadvantage to exploration rolls.
- [x] Add improvised tool mechanic validation and explicit GM approval flow.
- [x] Add scene-scoped temporary items built from grounded materials, with visible uses, snapshot support, and scenario-end expiration.
- [x] Ground omitted temporary-item template IDs from an unambiguous challenge policy and hide technical validator fields from players.
- [x] Persist interaction-scoped exploration conversations and restore their LLM context from snapshots.
- [x] Present exploration interactions as full-screen chat instances with scene intro, typing indicator, and an explicit return to the location menu.
- [x] Add visible scene-resource effects, correction, and consumption to exploration rolls.
- [x] Replace hardcoded functional item aliases with LLM property queries and deterministic scene-source matching.
- [x] Add generic pre-scenario prepared-spell selection and runtime enforcement MVP.
- [x] [K3-K4] Add class-derived spell lists, known/spellbook/prepared profiles, and full Constitution-save modifiers for concentration.
- [ ] [Deferred product UX] Add voice input and richer UI for free-form exploration declarations.
- [x] [Content production gate S0] Add a non-overwriting component-scenario scaffold, extended asset/paper-map/interaction-pad preflight, generic print-map manifests, and a real exploration-scenario selector in New Game.
- [x] [Content production gate S0] Document the current interaction resolvers and the scaffold → author → map → audit workflow.
- [ ] [Content production gate S0] Complete the final UI-5 checklist on the physical LED board before authoring the target scenario.
- [x] [MVP playtest P0] Clear `active_point_id` when the player leaves an NPC chat so zone actions are available again.
- [x] [MVP playtest P0] Consume scenario handoff by launching the target scene and mapping party, time, inventory, resources, flags, and target effects.
- [x] [MVP playtest P0] Route an explicitly declared available spell through deterministic spell execution instead of replacing it with an LLM-selected skill check.
- [x] [MVP playtest P1] Keep critical-hit player messages consistent with doubled damage dice.
- [x] [MVP playtest P1] Preserve defeated-actor loot, currency, dropped weapons, and recoverable ammunition when combat resolves back into exploration.
- [x] [MVP playtest P1] Give the watchtower hidden cache a collectible content-backed reward.
- [x] [MVP playtest P1] Fix caught-trap status, attack-preview ammunition count, and missing village party labels/portraits.
- [x] [MVP playtest P2] Stop serializing a complete path for every reachable combat tile; send only destination/cost and expose the full path for the selected preview.
- [ ] [MVP playtest P2] Replace repeated full actor/item definitions with stable refs and paginate long UI/session histories.
- [x] [MVP playful Gemini retest P0] Merge scenario handoff actors by preserving mutable campaign state while retaining target/canonical proficiencies, tools, spells, and other static capabilities.
- [x] [MVP playful Gemini retest P0] Prevent semantic leakage of locked NPC information from generated narration, not only unauthorized `revealed_information_ids`.
- [x] [MVP playful Gemini retest P1] Replace raw LLM validation errors with a player-facing retry and do not retain rejected declarations as accepted conversation history.
- [x] [MVP playful Gemini retest P1] Restrict generated numeric situational modifiers to authored/approved modifiers instead of allowing Gemini to change roll totals.
- [x] [MVP playful Gemini retest P1] Keep outcome narration behind player acceptance and add a visible loading/retry state for 20–30 second provider latency.
- [x] [MVP reference playtest P1] Resolve zero-risk cosmetic NPC exchanges immediately without a redundant acceptance step.
- [x] [MVP reference playtest UX] Return player guidance instead of a technical error when no interaction is active, without retaining the rejected declaration in chat.
- [x] [MVP reference playtest UX] Show objectives, secured loot, and an accessible restart action on the scenario-complete screen.
- [x] [Custom-party Gemini playtest P0] Make encounter player-start setup support the actual selected party size 1–5 instead of exhausting authored template positions.
- [x] [Exploration source binding P0] Require selected action source, participant/owner, grounded `used_resource_ids`, availability, and resolved cost to describe the same deterministic resource.
- [x] [Exploration pending UX P1] Disable or redirect the action composer while an observation, trap, or hazard must be resolved so the next declaration cannot be swallowed.
- [x] [Gemini declaration robustness P1] Normalize or repair `situational_modifiers` schema retries so valid longer weapon/item descriptions do not fail on missing generated metadata.
- [x] [Combat onboarding P1] Explain why the active attack source has no legal targets and suggest movement, line-of-sight, or weapon changes.
- [x] [Exploration provider resilience P1] Add jittered retry delays and automatic stable checkpoints after completed exploration resolutions.
- [x] [Exploration fixture fidelity P2] Document challenge checks as the intentional abstraction for attacking fixtures inside authored exploration goals.
- [x] [Character creator onboarding P2] Split the long character form into a five-step guided flow while preserving server-side validation.
- [x] [Character creator UX] Keep save ids internal and generated from unique character-name slugs; replace the public portrait path with a validated local image picker and roster-owned uploads.
- [x] [Character creator origin UX] Split species, species benefits, background, and background benefits into explicit stages; expose narrative and mechanical descriptions, live final ability values, and all 13 core 2014 background archetypes.
- [x] [Character creator feature help] Add mouse, keyboard, and touch-accessible explanations for every species, ancestry-variant, and background feature; distinguish automatic, creator, action, contextual, and table-assisted execution and enforce complete help/runtime coverage with an audit.
- [x] [Polish player terminology] Replace creator-facing technical ids and English spell/tool/skill names with one audited Polish label catalogue; localize all 138 loaded spell definitions and explain gaming-set, instrument, and artisan-tool proficiency choices.
- [ ] [Background content coverage] Add authored opportunities for appropriate background permissions across future scenarios; the generic ownership-plus-scene resolver is complete, but the current reference content does not exercise every one of the 13 backgrounds.
- [ ] [Deferred character art] Generate and integrate consistent class/species reference illustrations after the creator mechanics and content are final.
- [x] [Starter roster] Add, validate, and install one playable level-1 default build for every core class, with persistent portraits and Polish explanatory character cards.
- [x] [Village tavern] Replace the dice-game placeholder with a replayable physical-d20 gaming-set check, a real wager/payout, elapsed time, and wallet persistence.
- [x] [Village tavern] Add the nested Olan beer conversation: ordering unlocks a tasting prompt, Gemini interprets the player's description, the D&D social resolution handles uncertainty, and the outcome persists in Olan's attitude.
- [x] Clarify that the old watchtower interaction forms are historical briefs and update the current web-runtime instructions.
- [x] [Character creator MVP K1] Add a separate deterministic single-class level-1 character-creation module with versioned species/class/background catalogues and choice-derived Actor construction.
- [x] [Character creator MVP K1] Compose executable Fighter/Rogue level-1 grants: four Fighting Styles, Second Wind, Expertise, and Sneak Attack with shared combat/resource rules.
- [x] [Character creator MVP K1] Apply the currently supported species grants: ability bonuses, speed, skill/weapon proficiencies, darkvision, dwarf poison resistance, and dwarf heavy-armor speed.
- [x] [Character creator MVP K1] Separate cantrips, class-list/spellbook access, prepared spells and always-prepared domain spells; add an executable level-1 Life Domain and Arcane Recovery.
- [x] [Character creator MVP K1] Add shared physical-d20 species hooks: Halfling Lucky rerolls, Brave fear-save advantage, Fey Ancestry charm-save/magical-sleep protection, and dwarf poison-save advantage.
- [x] [Character creator MVP K1] Complete utility species/background hooks: Halfling Nimbleness, Trance duration, tagged Stonecunning expertise, and authored scene-gated background permissions exposed to the GM classifier.
- [x] [Test maintenance] Update the stale party-check fixture that assumes the expanded watchtower exploration contains exactly two actors.
- [x] [Exploration UX regression] Restore the `/szukaj` guidance for an unknown `/użyj` source instead of falling through to the generic declaration error.
- [x] [Character creator MVP] Add the main menu and separate New Game, Load Game, and Create Character flows.
  - [x] Add the launcher shell, move the existing runtime to `/play`, and provide separate routed New Game, compatible-snapshot Load Game, and catalogue-backed character-module entry screens.
  - [x] Add the persistent creator roster so Create Character can validate, save, reopen, copy, and recoverably delete a playable character.
- [x] [Character creator MVP] Add scenario selection followed by a one-to-five saved-character party selection.
- [x] [Character creator MVP] Replace scenario-authored player templates with the selected custom party while preserving scenario-owned NPCs and enemies.
- [x] [Character creator MVP] Complete the village-to-watchtower route with a saved custom party; use `docs/CHARACTER_CREATOR_MVP.md` as the milestone DOD.
- [x] [Character level 1–3 master milestone] Complete the legal SRD 5.1 character catalogue as one release target: all 12 classes, SRD species/variants, one SRD subclass per class, XP/level-up, executable class/species grants, spells levels 0–2, creator/roster integration, completeness audit, and documented board-game exceptions.
  - [x] Add persistent actor XP, official 2014 thresholds, party encounter awards, visible progress, character record v3, and session snapshot v24 migration.
  - [x] Add data-driven level progression and level-up choices/grants.
  - [x] Complete SRD species and variant choices.
  - [x] Complete all 12 classes and SRD subclasses through level 3.
  - [x] Complete executable SRD spell content required through spell level 2,
    replacing all 99 former assisted-table entries with deterministic combat,
    status, reaction, area or typed exploration-flag contracts.
  - [x] Add the pure one-level advancement transaction with XP gating, HP/Hit
    Dice/slot/resource reconciliation, and no implicit rest.
  - [x] Add flexible species ability-bonus choices and character-record v4
    migration; expand the top-level species catalogue to the nine SRD species.
  - [x] Execute Fighter Action Surge, Rogue Cunning Action, Barbarian Rage
    activation/damage, universal unarmed strikes and Monk Martial Arts basics.
  - [x] Add an authoritative SRD level-3 completeness manifest and gap report
    for 9 species, 12 classes/subclasses, and all 127 unique spells at levels 0–2.
  - [x] Preserve source-specific spellcasting abilities in spell access, attacks,
    save DC calculation, and session snapshot v25.
  - [x] Add per-slot rest recovery and session snapshot v26 so Warlock Pact
    Magic can recharge independently from ordinary Spellcasting.
  - [x] Replace placeholder background proficiencies with real gaming-set and
    language choices in creator, actor build, record v7, copy, and level-up.
  - [x] Add actor creature types and snapshot v27, plus executable Ray of Frost,
    Chill Touch, and Shocking Grasp secondary effects.
  - [x] Add all eight level-3 Metamagic choices, sorcery-point costs, legal
    combinations, targeting/range/action transformations, Twinned resolution,
    Careful/Heightened saves, Empowered rerolls and the bonus-action spell rule.
  - [x] Add an executable feature audit which rejects every unclassified
    species/class/subclass/choice feature and malformed assisted spell.
  - [x] Model the Ranger's humanoid Favored Enemy choice as exactly two
    humanoid races and require authored race tags before granting advantage.
  - [x] Route Bardic Inspiration, two-stage Help, and direct status, movement,
    summon, debuff and dispel targets through illuminated board fields instead
    of public actor ids; add area selection for Sleep and Faerie Fire.
  - [x] Route stabilization and secondary spell selections (Twinned, Sculpt,
    Careful and Heightened) through illuminated figures on the board; keep only
    dice values and non-spatial effect variants in the UI.
  - [x] Connect the second physical class-feature batch: Bardic Inspiration,
    Cutting Words, Preserve Life, Turn Undead, three-form Wild Shape with
    rescan-to-revert, Cunning Action, three-form Pact Weapon, and spell-first
    scanned Metamagic without pre-cast digital variant buttons.
  - [x] Complete the physical-card timing/resource follow-up: stage Prayer of
    Healing targets and dice before a cancellable 10-minute completion, use
    concentration while casting, advance the scenario clock only on completion,
    retain Goodberry's replaceable 10-charge pool, and return live class/slot
    counters in scanner feedback.
  - [x] Show an explicit mechanical effect while resolving every spell family
    and remove duplicate target selectors from status, movement, summon,
    debuff, and dispel panels.
- [x] Implement hardware adapter interface around `board.Connection`.
- [x] Add LED frame generation for selected path and movement range.
- [x] Decide first UI/runtime surface.
- [x] Add manual board checklist coverage for the first movement demo.

## SRD Level 3 Runtime Audit Follow-up

- [x] [P0 spell fidelity] Correct erroneous concentration metadata for
  `invisibility` and `gentle_repose`; add semantic validation for concentration
  and duration instead of auditing only supported schema kinds.
- [x] [P0 spell fidelity] Require every combat `effect_kind` to have a registered
  runtime consumer and close the marker-only effects identified in
  `docs/SRD_LEVEL_3_RUNTIME_AUDIT_2026-07-29.md`.
- [x] [P0 spell areas] Represent supported persistent spell zones as board objects with
  point/area targeting, entry/turn triggers, movement, expiry and visible LEDs.
- [x] [P1 Arena audit] Register all 236 canonical spell, species, class,
  subclass and cross-cutting cases with reproducible Arena configurations;
  link 177 cases to automatic behavioral tests and document an explicit,
  justified skip for the remaining 59.
- [x] [P1 character help] Extend player-facing help and Arena audit coverage
  from level-1 class grants to level-2/3 class, subclass and option features.
- [x] [P1 flanking] Exclude incapacitated allies from flanking and present
  flanking as advantage rather than a numeric `+0` modifier.

## Content Tasks

- [x] Define first demo scenario placeholder.
- [x] Define minimal monster schema.
- [x] Define minimal item/equipment schema.

## Open Decisions

- [x] [Physical card vertical slice] Add the reviewed action phase catalog,
  scanner routing, named combat checkpoints, Rage/Frenzy toggling, optional
  Bardic Inspiration/Guidance dice, two-stage Cutting Words, Preserve Life
  board targeting, short-rest Alarm protection, and combat Invisibility routing;
  complete scan-to-board-to-confirm flows and scanner
  feedback, then exercise them in the Mechanics Playground.
- [x] [Board-first basic attack] Retire the redundant `basic_attack` card and
  keep ordinary weapon/unarmed attacks behind contextual enemy-field selection;
  reserve physical cards for spells, class features and special maneuvers.
- [x] [Seven board-game archetypes] Replace the visible twelve-class starter
  roster with seven role-first level-3 builds defined in
  `docs/BOARDGAME_ARCHETYPES_LEVELS_1_3.md`: complete combat/exploration kits,
  fixed caster decks without preparation, a
  content-authored `ExplorationCardIntent` handler/attempt contract, short and
  long rests exposed only by eligible instances, hidden legacy starters and
  regenerated physical card set. The runtime installs complete level-3 kits
  and every personal card is available from the start.
- [x] [Archetype flaws and exploration reactions] Give each of the seven
  archetypes one deterministic flaw, synchronize its combat/exploration
  trigger, add data-driven card reactions to the village and abandoned
  watchtower, connect route preparation to the navigation roll, and regenerate
  color plus black-and-white playtest PDFs with the flaw rules on hero cards.
- [x] [Character-dependent exploration tiles] Disable physical exploration-card
  declarations without deleting their assets; let authored zone options require
  and auto-assign a party hero, show that hero on the tile, and add two optional
  narrative interactions for each of the seven playable archetypes across the
  village and abandoned-watchtower MVP.
- [ ] [Deferred archetype progression] Design progression only after scenario
  playtests establish whether levels, card unlocks, upgrades, or a hybrid are
  the better reward loop. Until then all seven heroes remain level 3 with their
  complete personal decks.
- [x] [Physical combat-card batch 1] Route 15 common spell cards through one
  shared attack/healing/combat-action/reaction dispatcher reused by the screen
  menu; cover single-target attacks, saves, healing, areas, movement, statuses,
  summons, multi-projectile damage and Shield in the Mechanics Playground.
- [x] [Physical combat-card batch 2] Route 15 damage and battlefield-control
  spell cards through the shared dispatcher; cover attack/save riders,
  directional and radial areas, separate Scorching Ray attacks, persistent
  difficult/obscuring zones and concentration, including scan-to-board Fog
  Cloud resolution in the Mechanics Playground.
- [x] [Physical combat-card batch 3] Route 15 defense, support and reaction
  spell cards through the shared dispatcher; auto-bind self spells, add scanned
  Hellish Rebuke after applied enemy damage, and make See Invisibility reveal
  both invisible and per-observer hidden enemies in the Mechanics Playground.
- [x] [Physical combat-card batch 4] Route 15 debuff and persistent battlefield
  spell cards through the shared dispatcher; support repeated saves, delayed
  riders, movement/start-turn zones, explicit healing targeting, and Moonbeam/
  Flaming Sphere rescan-to-move without spending another slot.
- [x] [Physical combat-card batch 5] Route 15 weapon buffs, mobility, rescue and
  utility spell cards through the shared dispatcher; bind selected weapons,
  support three emulated familiar forms, create/spend the Goodberry pool,
  stabilize from a scan, and exercise scanning plus representative resolutions
  in the Mechanics Playground.
- [x] [Physical martial-feature batch 1] Route Fighter, Barbarian, Monk and
  Paladin cards through their existing class-feature resolvers; add a shared
  scanner prompt for physical dice, weapon, saving-roll and spell-slot input,
  preserve pending hit/reaction windows for Divine Smite and Deflect Missiles,
  and cover all four classes in the Mechanics Playground.
- [x] [Physical card Arena smoke matrix] Start a fresh Mechanics Playground
  encounter for every one of the 12 classes and scan a real card from each
  starter set; verify scanner routing, next-step prompts and resource feedback.
- [x] [Martial archetype decision budget] Expand the level-1 combat decks for
  Garran, Brakka, Mira and Erynd using existing resolvers, add short/long-rest
  resources for their remixed techniques, and verify scans plus resource spend
  in fresh Mechanics Playground encounters.
- [x] [Seven-hero combat deck audit] Remove exploration cards from the seven
  current print decks; balance each level 1–3 pool to 7–9 tactical combat
  cards; synchronize level gates, named resources, passives, flaws, dossiers
  and statistics; verify routes, reaction windows and resource spending in the
  Mechanics Playground; regenerate color and toner-ready print sets.
- [x] [Physical card timing reminders] Add the compact inline combat reminder
  driven by the legal contextual-action catalogue and ordered reaction window;
  cover every printable combat card in the seven active decks, allow an
  explicitly selected non-active reaction owner, and verify action plus reaction
  reminders in the Mechanics Playground.
- [x] [Level-3 hero gameplay review] Start all seven heroes at level 3, add +2
  to each primary ability, expose every personal card immediately, replace the
  weak True Strike variants with same-turn attack setup, make MANEWRY and
  EKWIPUNEK cards open real menus, align spell riders/flaws/deck access with the
  runtime, and show finite resources in legal-card reminders.
- [x] [Level-3 dossier resource pass] Remove the obsolete level 1–3 progression
  section, replace it with exact card pools/slots and recovery rules, list only
  physical-deck spells on character sheets, and recalculate Lorian's Inspiration
  pool after the archetype Charisma bonus.
- [x] [Target campaign flow authoring] Extract the complete `Ostatni transport do
  Czarnego Brodu` map/NPC/interaction/player-tile flow into editable Mermaid and
  generate a multi-page `.drawio` workspace with individually movable nodes,
  collapsible instance groups, typed colors and regeneration coverage; model
  the reusable Guild hub as Map 0 with mandatory Nessa briefing, gated departure
  and visibly reserved but mechanically inactive future facilities.
- [x] [Guild Map 0 implementation spec] Create the living technical source for
  Nessa's mandatory briefing, optional information cards, persistent flags,
  departure flow and cross-scene knowledge callbacks that reward players for
  deliberately applying remembered details without blocking ordinary discovery.
- [x] [Guild Map 0 mechanical runtime] Add deterministic, knowledge-gated LLM
  argument scoring before a physical social roll; support unique performers,
  critical-failure/exhaustion effects and assigned NPC-goal actors; implement
  the loadable Nessa briefing, three negotiation outcomes, Erynd document check,
  persistent knowledge flags and gated departure to a Map 1 placeholder; render
  Nessa's negotiation response in a second, post-roll LLM phase while keeping
  the authored mechanical result immutable and providing safe fallbacks.
- [x] [Guild Map 0 authored briefing] Complete Nessa's opening assignment,
  disappearance, cargo, personnel, Insight, Erynd document-check and departure
  text; align route marks, medicine-cache details, caravan roster and propagated
  knowledge flags with the living campaign specification.
- [x] [Guild Map 0 art pack] Define the shared gothic-comic art direction and
  production prompts, generate the guild map, Nessa portrait, desk scene, seven
  interaction tiles and three future-feature placeholders, and bind the current
  zone, NPC point and authored goals to their scenario-local assets.
- [x] [Guild Map 0 hotspot and contract closure] Bind Nessa, Archive,
  Quartermaster, Training and the departure gate to stable board positions
  matching the isometric map; keep the locked gate inspectable, summarize only
  learned departure facts, define level-3-scale contract values, pay advances
  to every living party member, persist preparation packs, and verify the full
  Map 0 → Map 1 handoff.
- [x] [Guild Map 0 physical setup parity] Add the MVP-style paper-map setup,
  portrait 50 × 75 cm print source, eight-page A4 and full-size PDFs, location
  preview/confirmation, immediate single-field Nessa placement after unfolding
  the map, portrait preview before accepting her interaction, and illustrated
  Archive, Quartermaster and Training hotspots on the same physical map.
- [x] [Player campaign launcher] Make Ostatni transport the default runtime
  campaign; enforce New Game as physical-card party selection followed by
  scenario selection; expose only the Guild Map 0 campaign in the player
  catalog while retaining MVP, arenas and playgrounds as direct test content.
- [ ] [Black Ford Map 1 implementation] Replace the Zawalona Droga placeholder
  with the authored locations, interactions, encounter flow and callbacks from
  the campaign graph, consuming the knowledge flags propagated from Map 0.
  - [x] Add the encounter-first phase contract: immediate arrival trigger,
    exploration hidden until victory, and content-driven terminal Game Over on
    defeat, retreat or surrender.
  - [x] Add a dedicated encounter-start checkpoint and exact Game Over retry
    that restores party resources, actors, positions, terrain and initiative
    without overwriting the ordinary scenario save, then repeats the physical
    hero, enemy and terrain setup before reactivating combat.
  - [x] Add approach-mode and Erynd-knowledge opening variants.
  - [x] Add final tactical terrain, monster scaling, statblocks and AI profiles.
    - [x] Define the encounter fiction, tactical zones, provisional stat targets,
      party-size presets, morale sources, low-HP behavior, flee flow and
      exploration handoff in `MAPA_1_GLODNE_CIENIE_ENCOUNTER_SPEC.md`.
    - [x] Replace the bespoke behavior tree with the implementable
      `weighted_utility_v1` contract and a tunable Hungry Shadow pack JSON
      profile covering roles, fuzzy features, seeded noise and morale.
    - [x] Prepare the top-down encounter map base and editable tactical-zone
      overlay, AI decision diagram, complete skirmisher/leader statblocks and
      the LED feedback storyboard/semantic-role contract.
    - [x] Produce the comic-style v2 battlemap with stronger linework and
      saturated colors, plus explicit enemy start fields and party-size setup
      groups in the editable overlay and tactical layout JSON.
    - [x] Revise the battlemap to v3 with a restrained dark-fantasy palette and
      lower texture density while retaining the tactical layout and enemy slots.
    - [x] Wire the v3 map into encounter setup, add data-driven party-size
      variants 1–5, apply the tactical terrain to pathfinding, expose the map
      preview, and preserve the selected setup through Game Over Retry.
    - [x] Connect the `weighted_utility_v1` runtime baseline: profile/role/tag
      loading, deterministic intent scoring, pack morale, regroup/guard,
      forced flee/cornered behavior, escape fields, dead/escaped outcome ledger,
      victory without killing every beast, and snapshot persistence.
    - [x] Complete the remaining tactical scoring inputs (cover, isolation,
      opportunity risk, hazards and guard-zone threat) and tune voluntary flee
      behavior with simulated parties before the manual balance pass.
    - [x] Add the production-AI playtest runner, execute and persist 64 seeded
      fights across eight compositions and party sizes 1–5, fix repeated
      pathfinding, idle regroup/guard/flee loops, Dash approach, fixed-deck
      preparation and spell-handling regressions, and publish the result table.
    - [x] Add three walkable passive defensive spots granting automatic +2 AC,
      revise the battlemap/layout to v4, raise Hungry Shadow HP slightly, let
      guard/regroup attack after movement, and tune ranged-fire cover response
      so reachable attacks and low-HP/low-morale flee behavior take priority;
      rerun the 64-fight matrix with no timeout or deadlock.
    - [x] Add a data-driven `attack_bonus` that raises only attack rolls, give
      every Hungry Shadow attack `+1` (`+5` skirmisher, `+6` leader), and rerun
      the 64-fight matrix: 517 total damage, 64 resolved fights, no timeout.
    - [x] Add a deterministic end-to-end campaign walkthrough covering New Game,
      physical-card party selection, Guild setup, the complete useful Nessa
      briefing, checked knowledge, negotiation, quest activation, travel,
      same-session Map 1 handoff, encounter setup/initiative/checkpoint and
      victory-gated aftermath; publish its audit report and regression command.
  - [x] Replace the aftermath placeholder with same-map wagon and track
    investigation, Teren aid/question/fate, young-beast choice, route selection
    and a validated handoff to the Black Ford entry shell.
- [x] [Physical card print synchronization] Regenerate all 12 character-set
  PDFs from the current phase/effect catalogue, omit removed cards, validate
  every QR/manifest/page count, and add individual plus combined toner-friendly
  black-and-white A4 character sheets for the starter roster.
- [x] [Physical card low-toner playtest edition] Add illustration-free,
  front-only black-and-white card layouts with crop marks and validated QR
  payloads; generate 12 per-character PDFs and one combined 100-page test PDF.
- [x] [Exploration performer card scan] Let a scanned hero card select the
  performer for a checked zone option exactly like clicking that hero in the
  local action composer, while rejecting defeated, hostile or invalid actors.
- [x] [Physical spell preparation] Replace setup checkboxes with a visual
  default card set accepted by `ACCEPT`; let `DECLINE` start a scanner-only
  custom set that validates each spell and completes at the actor's limit.
- [x] [Board-native exploration navigation] Stop using `ACCEPT`/`DECLINE` for
  location and instance navigation; keep all location markers lit, use repeated
  `A → A` selection to confirm entry, reserve one red system-exit pad beside at
  most seven authored actions, and block that exit during unresolved flow.
- [x] [Hybrid board and numpad controls] Mirror exploration choices on numeric
  keypad keys, navigate combat context actions with Numpad 8/2, Enter and minus,
  keep the visible combat list compact with explicit overflow indicators, and
  require repeated board selection for movement, hotspots and area anchors.
- [x] [Exploration interaction input regression] Route the visible action button,
  Enter and `ACCEPT` through the same open-composer action; require explicit
  confirmation for automatic NPC goals, lock authored character moments to their
  assigned performer, expose all unlocked locations of the current scene after
  leaving an instance, and separate purple interaction LEDs from the fourth white
  option.
- [x] [Stable instance tiles and scoped results] Keep every interaction action on
  its initially assigned board position, number and color when sibling actions
  disappear; scope roll acknowledgements to messages created by the current
  request so an earlier NPC result cannot leak into a later location.
- [x] [Brakka QR and gate group-check regression] Accept owner-bound v2 combat
  card payloads from the keyboard scanner, keep board selection listening for
  five minutes, ignore cancelled stale scans, and make force-entry a fixed
  whole-party check resolved by any single success.
- [x] [Staged scenario travel] Split continuation into pace, hero-card
  navigator and physical-roll stages; show arrival/perception/stealth tradeoffs,
  preserve Natural Explorer and forced-march shortcuts, and make control cards
  advance or retreat one stage at a time.
- [x] [Ostatni transport travel consequences] Turn the Guild departure into a
  60-minute time-versus-readiness decision with authored pace explanations,
  Survival navigation delay, distinct Hungry Shadows combat openings, and
  persisted arrival-window/timing flags for later campaign maps.
- [ ] [Physical card timing follow-up] Give 10-minute Prayer of Healing a
  dedicated encounter-time/long-cast presentation instead of resolving its
  already-tested multi-target healing immediately after confirmation, and
  expire unused Goodberries after 24 hours of exploration time.

- [x] Preserve dynamically granted area attacks (including Rhogar's Breath
  Weapon) in the combat preview payload so the player can explicitly confirm
  the attack or return to area selection before spending the action/resource.
- [x] Replace the idle hero combat view with a persistent Numpad-driven action
  mode list, movement-first LED previews, Enter-confirmed area placement that
  retains legal anchors, Numpad 0 turn ending, and a 75-foot board range cap.
- [x] Present spell-backed starter-deck actions under their hero archetype
  groups (Taktyki, Dzikość, Fortele and Instynkt), label class actions as
  special abilities, and keep attacks from duplicate weapon copies uniquely
  selectable.
- [x] Accelerate the Hungry Shadows encounter with a player-chosen 5×4
  deployment zone, closer asymmetric enemy positions, flanker/harrier roles,
  real approach-progress scoring, anti-dogpile prey memory and one board
  confirmation for ordinary enemy turns; reduce ordinary Hungry Shadow Rend
  damage to `1d4 + 2` for the coordinated-pack rebalance.
- [x] Replace Hungry Shadows utility tactics with deterministic coordinated-pack
  focus fire, per-support attack/damage bonuses, leader ranged/melee and deferred
  healing, irreversible leader/follower retreat, illuminated escape targets,
  zero-progress dead-loop guards, and removal of the obsolete old bell.
- [x] Make targetless combat previews non-blocking: keep the active-hero LED
  passive, stop automatic scanning when an attack or healing action has no legal
  target, show an explicit player-facing explanation, move the action chooser
  into a compact list/stats layout, and prevent Numpad minus from cancelling a
  healing roll while its numeric input is focused.
- [x] Rebuild Brakka around three per-long-rest Rages and a three-point
  per-Rage Ferocity pool; replace Frenzy/Action Surge/Cunning Action and the
  two pseudo-spells with Reckless Attack, Powerful Strike, Shoulder Check,
  Hard as Rock, Acceleration and Deafening Roar, including board targeting,
  reaction timing, critical-save riders and edge-case tests.
- [x] Remove Danger Sense from Brakka's board-game archetype so her runtime
  passive rules match the deliberately reduced printed passive set.
- [x] Rebalance Dagna's starter kit: replace Warding Bond with Spiritual
  Weapon, expose Life Domain healing in card text, use the 75-foot board range
  for Guiding Bolt, hide Turn Undead without a legal target, and make her
  rescue flaw grant enemy saves advantage against her hostile spells.
- [x] Remove Dagna's non-playable Diagnosis feature, its card route and stale
  authored scenario references while retaining ordinary Medicine checks.
- [x] Rebalance Dagna's active spells: reduce Guiding Bolt to `2d6`, turn
  Sacred Flame into a 15-foot enemy-only cone, make Aid expire at encounter
  end, select Lesser Restoration conditions from actual target state, and
  verify Spiritual Weapon as a targetable 1 HP / AC 18 blocking flanker with
  owner-adjacent initiative.
- [x] Remove Stonecunning and Shelter of the Faithful from Dagna's curated
  board-game archetype and passive card while preserving her flaw.
- [x] Rebuild Dagna around mobile combat support: make Bless a moving 10-foot
  aura, replace Sanctuary with the 5-foot Divine Care attack/damage penalty
  aura, replace Aid with the limited-use Healing Grace aura, add the
  once-per-turn Field Medic Step prompt, dynamic actor statuses and optional
  LED aura inspection, with action previews retaining display priority.
- [x] Rebuild Garran as a stationary shield commander: make Action Surge spend
  a bonus action, replace field healing with Shield Bash, make Defensive Stance
  consume movement, add four Strength-scaled Tactics with board targeting and
  one-shot protection redirection, replace Command Guilt with cumulative-wound
  Remorse, remove Guard Duty/Military Rank, and cover edge cases and saves.
- [x] Rebuild Erynd as a mobile ranged controller: replace swords and travel
  passives with a Strength-based hunting knife, First Blood, Scout's Vigilance,
  movement-cost Aim and four Instinct arrows; collect the physical d4/d8 rider
  rolls, enforce ammunition/resources, statuses and expiry, allow free Hunter's
  Mark transfer after defeat, and cover profile, scanner and edge-case tests.
- [x] Make combat Hide unique to Mira with per-observer active Perception,
  20/25-foot stealth movement, visibility LEDs, manual exit, observer-aware AI
  targeting and accidental path-collision replanning; replace her shortbow with
  15-foot throwing knives and stack flank/hidden damage as `+1d6/+2d6/+3d6`.
- [x] Complete Mira's stealth-killer rebuild: Dexterity-scaled Fortels, ranged
  AC, Instinctive Dodge and Smoke Screen, Hamstring/Piercing/Vault/Blade attacks,
  persistent wound statuses, 45-foot combat trap detection, and retirement of
  Break In plus the obsolete rogue/spell package, with edge-case tests.
- [x] Rebuild Lorian as a social crossbow tactician: two-shot Crossbowman,
  Mocking/Provoking shots, Inspiration-linked Counterpoint and Distracting
  Shout reactions, narrow social expertise with one final Improvisation reroll,
  Panic Whisper, Stage Command and Accelerated Refrain, including bounded AI
  movement, silence fallbacks, bonus-action competition and edge-case tests.
- [x] Recast Lorian as a bard-inventor: reusable optical, destabilizing,
  provoking and entangling crossbow techniques; nearby-ally flaw; broad
  non-combat Charisma expertise; short-rest Inspiration; and persisted
  once-per-NPC Improvisation.
- [x] Rebuild Nimra as a save-based area controller with an Intelligence-scaled
  Metamagic pool, immediate board previews and atomic confirmation; add a
  deterministic ally-risking Lightning Path chain and make Arcane Leak Echo
  prevent repeating either the previous round's spell or Metamagic.
- [x] Simplify the shared combat action surface to Move, weapon attacks,
  character abilities/spells, Change Weapon, Use Item and End Turn; keep
  retired actions as hidden legacy resolvers, move Dash/Disengage to Erynd,
  Grapple to Brakka, auto-stand on movement, and collect victory loot into a
  persisted shared party pool.
- [x] Replace eager combat action previews with an explicit list/preview/selection
  protocol: Numpad 2/8 navigates without LED churn, first Enter arms the preview,
  board clicks only select, second Enter commits, and minus cancels without cost.

- [x] UI framework: local Flask/web UI for the current runtime and future authoring modules.
- [x] Content licensing/source strategy for D&D 5e data.
- [x] Save file format and state versioning.
- [x] Whether diagonal movement follows 5e optional grid rules or simplified board rules.
