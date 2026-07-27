"""Deterministic D&D 5e 2014 travel pace, navigation, and forced march."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Mapping

from dnd_board_game.actors import (
    Actor,
    ExhaustionRollKind,
    ability_check_roll_modifiers,
    apply_exhaustion_to_roll_request,
    increase_exhaustion,
    saving_throw_roll_modifiers,
)
from dnd_board_game.rules import (
    D20RollInput,
    D20RollRequest,
    D20RollResult,
    resolve_ability_check,
    resolve_d20_roll,
)

from .models import ScenarioContinuation, TravelPace


@dataclass(frozen=True, slots=True)
class TravelD20Input:
    natural_roll: int
    natural_roll_2: int | None = None


@dataclass(frozen=True, slots=True)
class TravelNavigationResult:
    required: bool
    success: bool
    actor_id: str | None = None
    roll: D20RollResult | None = None
    dc: int | None = None
    delay_minutes: int = 0

    def as_payload(self) -> dict[str, object]:
        return {
            "required": self.required,
            "success": self.success,
            "actor_id": self.actor_id,
            "natural_roll": self.roll.natural_roll if self.roll else None,
            "total": self.roll.total if self.roll else None,
            "dc": self.dc,
            "delay_minutes": self.delay_minutes,
        }


@dataclass(frozen=True, slots=True)
class ForcedMarchResult:
    actor_id: str
    hour_index: int
    dc: int
    roll: D20RollResult
    success: bool
    exhaustion_before: int
    exhaustion_after: int

    def as_payload(self) -> dict[str, object]:
        return {
            "actor_id": self.actor_id,
            "hour_index": self.hour_index,
            "dc": self.dc,
            "natural_roll": self.roll.natural_roll,
            "total": self.roll.total,
            "success": self.success,
            "exhaustion_before": self.exhaustion_before,
            "exhaustion_after": self.exhaustion_after,
        }


@dataclass(frozen=True, slots=True)
class TravelResolution:
    continuation: ScenarioContinuation
    pace: TravelPace
    actors: tuple[Actor, ...]
    base_minutes: int
    pace_minutes: int
    total_minutes: int
    passive_perception_modifier: int
    allows_stealth: bool
    navigation: TravelNavigationResult
    forced_march_results: tuple[ForcedMarchResult, ...] = ()

    def as_payload(self) -> dict[str, object]:
        return {
            "pace": self.pace.value,
            "base_minutes": self.base_minutes,
            "pace_minutes": self.pace_minutes,
            "total_minutes": self.total_minutes,
            "passive_perception_modifier": self.passive_perception_modifier,
            "allows_stealth": self.allows_stealth,
            "navigation": self.navigation.as_payload(),
            "forced_march": [
                result.as_payload() for result in self.forced_march_results
            ],
            "exhaustion_levels": {
                str(actor.id): actor.exhaustion_level for actor in self.actors
            },
        }


def travel_minutes_for_pace(
    base_minutes: int,
    pace: TravelPace,
) -> int:
    if base_minutes < 0:
        raise ValueError("Travel duration cannot be negative.")
    if pace == TravelPace.FAST:
        return ceil(base_minutes * 3 / 4)
    if pace == TravelPace.SLOW:
        return ceil(base_minutes * 4 / 3)
    return base_minutes


def forced_march_check_count(
    total_minutes: int,
    *,
    safe_travel_minutes: int,
) -> int:
    return max(0, ceil((total_minutes - safe_travel_minutes) / 60))


def resolve_travel(
    continuation: ScenarioContinuation,
    actors: tuple[Actor, ...],
    *,
    pace: TravelPace,
    navigator_actor_id: str | None = None,
    navigation_roll: TravelD20Input | None = None,
    forced_march_rolls: Mapping[str, tuple[TravelD20Input, ...]] | None = None,
) -> TravelResolution:
    policy = continuation.travel_policy
    pace_minutes = travel_minutes_for_pace(continuation.travel_minutes, pace)
    navigation = _resolve_navigation(
        policy.navigation_dc,
        policy.navigation_ability,
        policy.navigation_skill,
        policy.navigation_failure_delay_minutes,
        actors,
        navigator_actor_id=navigator_actor_id,
        navigation_roll=navigation_roll,
    )
    total_minutes = pace_minutes + navigation.delay_minutes
    check_count = forced_march_check_count(
        total_minutes,
        safe_travel_minutes=policy.safe_travel_minutes,
    )
    rolls = forced_march_rolls or {}
    updated_actors: list[Actor] = []
    march_results: list[ForcedMarchResult] = []
    for actor in actors:
        actor_rolls = rolls.get(str(actor.id), ())
        if len(actor_rolls) < check_count:
            raise ValueError(
                f"{actor.name} wymaga co najmniej {check_count} wyników forced march."
            )
        current = actor
        for hour_index, raw_roll in enumerate(
            actor_rolls[:check_count],
            start=1,
        ):
            if current.exhaustion_level >= 6:
                break
            dc = 10 + hour_index
            request = apply_exhaustion_to_roll_request(
                current,
                D20RollRequest(
                    modifiers=saving_throw_roll_modifiers(
                        current,
                        "constitution",
                    )
                ),
                ExhaustionRollKind.SAVING_THROW,
            )
            result = resolve_d20_roll(
                D20RollInput(
                    request=request,
                    natural_roll=raw_roll.natural_roll,
                    natural_roll_2=raw_roll.natural_roll_2,
                )
            )
            success = resolve_ability_check(result, dc).success
            before = current.exhaustion_level
            if not success:
                current = increase_exhaustion(current)
            march_results.append(
                ForcedMarchResult(
                    actor_id=str(actor.id),
                    hour_index=hour_index,
                    dc=dc,
                    roll=result,
                    success=success,
                    exhaustion_before=before,
                    exhaustion_after=current.exhaustion_level,
                )
            )
        updated_actors.append(current)
    return TravelResolution(
        continuation=continuation,
        pace=pace,
        actors=tuple(updated_actors),
        base_minutes=continuation.travel_minutes,
        pace_minutes=pace_minutes,
        total_minutes=total_minutes,
        passive_perception_modifier=-5 if pace == TravelPace.FAST else 0,
        allows_stealth=pace == TravelPace.SLOW,
        navigation=navigation,
        forced_march_results=tuple(march_results),
    )


def _resolve_navigation(
    dc: int | None,
    ability: str,
    skill: str | None,
    failure_delay_minutes: int,
    actors: tuple[Actor, ...],
    *,
    navigator_actor_id: str | None,
    navigation_roll: TravelD20Input | None,
) -> TravelNavigationResult:
    if dc is None:
        return TravelNavigationResult(required=False, success=True)
    navigator = next(
        (
            actor
            for actor in actors
            if str(actor.id) == (navigator_actor_id or "")
        ),
        None,
    )
    if navigator is None:
        raise ValueError("Podróż wymaga wskazania nawigatora.")
    if navigation_roll is None:
        raise ValueError("Podróż wymaga wyniku rzutu na nawigację.")
    request = apply_exhaustion_to_roll_request(
        navigator,
        D20RollRequest(
            modifiers=ability_check_roll_modifiers(
                navigator,
                ability,
                skill=skill,
            )
        ),
        ExhaustionRollKind.ABILITY_CHECK,
    )
    roll = resolve_d20_roll(
        D20RollInput(
            request=request,
            natural_roll=navigation_roll.natural_roll,
            natural_roll_2=navigation_roll.natural_roll_2,
        )
    )
    success = resolve_ability_check(roll, dc).success
    return TravelNavigationResult(
        required=True,
        success=success,
        actor_id=str(navigator.id),
        roll=roll,
        dc=dc,
        delay_minutes=0 if success else failure_delay_minutes,
    )


__all__ = [
    "ForcedMarchResult",
    "TravelD20Input",
    "TravelNavigationResult",
    "TravelResolution",
    "forced_march_check_count",
    "resolve_travel",
    "travel_minutes_for_pace",
]
