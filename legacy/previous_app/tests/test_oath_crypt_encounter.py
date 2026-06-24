from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from oath_crypt_encounter import ensure_state, present_proof, proof_bonus, reject_proof
from scenario_flow import load_scenario_flow
from scenario_session import ScenarioSession
from src.game import Game
from hero import Hero


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


def test_oath_crypt_loads_full_final_board_and_interactions():
    game = Game(conn=DummyConnection(), scenario="ashen_oath_oath_crypt")
    ids, positions = _interactable_ids(game)
    room_cells = list(game.scenario["rooms"][0]["positions"])

    assert len(room_cells) == 600
    assert game.requires_setup_phase() is True
    assert {enemy.__class__.__name__ for enemy in game.enemies} == {"OdransChampion", "AshenKnight", "AshenWatcher"}
    assert len(game.enemies) == 4
    assert {"warden_serai", "odran_vale"} <= ids
    assert "oath_crypt_overview" in ids
    assert "oath_crypt_reliquary" in ids
    assert "oath_crypt_odran_gate" in ids
    assert {"oath_crypt_proof_oath", "oath_crypt_proof_ash", "oath_crypt_proof_ledger", "oath_crypt_proof_witness"} <= ids
    assert {"restore_oath", "bargain_with_odran", "return_to_ruins_from_crypt"} <= ids
    assert positions["from_ruins"] == (10, 29)


def test_four_presented_proofs_unlock_restore_and_bargain_gate():
    game = Game(conn=DummyConnection(), scenario="ashen_oath_oath_crypt")

    for proof_id in ("oath", "ash", "ledger"):
        ok, _msg = present_proof(game, proof_id, method="test")
        assert ok is True
        assert game.global_flags.get("restore_oath_unlocked") is not True

    ok, msg = present_proof(game, "witness", method="test")

    assert ok is True
    assert "Czwarty dowód" in msg
    assert game.global_flags["restore_oath_unlocked"] is True
    assert game.global_flags["bargain_unlocked"] is True
    assert game.global_flags["odran_confronted"] is True
    assert ensure_state(game)["proof_score"] == 4


def test_previous_map_flags_give_contextual_proof_bonuses_without_hard_locking():
    game = Game(conn=DummyConnection(), scenario="ashen_oath_oath_crypt")
    game.global_flags = {
        "warden_medallion_recovered": True,
        "false_ash_secured": True,
        "mill_ledger_secured": True,
        "tovin_dead": True,
        "mira_truth_learned": True,
    }

    assert proof_bonus(game, "oath") == 3
    assert proof_bonus(game, "ash") == 3
    assert proof_bonus(game, "ledger") == 3
    assert proof_bonus(game, "witness") == 3

    ok, msg = present_proof(game, "witness", method="test")
    assert ok is True
    assert "1/4" in msg


def test_rejected_proof_increases_odran_pressure_and_can_start_escape():
    game = Game(conn=DummyConnection(), scenario="ashen_oath_oath_crypt")
    state = ensure_state(game)
    state["oath_integrity"] = 1

    msg = reject_proof(game, reason="test")

    assert "Brama Odrana" in msg
    assert game.global_flags["odran_escape_started"] is True
    assert ensure_state(game)["odran_pressure"] == 1


def test_ashen_oath_flow_oath_crypt_final_gates_and_checkpoints():
    flow = load_scenario_flow("ashen_oath")
    events = {event["id"]: event for event in flow["events"]}

    assert {"type": "checkpoint", "reason": "oath_crypt_entered"} in events["crypt_intro"]["actions"]
    assert {"type": "checkpoint", "reason": "oath_trial_started"} in events["oath_trial_started_checkpoint"]["actions"]
    assert {"type": "checkpoint", "reason": "odran_confronted"} in events["odran_confronted_checkpoint"]["actions"]
    assert events["restore_oath_ending"]["conditions"] == [{"type": "flag", "flag": "restore_oath_unlocked", "value": True}]
    assert events["bargain_ending"]["conditions"] == [{"type": "flag", "flag": "bargain_unlocked", "value": True}]


def test_restore_and_bargain_endings_are_not_available_before_unlock_flags():
    session = ScenarioSession(conn=DummyConnection(), scenario="ashen_oath")
    session.current_map_id = "oath_crypt"
    session._load_map("oath_crypt", entry_anchor_id=None, initial_load=False, place_party=False)  # noqa: SLF001

    assert session._conditions_pass([{"type": "flag", "flag": "restore_oath_unlocked", "value": True}], map_id="oath_crypt", target_id="restore_oath") is False  # noqa: SLF001
    assert session._conditions_pass([{"type": "flag", "flag": "bargain_unlocked", "value": True}], map_id="oath_crypt", target_id="bargain_with_odran") is False  # noqa: SLF001

    game = session.current_game
    assert game is not None
    present_proof(game, "oath", method="test")
    present_proof(game, "ash", method="test")
    present_proof(game, "ledger", method="test")
    present_proof(game, "witness", method="test")

    assert session._conditions_pass([{"type": "flag", "flag": "restore_oath_unlocked", "value": True}], map_id="oath_crypt", target_id="restore_oath") is True  # noqa: SLF001
    assert session._conditions_pass([{"type": "flag", "flag": "bargain_unlocked", "value": True}], map_id="oath_crypt", target_id="bargain_with_odran") is True  # noqa: SLF001


def test_oath_crypt_tpk_restores_map_checkpoint():
    session = ScenarioSession(conn=DummyConnection(), scenario="ashen_oath")
    session.current_map_id = "oath_crypt"
    session._load_map("oath_crypt", entry_anchor_id="from_ruins", initial_load=False)  # noqa: SLF001
    assert session.current_game is not None

    hero = Hero()
    hero.name = "Tester"
    hero.character_id = "tester"
    hero.max_hp = 12
    hero.hp = 12
    session.heroes = [hero]
    session.current_game.heroes = [hero]
    session._place_party_on_map(session.current_game, anchor_id="from_ruins")  # noqa: SLF001
    session.global_flags["mira_truth_learned"] = True
    session.save_checkpoint(reason="oath_crypt_entered")

    session.global_flags["village_condemned"] = True
    hero.hp = 0

    restored = session._maybe_restore_map_after_tpk()  # noqa: SLF001

    assert restored is True
    assert session.current_map_id == "oath_crypt"
    assert session.global_flags["mira_truth_learned"] is True
    assert session.global_flags.get("village_condemned") is not True
    assert hero.hp == 12
