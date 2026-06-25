from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Iterable


class RollMode(StrEnum):
    NORMAL = "normal"
    ADVANTAGE = "advantage"
    DISADVANTAGE = "disadvantage"


class RollModifierType(StrEnum):
    ABILITY = "ability"
    PROFICIENCY = "proficiency"
    EXPERTISE = "expertise"
    ITEM = "item"
    SPELL = "spell"
    FEATURE = "feature"
    COVER = "cover"
    SITUATIONAL = "situational"
    CUSTOM = "custom"


@dataclass(frozen=True, slots=True)
class RollModifier:
    label: str
    value: int
    modifier_type: RollModifierType
    stacking_key: str | None = None

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("Roll modifier label cannot be empty.")


@dataclass(frozen=True, slots=True)
class RollModifierBreakdown:
    active_modifiers: tuple[RollModifier, ...] = field(default_factory=tuple)
    ignored_modifiers: tuple[RollModifier, ...] = field(default_factory=tuple)
    modifier_total: int = 0


@dataclass(frozen=True, slots=True)
class D20RollRequest:
    mode: RollMode = RollMode.NORMAL
    modifiers: tuple[RollModifier, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class D20RollInstruction:
    message: str
    mode: RollMode
    breakdown: RollModifierBreakdown


@dataclass(frozen=True, slots=True)
class D20RollInput:
    request: D20RollRequest
    natural_roll: int


@dataclass(frozen=True, slots=True)
class D20RollResult:
    natural_roll: int
    breakdown: RollModifierBreakdown
    total: int
    mode: RollMode
    is_natural_20: bool
    is_natural_1: bool


def build_modifier_breakdown(modifiers: Iterable[RollModifier]) -> RollModifierBreakdown:
    unkeyed: list[RollModifier] = []
    keyed: dict[str, list[RollModifier]] = {}
    for modifier in modifiers:
        if modifier.stacking_key is None:
            unkeyed.append(modifier)
            continue
        keyed.setdefault(modifier.stacking_key, []).append(modifier)

    active = list(unkeyed)
    ignored: list[RollModifier] = []
    for group in keyed.values():
        selected = _select_stacking_modifier(group)
        active.append(selected)
        ignored.extend(modifier for modifier in group if modifier is not selected)

    active_tuple = tuple(active)
    ignored_tuple = tuple(ignored)
    return RollModifierBreakdown(
        active_modifiers=active_tuple,
        ignored_modifiers=ignored_tuple,
        modifier_total=sum(modifier.value for modifier in active_tuple),
    )


def roll_instruction(request: D20RollRequest) -> D20RollInstruction:
    breakdown = build_modifier_breakdown(request.modifiers)
    roll_text = {
        RollMode.NORMAL: "Rzuć 1d20 i wpisz wynik.",
        RollMode.ADVANTAGE: "Rzuć 2d20 i wpisz wyższy wynik.",
        RollMode.DISADVANTAGE: "Rzuć 2d20 i wpisz niższy wynik.",
    }[request.mode]
    message = f"{roll_text} Końcowy modyfikator: {_format_modifier(breakdown.modifier_total)}."
    if breakdown.active_modifiers:
        active = ", ".join(_format_component(modifier) for modifier in breakdown.active_modifiers)
        message = f"{message} Aktywne modyfikatory: {active}."
    if breakdown.ignored_modifiers:
        ignored = ", ".join(_format_component(modifier) for modifier in breakdown.ignored_modifiers)
        message = f"{message} Odrzucone duplikaty: {ignored}."
    return D20RollInstruction(message=message, mode=request.mode, breakdown=breakdown)


def resolve_d20_roll(roll_input: D20RollInput) -> D20RollResult:
    if not 1 <= roll_input.natural_roll <= 20:
        raise ValueError("A natural d20 roll must be between 1 and 20.")
    breakdown = build_modifier_breakdown(roll_input.request.modifiers)
    return D20RollResult(
        natural_roll=roll_input.natural_roll,
        breakdown=breakdown,
        total=roll_input.natural_roll + breakdown.modifier_total,
        mode=roll_input.request.mode,
        is_natural_20=roll_input.natural_roll == 20,
        is_natural_1=roll_input.natural_roll == 1,
    )


def _select_stacking_modifier(modifiers: list[RollModifier]) -> RollModifier:
    if not modifiers:
        raise ValueError("Cannot select a stacking modifier from an empty group.")
    if all(modifier.value >= 0 for modifier in modifiers):
        return max(modifiers, key=lambda modifier: modifier.value)
    if all(modifier.value <= 0 for modifier in modifiers):
        return min(modifiers, key=lambda modifier: modifier.value)
    return max(modifiers, key=lambda modifier: (abs(modifier.value), modifier.value))


def _format_component(modifier: RollModifier) -> str:
    return f"{modifier.label} {_format_modifier(modifier.value)}"


def _format_modifier(value: int) -> str:
    if value >= 0:
        return f"+{value}"
    return str(value)
