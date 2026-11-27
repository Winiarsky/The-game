---
name: headless-game-balance
description: Build and use deterministic headless simulations to tune game difficulty, progression, economies, drops, shops, encounters, and win rates without rendering. Use when balancing roguelites, puzzle games, strategy games, procedural runs, score curves, reward systems, or any game where seeded automated players can expose impossible stages, dominant choices, excessive variance, or regressions across balance versions.
---

# Headless Game Balance

Turn balance into a reproducible experiment. Run the same decision policy over fixed seeds, record structured outcomes, and change one hypothesis at a time.

## Establish a simulation boundary

The simulator must call the same game-logic functions as the shipped game. It may replace rendering, wall-clock time, input devices, and animation waits; it must not reimplement scoring, RNG, progression, shops, or win conditions.

Before implementing a simulator, confirm that:

- Game logic is separated from presentation and I/O.
- All randomness comes from explicit seeded state.
- Time-dependent rules accept a deterministic step or event.
- Balance/config is supplied as data and can be cloned or overridden.
- A complete run can advance without a GPU, audio device, window, or network.

If these are false, refactor the boundary before simulating. A fast second implementation only measures itself.

## Define the question first

Write one falsifiable question, for example:

- Does a competent policy win 30–45% of runs?
- Is stage 9 a difficulty cliff?
- Does one shop item dominate purchase rate?
- Does the new reward curve reduce early bankruptcies without trivializing the end?

Choose metrics that answer the question before running anything.

## Define a policy, not a perfect player

Automated play is a model of player behavior. Give each policy a name and version:

- Random legal player
- Greedy immediate-value player
- Competent heuristic player
- Conservative economy player
- Oracle or search player as an upper bound

Keep policy code separate from game logic. Record every decision and enough state to explain it. Do not silently improve a policy while comparing balance versions.

Read [references/simulation-contract.md](references/simulation-contract.md) before building the first policy.

## Use paired seeds

Compare candidates on the same ordered seed set. Paired seeds reduce noise and make regressions reproducible.

- Keep a small smoke set for every test run.
- Keep a fixed benchmark set for comparisons.
- Add random exploratory seeds only after the paired comparison.
- Print the seed for every failure, outlier, or invariant violation.

Never reseed inside a run unless the shipped game does so.

## Record useful output

Emit one JSON object per completed run. Include at least:

- Balance/version identifier
- Policy/version identifier
- Seed
- Win/loss outcome
- Furthest stage or stop
- Final score/resources
- Duration in simulated turns or seconds
- Failure reason

Add domain metrics such as purchases, item usage, damage, rerolls, cascades, or payout variance only when they answer an active question.

Use `scripts/summarize_runs.py` to summarize the common JSONL fields. Read its help before adapting the schema.

## Tune with controlled experiments

1. Save the baseline output.
2. Change one coherent group of balance values.
3. Run the same policies and seeds.
4. Compare aggregate and per-stage results.
5. Inspect individual paired seeds that changed outcome.
6. Play representative human runs.
7. Accept, reject, or revise the hypothesis.

Do not tune against one seed, one average, or one “decent” policy.

## Add balance invariants

Turn objective assumptions into tests:

- Curves are monotonic where intended.
- Every live item is reachable through at least one delivery path.
- Retired and event-only content cannot leak into normal shops.
- Every stage can terminate.
- Resource values stay finite and within supported bounds.
- The final stage is actually reachable and ends the run.
- Descriptions derive numeric claims from live balance data.

These tests prevent content drift; simulation measures player-facing outcomes.

## Interpret results carefully

- Report sample size and policy version with every rate.
- Prefer confidence intervals or paired differences over raw percentages.
- Inspect distributions, not just means; roguelites often hide pain in tails.
- Separate inability of the policy from impossibility of the game.
- Treat a policy that exploits one mechanic as a design signal, not automatically a bug.
- Do not claim human difficulty from bot win rate alone.

## Keep simulation in the release process

Run a small deterministic suite in CI. Run larger benchmarks before major balance releases. Store compact summaries as build artifacts and fail CI only on hard invariants or deliberately chosen thresholds; noisy metrics should produce reviewable reports rather than flaky failures.
