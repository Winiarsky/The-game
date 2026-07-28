from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import re
from collections.abc import Callable
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


class D20RollKind(StrEnum):
    ATTACK = "attack"
    ABILITY_CHECK = "ability_check"
    SAVING_THROW = "saving_throw"


class D20RollContextTag(StrEnum):
    STONEWORK = "stonework"
    ARTIFICERS_LORE = "artificers_lore"


@dataclass(frozen=True, slots=True)
class DiceExpression:
    """A transport-neutral NdM dice expression without a flat modifier."""

    count: int
    sides: int

    def __post_init__(self) -> None:
        if self.count < 1:
            raise ValueError("Dice count must be positive.")
        if self.sides < 2:
            raise ValueError("Die sides must be at least 2.")

    @classmethod
    def parse(cls, value: str) -> "DiceExpression":
        match = re.fullmatch(r"\s*(\d+)[dD](\d+)\s*", str(value))
        if match is None:
            raise ValueError("Dice expression must use NdM format, for example '2d6'.")
        return cls(count=int(match.group(1)), sides=int(match.group(2)))

    def format(self, *, dice_multiplier: int = 1) -> str:
        if dice_multiplier < 1:
            raise ValueError("Dice multiplier must be positive.")
        return f"{self.count * dice_multiplier}d{self.sides}"

    def roll(
        self,
        roll_die: Callable[[int], int],
        *,
        dice_multiplier: int = 1,
    ) -> tuple[int, ...]:
        if dice_multiplier < 1:
            raise ValueError("Dice multiplier must be positive.")
        results = tuple(
            int(roll_die(self.sides))
            for _ in range(self.count * dice_multiplier)
        )
        if any(result < 1 or result > self.sides for result in results):
            raise ValueError(
                f"Die result must be between 1 and {self.sides}."
            )
        return results


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
    reroll_natural_ones: bool = False
    reroll_label: str = ""
    ability: str | None = None

    def __post_init__(self) -> None:
        if self.reroll_label and not self.reroll_natural_ones:
            raise ValueError("A d20 reroll label requires an active reroll rule.")


@dataclass(frozen=True, slots=True)
class D20RollInstruction:
    message: str
    mode: RollMode
    breakdown: RollModifierBreakdown


@dataclass(frozen=True, slots=True)
class D20RollInput:
    request: D20RollRequest
    natural_roll: int
    natural_roll_2: int | None = None
    natural_rerolls: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class D20RollResult:
    natural_roll: int
    natural_rolls: tuple[int, ...]
    breakdown: RollModifierBreakdown
    total: int
    mode: RollMode
    is_natural_20: bool
    is_natural_1: bool
    original_natural_rolls: tuple[int, ...] = ()
    natural_rerolls: tuple[int, ...] = ()


class D20RerollRequired(ValueError):
    def __init__(self, count: int, label: str) -> None:
        self.count = count
        self.label = label
        super().__init__(
            f"{label or 'Cecha postaci'} wymaga {count} dodatkowego rzutu d20."
        )


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
        RollMode.ADVANTAGE: "Rzuć 2d20 z przewagą i wpisz oba wyniki.",
        RollMode.DISADVANTAGE: "Rzuć 2d20 z utrudnieniem i wpisz oba wyniki.",
    }[request.mode]
    message = f"{roll_text} Końcowy modyfikator: {_format_modifier(breakdown.modifier_total)}."
    if breakdown.active_modifiers:
        active = ", ".join(_format_component(modifier) for modifier in breakdown.active_modifiers)
        message = f"{message} Aktywne modyfikatory: {active}."
    if breakdown.ignored_modifiers:
        ignored = ", ".join(_format_component(modifier) for modifier in breakdown.ignored_modifiers)
        message = f"{message} Odrzucone duplikaty: {ignored}."
    if request.reroll_natural_ones:
        message = (
            f"{message} Jeśli na którejkolwiek kości wypadnie naturalne 1, "
            f"{request.reroll_label or 'aktywna cecha'} wymaga ponownego rzutu tej kości."
        )
    return D20RollInstruction(message=message, mode=request.mode, breakdown=breakdown)


def resolve_d20_roll(roll_input: D20RollInput) -> D20RollResult:
    original_natural_rolls = _natural_rolls_for_mode(roll_input)
    for natural_roll in (*original_natural_rolls, *roll_input.natural_rerolls):
        if not 1 <= natural_roll <= 20:
            raise ValueError("A natural d20 roll must be between 1 and 20.")
    natural_rolls = _apply_natural_one_rerolls(
        roll_input.request,
        original_natural_rolls,
        roll_input.natural_rerolls,
    )
    selected_roll = _selected_natural_roll(roll_input.request.mode, natural_rolls)
    breakdown = build_modifier_breakdown(roll_input.request.modifiers)
    return D20RollResult(
        natural_roll=selected_roll,
        natural_rolls=natural_rolls,
        breakdown=breakdown,
        total=selected_roll + breakdown.modifier_total,
        mode=roll_input.request.mode,
        is_natural_20=selected_roll == 20,
        is_natural_1=selected_roll == 1,
        original_natural_rolls=original_natural_rolls,
        natural_rerolls=roll_input.natural_rerolls,
    )


def _apply_natural_one_rerolls(
    request: D20RollRequest,
    natural_rolls: tuple[int, ...],
    rerolls: tuple[int, ...],
) -> tuple[int, ...]:
    required = sum(value == 1 for value in natural_rolls) if request.reroll_natural_ones else 0
    if not request.reroll_natural_ones and rerolls:
        raise ValueError("Ten rzut d20 nie pozwala na ponowne rzuty.")
    if len(rerolls) < required:
        raise D20RerollRequired(required - len(rerolls), request.reroll_label)
    if len(rerolls) > required:
        raise ValueError("Podano zbyt wiele ponownych rzutów d20.")
    reroll_index = 0
    effective: list[int] = []
    for value in natural_rolls:
        if value == 1 and request.reroll_natural_ones:
            effective.append(rerolls[reroll_index])
            reroll_index += 1
        else:
            effective.append(value)
    return tuple(effective)


def _natural_rolls_for_mode(roll_input: D20RollInput) -> tuple[int, ...]:
    if roll_input.request.mode == RollMode.NORMAL or roll_input.natural_roll_2 is None:
        return (roll_input.natural_roll,)
    return (roll_input.natural_roll, roll_input.natural_roll_2)


def _selected_natural_roll(mode: RollMode, natural_rolls: tuple[int, ...]) -> int:
    if mode == RollMode.ADVANTAGE:
        return max(natural_rolls)
    if mode == RollMode.DISADVANTAGE:
        return min(natural_rolls)
    return natural_rolls[0]


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
