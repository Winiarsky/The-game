"""Rune cards shared by the playable rules and the modular print source."""
from __future__ import annotations

import json
from functools import lru_cache
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from dnd_board_game.rules.runes import RESOURCE_RUNES
from dnd_board_game.rules.shared_mana_catalog import SharedAbility, Boost, shared_ability


@dataclass(frozen=True, slots=True)
class RuneCard:
    hero_id: str
    id: str
    rune: str
    slot: int
    budget: str
    name: str
    description: str
    boosts: tuple[Boost, ...] = ()
    once: bool = False
    free_first: bool = False
    boost_budgets: tuple[tuple[str, str], ...] = ()

    def payment(self, boosts: Mapping[str, int], *, free_base: bool = False) -> tuple[str, ...]:
        known = {b.id: b for b in self.boosts}
        if set(boosts) - known.keys() or any(type(v) is not int or v not in {0, 1} for v in boosts.values()) or sum(boosts.values()) > 1:
            raise ValueError("Wybierz najwyżej jedno wzmocnienie tej mocy.")
        return (() if free_base else (self.rune,)) + tuple(
            known[k].color for k, v in boosts.items() if v and known[k].color)

    def budget_for(self, boosts: Mapping[str, int]) -> str:
        self.payment(boosts)
        return next((budget for key, budget in self.boost_budgets if boosts.get(key)), self.budget)

    def ability(self) -> SharedAbility:
        return SharedAbility(self.hero_id, self.id, self.name, "R" if self.budget == "R" else "D", "rune", "", self.description, "T", self.boosts, 1)


_GARRAN_BOOST_IDS = {
    "shield_bash": ("damage_d4", "damage", "slow"),
    "second_wind": ("heal_d4", "temp_hp"),
    "defensive_stance": ("anchor", "temp_hp"),
    "garran_command_halt": ("root", "target"),
    "garran_guard_companion": ("reduce_d6", "reduce_d4"),
    "garran_shield_wall": ("ward", "anchor"),
    "garran_rally": ("all", "heal", "second"),
    "iron_bastion": ("armor", "radius"),
    "counterattack_command": ("move", "push"),
}
_COLOR_RUNES = {"B": "Kielich", "N": "Klepsydra", "C": "Błysk", "Z": "Brama", "F": "Oko", "*": "*"}


def rune_cards(hero_id: str) -> tuple[RuneCard, ...]:
    path = Path(__file__).resolve().parents[3] / "content/print/runes_v01/action_cards.json"
    return _rune_cards(hero_id, path.stat().st_mtime_ns)


@lru_cache(maxsize=28)
def _rune_cards(hero_id: str, modified: int) -> tuple[RuneCard, ...]:
    path = Path(__file__).resolve().parents[3] / "content/print/runes_v01/action_cards.json"
    rows = json.loads(path.read_text(encoding="utf-8")).get(hero_id, ())
    cards = []
    for index, row in enumerate(rows):
        legacy = shared_ability(hero_id, row["id"])
        if row.get("status") == "template":
            if legacy is None:
                continue
            rune = row["rune"] if row["rune"] in RESOURCE_RUNES else RESOURCE_RUNES[index % len(RESOURCE_RUNES)]
            boosts = tuple(Boost(b.id, _COLOR_RUNES[b.color], 1, b.label.split(": ", 1)[-1]) for b in legacy.boosts[:3])
            budget = "R" if legacy.timing == "R" else "M+A+S" if legacy.id in {"unstoppable", "blade_dance", "optical_scope"} else "A+S" if legacy.category == "ultimate" else "S"
            description = legacy.description
            if legacy.id == "mana_tuning":
                description = "Zamień jedną własną runę na wierzchnią runę talii. Odrzucona runa trafia na stos odrzuconych."
            elif legacy.id in {"mana_recovery", "mana_great_tuning"}:
                description = "Odzyskaj jedną runę ze stosu odrzuconych do własnej ręki (limit 7)."
            cards.append(RuneCard(hero_id, legacy.id, rune, row["slot"], budget, row["name"], description, boosts))
        else:
            boosts = tuple(Boost(key, cost, 1, text) for key, (cost, text) in zip(row.get("boost_ids", _GARRAN_BOOST_IDS.get(row["id"], ())), row["boosts"]))
            cards.append(RuneCard(hero_id, row["id"], row["rune"], row["slot"], row["budget"], row["name"], row["description"], boosts,
                                  bool(row.get("once", row["id"] == "second_wind")),
                                  bool(row.get("free_first", False)),
                                  tuple(row.get("boost_budgets", {}).items())))
    return tuple(cards)


def rune_card(hero_id: str, ability_id: str) -> RuneCard | None:
    key = "spiritual_weapon" if ability_id == "spiritual_weapon_activation" else ability_id
    card = next((c for c in rune_cards(hero_id) if c.id == key), None)
    if card is not None and ability_id == "spiritual_weapon_activation":
        from dataclasses import replace
        return replace(card, id=ability_id, budget="S")
    return card
