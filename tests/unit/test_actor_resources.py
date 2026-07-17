import pytest

from dnd_board_game.actors import (
    AbilityScores,
    Actor,
    ActorId,
    ActorResourcePool,
    Faction,
    RecoveryPeriod,
    ResourceRechargeRule,
    can_spend_actor_resource,
    depleted_recharge_resource_ids,
    resolve_actor_resource_recharge,
    spend_actor_resource,
)
from dnd_board_game.world import Coordinate


def _actor(pool: ActorResourcePool) -> Actor:
    return Actor(
        ActorId("actor"),
        "Aktor",
        12,
        10,
        0,
        30,
        Coordinate(0, 0),
        Faction.ALLY,
        ability_scores=AbilityScores(),
        resource_pools=(pool,),
    )


def test_limited_resource_is_spent_and_reports_exhaustion() -> None:
    actor = _actor(
        ActorResourcePool(
            "feature_uses",
            "Cecha testowa",
            1,
            1,
            RecoveryPeriod.SHORT_REST,
        )
    )

    spent = spend_actor_resource(actor, "feature_uses")

    assert spent.actor_after.resource_pools[0].current == 0
    assert can_spend_actor_resource(spent.actor_after, "feature_uses") is False
    with pytest.raises(ValueError, match="Brak użyć"):
        spend_actor_resource(spent.actor_after, "feature_uses")


def test_recharge_roll_keeps_or_restores_depleted_resource() -> None:
    actor = _actor(
        ActorResourcePool(
            "breath",
            "Oddech",
            0,
            1,
            RecoveryPeriod.NEVER,
            ResourceRechargeRule(die_sides=6, minimum_roll=5),
        )
    )

    failed = resolve_actor_resource_recharge(actor, "breath", 4)
    succeeded = resolve_actor_resource_recharge(failed.actor_after, "breath", 5)

    assert failed.recharged is False
    assert failed.actor_after.resource_pools[0].current == 0
    assert succeeded.recharged is True
    assert succeeded.actor_after.resource_pools[0].current == 1
    assert depleted_recharge_resource_ids(succeeded.actor_after) == ()


def test_recharge_rule_validates_die_and_threshold() -> None:
    with pytest.raises(ValueError, match="minimum roll"):
        ResourceRechargeRule(die_sides=6, minimum_roll=7)
    with pytest.raises(ValueError, match="at least two"):
        ResourceRechargeRule(die_sides=1, minimum_roll=1)
