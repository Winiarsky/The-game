"""Map enabled dice controls to the printed board edge, without rule decisions."""

from dnd_board_game.hardware.led_feedback import LedFeedback, LedFrame, LedRole
from dnd_board_game.world import Coordinate


def initiative_panel_feedback(enabled_slots: tuple[int, ...]) -> LedFeedback:
    colors = {26: (0, 255, 0), 27: (255, 0, 0), 28: (0, 80, 255), 29: (255, 160, 0)}
    return LedFeedback(
        tuple(
            LedFrame((Coordinate(19, 29 - slot),), colors[slot], LedRole.MARKER)
            for slot in enabled_slots
        )
    )
