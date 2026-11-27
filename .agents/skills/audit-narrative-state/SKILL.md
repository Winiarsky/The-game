---
name: audit-narrative-state
description: Audit explicit narrative variables, quest states, relationship states, flags, inventory/story conditions, and branch prerequisites for contradictions, impossible combinations, missing initialization, set-but-never-read variables, read-before-set states, invalid transitions, forgotten consequences, and state explosion. Use when the narrative is implemented or represented as stateful logic. Diagnose first; do not rewrite code or prose by default.
---

# Audit Narrative State

Treat narrative implementation as a **state machine and data-flow system**.

This audit focuses on explicit or inferable state such as:

- quest phase
- relationship state
- alive/dead/present status
- faction allegiance
- knowledge flags
- choice memory
- inventory/story objects
- world conditions
- romance state
- reputation
- story chapter

## Core Checks

### Initialization
- state read before it can be set
- ambiguous defaults
- old-save migration assumptions

### Transition validity
- impossible jumps
- missing transition path
- state can regress unintentionally
- terminal state can reopen unexpectedly

### Contradictory combinations
Examples:
- `dead = true` and `active_companion = true`
- `quest = completed` and objective still active

Do not assume combinations are invalid merely because they look strange; look for authored interpretation.

### Memory
- meaningful choice is set but never read
- state is read in one branch and ignored after reconvergence
- consequence resets without narrative explanation

### Reachability
- unreachable content
- conditions that can never all be true
- state that can be entered but never exited

### Data-flow
- set-but-never-read
- read-but-never-set
- duplicate flags representing the same concept
- two variables that can disagree about the same truth

### Combinatorial risk
Persistent independent variables may multiply downstream variants even when the visible branch graph is small.

## Procedure

1. Inventory variables/states.
2. Identify possible values and defaults.
3. Locate sets, reads, and resets.
4. Model valid transitions.
5. Enumerate or sample combinations where useful.
6. Trace critical player choices through reconvergence.
7. Identify unreachable, contradictory, or unhandled states.
8. Rank by player impact and production/QA risk.

## Output

### State inventory

| State | Values | Default | Set at | Read at | Reset at |
|---|---|---|---|---|---|

### Transition issues

### Contradictory / unhandled combinations

### Dead or unused state

### Memory failures

### Reachability issues

### Complexity hotspots

For each finding include:
- evidence
- severity
- confidence
- affected content
- smallest repair category

Repair categories:
- initialize explicitly
- merge duplicate state
- add/remove transition
- gate content
- preserve state across foldback
- add handler for combination
- remove dead flag
- convert multiple booleans to enum/state machine

## Severity

Critical for progression blockers, impossible saves, or major narrative contradictions.
High for broken consequence/quest logic.
Medium for latent combinations or wasted content.
Low for cleanup and maintainability risks.

## Final Quality Check

Separate logical validity from authorial desirability. A bitter romance can coexist with hostility if the narrative supports it; an unhandled combination is the problem, not complexity itself.
