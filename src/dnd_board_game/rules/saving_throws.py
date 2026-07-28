from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .checks import resolve_saving_throw
from .dice import D20RollResult, RollModifier


class SaveDamageOnSuccess(StrEnum):
    NONE = "none"
    HALF = "half"


class SavingThrowEffectTag(StrEnum):
    POISON = "poison"
    FEAR = "fear"
    CHARM = "charm"
    MAGICAL_SLEEP = "magical_sleep"
    MAGIC = "magic"
    DISEASE = "disease"
    VISIBLE_DANGER = "visible_danger"


@dataclass(frozen=True, slots=True)
class SavingThrowRequest:
    ability: str
    dc: int
    source_label: str
    damage_on_success: SaveDamageOnSuccess = SaveDamageOnSuccess.NONE
    dc_source_label: str = ""
    failure_effect_label: str = "pełny efekt"
    success_effect_label: str = ""
    effect_tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.dc < 0:
            raise ValueError("Saving throw DC cannot be negative.")
        if not self.ability:
            raise ValueError("Saving throw ability is required.")
        if any(not tag.strip() for tag in self.effect_tags):
            raise ValueError("Saving throw effect tags cannot be empty.")
        if len(self.effect_tags) != len(set(self.effect_tags)):
            raise ValueError("Saving throw effect tags must be unique.")

    @property
    def resolved_success_effect_label(self) -> str:
        if self.success_effect_label:
            return self.success_effect_label
        if self.damage_on_success == SaveDamageOnSuccess.HALF:
            return "połowa obrażeń"
        return "brak obrażeń lub efektu"

    def as_payload(self) -> dict[str, object]:
        return {
            "ability": self.ability,
            "ability_label": ability_label_pl(self.ability),
            "dc": self.dc,
            "source_label": self.source_label,
            "dc_source_label": self.dc_source_label,
            "damage_on_success": self.damage_on_success.value,
            "success_effect_label": self.resolved_success_effect_label,
            "failure_effect_label": self.failure_effect_label,
            "effect_tags": list(self.effect_tags),
        }


@dataclass(frozen=True, slots=True)
class SavingThrowResult:
    actor_id: str
    actor_name: str
    ability: str
    dc: int
    natural_roll: int
    modifier: int
    total: int
    success: bool
    damage_multiplier: float
    modifiers: tuple[RollModifier, ...] = ()
    source_label: str = ""
    dc_source_label: str = ""
    damage_on_success: SaveDamageOnSuccess = SaveDamageOnSuccess.NONE

    def as_payload(self) -> dict[str, object]:
        return {
            "actor_id": self.actor_id,
            "actor_name": self.actor_name,
            "ability": self.ability,
            "ability_label": ability_label_pl(self.ability),
            "dc": self.dc,
            "natural_roll": self.natural_roll,
            "modifier": self.modifier,
            "total": self.total,
            "success": self.success,
            "damage_multiplier": self.damage_multiplier,
            "source_label": self.source_label,
            "dc_source_label": self.dc_source_label,
            "damage_on_success": self.damage_on_success.value,
            "modifier_components": [
                {
                    "label": modifier.label,
                    "value": modifier.value,
                    "modifier_type": modifier.modifier_type.value,
                }
                for modifier in self.modifiers
            ],
        }


def resolve_saving_throw_request(
    request: SavingThrowRequest,
    *,
    actor_id: str,
    actor_name: str,
    roll: D20RollResult,
) -> SavingThrowResult:
    check = resolve_saving_throw(roll, request.dc)
    return SavingThrowResult(
        actor_id=actor_id,
        actor_name=actor_name,
        ability=request.ability,
        dc=request.dc,
        natural_roll=roll.natural_roll,
        modifier=roll.breakdown.modifier_total,
        total=roll.total,
        success=check.success,
        damage_multiplier=save_damage_multiplier(
            check.success,
            request.damage_on_success,
        ),
        modifiers=roll.breakdown.active_modifiers,
        source_label=request.source_label,
        dc_source_label=request.dc_source_label,
        damage_on_success=request.damage_on_success,
    )


def save_damage_multiplier(
    success: bool,
    damage_on_success: SaveDamageOnSuccess | str,
) -> float:
    if not success:
        return 1.0
    if SaveDamageOnSuccess(damage_on_success) == SaveDamageOnSuccess.HALF:
        return 0.5
    return 0.0


def ability_label_pl(ability: str) -> str:
    return {
        "strength": "Siła",
        "dexterity": "Zręczność",
        "constitution": "Kondycja",
        "intelligence": "Inteligencja",
        "wisdom": "Mądrość",
        "charisma": "Charyzma",
    }.get(ability, ability)


__all__ = [
    "SaveDamageOnSuccess",
    "SavingThrowRequest",
    "SavingThrowResult",
    "SavingThrowEffectTag",
    "ability_label_pl",
    "resolve_saving_throw_request",
    "save_damage_multiplier",
]
