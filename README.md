# Board Game Rebuild

This repository is being rebuilt as a new board-assisted tabletop RPG application based on Dungeons & Dragons 5e-style mechanics.

The previous application has been archived under `legacy/previous_app/`. It is reference material only.

## Start Here

- `PROJECT_CONTEXT.md` - current product and technical context.
- `GAME_DESIGN.md` - gameplay scope and first mechanics.
- `ARCHITECTURE.md` - target module layout and dependency rules.
- `TODO.md` - next small implementation tasks.
- `ROADMAP.md` - mechanics-first master plan through content, classes, and authoring tools.
- `docs/DND_IMPLEMENTATION_MATRIX.md` - living audit of implemented, partial, and missing D&D systems.
- `PROMPT_TEMPLATE.md` - recommended prompt shape for Codex work.
- `legacy/LEGACY_DESCRIPTION.md` - useful technical lessons from the previous app.

## Active Code Areas

- `board/` - existing board configuration, serial scan protocol, WLED LED control, LED mapping, and simulator backend.
- `src/dnd_board_game/` - new application code.
- `content/` - future data-driven scenarios, monsters, and items.
- `tests/` - root hardware boundary tests plus new unit/integration/hardware tests.
- `scripts/safe_pytest*.sh` - safe pytest wrappers.

## Rule Of Thumb

Build deterministic D&D 5e game logic first, with focused tests. UI and hardware adapters should sit at the edges. New rules code should not import from `board/`, Flask, WLED, serial, or `legacy/`.
