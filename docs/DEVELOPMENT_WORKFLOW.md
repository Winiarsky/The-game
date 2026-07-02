# Development Workflow

## Recommended Flow

1. Pick one small task from `TODO.md`.
2. Ask Codex for a short plan if the task touches more than one module.
3. Implement only that task.
4. Add focused tests.
5. Run tests through `scripts/safe_pytest.sh`.
6. If the task implements or changes a D&D 5e mechanic, update `docs/RULES_DECISIONS.md`.
7. Update `TODO.md`.
8. Commit.

## Task Size

Good task:

- "Implement grid bounds and neighbor lookup with unit tests."
- "Add D&D 5e d20 roll helper with advantage/disadvantage tests."
- "Add board hardware adapter interface without changing `board.Connection`."

Too broad:

- "Build combat."
- "Make the whole UI."
- "Implement D&D."

## Rules Decisions

Rules should not live only in code or memory.

When a D&D 5e mechanic is implemented, write the local project interpretation in:

```text
docs/RULES_DECISIONS.md
```

Keep entries short and practical:

- what the MVP implements,
- what is out of scope,
- what tabletop/board simplification was chosen,
- which tests cover it.

Do not copy long rulebook text into the repository.

## Scenario Interactions

For new NPC, object, location, obstacle, or event interactions, start from:

```text
docs/SCENARIO_INTERACTION_FORM.md
```

Copyable template:

```text
content/templates/interaction_form.md
```

The form is the handoff between scenario design and implementation. Fill it in with player-facing description, GM-only truth, intended intents, locked information, mechanical effects, limits, and example player declarations. Codex should then turn it into scenario JSON, tests, and any missing deterministic mechanics.

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
