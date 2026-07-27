from dataclasses import replace

from dnd_board_game.actors import (
    ExhaustionRollKind,
    apply_exhaustion_to_roll_request,
    effective_max_hit_points,
    increase_exhaustion,
)
from dnd_board_game.exploration import (
    ScenarioContinuation,
    TravelD20Input,
    TravelPace,
    TravelPolicy,
    forced_march_check_count,
    resolve_travel,
    travel_minutes_for_pace,
)
from dnd_board_game.inventory import effective_speed_feet
from dnd_board_game.rules import D20RollRequest, RollMode
from dnd_board_game.scenarios import (
    build_exploration_from_scenario,
    load_scenario,
)


def _party():
    exploration = build_exploration_from_scenario(
        load_scenario("content/scenarios/village_square_mvp.json")
    )
    return tuple(
        actor for actor in exploration.actors if actor.faction.value == "ally"
    )


def _route(**changes) -> ScenarioContinuation:
    route = ScenarioContinuation(
        id="road",
        label="Stary trakt",
        description="Drużyna rusza traktem.",
        departure_zone_id="road",
        target_scenario_id="tower",
        target_scenario_path="tower.json",
        travel_minutes=45,
        travel_policy=TravelPolicy(
            navigation_dc=12,
            navigation_failure_delay_minutes=30,
        ),
    )
    return replace(route, **changes)


def test_travel_pace_converts_normal_duration() -> None:
    assert travel_minutes_for_pace(45, TravelPace.FAST) == 34
    assert travel_minutes_for_pace(45, TravelPace.NORMAL) == 45
    assert travel_minutes_for_pace(45, TravelPace.SLOW) == 60


def test_navigation_success_and_failure_control_authored_delay() -> None:
    party = _party()
    navigator_id = str(party[0].id)

    success = resolve_travel(
        _route(),
        party,
        pace=TravelPace.NORMAL,
        navigator_actor_id=navigator_id,
        navigation_roll=TravelD20Input(20),
    )
    failure = resolve_travel(
        _route(),
        party,
        pace=TravelPace.NORMAL,
        navigator_actor_id=navigator_id,
        navigation_roll=TravelD20Input(1),
    )

    assert success.total_minutes == 45
    assert success.navigation.success is True
    assert failure.total_minutes == 75
    assert failure.navigation.success is False
    assert failure.navigation.delay_minutes == 30


def test_fast_and_slow_pace_expose_perception_and_stealth_rules() -> None:
    party = _party()
    navigator_id = str(party[0].id)

    fast = resolve_travel(
        _route(),
        party,
        pace=TravelPace.FAST,
        navigator_actor_id=navigator_id,
        navigation_roll=TravelD20Input(20),
    )
    slow = resolve_travel(
        _route(),
        party,
        pace=TravelPace.SLOW,
        navigator_actor_id=navigator_id,
        navigation_roll=TravelD20Input(20),
    )

    assert fast.passive_perception_modifier == -5
    assert fast.allows_stealth is False
    assert slow.passive_perception_modifier == 0
    assert slow.allows_stealth is True


def test_forced_march_applies_one_exhaustion_level_per_failed_hour() -> None:
    party = _party()
    route = _route(
        travel_minutes=600,
        travel_policy=TravelPolicy(safe_travel_minutes=480),
    )
    rolls = {
        str(actor.id): (
            TravelD20Input(1),
            TravelD20Input(1),
        )
        for actor in party
    }

    result = resolve_travel(
        route,
        party,
        pace=TravelPace.NORMAL,
        forced_march_rolls=rolls,
    )

    assert forced_march_check_count(600, safe_travel_minutes=480) == 2
    assert all(actor.exhaustion_level == 2 for actor in result.actors)
    assert len(result.forced_march_results) == len(party) * 2


def test_exhaustion_consequences_follow_2014_levels() -> None:
    actor = _party()[0]
    level_one = increase_exhaustion(actor)
    level_two = replace(actor, exhaustion_level=2)
    level_three = replace(actor, exhaustion_level=3)
    level_four = replace(actor, exhaustion_level=4)
    level_five = replace(actor, exhaustion_level=5)
    level_six = increase_exhaustion(replace(actor, exhaustion_level=5))

    check = apply_exhaustion_to_roll_request(
        level_one,
        D20RollRequest(),
        ExhaustionRollKind.ABILITY_CHECK,
    )
    attack = apply_exhaustion_to_roll_request(
        level_three,
        D20RollRequest(),
        ExhaustionRollKind.ATTACK,
    )

    assert check.mode == RollMode.DISADVANTAGE
    assert effective_speed_feet(level_two) == effective_speed_feet(actor) // 2
    assert attack.mode == RollMode.DISADVANTAGE
    assert effective_max_hit_points(level_four) == actor.max_hp // 2
    assert effective_speed_feet(level_five) == 0
    assert level_six.exhaustion_level == 6
    assert level_six.is_dead() is True
