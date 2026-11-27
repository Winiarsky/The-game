# Narrative State Audit Checklist

## Variables
- explicit default?
- all values documented?
- read-before-set?
- set-but-never-read?
- duplicated concept?

## Transitions
- valid predecessor?
- valid successor?
- unintended regression?
- terminal states respected?

## Combinations
- mutually exclusive states simultaneously true?
- all reachable combinations handled?
- old states cleared when new state replaces them?

## Consequences
- meaningful choice remembered after reconvergence?
- dialogue/quests react where expected?
- reset explained?

## Reachability
- unreachable branch?
- dead end?
- content gated by impossible conjunction?
