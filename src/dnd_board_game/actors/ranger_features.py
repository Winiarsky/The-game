"""Deterministic level-1 ranger exploration features."""

from __future__ import annotations

from dataclasses import dataclass, replace

from dnd_board_game.rules.dice import D20RollRequest, RollMode

from .models import Actor

_CREATURE_TYPES = frozenset(
    {
        "aberration",
        "beast",
        "celestial",
        "construct",
        "dragon",
        "elemental",
        "fey",
        "fiend",
        "giant",
        "humanoid",
        "monstrosity",
        "ooze",
        "plant",
        "undead",
    }
)
_HUMANOID_RACE_PREFIX = "favored_enemy_humanoid_race_"


@dataclass(frozen=True, slots=True)
class NaturalExplorerBenefits:
    terrain: str
    difficult_terrain_slows_travel: bool = False
    can_become_lost_magically_only: bool = True
    remains_alert_during_other_activity: bool = True
    forage_yield_multiplier: int = 2
    learns_tracking_details: bool = True


def favored_enemy_creature_type(actor: Actor) -> str | None:
    prefix = "favored_enemy_"
    return next(
        (
            creature_type
            for feature in actor.features
            for creature_type in (feature.feature_id.removeprefix(prefix),)
            if creature_type in _CREATURE_TYPES
        ),
        None,
    )


def favored_enemy_humanoid_races(actor: Actor) -> tuple[str, ...]:
    return tuple(
        feature.feature_id.removeprefix(_HUMANOID_RACE_PREFIX)
        for feature in actor.features
        if feature.feature_id.startswith(_HUMANOID_RACE_PREFIX)
    )


def natural_explorer_terrain(actor: Actor) -> str | None:
    prefix = "natural_explorer_"
    return next(
        (
            feature.feature_id.removeprefix(prefix)
            for feature in actor.features
            if feature.feature_id.startswith(prefix)
        ),
        None,
    )


def apply_favored_enemy_advantage(
    actor: Actor,
    request: D20RollRequest,
    *,
    creature_type: str,
    context: str,
    humanoid_race: str | None = None,
) -> D20RollRequest:
    """Grant the 2014 advantage for tracking or recalling favored enemies."""
    if favored_enemy_creature_type(actor) != creature_type:
        return request
    if creature_type == "humanoid":
        races = favored_enemy_humanoid_races(actor)
        if humanoid_race is None or humanoid_race not in races:
            return request
    if context not in {"survival_tracking", "intelligence_recall"}:
        return request
    mode = (
        RollMode.NORMAL
        if request.mode == RollMode.DISADVANTAGE
        else RollMode.ADVANTAGE
    )
    return replace(request, mode=mode)


def natural_explorer_benefits(
    actor: Actor,
    *,
    terrain: str,
) -> NaturalExplorerBenefits | None:
    return (
        NaturalExplorerBenefits(terrain)
        if natural_explorer_terrain(actor) == terrain
        else None
    )


__all__ = [
    "NaturalExplorerBenefits",
    "apply_favored_enemy_advantage",
    "favored_enemy_creature_type",
    "favored_enemy_humanoid_races",
    "natural_explorer_benefits",
    "natural_explorer_terrain",
]
