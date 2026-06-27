from dnd_board_game.exploration import exploration_setup_feedback
from dnd_board_game.hardware import LedColor
from dnd_board_game.world import Coordinate


def test_exploration_setup_feedback_uses_given_positions_and_color():
    feedback = exploration_setup_feedback(
        (Coordinate(1, 1), Coordinate(1, 2)),
        LedColor.MARKER,
        anchor_position=Coordinate(1, 2),
    )

    assert len(feedback.frames) == 2
    assert feedback.frames[0].positions == (Coordinate(1, 1),)
    assert feedback.frames[0].color == (76, 63, 0)
    assert feedback.frames[1].positions == (Coordinate(1, 2),)
    assert feedback.frames[1].color == LedColor.MARKER
