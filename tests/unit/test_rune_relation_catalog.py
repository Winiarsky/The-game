"""The accepted cards, graph and executable effect vocabulary share one source."""
from copy import deepcopy
from pathlib import Path
import importlib.util

import pytest

from dnd_board_game.scenarios.rune_relation_catalog import load_rune_relation_catalog, load_rune_relation_player_aid, validate_catalog


def test_accepted_edition_contains_all_powers_and_reachable_conditions() -> None:
    catalog = load_rune_relation_catalog()
    cards = [card for hero in catalog["heroes"].values() for card in hero["cards"]]
    assert len(cards) == 29
    assert sum(len(card["resonance_bonuses"]) for card in cards) == 51
    assert sum(bool(card.get("ends_resonance")) for card in cards) == 4
    assert [(hero_id, card["id"]) for hero_id, hero in catalog["heroes"].items()
            for card in hero["cards"] if card["rune"] == "Fala"] == [("nimra", "misty_step")]
    assert next(card for card in catalog["heroes"]["erynd"]["cards"] if card["id"] == "skirmish_shot")["rune"] == "Schody"


@pytest.mark.parametrize("change", ["copied_wave", "reserved_power", "wave_other_hero", "duplicate_condition",
    "legacy_price", "boolean_cost", "unknown_modifier", "malformed_die", "finisher_without_end", "unknown_condition"])
def test_invalid_content_fails_before_play(change: str) -> None:
    data = deepcopy(load_rune_relation_catalog())
    card = data["heroes"]["garran"]["cards"][0]
    if change == "copied_wave":
        data["rules"]["rune_relations"]["Fala"] = ["Wieża"]
    elif change == "reserved_power":
        card["rune"] = "Korona"
    elif change == "wave_other_hero":
        card["rune"] = "Fala"
    elif change == "duplicate_condition":
        card["resonance_bonuses"][0]["requires"] = ["Oko", "Oko"]
    elif change == "legacy_price":
        card["enhanced_cost"] = 8
    elif change == "boolean_cost":
        card["cost"] = True
    elif change == "unknown_modifier":
        card["resonance_bonuses"][0]["modifiers"] = {"global_ac": 1}
    elif change == "malformed_die":
        card["resonance_bonuses"][0]["modifiers"] = {"attack_bonus_dice": [{"count": True, "sides": 6, "damage_type": "weapon"}]}
    elif change == "finisher_without_end":
        finisher = next(c for c in data["heroes"]["brakka"]["cards"] if c.get("ends_resonance"))
        finisher["ends_resonance"] = False
    else:
        card["resonance_bonuses"][0]["requires"] = ["Gwiazda"]
    with pytest.raises(ValueError):
        validate_catalog(data)


def test_print_generator_accepts_runtime_catalog_without_changing_card_prices() -> None:
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location("relation_generator", root / "scripts/build_rune_relations.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = module.load_catalog()
    sheet = module.render_hero("mira", data)
    assert "Podst." not in sheet and "Wzm." not in sheet
    assert "Wymaga" in sheet and "Wyładowanie" in sheet
    assert "7 ładunków" in sheet
    assert "Po całej mocy dopisz ją" in sheet


def test_shared_aid_derives_graph_from_catalog_and_keeps_reputation_rules() -> None:
    import json
    catalog = load_rune_relation_catalog()
    catalog['rules']['rune_relations']['Wieża'] = ['Oko', 'Grot', 'Hak', 'Fala']
    aid = load_rune_relation_player_aid(catalog=catalog)
    relation_section = next(s for page in aid for s in page['sections'] if 'table' in s and s['title'] == 'Kierunkowe połączenia')
    assert relation_section['table'][1] == ['Wieża', 'Oko, Grot, Hak, Fala']
    assert 'relation_table' not in relation_section
    root = Path(__file__).resolve().parents[2]
    old = json.loads((root / 'content/scenarios/misja_0_dzwon/text/sciaga_runy.json').read_text())
    assert aid[2]['sections'] == next(p for p in old['pages'] if p['id'] == 'reputacja')['sections']
