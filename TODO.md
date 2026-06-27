# TODO

## Setup

- [x] Archive previous application into `legacy/previous_app/`.
- [x] Keep low-level board communication in root `board/`.
- [x] Add rebuild documentation and Codex working rules.
- [x] Add package structure for the new D&D 5e application.
- [x] Add local rules decision document for implemented D&D mechanics.
- [x] Add project roadmap with implementation milestones.

## Next Engineering Tasks

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
- [ ] Add full inventory/cantrip integration for exploration option bonuses.
- [ ] Reserve future LLM adapter for classifying free-form exploration declarations into validated options.
- [x] Implement hardware adapter interface around `board.Connection`.
- [x] Add LED frame generation for selected path and movement range.
- [x] Decide first UI/runtime surface.
- [x] Add manual board checklist coverage for the first movement demo.

## Content Tasks

- [x] Define first demo scenario placeholder.
- [x] Define minimal monster schema.
- [x] Define minimal item/equipment schema.

## Open Decisions

- [ ] UI framework.
- [ ] Content licensing/source strategy for D&D 5e data.
- [ ] Save file format and state versioning.
- [x] Whether diagonal movement follows 5e optional grid rules or simplified board rules.
