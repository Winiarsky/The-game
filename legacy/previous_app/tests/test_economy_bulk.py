from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.items.base_item import BaseItem  # noqa: E402
from GameObjects.items.armor import create_armor  # noqa: E402
from GameObjects.items.equipment import create_equipment  # noqa: E402
from GameObjects.items.inventory import get_equipped_weapons  # noqa: E402
from GameObjects.items.shield import create_shield  # noqa: E402
from GameObjects.items.weapon import create_weapon  # noqa: E402
from character_creation.pipeline import hero_from_snapshot  # noqa: E402
from economy import (  # noqa: E402
    ENCUMBERED_SOURCE,
    actor_bulk_summary,
    actor_total_cp,
    ensure_actor_coin_pouch,
    format_actor_money,
    refresh_actor_bulk_state,
    item_cost_cp,
    set_actor_starting_money_gp,
    set_actor_total_cp,
    spend_actor_cp,
)
from hero import Hero  # noqa: E402


def test_money_start_and_spend_flow():
    hero = Hero()
    set_actor_starting_money_gp(hero, 15)
    assert actor_total_cp(hero) == 1500
    assert spend_actor_cp(hero, 350)
    assert actor_total_cp(hero) == 1150
    assert format_actor_money(hero) == "1 pp, 1 gp, 5 sp"


def test_wallet_zero_is_not_refilled_from_starting_gold():
    hero = Hero()
    set_actor_starting_money_gp(hero, 15)
    assert spend_actor_cp(hero, 1500)
    assert actor_total_cp(hero) == 0
    ensure_actor_coin_pouch(hero, default_gp=15)
    assert actor_total_cp(hero) == 0
    assert format_actor_money(hero) == "0 cp"


def test_bulk_refresh_adds_and_clears_encumbered_status():
    hero = Hero()
    hero.ability_modifiers = {"strength": 0}
    hero.inventory = [BaseItem(item_id="test_crate", name="Crate", category="misc", description="")]
    setattr(hero.inventory[0], "bulk", 6)

    first = refresh_actor_bulk_state(hero, inventory=hero.inventory)
    assert first["encumbered"] is True
    assert hero.has_status("encumbered")
    assert any(str(getattr(status, "source", "") or "") == ENCUMBERED_SOURCE for status in hero.statuses)

    hero.inventory = []
    second = refresh_actor_bulk_state(hero, inventory=hero.inventory)
    assert second["encumbered"] is False
    assert not any(str(getattr(status, "source", "") or "") == ENCUMBERED_SOURCE for status in hero.statuses)


def test_coin_bulk_counts_per_thousand_coins():
    hero = Hero()
    hero.ability_modifiers = {"strength": 5}
    hero.coin_pouch = {"cp": 1200, "sp": 0, "gp": 0, "pp": 0}
    hero.inventory = []

    summary = actor_bulk_summary(hero, inventory=hero.inventory)
    assert summary["total_units"] == 10
    assert summary["encumbered"] is False


def test_hero_from_snapshot_restores_wallet_and_loadouts():
    snapshot = {
        "character_id": "hero_money",
        "name": "Money Hero",
        "class_id": "ranger",
        "level": 1,
        "coin_pouch": {"cp": 3, "sp": 2, "gp": 4, "pp": 0},
        "weapon_loadout": ["longbow"],
        "armor_loadout": ["leather_armor"],
        "shield_loadout": ["buckler"],
        "equipped_weapon_ids": ["longbow"],
        "equipped_armor_id": "leather_armor",
        "equipped_shield_id": "buckler",
        "ability_modifiers": {
            "strength": 1,
            "dexterity": 3,
            "constitution": 1,
            "intelligence": 0,
            "wisdom": 1,
            "charisma": 0,
        },
    }
    hero = hero_from_snapshot(snapshot)
    assert actor_total_cp(hero) == 423
    assert "longbow" in list(getattr(hero, "weapon_loadout", []) or [])
    assert "leather_armor" in list(getattr(hero, "armor_loadout", []) or [])
    assert "buckler" in list(getattr(hero, "shield_loadout", []) or [])
    inventory_ids = {str(getattr(item, "item_id", "") or "").strip().lower() for item in list(getattr(hero, "inventory", []) or [])}
    assert "longbow" in inventory_ids
    assert "leather_armor" in inventory_ids
    assert "buckler" in inventory_ids
    equipped_ids = {str(getattr(item, "item_id", "") or "").strip().lower() for item in get_equipped_weapons(hero)}
    assert "longbow" in equipped_ids


def test_hero_from_snapshot_preserves_zero_wallet():
    snapshot = {
        "character_id": "hero_zero_money",
        "name": "Zero Money",
        "class_id": "champion",
        "level": 1,
        "starting_gold_gp": 15,
        "coin_pouch": {"cp": 0, "sp": 0, "gp": 0, "pp": 0},
        "ability_modifiers": {
            "strength": 1,
            "dexterity": 1,
            "constitution": 1,
            "intelligence": 0,
            "wisdom": 0,
            "charisma": 1,
        },
    }
    hero = hero_from_snapshot(snapshot)
    assert actor_total_cp(hero) == 0
    assert format_actor_money(hero) == "0 cp"


def test_set_actor_total_cp_normalizes_wallet():
    hero = Hero()
    set_actor_total_cp(hero, 1999)
    assert hero.coin_pouch == {"cp": 9, "sp": 9, "gp": 9, "pp": 1}


def test_equipment_prices_and_bulk_match_pf2_defaults_for_supported_items():
    longsword = create_weapon("longsword")
    dagger = create_weapon("dagger")
    longbow = create_weapon("longbow")
    full_plate = create_armor("full_plate")
    chain_shirt = create_armor("chain_shirt")
    half_plate = create_armor("half_plate")
    buckler = create_shield("buckler")
    wooden_shield = create_shield("wooden_shield")
    assert longsword is not None and dagger is not None and longbow is not None
    assert full_plate is not None and buckler is not None
    assert chain_shirt is not None and half_plate is not None
    assert wooden_shield is not None

    assert getattr(longsword, "price_cp", 0) == 100
    assert getattr(longsword, "bulk", None) == 1
    assert getattr(dagger, "price_cp", 0) == 20
    assert str(getattr(dagger, "bulk", "")).lower() == "l"
    assert getattr(longbow, "price_cp", 0) == 600
    assert getattr(chain_shirt, "price_cp", 0) == 500
    assert getattr(chain_shirt, "bulk", None) == 1
    assert getattr(half_plate, "price_cp", 0) == 1800
    assert getattr(half_plate, "bulk", None) == 3
    assert getattr(full_plate, "price_cp", 0) == 3000
    assert getattr(full_plate, "bulk", None) == 4
    assert getattr(buckler, "price_cp", 0) == 100
    assert str(getattr(buckler, "bulk", "")).lower() == "l"
    assert getattr(wooden_shield, "price_cp", 0) == 100
    assert getattr(wooden_shield, "bulk", None) == 1


def test_basic_equipment_factory_and_costs_match_cp_and_bulk():
    healer_tools = create_equipment("healer_tools")
    arrows = create_equipment("arrows")
    rope = create_equipment("rope_hemp_50ft")
    assert healer_tools is not None and arrows is not None and rope is not None

    assert getattr(healer_tools, "price_cp", 0) == 500
    assert getattr(healer_tools, "bulk", None) == 1
    assert getattr(arrows, "price_cp", 0) == 10
    assert str(getattr(arrows, "bulk", "")).lower() == "l"
    assert getattr(rope, "price_cp", 0) == 10
    assert getattr(rope, "bulk", None) == 1
    assert item_cost_cp("healer_tools") == 500
    assert item_cost_cp("lantern_bullseye") == 1000
