"""Compose the printed edge lights with the independent game-board layer."""

from collections.abc import Mapping

from dnd_board_game.hardware.led_feedback import LedFeedback, LedFrame, LedRole
from dnd_board_game.hardware.led_palette import LedColor
from dnd_board_game.world import Coordinate


def panel_position(slot: int) -> Coordinate:
    if not 0 <= slot < 30:
        raise ValueError("Nieznane pole panelu.")
    return Coordinate(19, 29 - slot)


def setup_panel_feedback(
    base: LedFeedback, *, can_confirm: bool, selected: Coordinate | None = None,
) -> LedFeedback:
    """Keep placement guidance and illuminate accept only after a valid choice."""
    accept = panel_position(28)
    frames = [
        LedFrame(positions, frame.color, frame.role)
        for frame in base.frames
        if (positions := tuple(p for p in frame.positions if p not in (accept, selected)))
    ]
    if selected is not None:
        frames.append(LedFrame((selected,), LedColor.MOVEMENT_DESTINATION, LedRole.DESTINATION))
    if can_confirm:
        frames.append(LedFrame((accept,), LedColor.PANEL_ACCEPT, LedRole.MARKER))
    return LedFeedback(tuple(frames))


def panel_feedback(
    action_slots: tuple[int, ...] = (), *, selected_slot: int | None = None,
    control_slots: tuple[int, ...] = (), base: LedFeedback = LedFeedback(),
    action_colors: Mapping[int, tuple[int, int, int]] | None = None,
) -> LedFeedback:
    frames = [
        LedFrame(tuple(p for p in frame.positions if p.col != 19), frame.color, frame.role)
        for frame in base.frames if any(p.col != 19 for p in frame.positions)
    ]
    for slot in action_slots:
        intensity = 1.0 if slot == selected_slot else .35 if selected_slot is not None else .65
        base_color = (action_colors or {}).get(slot, LedColor.PANEL_ACTION)
        color = tuple(round(component * intensity) for component in base_color)
        frames.append(LedFrame((panel_position(slot),), color, LedRole.MARKER))
    colors = {26: LedColor.PANEL_MINUS, 27: LedColor.PANEL_PLUS,
              28: LedColor.PANEL_ACCEPT, 29: LedColor.PANEL_BACK}
    for slot in control_slots:
        frames.append(LedFrame((panel_position(slot),), colors[slot], LedRole.MARKER))
    return LedFeedback(tuple(frames))
