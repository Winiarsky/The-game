"""Authored Mission 0 outcomes reach settlement with their consequences intact."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from dnd_board_game.combat.scene import scene_flag
from dnd_board_game.scenarios.mission_pack import read_json
from dnd_board_game.ui import mission_zero as mission
from dnd_board_game.ui.training_arena import training_hero
from tests.unit.test_mission_zero import PACK, send, session, stage


@pytest.mark.parametrize("battle,bell,debt", [
    ("accepted", "village", "help"),
    ("refused", "guild", "decline"),
    ("refused", "fence", "garran"),
    ("defeated", "village", ""),
])
def test_quest_consequences_persist_through_settlement_and_completion(
    tmp_path: Path, battle: str, bell: str, debt: str,
) -> None:
    game = session(tmp_path, legacy_combat=False)
    game.configure_custom_party(tuple(training_hero(hero) for hero in ("garran", "mira", "nimra")))
    mission.initialize(game)
    stage(game, "explore", outcome=battle)
    for room in ("armory", "quarters"):
        send(game, room)
        send(game, "collect", room=room)
        send(game, "back")
    send(game, "store")
    send(game, "back")
    send(game, "leader")
    if debt:
        send(game, "debt_" + debt)
    send(game, "back")
    send(game, "dilemma")
    text = mission.payload(game)["text"]
    assert "{" not in text["body"]
    if battle == "defeated":
        assert text["id"] == "dilemma_defeated"
        assert {c["action"] for c in mission.payload(game)["choices"]} == {"bell_village", "back"}
        for unavailable in ("bell_guild", "bell_fence"):
            with pytest.raises(ValueError):
                send(game, unavailable)
    else:
        rewards = read_json(PACK, "mechanics/rewards.json")
        assert f"{rewards['bell_guild_gp']} sz" in text["body"]
        assert f"{rewards['bell_fence_gp']} sz" in text["body"]
        assert "nie znacie terminu wypłaty" in text["body"]
    send(game, "bell_" + bell)
    send(game, "next")
    send(game, "loaded")
    send(game, "next")
    send(game, "summary")
    send(game, "finish")
    before = mission.read(game)
    game._load_snapshot_from_path(game.save_dir / "misja_0_dzwon.completed.json")
    case = json.loads(scene_flag(game.state.flags, "campaign_mission_zero_case", ""))
    assert case == dict(debt=debt, bell=bell, truce=battle == "accepted",
                        documents=debt in ("help", "garran"), resolved=False)
    assert mission.read(game)["cargo"] == before["cargo"]
    assert mission.read(game)["ledger"] == before["ledger"]
    ledger = mission.read(game)["ledger"]
    assert sum(entry["amount"] for entry in ledger if entry["kind"] == "money") == 30 + (10 if bell == "guild" else 0)


def test_bell_presentation_matches_party_and_live_reward_values(tmp_path: Path) -> None:
    game = session(tmp_path, legacy_combat=False)
    stage(game, "dilemma")
    body = mission.payload(game)["text"]["body"]
    assert "{" not in body and "pośrednik" not in body
    assert not any(choice["action"] == "bell_fence" for choice in mission.payload(game)["choices"])
