from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from character_creation.pipeline import (
    _build_filter_options,
    _build_full_shop_offers,
    _filter_offers_for_section,
    _section_filter_state_defaults,
)


def test_full_shop_offers_include_all_core_sections():
    offers = _build_full_shop_offers()
    sections = {str(row.get("section") or "") for row in offers}

    assert "weapons" in sections
    assert "armors" in sections
    assert "shields" in sections
    assert "ammunition" in sections
    assert "alchemy" in sections
    assert "gear" in sections
    assert "magic" in sections

    ids = {str(row.get("id") or "") for row in offers}
    assert "tower_shield" in ids
    assert "full_plate" in ids
    assert "greatsword" in ids
    assert "longbow" in ids
    assert "holy_water" in ids
    assert "alchemists_fire" in ids


def test_weapon_filters_apply_to_offer_list():
    offers = _build_full_shop_offers()
    filters = {
        "weapon_type": "ranged",
        "proficiency": "martial",
        "hands": "2",
        "rarity": "all",
    }
    filtered = _filter_offers_for_section(offers, "weapons", filters)

    assert filtered
    for row in filtered:
        assert str(row.get("section") or "") == "weapons"
        assert str(row.get("weapon_type") or "") == "ranged"
        assert str(row.get("proficiency") or "") == "martial"
        assert str(row.get("hands") or "") == "2"


def test_filter_options_exist_for_each_shop_section():
    for section_id in ("weapons", "armors", "shields", "ammunition", "alchemy", "gear", "magic"):
        options = _build_filter_options(section_id, _section_filter_state_defaults(section_id))
        assert options
        assert all(str(row.get("id") or "").startswith("__filter:") for row in options)


def test_weapon_trait_filter_applies_to_offer_list():
    offers = _build_full_shop_offers()
    filters = {
        "weapon_type": "all",
        "proficiency": "all",
        "hands": "all",
        "rarity": "all",
        "trait": "agile",
    }
    filtered = _filter_offers_for_section(offers, "weapons", filters)

    assert filtered
    for row in filtered:
        traits = {str(item or "").strip().lower() for item in list(row.get("traits") or ())}
        assert "agile" in traits


def test_weapon_filter_options_include_trait_filter():
    options = _build_filter_options("weapons", _section_filter_state_defaults("weapons"))
    labels = [str(row.get("label") or "") for row in options]
    assert any(label.startswith("Filtr Trait:") for label in labels)


def test_weapon_damage_die_filter_applies_to_offer_list():
    offers = _build_full_shop_offers()
    filters = {
        "weapon_type": "all",
        "proficiency": "all",
        "hands": "all",
        "rarity": "all",
        "trait": "all",
        "damage_die": "k8",
    }
    filtered = _filter_offers_for_section(offers, "weapons", filters)

    assert filtered
    for row in filtered:
        assert str(row.get("damage_die") or "") == "k8"


def test_weapon_filter_options_include_damage_die_filter():
    options = _build_filter_options("weapons", _section_filter_state_defaults("weapons"))
    labels = [str(row.get("label") or "") for row in options]
    assert any(label.startswith("Filtr Kosc obrazen:") for label in labels)
