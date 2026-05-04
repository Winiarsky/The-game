from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import GameObjects.events.all_events  # noqa: F401
from GameObjects.events.attack import attack_base
from GameObjects.events.base import EventContext
from GameObjects.events.elixirs.smokestick_event import SmokestickEvent
from GameObjects.events.registry import list_events
from GameObjects.items.inventory import add_alchemical_item, has_ready_alchemical_item
from economy import item_cost_cp


class _Hero:
    def __init__(self, pos=(0, 0)):
        self.position = pos
        self.inventory = []
        self.statuses = []

    def add_status(self, status):
        self.statuses.append(status)
        return True

    def remove_status(self, status):
        sid = getattr(status, "id", status)
        self.statuses = [item for item in self.statuses if getattr(item, "id", item) != sid]
        return True


class _Enemy:
    def __init__(self, pos=(1, 0)):
        self.position = pos
        self.statuses = []

    def add_status(self, status):
        self.statuses.append(status)
        return True

    def remove_status(self, status):
        sid = getattr(status, "id", status)
        self.statuses = [item for item in self.statuses if getattr(item, "id", item) != sid]
        return True


class _Board:
    def __init__(self, hero, enemy):
        self.hero = hero
        self.enemy = enemy

    def occupant_at(self, pos):
        if tuple(pos) == tuple(self.hero.position):
            return self.hero
        if tuple(pos) == tuple(self.enemy.position):
            return self.enemy
        return None

    def get_neighbors(self, pos, include_position=False, diagonal=True):
        del include_position, diagonal
        x, y = pos
        return [
            (x + 1, y),
            (x - 1, y),
            (x, y + 1),
            (x, y - 1),
            (x + 1, y + 1),
            (x + 1, y - 1),
            (x - 1, y + 1),
            (x - 1, y - 1),
        ]


class _Conn:
    def __init__(self):
        self.led_calls = []
        self.leds_off_calls = 0

    def set_leds(self, positions, colors):
        self.led_calls.append((list(positions or []), colors))

    def leds_off(self):
        self.leds_off_calls += 1


class _UI:
    def __init__(self, *, hero=None, enemy=None):
        self.info_calls = []
        self.hero = hero
        self.enemy = enemy
        self.ready_check = None

    def prompt_info(self, title, *, prompt_long=None, **kwargs):
        if callable(self.ready_check):
            self.ready_check()
        self.info_calls.append({"title": title, "prompt_long": prompt_long, "kwargs": dict(kwargs)})
        return "ok"


def _has_concealed(actor) -> bool:
    return any(getattr(status, "id", None) == "concealed" for status in list(getattr(actor, "statuses", []) or []))


def test_crb_alchemical_gear_core_events_are_registered():
    registered = set(list_events().keys())
    expected = {
        "acidflask",
        "alchemists_fire",
        "bottled_lightning",
        "frost_vial",
        "tanglefoot_bag",
        "thunderstone",
        "antidote",
        "antiplague",
        "elixir_of_life",
        "smokestick",
    }
    missing = sorted(expected.difference(registered))
    assert not missing, f"Brakuje eventow alchemicznych z CRB: {missing}"


def test_alchemical_gear_from_crb_has_3gp_price_in_cost_map():
    # 3 gp = 300 cp
    for item_id in (
        "acidflask",
        "alchemists_fire",
        "bottled_lightning",
        "frost_vial",
        "tanglefoot_bag",
        "thunderstone",
        "antidote",
        "antiplague",
        "elixir_of_life",
        "smokestick",
    ):
        assert item_cost_cp(item_id) == 300


def test_acid_flask_alias_maps_to_acidflask_ready_item():
    hero = _Hero()
    item = add_alchemical_item(hero, event_name="acid_flask")
    assert str(getattr(item, "event_name", "")).lower() == "acidflask"
    assert has_ready_alchemical_item(hero, "acidflask") is True
    assert has_ready_alchemical_item(hero, "acid_flask") is True


def test_smokestick_applies_concealed_in_local_area():
    hero = _Hero((0, 0))
    enemy = _Enemy((1, 0))
    board = _Board(hero, enemy)
    conn = _Conn()
    ui = _UI(hero=hero, enemy=enemy)
    game = SimpleNamespace(
        board=board,
        heroes=[hero],
        enemies=[enemy],
        conn=conn,
        ui=ui,
        ui_log=lambda *_a, **_k: None,
        events=SimpleNamespace(safe_emit_action=lambda **_kwargs: None),
    )
    add_alchemical_item(hero, event_name="smokestick")

    def _assert_preview_before_apply():
        assert has_ready_alchemical_item(hero, "smokestick") is True
        assert _has_concealed(hero) is False
        assert _has_concealed(enemy) is False

    ui.ready_check = _assert_preview_before_apply
    event = SmokestickEvent()
    result = event.execute(EventContext(game=game, actor=hero))

    assert result.success is True
    assert has_ready_alchemical_item(hero, "smokestick") is False
    assert _has_concealed(hero) is True
    assert _has_concealed(enemy) is True
    assert conn.led_calls
    assert conn.leds_off_calls == 1
    assert ui.info_calls[0]["title"] == "Dymna fiolka"
    assert "Naciśnij Enter" in ui.info_calls[0]["prompt_long"]
    assert getattr(game, "_smoke_clouds")


def test_smokestick_smoke_cloud_forces_concealment_flat_check(monkeypatch):
    hero = _Hero((0, 0))
    enemy = _Enemy((3, 0))
    game = SimpleNamespace(
        _smoke_clouds=[
            {
                "positions": [(0, 0)],
                "expires_round": 11,
            }
        ],
        state=SimpleNamespace(round_index=1),
        ui=SimpleNamespace(prompt_info=lambda *_a, **_k: None),
        ui_log=lambda *_a, **_k: None,
    )

    monkeypatch.setattr(attack_base, "prompt_for_roll", lambda *_, **__: 1)

    assert attack_base.check_concealed(EventContext(game=game, actor=hero), enemy) is False
