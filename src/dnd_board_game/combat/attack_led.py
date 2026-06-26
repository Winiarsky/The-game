from __future__ import annotations

from dnd_board_game.hardware import LedColor, LedFeedback, LedFrame, LedRole
from dnd_board_game.rules import AttackRollOutcome

from .targets import CombatTarget

LEGAL_TARGET_COLOR = LedColor.LEGAL_ATTACK_TARGET
SELECTED_TARGET_COLOR = LedColor.SELECTED_ATTACK_TARGET
HIT_COLOR = LedColor.ATTACK_HIT
MISS_COLOR = LedColor.ATTACK_MISS
CRITICAL_HIT_COLOR = LedColor.ATTACK_CRITICAL_HIT


def attack_targets_led_feedback(targets: tuple[CombatTarget, ...]) -> LedFeedback:
    positions = tuple(sorted((target.position for target in targets)))
    if not positions:
        return LedFeedback()
    return LedFeedback((LedFrame(positions, LEGAL_TARGET_COLOR, LedRole.MOVEMENT_RANGE),))


def selected_attack_target_led_feedback(target: CombatTarget) -> LedFeedback:
    return LedFeedback((LedFrame((target.position,), SELECTED_TARGET_COLOR, LedRole.DESTINATION),))


def attack_result_led_feedback(target: CombatTarget, outcome: AttackRollOutcome) -> LedFeedback:
    color = {
        AttackRollOutcome.CRITICAL_HIT: CRITICAL_HIT_COLOR,
        AttackRollOutcome.HIT: HIT_COLOR,
        AttackRollOutcome.MISS: MISS_COLOR,
        AttackRollOutcome.CRITICAL_MISS: MISS_COLOR,
    }[outcome]
    return LedFeedback((LedFrame((target.position,), color, LedRole.DESTINATION),))
