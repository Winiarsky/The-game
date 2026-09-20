"""Typed ability-charge requirements, independent from loading and presentation."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Mapping

from .pooled_mana import COLORS, ability_charge
from .shared_mana_catalog import Boost


@dataclass(frozen=True, slots=True)
class PoolAbility:
    id: str
    hero: str
    minimum: int
    required: tuple[tuple[str, int], ...]
    free: bool = False
    burn: int = 1

    def __post_init__(self) -> None:
        if type(self.burn) is not int or self.burn < 0:
            raise ValueError("Nieprawidłowy koszt spalania.")
        if type(self.minimum) is not int or type(self.free) is not bool or self.minimum < 0 or (not self.free and self.minimum == 0) or (self.free and (self.minimum or self.required)):
            raise ValueError("Nieprawidłowy próg zdolności.")
        if len(dict(self.required)) != len(self.required) or any(c not in COLORS or type(n) is not int or n < 1 for c, n in self.required):
            raise ValueError("Nieprawidłowy warunek koloru.")

    def validate(self, hand: tuple[str, ...], values: Mapping[str, int], bonus: int = 0, surcharge: int = 0) -> None:
        if self.free:
            return
        total = ability_charge(hand, values) + bonus
        if not hand or total < self.minimum + surcharge:
            raise ValueError(f"Potrzeba {self.minimum + surcharge} ładunku; masz {total}.")
        counts = Counter(hand)
        missing = [f"{c} × {n - counts[c]}" for c, n in self.required if counts[c] < n]
        if missing:
            raise ValueError("Brakuje kolorów: " + ", ".join(missing))


def validate_boosts(hand: tuple[str, ...], boosts: Mapping[str, int], definitions: tuple[Boost, ...], limit: int) -> None:
    known = {b.id: b for b in definitions}
    if set(boosts) - known.keys():
        raise ValueError("Nieznane podbicie.")
    spent: Counter[str] = Counter()
    for key, amount in boosts.items():
        b = known[key]
        if type(amount) is not int or not 0 <= amount <= b.maximum:
            raise ValueError("Przekroczony limit podbicia.")
        spent[b.color] += amount
    if sum(spent.values()) > limit:
        raise ValueError("Przekroczony łączny limit podbić.")


def default_boosts(hand: tuple[str, ...], definitions: tuple[Boost, ...], limit: int) -> dict[str, int]:
    return {}
