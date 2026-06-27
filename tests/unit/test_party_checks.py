from dnd_board_game.exploration import PartyCheckInput, resolve_party_check
from dnd_board_game.rules import D20RollRequest
from dnd_board_game.scenarios import build_exploration_from_scenario, load_scenario


def test_party_check_uses_highest_total():
    exploration = build_exploration_from_scenario(load_scenario("content/scenarios/abandoned_watchtower.json"))
    hero, rogue = exploration.actors

    result = resolve_party_check(
        (
            PartyCheckInput(hero, 9, D20RollRequest()),
            PartyCheckInput(rogue, 16, D20RollRequest()),
        ),
        dc=12,
    )

    assert result.success is True
    assert result.winner.id == rogue.id
    assert result.winning_roll.total == 16
