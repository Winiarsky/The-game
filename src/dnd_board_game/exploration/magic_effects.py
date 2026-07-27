"""Minute-based lifecycle for exploration magic."""

from __future__ import annotations

from dataclasses import dataclass, replace

from dnd_board_game.combat import set_scene_flag

from .models import ExplorationState, TimedMagicEffect


@dataclass(frozen=True, slots=True)
class ExplorationTimeAdvance:
    state: ExplorationState
    elapsed_minutes: int
    expired_effects: tuple[TimedMagicEffect, ...] = ()


def apply_timed_magic_effect(
    state: ExplorationState,
    effect: TimedMagicEffect,
) -> ExplorationState:
    remaining = tuple(
        current
        for current in state.magic_effects
        if current.flag_key != effect.flag_key
    )
    return replace(
        state,
        flags=set_scene_flag(state.flags, effect.flag_key, effect.flag_value),
        magic_effects=(*remaining, effect),
    )


def advance_exploration_time(
    state: ExplorationState,
    minutes: int,
) -> ExplorationTimeAdvance:
    if minutes < 0:
        raise ValueError("Exploration time advance cannot be negative.")
    elapsed = state.elapsed_minutes + minutes
    expired = tuple(
        effect
        for effect in state.magic_effects
        if effect.expires_at_minute is not None
        and effect.expires_at_minute <= elapsed
    )
    expired_ids = {effect.id for effect in expired}
    remaining = tuple(
        effect for effect in state.magic_effects if effect.id not in expired_ids
    )
    flags = state.flags
    for effect in expired:
        replacement = next(
            (
                current
                for current in reversed(remaining)
                if current.flag_key == effect.flag_key
            ),
            None,
        )
        flags = set_scene_flag(
            flags,
            effect.flag_key,
            replacement.flag_value if replacement is not None else False,
        )
    return ExplorationTimeAdvance(
        state=replace(
            state,
            elapsed_minutes=elapsed,
            flags=flags,
            magic_effects=remaining,
        ),
        elapsed_minutes=minutes,
        expired_effects=expired,
    )
