"""Deterministic light and sight rules for abstract exploration zones."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Sequence

from dnd_board_game.actors import Actor
from dnd_board_game.rules import RollMode


class LightLevel(StrEnum):
    BRIGHT = "bright"
    DIM = "dim"
    DARKNESS = "darkness"


@dataclass(frozen=True, slots=True)
class ExplorationVisibility:
    ambient_light: LightLevel
    illuminated_light: LightLevel
    perceived_light: LightLevel
    distance_feet: int
    can_see: bool
    perception_roll_mode: RollMode
    passive_perception_adjustment: int
    sense_used: str = "normal_vision"
    light_source_actor_id: str | None = None
    light_source_name: str | None = None

    def as_payload(self) -> dict[str, object]:
        return {
            "ambient_light": self.ambient_light.value,
            "illuminated_light": self.illuminated_light.value,
            "perceived_light": self.perceived_light.value,
            "distance_feet": self.distance_feet,
            "can_see": self.can_see,
            "perception_roll_mode": self.perception_roll_mode.value,
            "passive_perception_adjustment": self.passive_perception_adjustment,
            "sense_used": self.sense_used,
            "light_source_actor_id": self.light_source_actor_id,
            "light_source_name": self.light_source_name,
        }


def exploration_visibility(
    observer: Actor,
    *,
    ambient_light: LightLevel,
    distance_feet: int,
    party: Sequence[Actor] = (),
) -> ExplorationVisibility:
    """Resolve sight at an abstract distance from a co-located exploration party."""

    if distance_feet < 0 or distance_feet % 5:
        raise ValueError(
            "Exploration visibility distance must be a non-negative multiple of 5 feet."
        )
    illuminated, source_actor, source_name = _strongest_party_light(
        ambient_light,
        distance_feet,
        party,
    )
    senses = observer.senses
    exceptional_sight_distance = max(
        senses.blindsight_feet,
        senses.truesight_feet,
    )
    if exceptional_sight_distance > 0 and exceptional_sight_distance >= distance_feet:
        sense = (
            "truesight"
            if senses.truesight_feet >= distance_feet
            else "blindsight"
        )
        return ExplorationVisibility(
            ambient_light=ambient_light,
            illuminated_light=illuminated,
            perceived_light=LightLevel.BRIGHT,
            distance_feet=distance_feet,
            can_see=True,
            perception_roll_mode=RollMode.NORMAL,
            passive_perception_adjustment=0,
            sense_used=sense,
            light_source_actor_id=source_actor,
            light_source_name=source_name,
        )
    perceived = illuminated
    sense_used = "normal_vision"
    if senses.darkvision_feet > 0 and senses.darkvision_feet >= distance_feet:
        sense_used = "darkvision"
        if illuminated == LightLevel.DARKNESS:
            perceived = LightLevel.DIM
        elif illuminated == LightLevel.DIM:
            perceived = LightLevel.BRIGHT
    can_see = perceived != LightLevel.DARKNESS
    return ExplorationVisibility(
        ambient_light=ambient_light,
        illuminated_light=illuminated,
        perceived_light=perceived,
        distance_feet=distance_feet,
        can_see=can_see,
        perception_roll_mode=(
            RollMode.DISADVANTAGE
            if perceived == LightLevel.DIM
            else RollMode.NORMAL
        ),
        passive_perception_adjustment=-5 if perceived == LightLevel.DIM else 0,
        sense_used=sense_used,
        light_source_actor_id=source_actor,
        light_source_name=source_name,
    )


def _strongest_party_light(
    ambient_light: LightLevel,
    distance_feet: int,
    party: Sequence[Actor],
) -> tuple[LightLevel, str | None, str | None]:
    if ambient_light == LightLevel.BRIGHT:
        return ambient_light, None, None
    best = ambient_light
    source_actor_id: str | None = None
    source_name: str | None = None
    for actor in party:
        light = actor.active_light
        if light is None:
            continue
        candidate = LightLevel.DARKNESS
        if distance_feet <= light.current_bright_distance_feet:
            candidate = LightLevel.BRIGHT
        elif distance_feet <= (
            light.current_bright_distance_feet
            + light.current_dim_additional_feet
        ):
            candidate = LightLevel.DIM
        if _light_rank(candidate) > _light_rank(best):
            best = candidate
            source_actor_id = str(actor.id)
            source_name = light.source_name
    return best, source_actor_id, source_name


def _light_rank(level: LightLevel) -> int:
    return {
        LightLevel.DARKNESS: 0,
        LightLevel.DIM: 1,
        LightLevel.BRIGHT: 2,
    }[level]


__all__ = ["ExplorationVisibility", "LightLevel", "exploration_visibility"]
