# Codex Notes

## Project Direction

- This repository is being rebuilt as a new board-assisted tabletop RPG application.
- The new rules baseline is Dungeons & Dragons 5e, not Pathfinder.
- Treat `legacy/previous_app/` as a reference archive only. Do not import from it in new runtime code.
- Keep low-level board communication in the existing `board/` package.
- New application code belongs under `src/dnd_board_game/`.
- New tests belong under `tests/`, grouped as `unit/`, `integration/`, or `hardware/`.

## Coding Rules

- Language: Python.
- Use type hints for new code.
- Prefer small pure functions and dataclasses for domain logic.
- Keep deterministic rules code independent from Flask, WLED, serial devices, files, and real time.
- Use composition over inheritance unless a local pattern clearly justifies inheritance.
- Avoid global mutable game state.
- Do not add dependencies unless the task explicitly needs one and the tradeoff is documented.
- Do not rename or move files without a clear reason.
- Do not perform broad refactors while adding a feature.

## Architecture Rules

- `board/` is the low-level hardware boundary and remains reusable.
- `src/dnd_board_game/rules/` owns D&D 5e mechanics.
- `src/dnd_board_game/world/` owns board topology, grid coordinates, pathfinding, terrain, rooms, and line of sight.
- `src/dnd_board_game/actors/` owns player characters, monsters, NPCs, and actor state.
- `src/dnd_board_game/actions/` owns action declarations and action resolution orchestration.
- `src/dnd_board_game/combat/` owns initiative, turns, attacks, damage, healing, conditions, and death saves.
- `src/dnd_board_game/hardware/` adapts game events to `board.Connection`; it must not contain D&D rule decisions.
- `src/dnd_board_game/ui/` owns user-facing presentation and input transport.
- `content/` stores data-driven scenarios, monsters, and item definitions.
- `legacy/` must not be changed unless the task is explicitly about documentation or archive maintenance.

## Workflow For Codex

- Before larger implementation work, read `PROJECT_CONTEXT.md`, `ARCHITECTURE.md`, `GAME_DESIGN.md`, and `TODO.md`.
- For larger tasks, first provide a short implementation plan and list expected files to change.
- Keep changes scoped to the requested feature.
- Add or update focused tests for every non-trivial rules or hardware-adapter change.
- Update `TODO.md` when a planned task is completed or a new concrete task is discovered.
- In final responses, mention changed files and tests run.

## Test Safety

- Run pytest in small, targeted batches instead of broad or parallel runs.
- Run pytest through `scripts/safe_pytest.sh` by default, with a concrete test file or node id.
- For a full suite, use `scripts/safe_pytest_suite.sh`; it runs `tests/test_*.py` one file at a time through the safe wrapper.
- Avoid launching multiple `pytest` processes at once in this workspace; the wrapper refuses to start if one is already active.
- Use a timeout for every pytest run. The wrapper defaults to 60 seconds and supports `--timeout SECONDS`.
- Keep command output capped when reading logs or test output.
- Be careful with broad searches through `data/debug_sessions`, `logs`, and Codex session logs; prefer narrow time windows and specific filenames.
- Use `scripts/read_recent_codex_logs.sh` for Codex logs instead of direct broad reads from `~/.codex/logs_2.sqlite`.
- Context: on 2026-04-24 around 13:20 local time, the VS Code/Codex scope reached about 13.9 GB memory and `systemd-oomd` killed the desktop session.
