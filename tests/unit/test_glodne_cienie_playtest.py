from dnd_board_game.runtime.glodne_cienie_playtest import (
    PlaytestCase,
    default_playtest_cases,
    run_playtest_case,
)


def test_default_matrix_covers_every_supported_party_size() -> None:
    assert {len(case.hero_ids) for case in default_playtest_cases(1)} == {1, 2, 3, 4, 5}


def test_playtest_is_reproducible_and_uses_production_enemy_ai() -> None:
    case = PlaytestCase("smoke", ("garran", "dagna", "erynd"), 1)

    first, first_log = run_playtest_case(case, seed=913, max_rounds=4)
    second, second_log = run_playtest_case(case, seed=913, max_rounds=4)

    assert first == second
    assert first_log == second_log
    enemy_events = [event for event in first_log if event.get("kind") == "enemy_ai"]
    assert enemy_events
    assert all(
        event["intent"]
        in {
            "leader_melee",
            "leader_ranged",
            "leader_advance",
            "pack_attack",
            "pack_advance",
            "flee",
            "cornered",
        }
        for event in enemy_events
    )
    assert all("utility_breakdown" in event for event in enemy_events)
