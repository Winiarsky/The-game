from dnd_board_game.combat import SetupStep, SetupStepKind, SetupVisibility, setup_led_feedback
from dnd_board_game.hardware import BoardLedAdapter, LedRole
from dnd_board_game.world import Coordinate


class FakeConnection:
    def __init__(self):
        self.calls = []
        self.cleared = False

    def set_leds(self, positions, rgb_color):
        self.calls.append((list(positions), list(rgb_color)))

    def leds_off(self):
        self.cleared = True


def test_setup_led_feedback_generates_frame_for_visible_step_and_can_clear():
    step = SetupStep(
        kind=SetupStepKind.ENVIRONMENT,
        label="trudny teren",
        positions=(Coordinate(2, 1), Coordinate(3, 1)),
        color=(255, 120, 0),
        message="Ustaw trudny teren.",
    )

    feedback = setup_led_feedback(step)
    connection = FakeConnection()
    adapter = BoardLedAdapter(connection)
    adapter.show_feedback(feedback)
    adapter.clear()

    assert feedback.frames[0].positions == (Coordinate(2, 1), Coordinate(3, 1))
    assert feedback.frames[0].role == LedRole.DIFFICULT_TERRAIN
    assert connection.calls == [([(2, 1), (3, 1)], [255, 120, 0])]
    assert connection.cleared is True


def test_setup_led_feedback_ignores_hidden_and_conditional_steps():
    hidden = SetupStep(
        kind=SetupStepKind.ENEMIES,
        label="ukryci wrogowie",
        positions=(Coordinate(5, 5),),
        color=(255, 0, 80),
        message="Ukryty.",
        visibility=SetupVisibility.HIDDEN,
    )
    conditional = SetupStep(
        kind=SetupStepKind.ENVIRONMENT,
        label="warunkowy obiekt",
        positions=(Coordinate(6, 6),),
        color=(0, 255, 120),
        message="Warunkowy.",
        visibility=SetupVisibility.CONDITIONAL,
    )

    assert setup_led_feedback(hidden).frames == ()
    assert setup_led_feedback(conditional).frames == ()
