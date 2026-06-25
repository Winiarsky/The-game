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
- [ ] Define D&D 5e dice primitives: d20 roll, advantage, disadvantage.
- [x] Define basic actor state: AC, HP, speed, ability scores, position.
- [ ] Implement initiative order.
- [ ] Implement basic melee/ranged attack resolution.
- [x] Implement hardware adapter interface around `board.Connection`.
- [x] Add LED frame generation for selected path and movement range.
- [x] Decide first UI/runtime surface.
- [x] Add manual board checklist coverage for the first movement demo.

## Content Tasks

- [ ] Define first demo scenario placeholder.
- [ ] Define minimal monster schema.
- [ ] Define minimal item/equipment schema.

## Open Decisions

- [ ] UI framework.
- [ ] Content licensing/source strategy for D&D 5e data.
- [ ] Save file format and state versioning.
- [x] Whether diagonal movement follows 5e optional grid rules or simplified board rules.
