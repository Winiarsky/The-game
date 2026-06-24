# TODO

## Setup

- [x] Archive previous application into `legacy/previous_app/`.
- [x] Keep low-level board communication in root `board/`.
- [x] Add rebuild documentation and Codex working rules.
- [x] Add package structure for the new D&D 5e application.

## Next Engineering Tasks

- [ ] Define `Coordinate`, board dimensions, and grid primitives.
- [ ] Implement pure neighbor lookup and bounds checks.
- [ ] Implement pathfinding with terrain/passability callbacks.
- [ ] Add unit tests for grid and pathfinding.
- [ ] Define D&D 5e dice primitives: d20 roll, advantage, disadvantage.
- [ ] Define basic actor state: AC, HP, speed, ability scores, position.
- [ ] Implement initiative order.
- [ ] Implement basic melee/ranged attack resolution.
- [ ] Implement hardware adapter interface around `board.Connection`.
- [ ] Add LED frame generation for selected path and movement range.
- [ ] Decide first UI/runtime surface.

## Content Tasks

- [ ] Define first demo scenario placeholder.
- [ ] Define minimal monster schema.
- [ ] Define minimal item/equipment schema.

## Open Decisions

- [ ] UI framework.
- [ ] Content licensing/source strategy for D&D 5e data.
- [ ] Save file format and state versioning.
- [ ] Whether diagonal movement follows 5e optional grid rules or simplified board rules.
