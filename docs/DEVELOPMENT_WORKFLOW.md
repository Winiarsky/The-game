# Development Workflow

## Recommended Flow

1. Pick one small task from `TODO.md`.
2. Ask Codex for a short plan if the task touches more than one module.
3. Implement only that task.
4. Add focused tests.
5. Run tests through `scripts/safe_pytest.sh`.
6. Update `TODO.md`.
7. Commit.

## Task Size

Good task:

- "Implement grid bounds and neighbor lookup with unit tests."
- "Add D&D 5e d20 roll helper with advantage/disadvantage tests."
- "Add board hardware adapter interface without changing `board.Connection`."

Too broad:

- "Build combat."
- "Make the whole UI."
- "Implement D&D."

## Testing

Use small batches:

```bash
scripts/safe_pytest.sh --timeout 60 tests/unit/test_grid.py
```

For all current root tests:

```bash
scripts/safe_pytest_suite.sh
```

Do not run multiple pytest processes at once.
