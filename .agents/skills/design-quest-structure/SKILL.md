---
name: design-quest-structure
description: Interactively design game quests around player verbs, motivation, objective structure, complications, state changes, optionality, reward, narrative consequences, and implementation scope. Use for main quests, side quests, companion quests, live events, mission chains, or when a story idea needs to become playable narrative rather than a synopsis.
---

# Design Quest Structure

Convert a narrative premise into **playable authored activity**.

Use this model:

**Motivation → Player verb → Objective → Resistance → Complication → Decision → Resolution → State change → Reward/aftermath**

The player should participate in the narrative through meaningful verbs rather than merely travel between exposition scenes.

## Inputs

Use available:

- quest premise
- player's role/fantasy
- available game mechanics
- locations
- characters/factions
- progression/reward systems
- desired duration
- production constraints
- required story state changes

## Define the Player Motivation

Why should the player care *now*?

Possible motivations:
- survival
- relationship
- curiosity
- duty
- greed
- revenge
- progression/resource
- faction commitment
- moral concern

Narrative motivation and systemic reward can coexist.

## Define Player Verbs

List what the player actually does:

- investigate
- observe
- question
- compare
- persuade
- trade
- sneak
- protect
- chase
- fight
- sabotage
- choose
- craft
- navigate

Avoid describing passive story consumption as a verb.

## Objective Grammar

Objectives should express understandable actions and progression.

Common structures:

- Discover → Investigate → Confront → Resolve
- Request → Acquire → Complication → Deliver/Choose
- Infiltrate → Learn → Decide → Escape
- Protect → Failure/escalation → Recover → Counterattack
- Explore → Find evidence → Reinterpret → Reveal

Do not apply a grammar mechanically; use it to expose repetitive structures.

## Complications

A complication should alter at least one of:

- objective
- information
- stakes
- available strategy
- relationship
- resource pressure
- moral interpretation

A second group of enemies is usually escalation, not a narrative complication.

## Choice and State

Where meaningful, define:

- decision question
- player intentions
- immediate feedback
- persistent state
- later callback

Use `$design-player-choice` for deep choice work.

## Quest Resolution

Define:

- success states
- partial success/failure where supported
- aftermath
- changed world/relationship state
- reward
- follow-up availability

## Production Scope

Track unique requirements:

- locations
- NPCs
- combat encounters
- cinematics
- VO
- animation
- bespoke mechanics
- branching
- QA paths

## Interactive Procedure

1. State the quest fantasy and motivation.
2. List available player verbs.
3. Choose a structural grammar.
4. Define objectives and transitions.
5. Add a complication that changes meaning or strategy.
6. Add decision/state where useful.
7. Define resolution and aftermath.
8. Check verb variety and pacing.
9. Check dependency/state requirements.
10. Estimate production scope.

## Output

### Quest fantasy

### Player motivation

### Primary verbs

### Quest flow

| Beat | Objective | Player verb | Resistance | Information/state change | Assets |
|---|---|---|---|---|---|

### Complication

### Choice/state changes

### Resolution and aftermath

### Reward

### Dependencies

### Production scope

## Failure Modes

Avoid:

- cutscene → walk → cutscene disguised as quest design
- every objective using the same verb
- complication that only adds more enemies
- reward unrelated to motivation/fantasy
- quest outcome that changes nothing
- requiring knowledge or state the player may not possess
- unique production assets for low-value beats
- branching whose consequence is immediately forgotten

## Final Quality Check

Ask: **What did the player do that made this story happen?** If the answer is mostly “watched,” redesign the playable structure.
