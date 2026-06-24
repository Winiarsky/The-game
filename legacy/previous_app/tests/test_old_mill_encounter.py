from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from old_mill_encounter import (
    ensure_state,
    increase_alarm,
    reveal_hidden_route,
    secure_false_ash,
    secure_ledger,
    secure_tovin,
)
from hero import Hero
from scenario_flow import load_scenario_flow
from scenario_session import ScenarioSession
from statuses.base import Status
from src.game import Game


class DummyConnection:
    def __init__(self):
        self.led_calls = []

    def set_leds(self, *args, **kwargs):
        self.led_calls.append((args, kwargs))
        return None

    def leds_off(self, *_args, **_kwargs):
        return None

    def scan_board(self, acceptable_responses=None, *_args, **_kwargs):
        if acceptable_responses:
            return tuple(acceptable_responses[0])
        return (0, 0)

    def read_card(self, *_args, **_kwargs):
        return "DECLINE"


def _interactable_ids(game):
    ids = set()
    for row in range(game.board.rows):
        for col in range(game.board.cols):
            for obj in game.board.cell_at((col, row)).interactables:
                ids.add(str(getattr(obj, "scenario_object_id", "") or getattr(obj, "cache_id", "") or getattr(obj, "exit_id", "") or ""))
                ids.add(obj.__class__.__name__)
    return ids


def test_old_mill_loads_hostage_evidence_alarm_setup():
    game = Game(conn=DummyConnection(), scenario="ashen_oath_old_mill")

    ids = _interactable_ids(game)

    assert {enemy.__class__.__name__ for enemy in game.enemies} == {"ValeGuard", "MillEnforcer"}
    assert len(game.enemies) == 3
    assert "old_mill_overview" in ids
    assert "old_mill_bound_tovin" in ids
    assert "old_mill_gear_lever" in ids
    assert "old_mill_false_ash_sacks" in ids
    assert "old_mill_ledger" in ids
    assert "old_mill_rope_hoist" in ids
    assert "old_mill_back_track" in ids
    assert "mill_hidden_track" in ids
    assert "TrapTile" in ids


def test_old_mill_direct_playtest_has_static_physical_setup_plan():
    game = Game(conn=DummyConnection(), scenario="ashen_oath_old_mill")
    plan = list(game.scenario.get("setup_plan") or [])

    assert game.requires_setup_phase() is True
    assert any("Tovina" in str(step.get("prompt", "")) for step in plan)
    assert any("wciągarce" in str(step.get("prompt", "")) for step in plan)
    assert any("fizycznym elementem planszy" in str(step.get("prompt", "")) for step in plan)


def test_alarm_thresholds_mark_evidence_tovin_and_odran():
    game = Game(conn=DummyConnection(), scenario="ashen_oath_old_mill")

    increase_alarm(game)
    increase_alarm(game)
    increase_alarm(game)
    increase_alarm(game)

    state = ensure_state(game)
    assert state["alarm_level"] == 4
    assert state["guards_alerted"] is True
    assert state["evidence_threatened"] is True
    assert state["tovin_in_danger"] is True
    assert state["odran_warned"] is True
    assert game.global_flags["mill_alarm_raised"] is True
    assert game.global_flags["odran_warned"] is True


def test_old_mill_rewards_and_route_set_expected_flags():
    game = Game(conn=DummyConnection(), scenario="ashen_oath_old_mill")

    secure_false_ash(game)
    secure_ledger(game)
    secure_tovin(game)
    reveal_hidden_route(game)

    assert game.global_flags["false_ash_found"] is True
    assert game.global_flags["false_ash_secured"] is True
    assert game.global_flags["mill_ledger_secured"] is True
    assert game.global_flags["tovin_secured"] is True
    assert game.global_flags["tovin_rescued"] is True
    assert game.global_flags["hidden_mill_route_found"] is True
    assert ensure_state(game)["hidden_route_found"] is True


def test_ashen_oath_flow_has_old_mill_checkpoints_and_non_game_over_failure():
    flow = load_scenario_flow("ashen_oath")
    events = {event["id"]: event for event in flow["events"]}

    assert {"type": "checkpoint", "reason": "old_mill_entered"} in events["mill_intro"]["actions"]
    assert {"type": "checkpoint", "reason": "tovin_rescued"} in events["mill_cleared_tovin_rescued"]["actions"]
    assert {"type": "checkpoint", "reason": "hidden_mill_route_found"} in events["mill_hidden_route_revealed"]["actions"]
    assert not any(action.get("type") == "finish_scenario" for action in events["mill_cleared_tovin_dead"]["actions"])


def test_short_rest_heals_and_does_not_restore_consumables():
    session = ScenarioSession(conn=DummyConnection(), scenario="ashen_oath")
    holy_water = SimpleNamespace(item_id="holy_water", quantity=0)
    hero = SimpleNamespace(
        hp=2,
        max_hp=11,
        inventory=[holy_water],
        statuses=[
            Status(id="slowed", label="Slowed", duration=1),
            Status(id="class_feature", label="Class Feature"),
        ],
    )
    session.heroes = [hero]

    session.apply_between_map_short_rest(reason="test")

    assert hero.hp == 11
    assert hero.inventory == [holy_water]
    assert [status.id for status in hero.statuses] == ["class_feature"]


def test_old_mill_tpk_restore_returns_to_map_checkpoint():
    session = ScenarioSession(conn=DummyConnection(), scenario="ashen_oath")
    session.current_map_id = "old_mill"
    session._load_map("old_mill", entry_anchor_id="from_square", initial_load=False)  # noqa: SLF001
    assert session.current_game is not None

    hero = Hero()
    hero.name = "Tester"
    hero.character_id = "tester"
    hero.max_hp = 12
    hero.hp = 12
    session.heroes = [hero]
    session.current_game.heroes = [hero]
    session._place_party_on_map(session.current_game, anchor_id="from_square")  # noqa: SLF001
    session.global_flags["holy_water_used"] = True
    session.save_checkpoint(reason="old_mill_entered")

    session.global_flags["tovin_dead"] = True
    hero.hp = 0

    restored = session.restore_checkpoint("old_mill_entered", reason="test")

    assert restored is True
    assert session.current_map_id == "old_mill"
    assert session.global_flags["holy_water_used"] is True
    assert session.global_flags.get("tovin_dead") is not True
    assert hero.hp == 12
