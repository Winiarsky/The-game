from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from hill_ruins_encounter import (
    add_ritual_stability,
    consume_hallowed_ash_vial,
    ensure_state,
    expose_false_ash,
    reconstruct_truth,
)
from scenario_flow import load_scenario_flow
from scenario_session import ScenarioSession
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
    positions = {}
    for row in range(game.board.rows):
        for col in range(game.board.cols):
            pos = (col, row)
            for obj in game.board.cell_at(pos).interactables:
                ident = str(
                    getattr(obj, "scenario_object_id", "")
                    or getattr(obj, "cache_id", "")
                    or getattr(obj, "exit_id", "")
                    or getattr(obj, "entry_anchor_id", "")
                    or getattr(obj, "npc_id", "")
                    or ""
                )
                ids.add(ident)
                ids.add(obj.__class__.__name__)
                if ident:
                    positions[ident] = pos
    return ids, positions


def test_hill_ruins_loads_expanded_ritual_map():
    game = Game(conn=DummyConnection(), scenario="ashen_oath_hill_ruins")
    ids, positions = _interactable_ids(game)
    room_cells = list(game.scenario["rooms"][0]["positions"])

    assert len(room_cells) >= 150
    assert game.requires_setup_phase() is True
    assert {enemy.__class__.__name__ for enemy in game.enemies} == {"AshenKnight", "AshenWatcher"}
    assert len(game.enemies) == 3
    assert "mira_ashwane" in ids
    assert "hill_ruins_overview" in ids
    assert {"hill_ruins_anchor_oath", "hill_ruins_anchor_ash", "hill_ruins_anchor_blood", "hill_ruins_anchor_relic"} <= ids
    assert "hill_ruins_oath_echo" in ids
    assert "hill_ruins_false_ash_drift" in ids
    assert "hill_ruins_ash_storm" in ids
    assert "hill_ruins_crypt_descent" in ids
    assert "hill_ruins_fallen_arch" in ids
    assert "ash_memory_circle" in ids
    assert "to_oath_crypt" in ids
    assert positions["from_mill_track"] == (6, 13)


def test_ritual_stability_is_gated_to_once_per_round():
    game = Game(conn=DummyConnection(), scenario="ashen_oath_hill_ruins")

    ok1, msg1 = add_ritual_stability(game, anchor_id="oath", method="test")
    ok2, msg2 = add_ritual_stability(game, anchor_id="ash", method="test")

    assert ok1 is True
    assert "1/4" in msg1
    assert ok2 is False
    assert "jedną stabilizację" in msg2
    assert ensure_state(game)["ritual_stability"] == 1


def test_ritual_completion_sets_truth_and_crypt_flags():
    game = Game(conn=DummyConnection(), scenario="ashen_oath_hill_ruins")
    state = ensure_state(game)
    state["ritual_stability"] = 3
    state["last_stability_round"] = -1

    ok, msg = add_ritual_stability(game, anchor_id="relic", method="test")

    assert ok is True
    assert "pełną scenę" in msg
    assert game.global_flags["mira_truth_learned"] is True
    assert game.global_flags["mira_allied"] is True
    assert game.global_flags["crypt_descent_unsealed"] is True
    assert game.global_flags["odran_relic_theft_proven"] is True
    assert ensure_state(game)["truth_reconstructed"] is True


def test_false_ash_secured_exposes_fabricated_trace():
    game = Game(conn=DummyConnection(), scenario="ashen_oath_hill_ruins")
    game.global_flags = {}
    game.global_flags["false_ash_secured"] = True

    msg = expose_false_ash(game)

    assert "spreparowany pył" in msg
    assert game.global_flags["false_ash_exposed"] is True
    assert "false_ash" in ensure_state(game)["memory_shards_revealed"]


def test_hallowed_ash_vial_is_consumed_once():
    game = Game(conn=DummyConnection(), scenario="ashen_oath_hill_ruins")
    item = SimpleNamespace(item_id="hallowed_ash_vial", name="Fiolka uświęconego popiołu", quantity=2)
    actor = SimpleNamespace(inventory=[item])

    first, msg1 = consume_hallowed_ash_vial(game, actor)
    second, msg2 = consume_hallowed_ash_vial(game, actor)

    assert first is True
    assert "Zużywacie" in msg1
    assert item.quantity == 1
    assert second is False
    assert "już zużyta" in msg2


def test_ashen_oath_flow_hill_ruins_checkpoints_and_crypt_gate():
    flow = load_scenario_flow("ashen_oath")
    events = {event["id"]: event for event in flow["events"]}
    transition = next(item for item in flow["transitions"] if item["id"] == "ruins_to_crypt")

    assert {"type": "checkpoint", "reason": "hill_ruins_entered"} in events["ruins_intro"]["actions"]
    assert {"type": "checkpoint", "reason": "mira_truth_learned"} in events["ash_memory_revealed"]["actions"]
    assert {"type": "checkpoint", "reason": "crypt_descent_unsealed"} in events["ash_memory_revealed"]["actions"]
    assert transition["conditions"] == [{"type": "flag", "flag": "mira_truth_learned", "value": True}]


def test_crypt_transition_unlocks_after_truth_reconstruction():
    session = ScenarioSession(conn=DummyConnection(), scenario="ashen_oath")
    session.current_map_id = "hill_ruins"
    session._load_map("hill_ruins", entry_anchor_id=None, initial_load=False, place_party=False)  # noqa: SLF001
    assert session.current_game is not None
    transition = session._find_transition(exit_id="to_oath_crypt", from_map_id="hill_ruins")  # noqa: SLF001

    assert transition is not None
    assert session._conditions_pass(transition["conditions"], map_id="hill_ruins", target_id="to_oath_crypt") is False  # noqa: SLF001

    reconstruct_truth(session.current_game, method="test")

    assert session._conditions_pass(transition["conditions"], map_id="hill_ruins", target_id="to_oath_crypt") is True  # noqa: SLF001
