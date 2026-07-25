import pytest

from dnd_board_game.actors import Actor, ActorId, Faction
from dnd_board_game.hardware import (
    BoardLedAdapter,
    BoardSessionAdapter,
    LedColor,
    LedFeedback,
    LedFrame,
    LedRole,
    movement_led_feedback,
)
from dnd_board_game.world import BoardState, Coordinate, find_path, movement_range


class FakeConnection:
    def __init__(self):
        self.calls = []
        self.cleared = False
        self.scan_calls = []
        self.reset = False

    def set_leds(self, positions, rgb_color):
        self.calls.append((list(positions), list(rgb_color)))

    def leds_off(self):
        self.cleared = True

    def scan_board(self, positions, *, timeout_s):
        self.scan_calls.append((positions, timeout_s))
        return positions[0]

    def reset_connection(self):
        self.reset = True


def _actor(actor_id: str, position: Coordinate) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id,
        ac=12,
        hp=10,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=Faction.ALLY,
    )


def test_movement_led_feedback_contains_origin_range_path_and_destination():
    board = BoardState()
    actor = _actor("hero", Coordinate(0, 0))
    result = movement_range(board, actor, [actor])
    path = find_path(board, actor, [actor], Coordinate(2, 0))

    feedback = movement_led_feedback(result, path)

    roles = [frame.role for frame in feedback.frames]
    assert roles == [
        LedRole.ACTIVE_ACTOR,
        LedRole.MOVEMENT_RANGE,
        LedRole.SELECTED_PATH,
        LedRole.DESTINATION,
    ]
    assert feedback.frames[0].positions == (Coordinate(0, 0),)
    assert Coordinate(2, 0) in feedback.frames[-1].positions


def test_board_led_adapter_writes_frames_to_connection_and_clears():
    board = BoardState()
    actor = _actor("hero", Coordinate(0, 0))
    feedback = movement_led_feedback(movement_range(board, actor, [actor]))
    connection = FakeConnection()
    adapter = BoardLedAdapter(connection)

    adapter.show_movement(feedback)
    adapter.clear()

    assert connection.calls
    assert (0, 0) in connection.calls[0][0]
    assert all(isinstance(color, list) for color in connection.calls[0][1])
    assert connection.cleared is True


@pytest.mark.parametrize("path_color", [LedColor.PLAYER_MOVEMENT_PATH, LedColor.ENEMY_MOVEMENT_PATH])
def test_selected_path_overrides_interactive_object_regardless_of_frame_order(path_color):
    overlap = Coordinate(4, 5)
    connection = FakeConnection()
    adapter = BoardLedAdapter(connection)
    feedback = LedFeedback(
        (
            LedFrame((overlap,), path_color, LedRole.SELECTED_PATH),
            LedFrame((overlap,), LedColor.INTERACTIVE_OBJECT, LedRole.INTERACTIVE_OBJECT),
        )
    )

    adapter.show_feedback(feedback)

    assert connection.calls == [([(4, 5)], list(path_color))]


def test_board_session_adapter_owns_scan_reset_and_led_transport():
    connection = FakeConnection()
    adapter = BoardSessionAdapter(connection)
    positions = (Coordinate(3, 4),)

    selected = adapter.scan(positions, timeout_s=12.5)
    action = adapter.reset_scan()
    adapter.show_feedback(movement_led_feedback(movement_range(BoardState(), _actor("hero", Coordinate(0, 0)), [])))

    assert selected == (3, 4)
    assert connection.scan_calls == [([(3, 4)], 12.5)]
    assert action == "reset_connection"
    assert connection.reset is True
    assert connection.cleared is True
    assert connection.calls


def test_board_session_uses_boosted_brightness_only_for_active_scan():
    class BrightnessConnection:
        scan_brightness = 240

        def __init__(self):
            self.calls = []
            self.clear_calls = 0

        def set_leds(self, positions, rgb_color, *, brightness=None):
            self.calls.append((tuple(positions), rgb_color, brightness))

        def leds_off(self):
            self.clear_calls += 1

    connection = BrightnessConnection()
    adapter = BoardSessionAdapter(connection)
    feedback = LedFeedback(
        (LedFrame((Coordinate(3, 4),), LedColor.INTERACTIVE_OBJECT, LedRole.INTERACTIVE_OBJECT),)
    )

    adapter.show_scan_feedback(feedback)
    adapter.restore_feedback(feedback)

    assert connection.calls[0][2] == 240
    assert connection.calls[1][2] is None
    assert connection.clear_calls == 1
