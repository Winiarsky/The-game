"""Translate combat presentation cues to LEDs, without deciding any rules."""
from __future__ import annotations

from dataclasses import dataclass

from dnd_board_game.world import Coordinate
from .board_panel import panel_feedback
from .led_feedback import LedFeedback, LedFrame, LedRole
from .led_palette import LedColor


@dataclass(frozen=True, slots=True)
class ResonanceBoardView:
    active: Coordinate
    legal: tuple[Coordinate, ...] = ()
    selected: tuple[Coordinate, ...] = ()
    path: tuple[Coordinate, ...] = ()
    destination: Coordinate | None = None
    area: tuple[Coordinate, ...] = ()
    excluded: Coordinate | None = None
    focus: Coordinate | None = None
    focus_result: bool | None = None
    enemy: bool = False
    action_slots: tuple[int, ...] = ()
    control_slots: tuple[int, ...] = ()
    selected_slot: int | None = None


def resonance_feedback(view: ResonanceBoardView) -> LedFeedback:
    frames = [LedFrame((view.active,), LedColor.ACTIVE_ACTOR, LedRole.ACTIVE_ACTOR)]
    cues = ((view.legal, LedColor.LEGAL_ABILITY_TARGET, LedRole.MOVEMENT_RANGE),
            (view.area, LedColor.AREA_EFFECT, LedRole.AREA_EFFECT),
            (view.path, LedColor.ENEMY_MOVEMENT_PATH if view.enemy else LedColor.PLAYER_MOVEMENT_PATH, LedRole.SELECTED_PATH),
            (view.selected, LedColor.SELECTED_ABILITY_TARGET, LedRole.ALLY))
    frames.extend(LedFrame(positions, color, role) for positions, color, role in cues if positions)
    if view.destination:
        frames.append(LedFrame((view.destination,), LedColor.SELECTED_ATTACK_TARGET, LedRole.DESTINATION))
    if view.excluded:
        frames.append(LedFrame((view.excluded,), LedColor.ALLY, LedRole.ALLY))
    if view.focus:
        color = LedColor.ATTACK_HIT if view.focus_result is True else LedColor.ATTACK_MISS if view.focus_result is False else LedColor.ENEMY if view.enemy else LedColor.ACTIVE_ACTOR
        frames.append(LedFrame((view.focus,), color, LedRole.PROJECTILE))
    return panel_feedback(view.action_slots, selected_slot=view.selected_slot, control_slots=view.control_slots, base=LedFeedback(tuple(frames)))
