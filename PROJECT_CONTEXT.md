# Project Context

This project is a new application for a physical board-assisted tabletop RPG game.

The previous application has been archived in `legacy/previous_app/`. It used Pathfinder-style mechanics and grew too tightly coupled. The rebuild should keep only the low-level board/LED communication layer and selected technical ideas documented in `legacy/LEGACY_DESCRIPTION.md`.

## New Game Baseline

- Rules family: Dungeons & Dragons 5e.
- Board: physical 20x30 grid.
- Coordinate format: `(col, row)`.
- One board square represents 5 feet unless a future design document says otherwise.
- Hardware layer: existing `board.Connection`.
- LED output: WLED through the existing board package.
- Board input: USB/serial scan through the existing board package or simulator backend.

## Product Goal

Build a reliable local game runtime that helps run D&D 5e-like tactical encounters on the physical board:

- track actors and positions,
- resolve movement and basic actions,
- support combat rounds and initiative,
- light valid movement, targets, areas, and feedback on the board LEDs,
- keep game state deterministic and testable,
- later add UI, content authoring, audio, and richer scenario flow.

## Current Known Decisions

- Use Python for the backend/game runtime.
- Start with a clean rules/domain core before rebuilding UI.
- Avoid copying Pathfinder mechanics from legacy.
- Prefer data-driven monsters/items/scenarios once the core model is stable.

## Unknowns / Placeholders

- Exact UI framework: TODO.
- Whether the first player UI is web, terminal, or hybrid: TODO.
- Exact D&D 5e license/content source strategy: TODO.
- Campaign setting and first demo scenario: TODO.
- Persistence format beyond early JSON snapshots: TODO.
