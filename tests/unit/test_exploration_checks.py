from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.exploration import (
    CheckAggregation,
    CheckParticipants,
    ConsequenceTarget,
    ExplorationCheckPlan,
    PartyCheckInput,
    resolve_exploration_check,
)
from dnd_board_game.rules import D20RollRequest
from dnd_board_game.world import Coordinate


def _actor(actor_id: str, name: str) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=name,
        ac=12,
        hp=10,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(0, 0),
        faction=Faction.ALLY,
        ability_scores=AbilityScores(),
    )


def _inputs(*rolls: tuple[Actor, int]) -> tuple[PartyCheckInput, ...]:
    return tuple(PartyCheckInput(actor, natural_roll, D20RollRequest()) for actor, natural_roll in rolls)


def _plan(
    aggregation: CheckAggregation,
    *,
    dc: int = 12,
    participants: CheckParticipants = CheckParticipants.WHOLE_PARTY,
    lead_actor_id: str | None = None,
    consequence_targets: tuple[ConsequenceTarget, ...] = (ConsequenceTarget.SCENE,),
) -> ExplorationCheckPlan:
    return ExplorationCheckPlan(
        participants=participants,
        aggregation=aggregation,
        consequence_targets=consequence_targets,
        ability="wisdom",
        dc=dc,
        lead_actor_id=lead_actor_id,
    )


def test_highest_uses_best_party_result():
    hero = _actor("hero", "Bohater")
    rogue = _actor("rogue", "Łotrzyca")

    result = resolve_exploration_check(_plan(CheckAggregation.HIGHEST), _inputs((hero, 8), (rogue, 15)))

    assert result.success is True
    assert result.selected_actor == rogue
    assert result.selected_roll.total == 15


def test_lowest_uses_worst_party_result():
    hero = _actor("hero", "Bohater")
    rogue = _actor("rogue", "Łotrzyca")

    result = resolve_exploration_check(_plan(CheckAggregation.LOWEST), _inputs((hero, 18), (rogue, 7)))

    assert result.success is False
    assert result.selected_actor == rogue
    assert result.failed_actors == (rogue,)


def test_majority_requires_at_least_half_successes():
    a = _actor("a", "A")
    b = _actor("b", "B")
    c = _actor("c", "C")

    result = resolve_exploration_check(_plan(CheckAggregation.MAJORITY), _inputs((a, 12), (b, 13), (c, 4)))

    assert result.success is True
    assert result.successful_actors == (a, b)
    assert result.failed_actors == (c,)


def test_all_must_succeed_fails_when_one_actor_fails():
    a = _actor("a", "A")
    b = _actor("b", "B")

    result = resolve_exploration_check(_plan(CheckAggregation.ALL_MUST_SUCCEED), _inputs((a, 12), (b, 11)))

    assert result.success is False


def test_any_success_succeeds_when_one_actor_succeeds():
    a = _actor("a", "A")
    b = _actor("b", "B")

    result = resolve_exploration_check(_plan(CheckAggregation.ANY_SUCCESS), _inputs((a, 3), (b, 12)))

    assert result.success is True
    assert result.selected_actor == b


def test_lead_result_uses_selected_lead_actor():
    hero = _actor("hero", "Bohater")
    rogue = _actor("rogue", "Łotrzyca")

    result = resolve_exploration_check(
        _plan(
            CheckAggregation.LEAD_RESULT,
            participants=CheckParticipants.LEAD_WITH_HELP,
            lead_actor_id="hero",
            consequence_targets=(ConsequenceTarget.LEAD_ACTOR,),
        ),
        _inputs((hero, 9), (rogue, 19)),
    )

    assert result.success is False
    assert result.selected_actor == hero
    assert result.consequence_actors == (hero,)


def test_failed_actors_are_consequence_targets():
    hero = _actor("hero", "Bohater")
    rogue = _actor("rogue", "Łotrzyca")

    result = resolve_exploration_check(
        _plan(CheckAggregation.LOWEST, consequence_targets=(ConsequenceTarget.FAILED_ACTORS,)),
        _inputs((hero, 8), (rogue, 16)),
    )

    assert result.consequence_actors == (hero,)


def test_sum_progress_counts_successful_actors():
    hero = _actor("hero", "Bohater")
    rogue = _actor("rogue", "Łotrzyca")

    result = resolve_exploration_check(_plan(CheckAggregation.SUM_PROGRESS), _inputs((hero, 12), (rogue, 16)))

    assert result.success is True
    assert result.progress_total == 2
