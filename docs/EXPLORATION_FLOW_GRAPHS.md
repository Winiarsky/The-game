# Exploration Flow Graphs

Exploration flow graphs organize authored scene and NPC routes without replacing D&D
mechanics. They are deterministic content: the runtime maps a player-selected
goal to one currently active route. The LLM interprets only the method described
inside that goal; it cannot switch goals, activate a route whose state condition
is false, or invent its mechanical outcome.

## Runtime model

A graph belongs to exactly one exploration challenge or NPC and contains:

- state-derived nodes with `all_flags`, `any_flags`, and `no_flags` conditions,
- transitions connecting one player-facing goal to one or more source nodes,
- a route kind identifying the deterministic resolver,
- references to authored challenge options, observations, and source actions.

Nodes do not store a mutable `current_node_id`. Every active node is derived
from the canonical exploration state. This allows independent facts such as an
opened lock, discovered wall route, active alarm, and found tool to coexist.

Supported route kinds in the first vertical slice:

- `challenge_option` — resolves through an authored challenge option and the
  normal D&D check flow,
- `observation_router` — matches the declaration to one of the transition's
  authored graded observations,
- `npc_intent` — locks a selected NPC goal to one authored intent before the
  method is sent to the LLM.

## Player declaration flow

```text
selected visible goal
  -> runtime resolves its active graph transition
  -> player selects participants and describes the method
  -> deterministic/source-first intent matching
  -> optional LLM interpretation
  -> referenced mechanic resolver
  -> outcome effects and flags
  -> active nodes and goals derived again
```

If a transition is unavailable, the runtime rejects it before a roll. Player
presentation should turn that rejection into an in-fiction response rather
than expose node ids, flags, or validator details.

The general GM message field is not an action entry point. It answers questions
without creating a roll or changing scene state. Actions begin only from a
visible goal card and its separate method field.

## Content example

```json
{
  "id": "open_gate_lock",
  "goal_id": "open_lock",
  "from": ["lock_closed"],
  "route_kind": "challenge_option",
  "route_ref": "lockpick_gate"
}
```

The reference implementation is
`content/scenarios/abandoned_watchtower/exploration/flows.json`.
It contains both `closed_gate_flow` and the first NPC graph,
`wounded_scout_flow`.

## LLM method contract

For a `challenge_option` transition the graph option owns the base ability,
skill or tool, DC, participant policy, outcome branches, noise, complications,
and completion effects. The LLM response may omit all of those fields.

The LLM remains responsible only for interpreting the declared method:

- approach label and allowed tags,
- grounded resource/source references,
- allowed situational modifiers and roll mode,
- improvised-tool description when applicable,
- pre-roll narration.

The runtime fills the omitted mechanics before validation and records the
grounded proposal. This keeps old classifier clients compatible while making
the reduced contract the preferred prompt format for migrated graph routes.

## Validation

Scenario loading rejects:

- duplicate flow, challenge ownership or NPC ownership,
- unknown challenges, NPCs, nodes, goals, intents, options, observations, or source actions,
- goals missing a transition,
- duplicate goal transitions,
- non-terminal nodes without outgoing routes,
- contradictory or malformed flag conditions.

## Migration

Challenges without a flow graph continue to use the legacy
`InteractionGoal.required_flags`, `forbidden_flags`, `resolution_option_id`,
`observation_ids`, and `source_actions` fields.

For a migrated challenge, the graph is authoritative for visible goals,
routing, observation scope and base check mechanics. Do not duplicate
`required_flags`, `forbidden_flags`, `resolution_option_id`, `observation_ids`
or `default_observation_id` on its goal cards. A goal may still define the
descriptive body of a procedural `source_action`; the transition explicitly
lists which of those action ids belong to the active route.

`ExplorationGoalExecutionPlanner` is the application boundary between a
selected card and UI pending state. It revalidates the active route, resolves
the authored participant policy, checks actor/tool eligibility and restricts
source actions and observations to that route. The UI records and presents the
returned plan but does not recreate those decisions.

`NpcGoalExecutionPlanner` performs the equivalent work for conversations. It
derives visible NPC goals from flags, locks the transition's `route_ref` as the
intent, and validates the selected leader/helper or whole party before the
players describe their method. The NPC LLM receives the routed intent and
cannot move the declaration to another conversation branch. An NPC permission
may additionally own a fixed `check` and authored `effects_on_success` /
`effects_on_failure`. On a routed goal the runtime replaces LLM-proposed
mechanics with those values. Social request risk remains an LLM classification,
but attitude-to-DC conversion and effects are deterministic.
