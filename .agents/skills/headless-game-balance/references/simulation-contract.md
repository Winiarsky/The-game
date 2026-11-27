# Simulation contract

Document this contract beside the simulator.

## Shared with the game

- State allocation and initialization
- Seeded RNG and draw order
- Legal actions
- Scoring and economy
- Progression and termination
- Balance/config values
- Save-compatible identifiers when relevant

## Replaced by the simulator

- Rendering and animation interpolation
- Audio, haptics, achievements, and analytics
- Real-time delays
- Human input, replaced by a named policy

## Required reproducibility

Given the same executable revision, balance version, policy version, and seed, the simulator must produce the same action trace and final state.

When reproducibility breaks, stop tuning and find the source: hidden global RNG, unordered collection iteration, wall-clock reads, floating-point platform drift, or mutable shared config.

## Policy trace

For a failed or changed run, be able to emit:

1. State summary before each decision
2. Legal actions considered
3. Policy score for each action
4. Chosen action
5. RNG state or draw counter
6. Resulting state summary

Keep full traces optional so large benchmark runs stay fast.
