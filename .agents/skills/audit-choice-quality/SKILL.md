---
name: audit-choice-quality
description: Audit existing narrative or gameplay choices for intention clarity, meaningful differentiation, information fairness, tradeoffs, dominant options, fake agency, morality-button design, feedback, consequence visibility, state persistence, and production efficiency. Use when the user asks whether choices are meaningful, wants to improve dialogue or quest options, or wants a systematic choice-quality review. Do not assume every flavor choice needs branching consequences.
---

# Audit Choice Quality

Audit the decision the player experiences, not only the text of the options.

A choice can be meaningful without creating a separate storyline. Conversely, a large branch can still feel meaningless if the player's intention is unclear or the game does not acknowledge it.

## Core Dimensions

### Decision clarity
What question does the player believe they are answering?

### Intention differentiation
Do options express meaningfully different intentions, strategies, identities, or relationship positions?

### Information fairness
Does the player know enough to make the type of decision being presented?

### Tradeoff quality
What is gained and lost by each option?

### Dominance
Is one option strictly better under visible incentives?

### Feedback
Does the game quickly acknowledge what the player chose?

### Persistence
Is the choice remembered where future content logically depends on it?

### Consequence legibility
Can the player connect later outcomes to the decision?

### Production efficiency
How much unique content is required to support the perceived agency?

## Agency Layers

Classify the choice:

- expression
- local reaction
- state
- content
- outcome

Do not penalize an expression choice for lacking ending-level consequences if the game presents it honestly as expression.

## Common Finding Types

- **Duplicate intention** — multiple options mean the same thing.
- **Dominant option** — one option offers equal or greater benefits with no meaningful cost.
- **Morality button** — options reduce a complex tension to obviously virtuous / cruel labels.
- **Fake strategic choice** — options imply strategic consequence but resolve identically and are not acknowledged.
- **Hidden punishment** — consequence could not reasonably be inferred and functions as arbitrary penalty.
- **Weak feedback** — game does not acknowledge the player's expressed intention.
- **State amnesia** — later content behaves as if the decision never happened.
- **Overproduction** — expensive branch produces little additional perceived agency.
- **Under-signaled commitment** — option locks major content without communicating commitment.
- **Strong flavor choice** — low-consequence option succeeds because expression and reaction are clear.

## Procedure

1. Identify the decision question.
2. Infer the intention represented by each option.
3. List what the player knows at decision time.
4. Map visible and hidden tradeoffs.
5. Check dominance.
6. Track immediate feedback.
7. Track persistent state and future callbacks.
8. Evaluate consequence legibility.
9. Compare unique-content cost with perceived agency.
10. Rank material findings.

## Severity

- **Critical** — choice breaks trust, e.g. major arbitrary consequence or false strategic representation.
- **High** — options are materially non-distinct, dominated, or forgotten.
- **Medium** — choice works but feedback, signaling, or tradeoff could be stronger.
- **Low** — wording or local optimization opportunity.

Confidence is separate.

## Repair Categories

- clarify decision question
- differentiate intention
- add tradeoff
- rebalance rewards
- signal risk
- signal commitment
- add immediate reaction
- persist state
- add callback
- convert to honest flavor choice
- fold branch while preserving state
- remove redundant option

## Output

### Choice verdict

### Decision question

### Option matrix

| Option | Intended meaning | Player-visible tradeoff | Actual consequence | Finding |
|---|---|---|---|---|

### Material findings

| Finding | Severity | Confidence | Why it matters | Smallest fix |
|---|---|---|---|---|

### Agency assessment
Expression / reaction / state / content / outcome.

### Production assessment
Unique content required vs perceived agency delivered.

## Failure Modes

Avoid:

- requiring every choice to branch the plot
- confusing unequal outcomes with bad design
- judging without the information available at decision time
- treating surprise as unfair by default
- ignoring role-play value
- recommending more branches when stateful callbacks would suffice
- rewriting option text before diagnosing the decision structure

## Final Quality Check

Every finding should connect to intention, information, tradeoff, feedback, state, consequence, or production cost.
