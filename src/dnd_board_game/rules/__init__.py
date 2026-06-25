"""D&D 5e rules primitives."""

from .attacks import AttackRollOutcome, AttackRollResult, resolve_attack_roll
from .checks import CheckResult, resolve_ability_check, resolve_saving_throw
from .dice import (
    D20RollInput,
    D20RollInstruction,
    D20RollRequest,
    D20RollResult,
    RollMode,
    RollModifier,
    RollModifierBreakdown,
    RollModifierType,
    build_modifier_breakdown,
    resolve_d20_roll,
    roll_instruction,
)

__all__ = [
    "AttackRollOutcome",
    "AttackRollResult",
    "CheckResult",
    "D20RollInput",
    "D20RollInstruction",
    "D20RollRequest",
    "D20RollResult",
    "RollMode",
    "RollModifier",
    "RollModifierBreakdown",
    "RollModifierType",
    "build_modifier_breakdown",
    "resolve_ability_check",
    "resolve_attack_roll",
    "resolve_d20_roll",
    "resolve_saving_throw",
    "roll_instruction",
]
