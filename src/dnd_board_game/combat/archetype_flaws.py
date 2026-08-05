"""Deterministic combat rules for the seven board-game archetype flaws."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from dnd_board_game.actors import Actor, Faction, actor_has_feature
from dnd_board_game.rules import (
    ActiveEffect,
    EffectDuration,
    EffectSource,
    EffectSourceType,
    RollModifier,
    RollModifierType,
)

from .conditions import ConditionState
from .spells import grid_distance_feet


FLAW_FEATURE_IDS: dict[str, tuple[str, str]] = {
    "garran": ("flaw_command_guilt", "Skaza: Wina dowódcy"),
    "brakka": ("flaw_chains", "Skaza: Bitewny amok"),
    "mira": ("flaw_interrogation", "Skaza: Lęk przed przesłuchaniem"),
    "dagna": ("flaw_leave_no_one", "Skaza: Nikogo nie zostawiam"),
    "lorian": ("flaw_approval", "Skaza: Głód aprobaty"),
    "nimra": ("flaw_arcane_echo", "Skaza: Echo magicznego wycieku"),
    "erynd": ("flaw_ambush_survivor", "Skaza: Ocalały z zasadzki"),
}

DYNAMIC_FLAW_KINDS = frozenset(
    {
        "flaw_command_guilt_active",
        "flaw_chains_active",
        "flaw_triage_active",
    }
)


@dataclass(frozen=True, slots=True)
class FlawActivation:
    actor_id: str
    kind: str
    label: str
    value: int = 0
    target_actor_id: str | None = None

    def as_effect(self) -> ActiveEffect:
        return ActiveEffect(
            id=f"{self.kind}:{self.actor_id}",
            actor_id=self.actor_id,
            kind=self.kind,
            label=self.label,
            object_id=f"feature:{self.kind}",
            value=self.value,
            source=EffectSource(EffectSourceType.SYSTEM, self.kind, self.label),
            duration=EffectDuration.UNTIL_ENCOUNTER_END,
            target_actor_id=self.target_actor_id,
        )


def _living_downed_allies(actor: Actor, actors: Sequence[Actor]) -> tuple[Actor, ...]:
    return tuple(
        ally
        for ally in actors
        if ally.id != actor.id
        and ally.faction == actor.faction == Faction.ALLY
        and ally.hp <= 0
        and not ally.is_dead()
        and grid_distance_feet(actor.position, ally.position) <= 30
    )


def dynamic_flaw_activations(
    actors: Sequence[Actor],
    condition_states: Sequence[ConditionState] = (),
) -> tuple[FlawActivation, ...]:
    """Derive live flaws from actor positions, HP and conditions."""
    activations: list[FlawActivation] = []
    for actor in actors:
        actor_id = str(actor.id)
        if actor.is_defeated():
            continue
        downed = _living_downed_allies(actor, actors)
        if actor_has_feature(actor, "flaw_command_guilt") and any(
            grid_distance_feet(actor.position, ally.position) > 5 for ally in downed
        ):
            activations.append(
                FlawActivation(
                    actor_id,
                    "flaw_command_guilt_active",
                    "Wina dowódcy",
                    -1,
                )
            )
        if actor_has_feature(actor, "flaw_leave_no_one") and downed:
            activations.append(
                FlawActivation(
                    actor_id,
                    "flaw_triage_active",
                    "Nikogo nie zostawiam",
                )
            )
    return tuple(activations)


def synchronize_dynamic_flaw_effects(
    actors: Sequence[Actor],
    condition_states: Sequence[ConditionState],
    active_effects: Sequence[ActiveEffect],
) -> tuple[ActiveEffect, ...]:
    retained = tuple(
        effect for effect in active_effects if effect.kind not in DYNAMIC_FLAW_KINDS
    )
    return (*retained, *(item.as_effect() for item in dynamic_flaw_activations(actors, condition_states)))


def flaw_saving_throw_modifiers(
    actor: Actor,
    active_effects: Sequence[ActiveEffect],
) -> tuple[RollModifier, ...]:
    return tuple(
        RollModifier(
            effect.label,
            effect.value,
            RollModifierType.CUSTOM,
            stacking_key=effect.kind,
        )
        for effect in active_effects
        if effect.actor_id == str(actor.id)
        and effect.kind == "flaw_command_guilt_active"
    )


def flaw_blocks_concentration_spell(
    actor: Actor,
    active_effects: Sequence[ActiveEffect],
) -> bool:
    return actor_has_feature(actor, "flaw_arcane_echo") and any(
        effect.actor_id == str(actor.id) and effect.kind == "flaw_arcane_echo_active"
        for effect in active_effects
    )


def flaw_blocks_equipment_use(
    actor: Actor,
    active_effects: Sequence[ActiveEffect],
) -> bool:
    """Return whether Brakka's flaw blocks active item use during Rage.

    Held weapons remain usable: this rule blocks consumables, scrolls and item
    powers, not ordinary attacks made with already equipped weapons.
    """

    return actor_has_feature(actor, "flaw_chains") and any(
        effect.actor_id == str(actor.id) and effect.kind == "rage"
        for effect in active_effects
    )


__all__ = [
    "DYNAMIC_FLAW_KINDS",
    "FLAW_FEATURE_IDS",
    "FlawActivation",
    "dynamic_flaw_activations",
    "flaw_blocks_concentration_spell",
    "flaw_blocks_equipment_use",
    "flaw_saving_throw_modifiers",
    "synchronize_dynamic_flaw_effects",
]
