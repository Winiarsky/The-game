from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class TriggerEventType(StrEnum):
    ATTACK_HIT = "attack_hit"
    DAMAGE_TAKEN = "damage_taken"
    ACTOR_MOVED = "actor_moved"
    TURN_START = "turn_start"
    TURN_END = "turn_end"
    SHORT_REST_COMPLETED = "short_rest_completed"
    LONG_REST_COMPLETED = "long_rest_completed"
    ENCOUNTER_ENDED = "encounter_ended"


class TriggerEffectKind(StrEnum):
    GRANT_TEMP_HP = "grant_temp_hp"


@dataclass(frozen=True, slots=True)
class ActorTrigger:
    id: str
    label: str
    event_type: TriggerEventType
    effect_kind: TriggerEffectKind
    value: int

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Trigger id cannot be empty.")
        if not self.label.strip():
            raise ValueError("Trigger label cannot be empty.")
        if self.value < 0:
            raise ValueError("Trigger value cannot be negative.")
