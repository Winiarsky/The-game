"""Mission clues and suspended decisions use the same live rule state."""
from __future__ import annotations

from pathlib import Path

import pytest

from dnd_board_game.rules import progress_confrontation as rules
from dnd_board_game.ui import confrontation, mission_zero as mission
from tests.unit.test_mission_zero import send, session, stage


@pytest.mark.parametrize("outcome,cost", [("accepted", 0), ("refused", 100)])
def test_borut_clue_changes_real_check_and_survives_reload(
    tmp_path: Path, outcome: str, cost: int,
) -> None:
    game = session(tmp_path, legacy_combat=False)
    stage(game, "explore", outcome=outcome)
    gold = game.exploration.actors[0].currency.total_cp
    send(game, "leader")
    send(game, "rumor")
    assert game.exploration.actors[0].currency.total_cp == gold - cost
    send(game, "back")
    send(game, "quarters")
    send(game, "search", room="quarters")
    data = confrontation.read_store(game)
    state = rules.Confrontation.from_data(data["current"]["state"])
    assert {option.dc for person in state.participants for option in person.options} == {12}
    def command(action: str, **extra: object) -> None:
        confrontation.command(game, dict(action=action, revision=confrontation.read_store(game)["revision"], **extra))
    command("acknowledge")
    command("approach", approach=state.actor.options[0].id)
    selected = rules.Confrontation.from_data(confrontation.read_store(game)["current"]["state"])
    # A total of 12 fails without the clue and succeeds with it.
    natural = 12 - selected.check_modifier
    assert 2 <= natural <= 19
    command("roll", rolls=[natural])
    command("confirm")
    assert confrontation.payload(game)["progress"] == 1
    game._load_snapshot_from_path(game.snapshot_path)
    restored = rules.Confrontation.from_data(confrontation.read_store(game)["current"]["state"])
    assert restored.participants == rules.Confrontation.from_data(data["current"]["state"]).participants
    assert restored.progress == 1 and restored.stage == "after_action"
    assert mission.read(game)["flags"].count("rumor_known") == 1
    assert game.exploration.actors[0].currency.total_cp == gold - cost


def test_mission_cannot_advance_under_unresolved_confrontation(tmp_path: Path) -> None:
    game = session(tmp_path, legacy_combat=False)
    stage(game, "brief")
    send(game, "negotiate")
    before = game.state
    with pytest.raises(ValueError, match="konfrontacj"):
        send(game, "why")
    assert game.state == before


def test_clue_is_unavailable_after_quarters_are_resolved(tmp_path: Path) -> None:
    game = session(tmp_path, legacy_combat=False)
    stage(game, "explore", outcome="refused")
    send(game, "quarters")
    send(game, "collect", room="quarters")
    send(game, "back")
    send(game, "leader")
    gold = game.exploration.actors[0].currency.total_cp
    assert not any(c["action"] == "rumor" for c in mission.payload(game)["choices"])
    with pytest.raises(ValueError):
        send(game, "rumor")
    assert game.exploration.actors[0].currency.total_cp == gold


def test_existing_confrontation_keeps_its_saved_dc_when_resumed(tmp_path: Path) -> None:
    game = session(tmp_path, legacy_combat=False)
    stage(game, "explore")
    send(game, "quarters")
    send(game, "search", room="quarters")
    original = confrontation.read_store(game)["current"]
    assert rules.Confrontation.from_data(original["state"]).actor.options[0].dc == 14
    # A pre-fix save can already own the clue but have stored DC 14.
    data = mission.read(game)
    data["flags"].append("rumor_known")
    mission.write(game, data)
    mission.autosave(game)
    game._load_snapshot_from_path(game.snapshot_path)
    confrontation.command(game, dict(action="leave", revision=confrontation.read_store(game)["revision"]))
    send(game, "resume_search")
    restored = confrontation.read_store(game)["current"]
    assert restored["token"] == original["token"]
    assert restored["state"] == original["state"]
