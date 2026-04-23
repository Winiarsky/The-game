from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from led_fx import animate_area_wave, animate_projectile_line


class DummyConn:
    def __init__(self, *, backend="simulator"):
        self.backend = backend
        self.calls = []
        self.off_calls = 0

    def set_leds(self, positions, colors):
        self.calls.append((list(positions), list(colors)))

    def leds_off(self):
        self.off_calls += 1


def test_animate_projectile_line_steps_along_path_without_sleep():
    conn = DummyConn()

    animated = animate_projectile_line(
        conn,
        (0, 0),
        (2, 0),
        trail_color=[10, 20, 30],
        head_color=[200, 210, 220],
        impact_color=[255, 255, 255],
        frame_delay_s=0,
        impact_hold_s=0,
        sleep_fn=lambda *_args, **_kwargs: None,
    )

    assert animated is True
    assert len(conn.calls) == 3
    assert conn.calls[0][0] == [(0, 0)]
    assert conn.calls[1][0] == [(0, 0), (1, 0)]
    assert conn.calls[2][0] == [(0, 0), (1, 0), (2, 0)]
    assert conn.off_calls == 1


def test_animate_projectile_line_skips_unknown_backends():
    conn = DummyConn(backend="")

    animated = animate_projectile_line(
        conn,
        (0, 0),
        (1, 1),
        frame_delay_s=0,
        impact_hold_s=0,
        sleep_fn=lambda *_args, **_kwargs: None,
    )

    assert animated is False
    assert conn.calls == []
    assert conn.off_calls == 0


def test_animate_projectile_line_palette_cycles_magic_colors():
    conn = DummyConn()

    animated = animate_projectile_line(
        conn,
        (0, 0),
        (2, 0),
        palette=[[10, 20, 30], [40, 50, 60], [70, 80, 90]],
        impact_color=[255, 255, 255],
        frame_delay_s=0,
        impact_hold_s=0.01,
        sleep_fn=lambda *_args, **_kwargs: None,
    )

    assert animated is True
    assert conn.calls[0][1] == [[10, 20, 30]]
    assert conn.calls[1][1][-1] == [40, 50, 60]
    assert conn.calls[2][1][-1] == [70, 80, 90]
    assert conn.off_calls == 1


def test_animate_area_wave_expands_from_origin():
    conn = DummyConn()

    animated = animate_area_wave(
        conn,
        (1, 1),
        [(1, 1), (2, 1), (3, 1)],
        palette=[[10, 20, 30], [40, 50, 60], [70, 80, 90]],
        frame_delay_s=0,
        hold_s=0,
        sleep_fn=lambda *_args, **_kwargs: None,
    )

    assert animated is True
    assert conn.calls[0][0] == [(1, 1)]
    assert set(conn.calls[1][0]) == {(1, 1), (2, 1)}
    assert set(conn.calls[2][0]) == {(1, 1), (2, 1), (3, 1)}
    assert conn.off_calls == 1
