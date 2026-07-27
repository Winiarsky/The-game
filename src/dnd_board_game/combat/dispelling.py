from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Sequence

from dnd_board_game.rules import ActiveEffect, EffectSourceType

from .conditions import CombatCondition, ConditionState
from .session import CombatState


@dataclass(frozen=True, slots=True)
class DispellableSpellEffect:
    target_actor_id: str
    source_actor_id: str | None
    spell_id: str
    label: str
    spell_level: int
    active_effect_ids: tuple[str, ...] = ()
    conditions: tuple[CombatCondition, ...] = ()

    @property
    def key(self) -> str:
        source = self.source_actor_id or "-"
        return f"{self.target_actor_id}:{source}:{self.spell_id}:{self.spell_level}"


@dataclass(frozen=True, slots=True)
class DispelRemoval:
    state: CombatState
    active_effects: tuple[ActiveEffect, ...]
    removed_active_effect_ids: tuple[str, ...]
    removed_conditions: tuple[CombatCondition, ...]


def dispellable_spell_effects_for_target(
    state: CombatState,
    active_effects: Sequence[ActiveEffect],
    target_actor_id: str,
) -> tuple[DispellableSpellEffect, ...]:
    grouped: dict[
        tuple[str | None, str, int],
        dict[str, object],
    ] = {}
    for effect in active_effects:
        source = effect.source
        if (
            source is None
            or source.source_type != EffectSourceType.SPELL
            or effect.spell_level is None
            or (
                effect.actor_id != target_actor_id
                and effect.target_actor_id != target_actor_id
            )
        ):
            continue
        group = grouped.setdefault(
            (effect.source_actor_id, source.id, effect.spell_level),
            {
                "label": source.label or effect.label or source.id,
                "effect_ids": [],
                "conditions": [],
            },
        )
        effect_ids = group["effect_ids"]
        assert isinstance(effect_ids, list)
        effect_ids.append(effect.id)
    for condition in state.condition_states:
        if (
            condition.actor_id != target_actor_id
            or condition.source_spell_id is None
            or condition.source_spell_level is None
        ):
            continue
        group = grouped.setdefault(
            (
                condition.source_actor_id,
                condition.source_spell_id,
                condition.source_spell_level,
            ),
            {
                "label": condition.source_label or condition.source_spell_id,
                "effect_ids": [],
                "conditions": [],
            },
        )
        conditions = group["conditions"]
        assert isinstance(conditions, list)
        conditions.append(condition.condition)
    return tuple(
        DispellableSpellEffect(
            target_actor_id=target_actor_id,
            source_actor_id=source_actor_id,
            spell_id=spell_id,
            label=str(group["label"]),
            spell_level=spell_level,
            active_effect_ids=tuple(sorted(set(group["effect_ids"]))),
            conditions=tuple(dict.fromkeys(group["conditions"])),
        )
        for (source_actor_id, spell_id, spell_level), group in sorted(
            grouped.items(),
            key=lambda item: (
                item[0][2],
                item[0][1],
                item[0][0] or "",
            ),
        )
    )


def dispellable_target_ids(
    state: CombatState,
    active_effects: Sequence[ActiveEffect],
) -> tuple[str, ...]:
    return tuple(
        str(actor.id)
        for actor in state.actors
        if not actor.is_defeated()
        and dispellable_spell_effects_for_target(
            state,
            active_effects,
            str(actor.id),
        )
    )


def remove_dispellable_spell_effect(
    state: CombatState,
    active_effects: Sequence[ActiveEffect],
    effect: DispellableSpellEffect,
) -> DispelRemoval:
    current = next(
        (
            candidate
            for candidate in dispellable_spell_effects_for_target(
                state,
                active_effects,
                effect.target_actor_id,
            )
            if candidate.key == effect.key
        ),
        None,
    )
    if current is None:
        return DispelRemoval(state, tuple(active_effects), (), ())
    effect_ids = set(current.active_effect_ids)
    conditions = set(current.conditions)
    remaining_effects = tuple(
        candidate
        for candidate in active_effects
        if candidate.id not in effect_ids
    )
    remaining_conditions = tuple(
        condition
        for condition in state.condition_states
        if not (
            condition.actor_id == current.target_actor_id
            and condition.source_actor_id == current.source_actor_id
            and condition.source_spell_id == current.spell_id
            and condition.source_spell_level == current.spell_level
            and condition.condition in conditions
        )
    )
    return DispelRemoval(
        replace(state, condition_states=remaining_conditions),
        remaining_effects,
        current.active_effect_ids,
        current.conditions,
    )
