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


def test_board_session_adapter_turns_leds_off_before_closing_connection():
    class CloseableConnection:
        def __init__(self):
            self.events = []

        def leds_off(self):
            self.events.append("leds_off")

        def close(self):
            self.events.append("close")

    connection = CloseableConnection()

    BoardSessionAdapter(connection).close()

    assert connection.events == ["leds_off", "close"]


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
    assert connection.clear_calls == 2


def test_board_session_replaces_atomic_frames_without_black_clear():
    class AtomicConnection:
        led_transition_ms = 180
        scan_led_transition_ms = 80
        scan_brightness = 255

        def __init__(self):
            self.calls = []
            self.clear_calls = 0

        def set_leds(
            self,
            positions,
            rgb_color,
            *,
            brightness=None,
            replace=False,
            transition_ms=None,
        ):
            self.calls.append(
                {
                    "positions": tuple(positions),
                    "colors": rgb_color,
                    "brightness": brightness,
                    "replace": replace,
                    "transition_ms": transition_ms,
                }
            )

        def leds_off(self):
            self.clear_calls += 1

    connection = AtomicConnection()
    adapter = BoardSessionAdapter(connection)
    first = LedFeedback(
        (LedFrame((Coordinate(1, 1),), LedColor.ACTIVE_ACTOR, LedRole.ACTIVE_ACTOR),)
    )
    second = LedFeedback(
        (LedFrame((Coordinate(2, 1),), LedColor.ACTIVE_ACTOR, LedRole.ACTIVE_ACTOR),)
    )

    adapter.show_feedback(first)
    adapter.show_feedback(second)

    assert connection.clear_calls == 0
    assert [call["positions"] for call in connection.calls] == [
        ((1, 1),),
        ((2, 1),),
    ]
    assert all(call["replace"] is True for call in connection.calls)
    assert all(call["transition_ms"] == 180 for call in connection.calls)


def test_board_session_skips_duplicate_frame_but_renders_scan_brightness_change():
    class AtomicConnection:
        led_transition_ms = 180
        scan_led_transition_ms = 80
        scan_brightness = 250

        def __init__(self):
            self.calls = []

        def set_leds(self, positions, rgb_color, **kwargs):
            self.calls.append((tuple(positions), rgb_color, kwargs))

        def leds_off(self):
            raise AssertionError("Pełna klatka nie powinna gasić LED-ów osobnym żądaniem.")

    connection = AtomicConnection()
    adapter = BoardSessionAdapter(connection)
    feedback = LedFeedback(
        (LedFrame((Coordinate(3, 4),), LedColor.INTERACTIVE_OBJECT, LedRole.INTERACTIVE_OBJECT),)
    )

    adapter.show_feedback(feedback)
    adapter.show_feedback(feedback)
    adapter.show_scan_feedback(feedback)

    assert len(connection.calls) == 2
    assert connection.calls[0][2]["transition_ms"] == 180
    assert connection.calls[1][2] == {
        "brightness": 250,
        "replace": True,
        "transition_ms": 80,
    }


def test_board_session_animates_projectile_one_field_at_a_time():
    class AtomicConnection:
        def __init__(self):
            self.calls = []

        def set_leds(self, positions, rgb_color, **kwargs):
            self.calls.append((tuple(positions), rgb_color, kwargs))

        def leds_off(self):
            raise AssertionError("Animacja atomowa nie powinna osobno gasić planszy.")

    connection = AtomicConnection()
    adapter = BoardSessionAdapter(connection)

    adapter.animate_projectile(
        (
            Coordinate(1, 1),
            Coordinate(2, 1),
            Coordinate(3, 2),
            Coordinate(4, 2),
        ),
        step_ms=0,
    )

    assert [call[0] for call in connection.calls] == [
        ((2, 1),),
        ((3, 2),),
        ((4, 2),),
    ]
    assert all(
        call[1] == list(LedColor.RANGED_PROJECTILE)
        for call in connection.calls
    )
    assert all(call[2]["replace"] is True for call in connection.calls)
    assert all(call[2]["transition_ms"] == 0 for call in connection.calls)


def test_projectile_animation_keeps_context_and_restores_base_frame():
    class AtomicConnection:
        def __init__(self):
            self.calls = []

        def set_leds(self, positions, rgb_color, **kwargs):
            self.calls.append((tuple(positions), rgb_color, kwargs))

        def leds_off(self):
            raise AssertionError("Animacja z tłem nie powinna wygaszać planszy.")

    connection = AtomicConnection()
    adapter = BoardSessionAdapter(connection)
    base = LedFeedback(
        (LedFrame((Coordinate(1, 1),), LedColor.ACTIVE_ACTOR, LedRole.ACTIVE_ACTOR),)
    )
    adapter.show_feedback(base)
    connection.calls.clear()

    adapter.animate_projectile(
        (Coordinate(1, 1), Coordinate(2, 1), Coordinate(3, 1)),
        step_ms=0,
    )

    assert [call[0] for call in connection.calls] == [
        ((1, 1), (2, 1)),
        ((1, 1), (3, 1)),
        ((1, 1),),
    ]
    assert connection.calls[-1][2]["transition_ms"] == 80


def test_continuous_scan_keeps_brightness_and_sends_only_changed_frames() -> None:
    class AtomicConnection:
        def __init__(self):
            self.calls = []

        def set_leds(self, positions, rgb_color, **kwargs):
            self.calls.append((tuple(positions), rgb_color, kwargs))

        def leds_off(self):
            raise AssertionError('Continuous panel input must not blank the LEDs.')

    connection = AtomicConnection()
    adapter = BoardSessionAdapter(connection)
    first = LedFeedback((LedFrame((Coordinate(19, 1),), LedColor.PANEL_ACCEPT, LedRole.MARKER),))
    second = LedFeedback((LedFrame((Coordinate(19, 2),), LedColor.PANEL_PLUS, LedRole.MARKER),))
    adapter.show_feedback(first)
    for _ in range(3):
        adapter.show_scan_feedback(first, boost_brightness=False)
        adapter.restore_feedback(first)
    adapter.show_feedback(second)
    adapter.show_scan_feedback(second, boost_brightness=False)
    adapter.restore_feedback(second)
    assert len(connection.calls) == 2
    assert all(call[2]['brightness'] is None for call in connection.calls)
    assert all(call[2]['replace'] for call in connection.calls)


def test_projectile_timing_includes_transport_time(monkeypatch) -> None:
    import dnd_board_game.hardware.board_session as module

    elapsed = [0.0]
    sleeps = []

    class AtomicConnection:
        def set_leds(self, positions, rgb_color, **kwargs):
            elapsed[0] += .02

        def leds_off(self):
            pass

    def sleep(seconds):
        sleeps.append(seconds)
        elapsed[0] += seconds

    monkeypatch.setattr(module.time, 'monotonic', lambda: elapsed[0])
    monkeypatch.setattr(module.time, 'sleep', sleep)
    adapter = BoardSessionAdapter(AtomicConnection())
    adapter.animate_projectile((Coordinate(0, 0), Coordinate(1, 0), Coordinate(2, 0)), step_ms=55)
    assert len(sleeps) == 2
    assert all(abs(delay - .035) < .00001 for delay in sleeps)
    assert abs(elapsed[0] - .110) < .00001


def test_failed_led_frame_and_clear_are_not_cached_as_delivered():
    class FailingConnection:
        def __init__(self):
            self.sends = 0
            self.clears = 0

        def set_leds(self, positions, colors, **kwargs):
            self.sends += 1
            return self.sends > 1

        def leds_off(self):
            self.clears += 1
            return self.clears > 1

    connection = FailingConnection()
    adapter = BoardLedAdapter(connection)
    feedback = LedFeedback((LedFrame((Coordinate(19, 1),), LedColor.PANEL_ACCEPT, LedRole.MARKER),))
    adapter.show_feedback(feedback, replace=True)
    adapter.show_feedback(feedback, replace=True)
    adapter.show_feedback(feedback, replace=True)
    assert connection.sends == 2
    adapter.clear()
    adapter.clear()
    adapter.clear()
    assert connection.clears == 2
