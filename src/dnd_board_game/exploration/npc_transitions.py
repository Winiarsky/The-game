from __future__ import annotations

from dataclasses import dataclass

from dnd_board_game.combat import scene_flag

from .effects import ExplorationEffectResult, apply_exploration_effect
from .models import (
    ExplorationState,
    NpcSceneTransition,
    NpcTransitionReaction,
    NpcTransitionVariant,
    PendingNpcTransition,
)


@dataclass(frozen=True, slots=True)
class NpcTransitionPlan:
    definition: NpcSceneTransition
    variant: NpcTransitionVariant

    @property
    def pending(self) -> PendingNpcTransition:
        return PendingNpcTransition(
            self.definition.id,
            self.variant.id,
            self.definition.npc_id,
        )

    def as_payload(self) -> dict[str, object]:
        return {
            "transition_id": self.definition.id,
            "variant_id": self.variant.id,
            "npc_id": self.definition.npc_id,
            "title": self.variant.title,
            "narration": self.variant.narration,
            "reactions": [reaction.as_payload() for reaction in self.variant.reactions],
        }


@dataclass(frozen=True, slots=True)
class NpcTransitionResolution:
    state: ExplorationState
    plan: NpcTransitionPlan
    reaction: NpcTransitionReaction
    effect_results: tuple[ExplorationEffectResult, ...]


def plan_npc_transition(
    transitions: tuple[NpcSceneTransition, ...],
    *,
    transition_id: str,
    state: ExplorationState,
    resolved_encounter_trigger_ids: set[str] | frozenset[str],
) -> NpcTransitionPlan:
    definition = next(
        (item for item in transitions if item.id == transition_id.strip().lower()),
        None,
    )
    if definition is None:
        raise ValueError(f"Unknown NPC scene transition: {transition_id}.")
    resolved = set(resolved_encounter_trigger_ids)
    variant = next(
        (
            candidate
            for candidate in definition.variants
            if _variant_matches(candidate, state, resolved)
        ),
        None,
    )
    if variant is None:
        raise ValueError(f"NPC scene transition {definition.id} has no matching variant.")
    return NpcTransitionPlan(definition, variant)


def restore_npc_transition_plan(
    transitions: tuple[NpcSceneTransition, ...],
    pending: PendingNpcTransition,
) -> NpcTransitionPlan:
    definition = next(
        (item for item in transitions if item.id == pending.transition_id),
        None,
    )
    if definition is None or definition.npc_id != pending.npc_id:
        raise ValueError(f"Unknown saved NPC scene transition: {pending.transition_id}.")
    variant = next(
        (item for item in definition.variants if item.id == pending.variant_id),
        None,
    )
    if variant is None:
        raise ValueError(f"Unknown saved NPC transition variant: {pending.variant_id}.")
    return NpcTransitionPlan(definition, variant)


def resolve_npc_transition_reaction(
    state: ExplorationState,
    plan: NpcTransitionPlan,
    reaction_id: str,
) -> NpcTransitionResolution:
    reaction = plan.variant.reaction(reaction_id)
    if reaction is None:
        raise ValueError(
            f"NPC transition variant {plan.variant.id} has no reaction: {reaction_id}."
        )
    current = state
    results: list[ExplorationEffectResult] = []
    for effect in reaction.effects:
        result = apply_exploration_effect(current, effect)
        current = result.state
        results.append(result)
    return NpcTransitionResolution(current, plan, reaction, tuple(results))


def _variant_matches(
    variant: NpcTransitionVariant,
    state: ExplorationState,
    resolved_encounter_trigger_ids: set[str],
) -> bool:
    if any(not scene_flag(state.flags, flag, False) for flag in variant.required_flags):
        return False
    if any(scene_flag(state.flags, flag, False) for flag in variant.forbidden_flags):
        return False
    if any(
        trigger_id not in resolved_encounter_trigger_ids
        for trigger_id in variant.required_resolved_encounter_trigger_ids
    ):
        return False
    if any(
        trigger_id in resolved_encounter_trigger_ids
        for trigger_id in variant.forbidden_resolved_encounter_trigger_ids
    ):
        return False
    return True


__all__ = [
    "NpcTransitionPlan",
    "NpcTransitionResolution",
    "plan_npc_transition",
    "resolve_npc_transition_reaction",
    "restore_npc_transition_plan",
]
