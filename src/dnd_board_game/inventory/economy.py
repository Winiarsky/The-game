"""Currency, item mass, and D&D 5e carrying-capacity rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from dnd_board_game.actors import Actor
    from dnd_board_game.inventory import InventoryItem


COPPER_PER_SP = 10
COPPER_PER_EP = 50
COPPER_PER_GP = 100
COPPER_PER_PP = 1_000
COINS_PER_POUND = 50


@dataclass(frozen=True, slots=True)
class CurrencyWallet:
    cp: int = 0
    sp: int = 0
    ep: int = 0
    gp: int = 0
    pp: int = 0

    def __post_init__(self) -> None:
        if any(value < 0 for value in self.as_tuple()):
            raise ValueError("Currency amounts cannot be negative.")

    def as_tuple(self) -> tuple[int, int, int, int, int]:
        return (self.cp, self.sp, self.ep, self.gp, self.pp)

    @property
    def total_coins(self) -> int:
        return sum(self.as_tuple())

    @property
    def total_cp(self) -> int:
        return (
            self.cp
            + self.sp * COPPER_PER_SP
            + self.ep * COPPER_PER_EP
            + self.gp * COPPER_PER_GP
            + self.pp * COPPER_PER_PP
        )

    @property
    def is_empty(self) -> bool:
        return self.total_coins == 0

    def add(self, other: CurrencyWallet) -> CurrencyWallet:
        return CurrencyWallet(*(left + right for left, right in zip(self.as_tuple(), other.as_tuple())))

    def subtract(self, other: CurrencyWallet) -> CurrencyWallet:
        values = tuple(left - right for left, right in zip(self.as_tuple(), other.as_tuple()))
        if any(value < 0 for value in values):
            raise ValueError("Currency wallet does not contain the requested coins.")
        return CurrencyWallet(*values)

    def as_payload(self) -> dict[str, int | float]:
        return {
            "cp": self.cp,
            "sp": self.sp,
            "ep": self.ep,
            "gp": self.gp,
            "pp": self.pp,
            "total_cp": self.total_cp,
            "weight_lb": currency_weight_lb(self),
        }


def currency_weight_lb(wallet: CurrencyWallet) -> float:
    return wallet.total_coins / COINS_PER_POUND


def currency_wallet_from_cp(total_cp: int) -> CurrencyWallet:
    """Normalize a non-negative copper value into stable coin denominations."""

    if total_cp < 0:
        raise ValueError("Currency value cannot be negative.")
    pp, remaining = divmod(total_cp, COPPER_PER_PP)
    gp, remaining = divmod(remaining, COPPER_PER_GP)
    sp, cp = divmod(remaining, COPPER_PER_SP)
    return CurrencyWallet(cp=cp, sp=sp, gp=gp, pp=pp)


def inventory_weight_lb(items: Iterable[InventoryItem]) -> float:
    return sum(item.weight_lb * item.quantity for item in items)


def carried_weight_lb(actor: Actor) -> float:
    return inventory_weight_lb(actor.inventory) + currency_weight_lb(actor.currency)


def carrying_capacity_lb(actor: Actor) -> float:
    """Return the standard 5e carrying capacity: Strength score × 15 lb."""

    return max(0, actor.ability_scores.strength) * 15.0


def remaining_capacity_lb(actor: Actor) -> float:
    return max(0.0, carrying_capacity_lb(actor) - carried_weight_lb(actor))


def carrying_payload(actor: Actor) -> dict[str, float | bool]:
    weight = carried_weight_lb(actor)
    capacity = carrying_capacity_lb(actor)
    return {
        "weight_lb": weight,
        "capacity_lb": capacity,
        "remaining_lb": max(0.0, capacity - weight),
        "over_capacity": weight > capacity,
    }
