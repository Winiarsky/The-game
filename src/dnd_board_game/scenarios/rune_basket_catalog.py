"""Validated content shared by live personal baskets, printed cards and previews.

The JSON supplies costs, capacities, and implemented resonance identifiers.  This
adapter reads files; callers receive a fresh payload, never a shared mutable
catalog.  Validation itself is deterministic and performs no I/O.
"""
from __future__ import annotations

import json
from functools import lru_cache
from collections.abc import Collection
from pathlib import Path
from typing import Any, cast


CATEGORY_IDS: tuple[str, ...] = ("offense", "defense", "mobility", "aura")
HERO_IDS: frozenset[str] = frozenset(
    {"garran", "brakka", "mira", "dagna", "lorian", "nimra", "erynd"}
)
CATALOG_PATH = Path(__file__).resolve().parents[3] / "content/print/rune_baskets_v01/catalog.json"
_BUDGETS = frozenset({"S", "R", "A+S", "M+S", "M+A+S"})
_TARGETS = frozenset({"enemy", "ally", "self", "area", "position"})


def _mapping(value: object, where: str) -> dict[str, Any]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ValueError(f"{where}: expected an object with string keys")
    return cast(dict[str, Any], value)


def _list(value: object, where: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{where}: expected a list")
    return value


def _text(value: object, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{where}: expected nonempty text")
    return value


def _integer(value: object, where: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{where}: expected integer >= {minimum}")
    return value


def _choice(value: object, choices: Collection[str], where: str) -> str:
    text = _text(value, where)
    if text not in choices:
        raise ValueError(f"{where}: unknown value {text!r}")
    return text


def _boolean(value: object, where: str) -> None:
    if type(value) is not bool:
        raise ValueError(f"{where}: expected a boolean")


def _validate_categories(data: dict[str, Any]) -> dict[str, str]:
    rows = _list(data.get("categories"), "categories")
    if len(rows) != len(CATEGORY_IDS):
        raise ValueError("categories: exactly four categories are required")
    rune_categories: dict[str, str] = {}
    for row, expected in zip(rows, CATEGORY_IDS, strict=True):
        category = _mapping(row, "category")
        if category.get("id") != expected:
            raise ValueError(f"categories: expected {expected!r} in canonical order")
        _text(category.get("name"), f"{expected}.name")
        symbols = _list(category.get("runes"), f"{expected}.runes")
        if len(symbols) != 4:
            raise ValueError(f"{expected}: exactly four ordered k4 symbols are required")
        for symbol in symbols:
            symbol = _text(symbol, f"{expected}.runes")
            if symbol == "*" or symbol in rune_categories:
                raise ValueError("categories: rune symbols must be concrete and unique")
            rune_categories[symbol] = expected
    return rune_categories


def _validate_rules(data: dict[str, Any]) -> None:
    rules = _mapping(data.get("rules"), "rules")
    # These are the v0.1 rules, not configurable limits silently overriding it.
    exact: dict[str, object] = {
        "base_cost": 1, "base_owner": "self", "max_resonances": 1,
        "max_resonance_options": 3, "resonance_other_category": True,
        "support_distance": 3, "support_reaction": True, "support_base_cost": False,
        "focus_count": 2, "focus_budget": "S", "focus_variant": "A", "recharge_die": 4,
        "duplicate_prepared_symbols": True,
    }
    for key, expected in exact.items():
        actual = rules.get(key)
        if type(actual) is not type(expected) or actual != expected:
            raise ValueError(f"rules.{key}: v0.1 requires {expected!r}")
    _choice(rules.get("reaction_reset"), {"round"}, "rules.reaction_reset")
    _choice(rules.get("distance_metric"), {"chebyshev"}, "rules.distance_metric")
    _boolean(rules.get("full_basket_consumes_regeneration"), "rules.full_basket_consumes_regeneration")


def _validate_card(card: dict[str, Any], where: str, rune_categories: dict[str, str]) -> None:
    _text(card.get("id"), f"{where}.id")
    _text(card.get("name"), f"{where}.name")
    _text(card.get("description"), f"{where}.description")
    category = _choice(card.get("category"), CATEGORY_IDS, f"{where}.category")
    _choice(card.get("button"), rune_categories, f"{where}.button")
    if rune_categories[card["button"]] != category:
        raise ValueError(f"{where}: base category must match the power button")
    slot = _integer(card.get("slot"), f"{where}.slot", minimum=5)
    if slot >= 24 or slot in {19, 21}:
        raise ValueError(f"{where}.slot: cannot occupy a reserved control button")
    _choice(card.get("budget"), _BUDGETS, f"{where}.budget")
    target = _choice(card.get("target"), _TARGETS, f"{where}.target")
    distance = _integer(card.get("range"), f"{where}.range")
    if target == "self" and distance:
        raise ValueError(f"{where}.range: a self power must have range zero")
    for flag in ("once", "allow_self"):
        if flag in card:
            _boolean(card[flag], f"{where}.{flag}")
    if {"rune", "boosts", "free_first"} & card.keys():
        raise ValueError(f"{where}: obsolete rune/boost/free-first fields are forbidden")
    if "effect" in card:
        effect = _mapping(card["effect"], f"{where}.effect")
        _text(effect.get("type"), f"{where}.effect.type")
    resonances = _list(card.get("resonances"), f"{where}.resonances")
    if len(resonances) > 3:
        raise ValueError(f"{where}: at most three resonance choices are allowed")
    ids: set[str] = set()
    symbols: set[str] = set()
    for raw in resonances:
        resonance = _mapping(raw, f"{where}.resonance")
        rid = _text(resonance.get("id"), f"{where}.resonance.id")
        rune = _choice(resonance.get("rune"), rune_categories, f"{where}.resonance.rune")
        if rid in ids or rune in symbols:
            raise ValueError(f"{where}: resonance ids and buttons must be unique")
        if rune_categories[rune] == category:
            raise ValueError(f"{where}: a resonance must use another category")
        ids.add(rid)
        symbols.add(rune)
        _text(resonance.get("description"), f"{where}.resonance.description")
        if "budget" in resonance:
            _choice(resonance["budget"], _BUDGETS, f"{where}.resonance.budget")
        if "effect" in resonance:
            _mapping(resonance["effect"], f"{where}.resonance.effect")


def _validate_hero(hero: dict[str, Any], hero_id: str, rune_categories: dict[str, str]) -> None:
    capacities = _mapping(hero.get("capacities"), f"{hero_id}.capacities")
    preparation = _mapping(hero.get("preparation"), f"{hero_id}.preparation")
    if set(capacities) != set(CATEGORY_IDS) or set(preparation) != set(CATEGORY_IDS):
        raise ValueError(f"{hero_id}: capacities and preparation need all four categories")
    for category in CATEGORY_IDS:
        capacity = _integer(capacities[category], f"{hero_id}.{category}.capacity")
        symbols = _list(preparation[category], f"{hero_id}.{category}.preparation")
        if len(symbols) != capacity:
            raise ValueError(f"{hero_id}.{category}: preparation must fill the exact capacity")
        for symbol in symbols:
            symbol = _choice(symbol, rune_categories, f"{hero_id}.{category}.preparation")
            if rune_categories[symbol] != category:
                raise ValueError(f"{hero_id}.{category}: prepared symbol has the wrong category")
    regeneration = _list(hero.get("regeneration"), f"{hero_id}.regeneration")
    events: set[str] = set()
    ids: set[str] = set()
    if not regeneration:
        raise ValueError(f"{hero_id}: at least one regeneration rule is required")
    for raw in regeneration:
        rule = _mapping(raw, f"{hero_id}.regeneration")
        rid = _text(rule.get("id"), f"{hero_id}.regeneration.id")
        event = _text(rule.get("event"), f"{hero_id}.regeneration.event")
        if rid in ids or event in events:
            raise ValueError(f"{hero_id}: regeneration ids/events must be unique")
        ids.add(rid)
        events.add(event)
        _choice(rule.get("category"), CATEGORY_IDS, f"{hero_id}.regeneration.category")
        _choice(rule.get("limit"), {"round"}, f"{hero_id}.regeneration.limit")
        _integer(rule.get("count"), f"{hero_id}.regeneration.count", minimum=1)
        _text(rule.get("label"), f"{hero_id}.regeneration.label")
    provisional = _mapping(hero.get("provisional"), f"{hero_id}.provisional")
    for key in ("capacities", "regeneration"):
        _boolean(provisional.get(key), f"{hero_id}.provisional.{key}")
    _text(provisional.get("note"), f"{hero_id}.provisional.note")
    flaw = _mapping(hero.get("flaw"), f"{hero_id}.flaw")
    _text(flaw.get("name"), f"{hero_id}.flaw.name")
    _text(flaw.get("description"), f"{hero_id}.flaw.description")
    if "surcharge" in flaw:
        surcharge = _mapping(flaw["surcharge"], f"{hero_id}.flaw.surcharge")
        _text(surcharge.get("condition"), f"{hero_id}.flaw.surcharge.condition")
        _choice(surcharge.get("owner"), {"self"}, f"{hero_id}.flaw.surcharge.owner")
        _choice(surcharge.get("category"), {"any"}, f"{hero_id}.flaw.surcharge.category")
        _integer(surcharge.get("max"), f"{hero_id}.flaw.surcharge.max", minimum=1)
    cards = _list(hero.get("cards"), f"{hero_id}.cards")
    if not 1 <= len(cards) <= 12:
        raise ValueError(f"{hero_id}: expected between one and twelve power cards")
    card_ids: set[str] = set()
    slots: set[int] = set()
    for index, raw in enumerate(cards):
        card = _mapping(raw, f"{hero_id}.cards[{index}]")
        _validate_card(card, f"{hero_id}.cards[{index}]", rune_categories)
        if card["id"] in card_ids or card["slot"] in slots:
            raise ValueError(f"{hero_id}: card ids and board slots must be unique")
        card_ids.add(card["id"])
        slots.add(card["slot"])


def validate_rune_basket_catalog(value: object) -> dict[str, Any]:
    """Validate a complete v0.1 payload or raise an explanatory ValueError."""
    data = _mapping(value, "catalog")
    if type(data.get("version")) is not int or data["version"] != 1:
        raise ValueError("catalog.version: expected version 1")
    rune_categories = _validate_categories(data)
    _validate_rules(data)
    heroes = _mapping(data.get("heroes"), "heroes")
    if set(heroes) != HERO_IDS:
        raise ValueError("heroes: expected the seven prototype heroes")
    for hero_id, raw in heroes.items():
        _validate_hero(_mapping(raw, hero_id), hero_id, rune_categories)
    return data


def load_rune_basket_catalog(path: Path | None = None) -> dict[str, Any]:
    """Read the current basket source; legacy rune saves use their own catalogue."""
    source = path if path is not None else CATALOG_PATH
    return validate_rune_basket_catalog(json.loads(source.read_text(encoding="utf-8")))


def basket_cards(hero_id: str) -> tuple:
    """Same immutable definitions for live powers, preview, and printed cards."""
    return _basket_cards(hero_id, CATALOG_PATH.stat().st_mtime_ns)


@lru_cache(maxsize=28)
def _basket_cards(hero_id: str, modified: int) -> tuple:
    from .rune_catalog import RuneCard
    from dnd_board_game.rules.shared_mana_catalog import Boost
    hero = load_rune_basket_catalog()['heroes'].get(hero_id)
    if not hero:
        return ()
    return tuple(RuneCard(hero_id, row['id'], row['button'], row['slot'], row['budget'], row['name'],
        row['description'], tuple(Boost(b['id'], b['rune'], 1, b['description']) for b in row['resonances']),
        bool(row.get('once')), False,
        tuple((b['id'], b['budget']) for b in row['resonances'] if 'budget' in b), row['category'])
        for row in hero['cards'])
