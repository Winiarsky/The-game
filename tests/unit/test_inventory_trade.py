from dataclasses import replace

import pytest

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.inventory import (
    CurrencyWallet,
    InventoryItem,
    MerchantState,
    buy_from_merchant,
    currency_wallet_from_cp,
    sell_to_merchant,
)
from dnd_board_game.world import Coordinate


def _actor(
    *,
    currency: CurrencyWallet = CurrencyWallet(gp=10),
    inventory: tuple[InventoryItem, ...] = (),
    strength: int = 10,
) -> Actor:
    return Actor(
        id=ActorId("hero"),
        name="Bohater",
        ac=12,
        hp=10,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(0, 0),
        faction=Faction.ALLY,
        ability_scores=AbilityScores(strength=strength),
        currency=currency,
        inventory=inventory,
    )


def _merchant(
    *,
    currency: CurrencyWallet = CurrencyWallet(gp=20),
) -> MerchantState:
    return MerchantState(
        id="mira",
        name="Mira",
        inventory=(
            InventoryItem(
                "crossbow_bolt",
                "Bełt",
                "ammunition",
                quantity=20,
                equipped=False,
                ammunition_type="bolt",
                value_cp=5,
                weight_lb=0.075,
            ),
        ),
        currency=currency,
    )


def test_currency_wallet_from_cp_returns_canonical_change():
    assert currency_wallet_from_cp(1_237) == CurrencyWallet(cp=7, sp=3, gp=2, pp=1)


def test_buy_from_merchant_moves_partial_stock_money_and_returns_change():
    result = buy_from_merchant(
        _merchant(),
        _actor(currency=CurrencyWallet(gp=1)),
        item_id="crossbow_bolt",
        quantity=7,
    )

    assert result.total_cp == 35
    assert result.actor.currency == CurrencyWallet(cp=5, sp=6)
    assert result.merchant.currency.total_cp == 2_035
    assert result.actor.inventory[0].quantity == 7
    assert result.merchant.inventory[0].quantity == 13


def test_buy_rejects_insufficient_money_or_capacity_without_mutation():
    merchant = _merchant()
    poor = _actor(currency=CurrencyWallet(cp=4))

    with pytest.raises(ValueError, match="dość monet"):
        buy_from_merchant(
            merchant,
            poor,
            item_id="crossbow_bolt",
            quantity=1,
        )

    overloaded = _actor(
        strength=1,
        inventory=(
            InventoryItem(
                "ballast",
                "Balast",
                "gear",
                equipped=False,
                weight_lb=15,
            ),
        ),
    )
    with pytest.raises(ValueError, match="udźwig"):
        buy_from_merchant(
            merchant,
            overloaded,
            item_id="crossbow_bolt",
            quantity=1,
        )

    assert merchant.inventory[0].quantity == 20
    assert poor.currency == CurrencyWallet(cp=4)


def test_sell_to_merchant_uses_buyback_rate_and_partial_quantity():
    bolts = replace(_merchant().inventory[0], quantity=8)
    actor = _actor(currency=CurrencyWallet(), inventory=(bolts,))
    merchant = MerchantState(
        id="mira",
        name="Mira",
        currency=CurrencyWallet(gp=1),
        buyback_percent=50,
    )

    result = sell_to_merchant(
        merchant,
        actor,
        item_id="crossbow_bolt",
        quantity=4,
    )

    assert result.total_cp == 8
    assert result.actor.currency == CurrencyWallet(cp=8)
    assert result.actor.inventory[0].quantity == 4
    assert result.merchant.inventory[0].quantity == 4
    assert result.merchant.currency.total_cp == 92


def test_sell_rejects_equipped_item_and_merchant_without_funds():
    equipped = InventoryItem(
        "dagger",
        "Sztylet",
        "weapon",
        equipped=True,
        value_cp=200,
    )
    actor = _actor(currency=CurrencyWallet(), inventory=(equipped,))
    merchant = MerchantState(id="mira", name="Mira")

    with pytest.raises(ValueError, match="nie może"):
        sell_to_merchant(merchant, actor, item_id="dagger", quantity=1)

    actor = replace(actor, inventory=(replace(equipped, equipped=False),))
    with pytest.raises(ValueError, match="dość monet"):
        sell_to_merchant(merchant, actor, item_id="dagger", quantity=1)
