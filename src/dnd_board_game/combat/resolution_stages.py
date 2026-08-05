"""Stable names for player-visible combat resolution checkpoints."""

from enum import StrEnum


class CombatResolutionStage(StrEnum):
    COMBAT_STARTED = "combat_started"
    ROUND_STARTED = "round_started"
    TURN_STARTED = "turn_started"
    ACTION_SELECTION = "action_selection"
    TARGET_SELECTION = "target_selection"
    ACTION_COMMITTED = "action_committed"
    ATTACK_ROLL_REVEALED = "attack_roll_revealed"
    ATTACK_RESULT_CONFIRMED = "attack_result_confirmed"
    SAVE_ROLL_REVEALED = "save_roll_revealed"
    SAVE_RESULT_CONFIRMED = "save_result_confirmed"
    DAMAGE_ROLL_REVEALED = "damage_roll_revealed"
    DAMAGE_APPLIED = "damage_applied"
    STATUS_APPLIED = "status_applied"
    MOVEMENT_RESOLVED = "movement_resolved"
    ACTION_RESOLVED = "action_resolved"
    TURN_ENDED = "turn_ended"
    ROUND_ENDED = "round_ended"
    COMBAT_ENDED = "combat_ended"


__all__ = ["CombatResolutionStage"]
