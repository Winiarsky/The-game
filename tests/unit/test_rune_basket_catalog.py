"""Content invariants for the paper/browser personal-rune prototype."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from dnd_board_game.scenarios.rune_basket_catalog import (
    CATEGORY_IDS,
    load_rune_basket_catalog,
    validate_rune_basket_catalog,
)
from dnd_board_game.ui.board_panel_symbols import SYMBOLS


ROOT = Path(__file__).resolve().parents[2]


def _card(data: dict[str, Any], hero: str, card_id: str) -> dict[str, Any]:
    return next(card for card in data["heroes"][hero]["cards"] if card["id"] == card_id)


def test_prepared_profiles_and_k4_order_match_the_system_document() -> None:
    data = load_rune_basket_catalog()
    assert {row["id"]: row["runes"] for row in data["categories"]} == {
        "offense": ["Grot", "Hak", "Trójząb", "Błysk"],
        "defense": ["Wieża", "Kotwica", "Brama", "Węzeł"],
        "mobility": ["Oko", "Schody", "Rozwidlenie", "Klepsydra"],
        "aura": ["Korona", "Kielich", "Klucz", "Romb"],
    }
    for hero_id, profile in {
        "mira": (3, 1, 4, 1), "garran": (2, 4, 1, 2),
        "brakka": (4, 1, 3, 1), "lorian": (1, 2, 2, 4),
    }.items():
        hero = data["heroes"][hero_id]
        assert tuple(hero["capacities"][category] for category in CATEGORY_IDS) == profile
        assert hero["provisional"]["capacities"] is False
    for hero_id in ("dagna", "nimra", "erynd"):
        assert data["heroes"][hero_id]["provisional"]["capacities"] is True
    assert data["heroes"]["nimra"]["provisional"]["regeneration"] is True


def test_all_65_power_ids_and_fixed_board_buttons_survive_the_adaptation() -> None:
    old = json.loads((ROOT / "content/print/runes_v01/action_cards.json").read_text())
    data = load_rune_basket_catalog()
    assert sum(len(hero["cards"]) for hero in data["heroes"].values()) == 65
    for hero_id, hero in data["heroes"].items():
        assert [(card["id"], card["slot"], card["button"]) for card in hero["cards"]] == [
            (card["id"], card["slot"], card["rune"]) for card in old[hero_id]
        ]
        for card in hero["cards"]:
            assert SYMBOLS[card["slot"]][0] == card["button"]
            assert card["slot"] not in {19, 21, 24}
            assert "free_first" not in card
    assert data["rules"]["control_slots"] == {"focus": 19, "support": 21, "information": 25}


def test_buttons_define_cost_and_resonances_use_other_categories() -> None:
    from dnd_board_game.rules.rune_baskets import category_of
    data = load_rune_basket_catalog()
    for hero in data['heroes'].values():
        for card in hero['cards']:
            assert category_of(card['button']) == card['category']
            assert card['resonances']
            assert all(category_of(b['rune']) != card['category'] for b in card['resonances'])
    bash = _card(data, 'garran', 'shield_bash')
    assert bash['category'] == 'defense'
    assert {r['id']:r['rune'] for r in bash['resonances']} == {'push':'Oko','damage':'Grot'}


def test_lorian_has_renewable_personal_resources_and_explicit_budget_overrides() -> None:
    data = load_rune_basket_catalog()
    tune = _card(data, "lorian", "mana_tuning")
    recovery = _card(data, "lorian", "mana_recovery")
    scope = _card(data, "lorian", "optical_scope")
    assert tune["effect"] == {"type": "tune", "sameCategory": True, "excludePayment": True}
    assert recovery["effect"] == {"type": "recharge", "count": 2, "excludePayment": True}
    assert recovery["once"] is True
    assert recovery["resonances"][0]["rune"] == "Wieża"
    assert (scope["budget"], scope["resonances"][0]["budget"]) == ("M+S", "M+A+S")
    for card in (tune, recovery):
        assert "talii" not in card["description"]
        assert "odrzuconych" not in card["description"]


def test_regeneration_is_a_once_per_round_event_with_separate_mira_limits() -> None:
    data = load_rune_basket_catalog()
    assert {(row["event"], row["category"]) for row in data["heroes"]["mira"]["regeneration"]} == {
        ("flank_entry", "mobility"), ("hidden_hit", "offense"),
    }
    for hero in data["heroes"].values():
        assert all(row["limit"] == "round" and row["count"] == 1 for row in hero["regeneration"])
    assert data["rules"]["full_basket_consumes_regeneration"] is True
    assert data["rules"]["reaction_reset"] == "round"
    assert data["rules"]["support_distance"] == 3


def test_duplicate_starting_symbols_are_allowed_within_the_category_capacity() -> None:
    data = load_rune_basket_catalog()
    data["heroes"]["mira"]["preparation"]["mobility"] = ["Oko"] * 4
    validate_rune_basket_catalog(data)


@pytest.mark.parametrize(("path", "replacement"), [
    (("version",), True),
    (("categories", 0, "runes"), ["Grot", "Grot", "Hak", "Błysk"]),
    (("categories", 0, "runes"), ["Grot", "Hak", "Błysk"]),
    (("categories", 0, "runes", 0), "*"),
    (("heroes", "garran", "capacities", "offense"), True),
    (("heroes", "garran", "preparation", "offense"), ["Grot"]),
    (("heroes", "garran", "preparation", "offense", 0), "Oko"),
    (("heroes", "garran", "regeneration", 0, "limit"), "unlimited"),
    (("heroes", "garran", "cards", 0, "slot"), 19),
    (("heroes", "garran", "cards", 0, "slot"), 21),
    (("heroes", "garran", "cards", 0, "slot"), 24),
    (("heroes", "garran", "cards", 0, "category"), "unknown"),
    (("heroes", "garran", "cards", 0, "resonances", 0, "rune"), "Grot"),
    (("heroes", "garran", "cards", 0, "resonances", 0, "rune"), "*"),
    (("heroes", "garran", "cards", 0, "budget"), "FREE"),
    (("heroes", "garran", "cards", 0, "range"), -1),
    (("heroes", "garran", "cards", 0, "free_first"), True),
    (("rules", "max_resonances"), 2),
    (("rules", "base_owner"), "ally"),
    (("rules", "support_reaction"), False),
])
def test_invalid_resource_contract_is_rejected(path: tuple[str | int, ...], replacement: object) -> None:
    data = load_rune_basket_catalog()
    parent: Any = data
    for key in path[:-1]:
        parent = parent[key]
    parent[path[-1]] = replacement
    with pytest.raises(ValueError):
        validate_rune_basket_catalog(data)


def test_duplicate_slots_and_unlimited_resonance_menus_are_rejected() -> None:
    data = load_rune_basket_catalog()
    cards = data["heroes"]["garran"]["cards"]
    cards[1]["slot"] = cards[0]["slot"]
    with pytest.raises(ValueError, match="slots must be unique"):
        validate_rune_basket_catalog(data)
    data = load_rune_basket_catalog()
    resonances = data["heroes"]["garran"]["cards"][0]["resonances"]
    resonances.extend([{"id": "extra", "rune": "Brama", "description": "Fourth choice"}] * 2)
    with pytest.raises(ValueError, match="three resonance"):
        validate_rune_basket_catalog(data)


def test_reading_the_catalog_cannot_share_mutable_state_with_another_session() -> None:
    first = load_rune_basket_catalog()
    first["heroes"]["garran"]["preparation"]["mobility"].clear()
    assert load_rune_basket_catalog()["heroes"]["garran"]["preparation"]["mobility"] == ["Oko"]
