from dnd_board_game.actors import Actor, ActorId, Faction
from dnd_board_game.hardware import BoardLedAdapter, LedRole, movement_led_feedback
from dnd_board_game.world import BoardState, Coordinate, find_path, movement_range


class FakeConnection:
    def __init__(self):
        self.calls = []
        self.cleared = False

    def set_leds(self, positions, rgb_color):
        self.calls.append((list(positions), list(rgb_color)))

    def leds_off(self):
        self.cleared = True


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
