"""Persistent Web spell zone checks and restraint resolution."""

from __future__ import annotations

from dataclasses import dataclass, replace
from random import Random
from typing import Sequence

from dnd_board_game.actors import Actor
from dnd_board_game.rules import ActiveEffect, EffectDuration, SavingThrowResult
from dnd_board_game.world import Coordinate

from .conditions import (
    CombatCondition,
    ConditionSaveTiming,
    apply_condition,
    has_condition,
)
from .session import CombatState
from .spells import resolve_spell_save


def web_zone_contains(effect: ActiveEffect, position: Coordinate) -> bool:
    if effect.kind != "web_zone" or effect.anchor_position is None:
        return False
    if position in effect.excluded_positions:
        return False
    side = max(1, effect.value // 5)
    before = (side - 1) // 2
    after = side - before - 1
    return (
        effect.anchor_position.col - before
        <= position.col
        <= effect.anchor_position.col + after
        and effect.anchor_position.row - before
        <= position.row
        <= effect.anchor_position.row + after
    )


@dataclass(frozen=True, slots=True)
class WebSaveResolution:
    state: CombatState
    saving_throw: SavingThrowResult | None
    restrained: bool


def resolve_web_save(
    state: CombatState,
    *,
    actor_id: str,
    zone: ActiveEffect,
    rng: Random,
) -> WebSaveResolution:
    actor = next(candidate for candidate in state.actors if str(candidate.id) == actor_id)
    if not web_zone_contains(zone, actor.position):
        return WebSaveResolution(state, None, False)
    if has_condition(state.condition_states, actor_id, CombatCondition.RESTRAINED):
        return WebSaveResolution(state, None, True)
    caster = next(
        (
            candidate
            for candidate in state.actors
            if str(candidate.id) == zone.source_actor_id
        ),
        None,
    )
    dc = caster.spell_save_dc if caster is not None else 10
    save = resolve_spell_save(
        actor,
        ability="dexterity",
        dc=dc,
        natural_roll=rng.randint(1, 20),
        condition_states=state.condition_states,
        combat_actors=state.actors,
    )
    if save.success:
        return WebSaveResolution(state, save, False)
    application = apply_condition(
        state.condition_states,
        actor,
        CombatCondition.RESTRAINED,
        source_actor_id=zone.source_actor_id,
        source_label=f"Sieć: {zone.label}",
        duration=EffectDuration.CONCENTRATION if state.shared_mana else EffectDuration.PERMANENT,
        save_ability="strength",
        save_dc=dc,
        save_timing=ConditionSaveTiming.ACTION,
        source_spell_id=zone.source.id if state.shared_mana and zone.source else "web",
        source_spell_level=zone.spell_level,
    )
    return WebSaveResolution(
        replace(state, condition_states=application.condition_states),
        save,
        application.applied,
    )


def web_zones(
    active_effects: Sequence[ActiveEffect],
) -> tuple[ActiveEffect, ...]:
    return tuple(effect for effect in active_effects if effect.kind == "web_zone")


__all__ = [
    "WebSaveResolution",
    "resolve_web_save",
    "web_zone_contains",
    "web_zones",
]
