import pytest

from dnd_board_game.combat import (
    CombatMenuAction,
    CombatMenuCategory,
    CombatMenuOption,
    ContextualActionCatalog,
)


def _option(option_id: str, category: CombatMenuCategory) -> CombatMenuOption:
    return CombatMenuOption(
        option_id,
        option_id,
        "",
        category,
        CombatMenuAction.COMBAT_ACTION,
        provider="test",
    )


def test_contextual_action_catalog_groups_independent_providers_in_stable_order() -> None:
    catalog = ContextualActionCatalog.collect(
        (_option("item", CombatMenuCategory.ITEM),),
        (
            _option("shove", CombatMenuCategory.MANEUVER),
            _option("sword", CombatMenuCategory.ATTACK),
        ),
        (_option("spell", CombatMenuCategory.MAGIC),),
    )

    assert [option.id for option in catalog.options] == ["sword", "shove", "spell", "item"]


def test_contextual_action_catalog_rejects_ambiguous_duplicate_ids() -> None:
    duplicate = _option("same", CombatMenuCategory.ITEM)

    with pytest.raises(ValueError, match="ids must be unique"):
        ContextualActionCatalog.collect((duplicate,), (duplicate,))
