"""Translate combat presentation cues to LEDs, without deciding any rules."""
from __future__ import annotations

from dataclasses import dataclass

from dnd_board_game.world import Coordinate
from .board_panel import panel_feedback, panel_position
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
    action_cues: tuple[tuple[int, str], ...] = ()
    legal_kind: str = "target"
    illegal: tuple[Coordinate, ...] = ()


def resonance_feedback(view: ResonanceBoardView) -> LedFeedback:
    frames = [LedFrame((view.active,), LedColor.ACTIVE_ACTOR, LedRole.ACTIVE_ACTOR)]
    legal_color = LedColor.MOVEMENT_RANGE if view.legal_kind == "movement" else LedColor.PANEL_RUNE
    cues = ((view.legal, legal_color, LedRole.MOVEMENT_RANGE),
            (view.illegal, LedColor.ATTACK_MISS, LedRole.ENEMY),
            (view.area, LedColor.AREA_EFFECT, LedRole.AREA_EFFECT),
            (view.path, LedColor.ENEMY_MOVEMENT_PATH if view.enemy else LedColor.PLAYER_MOVEMENT_PATH, LedRole.SELECTED_PATH),
            (view.selected, LedColor.ACTIVE_ACTOR, LedRole.ALLY))
    frames.extend(LedFrame(positions, color, role) for positions, color, role in cues if positions)
    if view.destination:
        frames.append(LedFrame((view.destination,), LedColor.ENEMY_MOVEMENT_DESTINATION if view.enemy else LedColor.MOVEMENT_DESTINATION, LedRole.DESTINATION))
    if view.excluded:
        frames.append(LedFrame((view.excluded,), LedColor.ALLY, LedRole.ALLY))
    if view.focus:
        color = LedColor.ATTACK_HIT if view.focus_result is True else LedColor.ATTACK_MISS if view.focus_result is False else LedColor.ENEMY if view.enemy else LedColor.ACTIVE_ACTOR
        frames.append(LedFrame((view.focus,), color, LedRole.PROJECTILE))
    # The presentation owns legality and transitions. The hardware boundary
    # merely translates semantic cues, including silent locked skills.
    cues_by_slot = dict(view.action_cues)
    action_slots = tuple(slot for slot in view.action_slots if cues_by_slot.get(slot) != "locked")
    action_colors = {slot: LedColor.PANEL_RESONANCE_RESET if cue == "reset" else LedColor.PANEL_RUNE
                     for slot, cue in view.action_cues if cue != "locked"}
    feedback = panel_feedback(action_slots, selected_slot=view.selected_slot,
                              control_slots=view.control_slots, action_colors=action_colors,
                              base=LedFeedback(tuple(frames)))
    if view.selected_slot is None:
        return feedback
    selected_position = panel_position(view.selected_slot)
    retained = tuple(LedFrame(positions, frame.color, frame.role) for frame in feedback.frames
                     if (positions := tuple(p for p in frame.positions if p != selected_position)))
    return LedFeedback((*retained, LedFrame((selected_position,), LedColor.ACTIVE_ACTOR, LedRole.MARKER)))
