from dataclasses import replace

import pytest

from dnd_board_game.exploration import (
    complete_downtime_crafting,
    plan_downtime_crafting,
)
from dnd_board_game.scenarios import (
    build_exploration_from_scenario,
    load_scenario,
)


def _context():
    exploration = build_exploration_from_scenario(
        load_scenario("content/scenarios/village_square_mvp.json")
    )
    hero = next(
        actor for actor in exploration.actors if str(actor.id) == "hero"
    )
    recipe = exploration.downtime_policy.recipe_by_id("forge_dagger")
    return hero, recipe


def test_downtime_crafting_derives_material_cost_and_full_workdays() -> None:
    hero, recipe = _context()
    three_daggers = replace(
        recipe,
        product=replace(recipe.product, quantity=3),
    )

    plan = plan_downtime_crafting(
        actor=hero,
        recipe=three_daggers,
        current_zone_id="market",
    )

    assert three_daggers.market_value_cp == 600
    assert plan.material_cost_cp == 300
    assert three_daggers.work_days == 2
    assert plan.time_cost_minutes == 960


def test_downtime_crafting_consumes_money_and_adds_permanent_item() -> None:
    hero, recipe = _context()
    plan = plan_downtime_crafting(
        actor=hero,
        recipe=recipe,
        current_zone_id="market",
    )

    result = complete_downtime_crafting(plan)

    assert result.actor_before.currency.total_cp == 1_000
    assert result.actor_after.currency.total_cp == 900
    dagger = next(item for item in result.actor_after.inventory if item.id == "dagger")
    assert dagger.quantity == 1
    assert dagger.equipped is False
    assert dagger.value_cp == 200


@pytest.mark.parametrize(
    ("actor_change", "zone_id", "message"),
    [
        (
            lambda actor: replace(
                actor,
                proficiencies=replace(actor.proficiencies, tools=()),
            ),
            "market",
            "biegłości",
        ),
        (
            lambda actor: replace(
                actor,
                inventory=tuple(
                    item for item in actor.inventory if item.id != "smiths_tools"
                ),
            ),
            "market",
            "narzędzi",
        ),
        (
            lambda actor: replace(
                actor,
                currency=replace(actor.currency, gp=0),
            ),
            "market",
            "dość monet",
        ),
        (
            lambda actor: actor,
            "tavern",
            "Kuźnia na rynku",
        ),
    ],
)
def test_downtime_crafting_rejects_missing_requirement(
    actor_change,
    zone_id: str,
    message: str,
) -> None:
    hero, recipe = _context()

    with pytest.raises(ValueError, match=message):
        plan_downtime_crafting(
            actor=actor_change(hero),
            recipe=recipe,
            current_zone_id=zone_id,
        )
