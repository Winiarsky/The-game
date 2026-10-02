# Board Game Rebuild

This repository is being rebuilt as a new board-assisted tabletop RPG application based on Dungeons & Dragons 5e-style mechanics.

The previous Pathfinder-like application was removed from the active tree after
the D&D 5e rebuild became self-contained. It remains recoverable from Git history.

## Start Here

- `PROJECT_CONTEXT.md` - current product and technical context.
- `GAME_DESIGN.md` - gameplay scope and first mechanics.
- `ARCHITECTURE.md` - target module layout and dependency rules.
- `TODO.md` - next small implementation tasks.
- `ROADMAP.md` - mechanics-first master plan through content, classes, and authoring tools.
- `docs/DND_IMPLEMENTATION_MATRIX.md` - living audit of implemented, partial, and missing D&D systems.
- `PROMPT_TEMPLATE.md` - recommended prompt shape for Codex work.
- [handouts](handouts/README.md) - current monochrome character cards, board maps, and Mission 0 print materials.

## Active Code Areas

- `board/` - existing board configuration, serial scan protocol, WLED LED control, LED mapping, and simulator backend.
- `src/dnd_board_game/` - new application code.
- `content/` - future data-driven scenarios, monsters, and items.
- `tests/` - root hardware boundary tests plus new unit/integration/hardware tests.
- `scripts/safe_pytest*.sh` - safe pytest wrappers.

## Rule Of Thumb

Build deterministic D&D 5e game logic first, with focused tests. UI and hardware adapters should sit at the edges. New rules code should not import from `board/`, Flask, WLED, or serial.
