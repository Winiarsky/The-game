from __future__ import annotations

from typing import Any, Iterable

from statuses import EncumberedStatus


COIN_CP_VALUES: dict[str, int] = {
    "cp": 1,
    "sp": 10,
    "gp": 100,
    "pp": 1000,
}

COIN_ORDER: tuple[str, ...] = ("pp", "gp", "sp", "cp")
ENCUMBERED_SOURCE = "bulk:encumbered"


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _ability_mod(actor: Any, ability_id: str) -> int:
    key = str(ability_id or "").strip().lower()
    if not key:
        return 0
    short = {
        "strength": "str_mod",
        "dexterity": "dex_mod",
        "constitution": "con_mod",
        "intelligence": "int_mod",
        "wisdom": "wis_mod",
        "charisma": "cha_mod",
    }.get(key)
    if short:
        raw = getattr(actor, short, None)
        if raw is not None:
            return _safe_int(raw, 0)
    mods = getattr(actor, "ability_modifiers", None)
    if isinstance(mods, dict):
        return _safe_int(mods.get(key), 0)
    return 0


def normalize_coin_pouch(raw: Any) -> dict[str, int]:
    if not isinstance(raw, dict):
        return {"cp": 0, "sp": 0, "gp": 0, "pp": 0}
    out = {"cp": 0, "sp": 0, "gp": 0, "pp": 0}
    for coin in out:
        out[coin] = max(0, _safe_int(raw.get(coin), 0))
    return out


def coin_pouch_total_cp(pouch: dict[str, int] | None) -> int:
    normalized = normalize_coin_pouch(pouch)
    total = 0
    for coin, cp_value in COIN_CP_VALUES.items():
        total += _safe_int(normalized.get(coin), 0) * int(cp_value)
    return max(0, int(total))


def coin_pouch_from_cp(total_cp: int) -> dict[str, int]:
    remaining = max(0, _safe_int(total_cp, 0))
    out = {"cp": 0, "sp": 0, "gp": 0, "pp": 0}
    for coin in COIN_ORDER:
        step = int(COIN_CP_VALUES.get(coin, 1))
        if step <= 0:
            continue
        qty = remaining // step
        out[coin] = int(qty)
        remaining -= qty * step
    return out


def ensure_actor_coin_pouch(actor: Any, *, default_gp: int = 0) -> dict[str, int]:
    raw = getattr(actor, "coin_pouch", None)
    current = normalize_coin_pouch(raw)
    # Seed only when wallet is missing/unset, not when it is intentionally zero.
    if raw is None:
        starting_gp = _safe_int(getattr(actor, "starting_gold_gp", default_gp), default_gp)
        if starting_gp > 0:
            current["gp"] = int(starting_gp)
    try:
        setattr(actor, "coin_pouch", dict(current))
    except Exception:
        pass
    return current


def actor_total_cp(actor: Any) -> int:
    pouch = ensure_actor_coin_pouch(actor, default_gp=0)
    return coin_pouch_total_cp(pouch)


def set_actor_total_cp(actor: Any, total_cp: int) -> dict[str, int]:
    pouch = coin_pouch_from_cp(total_cp)
    try:
        setattr(actor, "coin_pouch", dict(pouch))
    except Exception:
        pass
    refresh_actor_bulk_state(actor)
    return pouch


def set_actor_starting_money_gp(actor: Any, gp: int = 15) -> dict[str, int]:
    amount_gp = max(0, _safe_int(gp, 15))
    try:
        setattr(actor, "starting_gold_gp", int(amount_gp))
    except Exception:
        pass
    return set_actor_total_cp(actor, amount_gp * COIN_CP_VALUES["gp"])


def can_actor_afford_cp(actor: Any, cost_cp: int) -> bool:
    return actor_total_cp(actor) >= max(0, _safe_int(cost_cp, 0))


def spend_actor_cp(actor: Any, cost_cp: int) -> bool:
    cost = max(0, _safe_int(cost_cp, 0))
    current = actor_total_cp(actor)
    if cost > current:
        return False
    set_actor_total_cp(actor, current - cost)
    return True


def add_actor_cp(actor: Any, delta_cp: int) -> None:
    delta = _safe_int(delta_cp, 0)
    current = actor_total_cp(actor)
    set_actor_total_cp(actor, max(0, current + delta))


def format_cp_value(cost_cp: int) -> str:
    pouch = coin_pouch_from_cp(max(0, _safe_int(cost_cp, 0)))
    parts: list[str] = []
    for coin in COIN_ORDER:
        qty = _safe_int(pouch.get(coin), 0)
        if qty > 0:
            parts.append(f"{qty} {coin}")
    return ", ".join(parts) if parts else "0 cp"


def format_actor_money(actor: Any) -> str:
    pouch = ensure_actor_coin_pouch(actor, default_gp=0)
    parts: list[str] = []
    for coin in ("pp", "gp", "sp", "cp"):
        qty = _safe_int(pouch.get(coin), 0)
        if qty > 0:
            parts.append(f"{qty} {coin}")
    return ", ".join(parts) if parts else "0 cp"


def total_coin_count(actor: Any) -> int:
    pouch = ensure_actor_coin_pouch(actor, default_gp=0)
    return sum(max(0, _safe_int(pouch.get(coin), 0)) for coin in COIN_CP_VALUES.keys())


def _item_id(item: Any) -> str:
    return str(getattr(item, "item_id", "") or "").strip().lower()


def parse_bulk_units(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, str):
        raw = value.strip().lower()
        if raw in {"", "-", "—", "none"}:
            return 0
        if raw == "l":
            return 1
        try:
            return max(0, int(float(raw) * 10))
        except Exception:
            return 0
    if isinstance(value, (int, float)):
        return max(0, int(float(value) * 10))
    return 0


def _default_item_bulk_units(item_id: str) -> int:
    bulk_map: dict[str, object] = {
        "unarmed": "-",
        "razortooth_jaws": "-",
        "dagger": "L",
        "shortsword": "L",
        "rapier": 1,
        "javelin": "L",
        "sword": 1,
        "longsword": 1,
        "club": 1,
        "spear": 1,
        "mace": 1,
        "warhammer": 1,
        "longbow": 1,
        "shortbow": 1,
        "crossbow": 1,
        "light_crossbow": 1,
        "greataxe": 2,
        "glaive": 2,
        "halberd": 2,
        "padded_armor": "L",
        "leather_armor": 1,
        "studded_leather": 1,
        "chain_shirt": 1,
        "hide_armor": 2,
        "scale_mail": 2,
        "breastplate": 2,
        "chain_mail": 2,
        "splint_mail": 3,
        "half_plate": 3,
        "full_plate": 4,
        "buckler": "L",
        "wooden_shield": 1,
        "steel_shield": 1,
        "standard_shield": 1,
        "tower_shield": 4,
        "arrow": "L",
        "arrows": "L",
        "bolt": "L",
        "bolts": "L",
        "sling_bullet": "L",
        "sling_bullets": "L",
        "backpack": "L",
        "bedroll": "L",
        "belt_pouch": "L",
        "chalk": "-",
        "caltrops": "L",
        "chain_10ft": 1,
        "climbing_kit": 1,
        "crowbar": "L",
        "flint_and_steel": "-",
        "grappling_hook": "L",
        "hammer": "L",
        "healer_tools": 1,
        "mirror_steel": "-",
        "soap": "-",
        "thieves_tools": "L",
        "repair_kit": 1,
        "rope_hemp_50ft": 1,
        "rope_silk_50ft": "L",
        "rations_week": "L",
        "sack": "L",
        "shovel": 1,
        "signal_whistle": "-",
        "spike_iron_10": "L",
        "torch": "L",
        "waterskin": "L",
        "lantern_hooded": 1,
        "lantern_bullseye": 1,
        "lock_simple": "L",
        "lock_good": "L",
        "oil_flask": "L",
        "spellbook": "L",
        "formula_book": "L",
        "holy_symbol_wooden": "L",
        "holy_symbol_silver": "L",
        "writing_set": "L",
        "tent": 2,
        "holy_water": "L",
        "unholy_water": "L",
        "minor_healing_potion": "L",
        "scroll_common_rank1": "L",
        "potency_crystal": "-",
    }
    return parse_bulk_units(bulk_map.get(item_id))


def item_bulk_units(item: Any) -> int:
    explicit = parse_bulk_units(getattr(item, "bulk", None))
    if explicit > 0:
        return explicit
    if str(getattr(item, "bulk", "") or "").strip().lower() in {"-", "—"}:
        return 0
    by_alt = parse_bulk_units(getattr(item, "bulk_value", None))
    if by_alt > 0:
        return by_alt
    category = str(getattr(item, "category", "") or "").strip().lower()
    if category in {"potion", "consumable", "ammo", "ammunition"}:
        return 1
    return _default_item_bulk_units(_item_id(item))


def actor_inventory_bulk_units(actor: Any, *, inventory: Iterable[Any] | None = None, include_coins: bool = True) -> int:
    source = list(inventory) if inventory is not None else list(getattr(actor, "inventory", []) or [])
    item_units = sum(item_bulk_units(item) for item in source)
    if not include_coins:
        return max(0, int(item_units))
    coin_bulk = (max(0, int(total_coin_count(actor))) // 1000) * 10
    return max(0, int(item_units) + int(coin_bulk))


def actor_bulk_limits(actor: Any) -> tuple[int, int]:
    str_mod = _ability_mod(actor, "strength")
    enc = max(0, 5 + int(str_mod)) * 10
    cap = max(0, 10 + int(str_mod)) * 10
    return int(enc), int(cap)


def format_bulk_units(units: int) -> str:
    raw = max(0, _safe_int(units, 0))
    bulk = raw // 10
    light = raw % 10
    if light > 0:
        return f"{bulk}B {light}L"
    return f"{bulk}B"


def actor_bulk_summary(actor: Any, *, inventory: Iterable[Any] | None = None) -> dict[str, Any]:
    total_units = actor_inventory_bulk_units(actor, inventory=inventory, include_coins=True)
    enc_limit_units, max_limit_units = actor_bulk_limits(actor)
    return {
        "total_units": int(total_units),
        "total_display": format_bulk_units(total_units),
        "encumbered_limit_units": int(enc_limit_units),
        "encumbered_limit_display": format_bulk_units(enc_limit_units),
        "max_limit_units": int(max_limit_units),
        "max_limit_display": format_bulk_units(max_limit_units),
        "encumbered": bool(total_units > enc_limit_units),
        "over_limit": bool(total_units > max_limit_units),
    }


def _status_id(status: Any) -> str:
    return str(getattr(status, "id", "") or "").strip().lower()


def _status_source(status: Any) -> str:
    return str(getattr(status, "source", "") or "").strip().lower()


def _remove_statuses_by_source(actor: Any, source: str) -> int:
    statuses = list(getattr(actor, "statuses", []) or [])
    if not statuses:
        return 0
    needle = str(source or "").strip().lower()
    if not needle:
        return 0
    kept: list[Any] = []
    removed = 0
    for status in statuses:
        if _status_source(status) == needle:
            removed += 1
            continue
        kept.append(status)
    if removed:
        try:
            setattr(actor, "statuses", kept)
        except Exception:
            pass
    return removed


def refresh_actor_bulk_state(actor: Any, *, inventory: Iterable[Any] | None = None) -> dict[str, Any]:
    summary = actor_bulk_summary(actor, inventory=inventory)
    has_encumbered = False
    for status in list(getattr(actor, "statuses", []) or []):
        if _status_id(status) == "encumbered" and _status_source(status) == ENCUMBERED_SOURCE:
            has_encumbered = True
            break

    if summary["encumbered"] and not has_encumbered:
        adder = getattr(actor, "add_status", None)
        if callable(adder):
            try:
                adder(EncumberedStatus(source=ENCUMBERED_SOURCE))
            except Exception:
                pass
    if not summary["encumbered"]:
        _remove_statuses_by_source(actor, ENCUMBERED_SOURCE)
    return summary


def item_cost_cp(item_id: str, *, fallback: int = 0) -> int:
    iid = str(item_id or "").strip().lower()
    if iid.startswith("alchemical:"):
        iid = iid.split(":", 1)[1].strip().lower()
    try:
        from GameObjects.items.alchemical_item import normalize_alchemical_event_id

        normalized_alchemical = normalize_alchemical_event_id(iid)
        if normalized_alchemical:
            iid = normalized_alchemical
    except Exception:
        pass

    try:
        from GameObjects.items.weapon import create_weapon
        from GameObjects.items.armor import create_armor
        from GameObjects.items.equipment import create_equipment
        from GameObjects.items.shield import create_shield

        for factory in (create_weapon, create_armor, create_shield, create_equipment):
            try:
                obj = factory(iid)
            except Exception:
                obj = None
            if obj is None:
                continue
            direct = _safe_int(getattr(obj, "price_cp", 0), 0)
            if direct > 0:
                return int(direct)
    except Exception:
        pass

    price_map = {
        "dagger": 20,
        "club": 0,
        "spear": 10,
        "mace": 10,
        "shortsword": 90,
        "rapier": 200,
        "sword": 100,
        "longsword": 100,
        "longbow": 600,
        "shortbow": 300,
        "crossbow": 300,
        "light_crossbow": 300,
        "javelin": 10,
        "warhammer": 100,
        "greataxe": 200,
        "halberd": 200,
        "glaive": 100,
        "buckler": 100,
        "wooden_shield": 100,
        "steel_shield": 200,
        "standard_shield": 200,
        "tower_shield": 1000,
        "padded_armor": 20,
        "leather_armor": 200,
        "studded_leather": 300,
        "chain_shirt": 500,
        "hide_armor": 200,
        "scale_mail": 400,
        "breastplate": 800,
        "chain_mail": 600,
        "splint_mail": 1300,
        "half_plate": 1800,
        "full_plate": 3000,
        "arrow": 10,
        "arrows": 10,
        "bolt": 10,
        "bolts": 10,
        "sling_bullet": 1,
        "sling_bullets": 1,
        "backpack": 10,
        "bedroll": 1,
        "belt_pouch": 4,
        "chalk": 1,
        "caltrops": 30,
        "chain_10ft": 300,
        "climbing_kit": 500,
        "crowbar": 20,
        "flint_and_steel": 5,
        "grappling_hook": 10,
        "hammer": 10,
        "healer_tools": 500,
        "mirror_steel": 100,
        "soap": 1,
        "thieves_tools": 300,
        "repair_kit": 200,
        "rope_hemp_50ft": 10,
        "rope_silk_50ft": 100,
        "rations_week": 40,
        "sack": 1,
        "shovel": 20,
        "signal_whistle": 8,
        "spike_iron_10": 10,
        "torch": 1,
        "waterskin": 5,
        "lantern_hooded": 70,
        "lantern_bullseye": 1000,
        "lock_simple": 100,
        "lock_good": 800,
        "oil_flask": 1,
        "spellbook": 100,
        "formula_book": 100,
        "holy_symbol_wooden": 10,
        "holy_symbol_silver": 250,
        "writing_set": 100,
        "tent": 100,
        "acid_flask": 300,
        "acidflask": 300,
        "alchemists_fire": 300,
        "bottled_lightning": 300,
        "frost_vial": 300,
        "tanglefoot_bag": 300,
        "thunderstone": 300,
        "smokestick": 300,
        "elixir_of_life": 300,
        "minor_elixir_of_life": 300,
        "antidote": 300,
        "antiplague": 300,
        "lesser_acid_flask": 300,
        "lesser_alchemists_fire": 300,
        "lesser_bottled_lightning": 300,
        "lesser_frost_vial": 300,
        "lesser_tanglefoot_bag": 300,
        "lesser_thunderstone": 300,
        "lesser_antidote": 300,
        "lesser_antiplague": 300,
        "lesser_smokestick": 300,
        "cognitive_mutagen": 300,
        "eagle_eye_elixir": 300,
        "juggernaut_mutagen": 300,
        "quicksilver_mutagen": 300,
        "serene_mutagen": 300,
        "silvertongue_mutagen": 300,
        "holy_water": 300,
        "unholy_water": 300,
        "minor_healing_potion": 400,
        "scroll_common_rank1": 400,
        "potency_crystal": 400,
    }
    if iid in price_map:
        return int(price_map[iid])
    return max(0, _safe_int(fallback, 0))


__all__ = [
    "COIN_CP_VALUES",
    "COIN_ORDER",
    "ENCUMBERED_SOURCE",
    "add_actor_cp",
    "actor_bulk_limits",
    "actor_bulk_summary",
    "actor_inventory_bulk_units",
    "actor_total_cp",
    "can_actor_afford_cp",
    "coin_pouch_from_cp",
    "coin_pouch_total_cp",
    "ensure_actor_coin_pouch",
    "format_actor_money",
    "format_bulk_units",
    "format_cp_value",
    "item_bulk_units",
    "item_cost_cp",
    "normalize_coin_pouch",
    "parse_bulk_units",
    "refresh_actor_bulk_state",
    "set_actor_starting_money_gp",
    "set_actor_total_cp",
    "spend_actor_cp",
    "total_coin_count",
]
