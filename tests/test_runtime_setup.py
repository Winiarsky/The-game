from __future__ import annotations

import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from runtime_setup import build_runtime_setup_plan
from src.game import Game


class DummyConnection:
    def set_leds(self, *_args, **_kwargs):
        return None

    def leds_off(self, *_args, **_kwargs):
        return None

    def scan_board(self, acceptable_responses=None):
        if acceptable_responses:
            return tuple(acceptable_responses[0])
        return (0, 0)


def _load_runtime_payload(name: str) -> dict:
    path = PROJECT_ROOT / "scenarios" / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_runtime_setup_plan_builds_from_bandit_cave_runtime_board():
    payload = _load_runtime_payload("bandit_cave_cave_entrance")
    game = Game(
        conn=DummyConnection(),
        scenario_payload=payload,
        scenario_label="bandit_cave:cave_entrance",
    )

    plan = build_runtime_setup_plan(game)
    kinds = [step["kind"] for step in plan]

    assert "room" in kinds
    assert "wall" in kinds
    assert "terrain" in kinds
    assert "obstacle" in kinds
    assert "enemy" in kinds
    assert "interactable" not in kinds
    assert "scenario_exit" in kinds

    exit_step = next(step for step in plan if step["kind"] == "scenario_exit")
    exit_positions = {tuple(pos) for pos in exit_step["positions"]}
    assert (18, 9) in exit_positions
    assert (10, 7) not in exit_positions
    assert "Tunnel to Docks" in str(exit_step["prompt"] or "")
    assert "LED" in str(exit_step["prompt"] or "")
    assert len(exit_step["colors"]) == len(exit_step["positions"])
    assert exit_step["legend"][0]["label"] == "Tunnel to Docks"


def test_runtime_setup_distinguishes_multiple_visible_exits_by_color():
    payload = _load_runtime_payload("bandit_cave_smuggler_docks")
    game = Game(
        conn=DummyConnection(),
        scenario_payload=payload,
        scenario_label="bandit_cave:smuggler_docks",
    )

    plan = build_runtime_setup_plan(game)
    exit_step = next(step for step in plan if step["kind"] == "scenario_exit")

    assert len(exit_step["positions"]) >= 2
    assert len({tuple(color) for color in exit_step["colors"]}) >= 2
    prompt = str(exit_step["prompt"] or "")
    assert "Smuggler Ship" in prompt
    assert "Back to Cave" in prompt
    assert "pomarańczowy" in prompt
    assert "niebieski" in prompt


def test_runtime_setup_plan_skips_defeated_enemies():
    payload = _load_runtime_payload("bandit_cave_cave_entrance")
    game = Game(
        conn=DummyConnection(),
        scenario_payload=payload,
        scenario_label="bandit_cave:cave_entrance",
    )
    assert game.enemies

    defeated = game.enemies[0]
    defeated.hp = 0

    plan = build_runtime_setup_plan(game)
    enemy_steps = [step for step in plan if step["kind"] == "enemy"]

    assert enemy_steps
    enemy_positions = {tuple(pos) for step in enemy_steps for pos in step["positions"]}
    assert getattr(defeated, "position", None) not in enemy_positions
