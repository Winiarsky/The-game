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
    assert "czerwony" in prompt
    assert "zielony" in prompt


def test_runtime_setup_batches_visible_interactables_by_four_distinct_colors():
    payload = _load_runtime_payload("ashen_oath_brindleford_square")
    game = Game(
        conn=DummyConnection(),
        scenario_payload=payload,
        scenario_label="ashen_oath:brindleford_square",
    )

    plan = build_runtime_setup_plan(game)
    interactable_steps = [step for step in plan if step["kind"] == "interactable"]
    assert len(interactable_steps) == 4

    labels = {str(item["label"]) for step in interactable_steps for item in step["legend"]}
    assert {
        "Castellan Odran Vale",
        "Elna Barrow",
        "Mara Fen, zielarka",
        "Znajdź czystą wodę dla Brena",
        "Sprawdź ślad worka z popiołem",
    } <= labels
    for step in interactable_steps:
        assert len(step["positions"]) <= 4
        assert len(step["colors"]) == len(step["positions"])
        assert len({tuple(color) for color in step["colors"]}) == len(step["positions"])
        prompt = str(step["prompt"] or "")
        assert "LED czerwony" in prompt
        assert "paczka" in prompt
    first_prompt = str(interactable_steps[0]["prompt"] or "")
    second_prompt = str(interactable_steps[1]["prompt"] or "")
    assert "1. " in first_prompt
    assert "4. " in first_prompt
    assert "5. " in second_prompt
    assert "8. " in second_prompt
    assert "13. " in str(interactable_steps[3]["prompt"] or "")


def test_ashen_oath_runtime_setup_uses_corner_orientation_markers():
    payload = _load_runtime_payload("ashen_oath_brindleford_square")
    game = Game(
        conn=DummyConnection(),
        scenario_payload=payload,
        scenario_label="ashen_oath:brindleford_square",
    )

    plan = build_runtime_setup_plan(game)
    room_step = next(step for step in plan if step["kind"] == "room")

    assert room_step["label"] == "Map orientation 20x30"
    assert room_step["positions"] == [[0, 0], [19, 0], [0, 29]]
    assert room_step["colors"] == [[0, 90, 255], [255, 210, 0], [255, 30, 30]]
    assert [0, 0] in room_step["positions"]
    assert [19, 0] in room_step["positions"]
    assert [0, 29] in room_step["positions"]
    assert "Potwierdz Enterem" in str(room_step["prompt"])


def test_ashen_oath_runtime_setup_obstacles_list_count_and_positions():
    payload = _load_runtime_payload("ashen_oath_brindleford_square")
    game = Game(
        conn=DummyConnection(),
        scenario_payload=payload,
        scenario_label="ashen_oath:brindleford_square",
    )

    plan = build_runtime_setup_plan(game)
    obstacle_step = next(step for step in plan if step["kind"] == "obstacle")
    prompt = str(obstacle_step["prompt"] or "")

    assert "8" in prompt
    assert "(6, 9)" in prompt
    assert "(7, 9)" in prompt
    assert "(9, 10)" in prompt
    assert "(15, 10)" in prompt


def test_ashen_oath_runtime_setup_exits_are_numbered():
    payload = _load_runtime_payload("ashen_oath_brindleford_square")
    game = Game(
        conn=DummyConnection(),
        scenario_payload=payload,
        scenario_label="ashen_oath:brindleford_square",
    )

    plan = build_runtime_setup_plan(game)
    exit_step = next(step for step in plan if step["kind"] == "scenario_exit")
    prompt = str(exit_step["prompt"] or "")

    assert "1. " in prompt
    assert "2. " in prompt
    assert "3. " in prompt


def test_runtime_setup_batches_visible_exits_when_more_than_four():
    payload = _load_runtime_payload("ashen_oath_brindleford_square")
    extra = []
    for idx in range(5):
        extra.append(
            {
                "position": [2 + idx, 7],
                "config": {
                    "exit_id": f"extra_exit_{idx}",
                    "label": f"Dodatkowe przejście {idx + 1}",
                    "interaction_mode": "on_enter",
                },
            }
        )
    for object_group in payload["objects"]:
        if object_group.get("object_id") == "scenario_exit":
            object_group["instances"].extend(extra)
            break
    game = Game(
        conn=DummyConnection(),
        scenario_payload=payload,
        scenario_label="ashen_oath:brindleford_square",
    )

    plan = build_runtime_setup_plan(game)
    exit_steps = [step for step in plan if step["kind"] == "scenario_exit"]

    assert len(exit_steps) == 2
    assert [len(step["positions"]) for step in exit_steps] == [4, 4]
    assert "paczka 1/2" in str(exit_steps[0]["prompt"] or "")
    assert "paczka 2/2" in str(exit_steps[1]["prompt"] or "")
    assert "LED czerwony" in str(exit_steps[0]["prompt"] or "")
    assert "LED czerwony" in str(exit_steps[1]["prompt"] or "")


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


def test_runtime_setup_prompts_include_counts_and_positions_for_terrain_and_enemies():
    payload = _load_runtime_payload("bandit_cave_cave_entrance")
    game = Game(
        conn=DummyConnection(),
        scenario_payload=payload,
        scenario_label="bandit_cave:cave_entrance",
    )

    plan = build_runtime_setup_plan(game)
    terrain_step = next(step for step in plan if step["kind"] == "terrain")
    enemy_step = next(step for step in plan if step["kind"] == "enemy")

    terrain_prompt = str(terrain_step["prompt"] or "")
    enemy_prompt = str(enemy_step["prompt"] or "")

    assert f"({len(terrain_step['positions'])}):" in terrain_prompt
    assert str(tuple(terrain_step["positions"][0])) in terrain_prompt
    assert f"({len(enemy_step['positions'])}):" in enemy_prompt
    assert str(tuple(enemy_step["positions"][0])) in enemy_prompt


def test_ashen_oath_return_exit_labels_are_polish_in_runtime_setup():
    payload = _load_runtime_payload("ashen_oath_burned_chapel")
    game = Game(
        conn=DummyConnection(),
        scenario_payload=payload,
        scenario_label="ashen_oath:burned_chapel",
    )

    plan = build_runtime_setup_plan(game)
    exit_step = next(step for step in plan if step["kind"] == "scenario_exit")
    prompt = str(exit_step["prompt"] or "")

    assert "Powrót do Brindleford" in prompt
    assert "Return to Brindleford" not in prompt
