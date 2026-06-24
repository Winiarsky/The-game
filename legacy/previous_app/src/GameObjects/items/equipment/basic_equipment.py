from __future__ import annotations

from GameObjects.items.base_item import BaseItem


_EQUIPMENT_DEFS: dict[str, dict[str, object]] = {
    "arrows": {
        "name": "Strzaly (10)",
        "category": "ammo",
        "description": "Pek 10 strzal do lukow.",
        "price_cp": 10,
        "bulk": "L",
        "traits": ("ammunition",),
        "ammo_count": 10,
    },
    "bolts": {
        "name": "Belty (10)",
        "category": "ammo",
        "description": "Pek 10 beltow do kusz.",
        "price_cp": 10,
        "bulk": "L",
        "traits": ("ammunition",),
        "ammo_count": 10,
    },
    "sling_bullets": {
        "name": "Pociski do procy (10)",
        "category": "ammo",
        "description": "Pek 10 pociskow do procy.",
        "price_cp": 1,
        "bulk": "L",
        "traits": ("ammunition",),
        "ammo_count": 10,
    },
    "backpack": {
        "name": "Plecak",
        "category": "gear",
        "description": "Podstawowy plecak podrozny.",
        "price_cp": 10,
        "bulk": "L",
        "traits": ("container",),
    },
    "bedroll": {
        "name": "Poslanie",
        "category": "gear",
        "description": "Poslanie podrozne.",
        "price_cp": 1,
        "bulk": "L",
        "traits": (),
    },
    "belt_pouch": {
        "name": "Sakiewka na pas",
        "category": "gear",
        "description": "Mala sakiewka na pas.",
        "price_cp": 4,
        "bulk": "L",
        "traits": ("container",),
    },
    "climbing_kit": {
        "name": "Zestaw wspinaczkowy",
        "category": "gear",
        "description": "Kompletny zestaw do wspinaczki.",
        "price_cp": 500,
        "bulk": 1,
        "traits": ("tools",),
    },
    "chalk": {
        "name": "Kreda (10)",
        "category": "gear",
        "description": "Pakiet kredy do oznaczania szlaku.",
        "price_cp": 1,
        "bulk": "-",
        "traits": (),
    },
    "caltrops": {
        "name": "Kolce",
        "category": "gear",
        "description": "Rozsypywane kolce utrudniajace ruch.",
        "price_cp": 30,
        "bulk": "L",
        "traits": ("consumable",),
    },
    "chain_10ft": {
        "name": "Lancuch (10 ft)",
        "category": "gear",
        "description": "Metalowy lancuch dlugosci 10 stop.",
        "price_cp": 300,
        "bulk": 1,
        "traits": (),
    },
    "crowbar": {
        "name": "Lom",
        "category": "gear",
        "description": "Lom do podwazania i silowego otwierania.",
        "price_cp": 20,
        "bulk": "L",
        "traits": (),
    },
    "flint_and_steel": {
        "name": "Krzesiwo",
        "category": "gear",
        "description": "Krzesiwo do rozpalania ognia.",
        "price_cp": 5,
        "bulk": "-",
        "traits": (),
    },
    "grappling_hook": {
        "name": "Hak zadziorny",
        "category": "gear",
        "description": "Hak do wspinaczki uzywany z lina.",
        "price_cp": 10,
        "bulk": "L",
        "traits": (),
    },
    "hammer": {
        "name": "Mlotek",
        "category": "gear",
        "description": "Podreczny mlotek uzytkowy.",
        "price_cp": 10,
        "bulk": "L",
        "traits": ("tool",),
    },
    "healer_tools": {
        "name": "Narzędzia medyka",
        "category": "gear",
        "description": "Narzędzia medyczne do leczenia ran.",
        "price_cp": 500,
        "bulk": 1,
        "traits": ("tools", "healing"),
    },
    "thieves_tools": {
        "name": "Narzędzia zlodziejskie",
        "category": "gear",
        "description": "Narzędzia zlodziejskie do zamkow i pulapek.",
        "price_cp": 300,
        "bulk": "L",
        "traits": ("tools", "thievery"),
    },
    "repair_kit": {
        "name": "Zestaw naprawczy",
        "category": "gear",
        "description": "Narzędzia do naprawy przedmiotów.",
        "price_cp": 200,
        "bulk": 1,
        "traits": ("tools", "crafting"),
    },
    "mirror_steel": {
        "name": "Lusterko stalowe",
        "category": "gear",
        "description": "Male lusterko stalowe.",
        "price_cp": 100,
        "bulk": "-",
        "traits": (),
    },
    "soap": {
        "name": "Mydlo",
        "category": "gear",
        "description": "Kostka mydla.",
        "price_cp": 1,
        "bulk": "-",
        "traits": ("consumable",),
    },
    "rope_hemp_50ft": {
        "name": "Lina konopna (50 ft)",
        "category": "gear",
        "description": "Lina konopna dlugosci 50 stop.",
        "price_cp": 10,
        "bulk": 1,
        "traits": (),
    },
    "rope_silk_50ft": {
        "name": "Lina jedwabna (50 ft)",
        "category": "gear",
        "description": "Lina jedwabna dlugosci 50 stop.",
        "price_cp": 100,
        "bulk": "L",
        "traits": (),
    },
    "rations_week": {
        "name": "Racje (1 tydzien)",
        "category": "gear",
        "description": "Racje zywnosciowe na tydzien.",
        "price_cp": 40,
        "bulk": "L",
        "traits": ("consumable",),
    },
    "sack": {
        "name": "Worek",
        "category": "gear",
        "description": "Prosty worek na zapasy.",
        "price_cp": 1,
        "bulk": "L",
        "traits": ("container",),
    },
    "shovel": {
        "name": "Lopata",
        "category": "gear",
        "description": "Narzędzie do kopania.",
        "price_cp": 20,
        "bulk": 1,
        "traits": ("tool",),
    },
    "signal_whistle": {
        "name": "Gwizdek sygnalowy",
        "category": "gear",
        "description": "Gwizdek do sygnalizacji.",
        "price_cp": 8,
        "bulk": "-",
        "traits": (),
    },
    "spike_iron_10": {
        "name": "Zelazne kolki (10)",
        "category": "gear",
        "description": "Pakiet 10 zelaznych kolkow.",
        "price_cp": 10,
        "bulk": "L",
        "traits": (),
    },
    "torch": {
        "name": "Pochodnia",
        "category": "gear",
        "description": "Pochodnia zapewniajaca swiatlo.",
        "price_cp": 1,
        "bulk": "L",
        "traits": ("consumable", "light_source"),
    },
    "waterskin": {
        "name": "Buklak",
        "category": "gear",
        "description": "Bukłak na wodę.",
        "price_cp": 5,
        "bulk": "L",
        "traits": ("container",),
    },
    "lantern_hooded": {
        "name": "Latarnia kapturowa",
        "category": "gear",
        "description": "Latarnia kapturowa.",
        "price_cp": 70,
        "bulk": 1,
        "traits": ("light_source",),
    },
    "lantern_bullseye": {
        "name": "Latarnia reflektorowa",
        "category": "gear",
        "description": "Latarnia kierunkowa dajaca skupione swiatlo.",
        "price_cp": 1000,
        "bulk": 1,
        "traits": ("light_source",),
    },
    "lock_simple": {
        "name": "Zamek prosty",
        "category": "gear",
        "description": "Podstawowy zamek do drzwi/skrzyn.",
        "price_cp": 100,
        "bulk": "L",
        "traits": ("lock",),
    },
    "lock_good": {
        "name": "Zamek dobry",
        "category": "gear",
        "description": "Solidny zamek o podwyzszonej jakosci.",
        "price_cp": 800,
        "bulk": "L",
        "traits": ("lock",),
    },
    "oil_flask": {
        "name": "Olej (1 flaszka)",
        "category": "gear",
        "description": "Flaszka oleju do lamp i pochodni.",
        "price_cp": 1,
        "bulk": "L",
        "traits": ("consumable",),
    },
    "spellbook": {
        "name": "Ksiega zaklec",
        "category": "gear",
        "description": "Ksiega do zapisywania i przygotowania zaklec.",
        "price_cp": 100,
        "bulk": "L",
        "traits": ("tool", "magic"),
    },
    "formula_book": {
        "name": "Ksiega formul",
        "category": "gear",
        "description": "Ksiega receptur i formul alchemicznych.",
        "price_cp": 100,
        "bulk": "L",
        "traits": ("tool", "alchemy"),
    },
    "holy_symbol_wooden": {
        "name": "Swiety symbol (drewniany)",
        "category": "gear",
        "description": "Drewniany swiety symbol.",
        "price_cp": 10,
        "bulk": "L",
        "traits": ("religious", "focus"),
    },
    "holy_symbol_silver": {
        "name": "Swiety symbol (srebrny)",
        "category": "gear",
        "description": "Srebrny swiety symbol.",
        "price_cp": 250,
        "bulk": "L",
        "traits": ("religious", "focus"),
    },
    "writing_set": {
        "name": "Zestaw pisarski",
        "category": "gear",
        "description": "Atrament, pioro i materialy pisarskie.",
        "price_cp": 100,
        "bulk": "L",
        "traits": ("tool",),
    },
    "tent": {
        "name": "Namiot",
        "category": "gear",
        "description": "Dwuosobowy namiot podrozny.",
        "price_cp": 100,
        "bulk": 2,
        "traits": ("camp",),
    },
    "holy_water": {
        "name": "Woda swiecona",
        "category": "potion",
        "description": "Fiolka swietej wody. Rzut jak bomba; zadaje 1k6 obrazen good fiendom i nieumarlym.",
        "price_cp": 300,
        "bulk": "L",
        "traits": ("consumable", "magic", "good", "bomb"),
        "event_name": "holy_water",
    },
    "unholy_water": {
        "name": "Woda plugawa",
        "category": "potion",
        "description": "Fiolka plugawej wody. Rzut jak bomba; zadaje 1k6 obrazen evil celestials.",
        "price_cp": 300,
        "bulk": "L",
        "traits": ("consumable", "magic", "evil", "bomb"),
        "event_name": "unholy_water",
    },
    "minor_healing_potion": {
        "name": "Mikstura leczenia (slaba)",
        "category": "potion",
        "description": "Po wypiciu odzyskujesz 1k8 HP.",
        "price_cp": 400,
        "bulk": "L",
        "traits": ("consumable", "healing", "magic"),
        "event_name": "minor_healing_potion",
    },
    "brindleford_healing_herb": {
        "name": "Ziele uzdrawiajace z Brindleford",
        "category": "potion",
        "description": "Jednorazowe ziele od mieszkancow Brindleford. Po uzyciu leczy dokladnie 1 HP.",
        "price_cp": 100,
        "bulk": "L",
        "traits": ("consumable", "healing", "herbal"),
        "event_name": "brindleford_healing_herb",
    },
    "scroll_common_rank1": {
        "name": "Zwoj czaru 1. rangi (wspolny)",
        "category": "potion",
        "description": "Jednorazowo rzuca wybrany wspolny czar 1. rangi z listy.",
        "price_cp": 400,
        "bulk": "L",
        "traits": ("consumable", "magic", "scroll"),
        "event_name": "scroll_common_rank1",
    },
    "potency_crystal": {
        "name": "Krysztal potencji",
        "category": "gear",
        "description": "Talizman: daje +1 item do ataku bronia do konca tury.",
        "price_cp": 400,
        "bulk": "-",
        "traits": ("consumable", "magic", "talisman"),
        "event_name": "potency_crystal",
    },
}

_ALIASES = {
    "arrow": "arrows",
    "arrows_10": "arrows",
    "bolt": "bolts",
    "bolts_10": "bolts",
    "bełty": "bolts",
    "sling_bullet": "sling_bullets",
    "sling_bullets_10": "sling_bullets",
    "backpack": "backpack",
    "bedroll": "bedroll",
    "belt_pouch": "belt_pouch",
    "climbing_kit": "climbing_kit",
    "healers_tools": "healer_tools",
    "healers_tool": "healer_tools",
    "thieves_tool": "thieves_tools",
    "rope": "rope_hemp_50ft",
    "hemp_rope_50ft": "rope_hemp_50ft",
    "silk_rope_50ft": "rope_silk_50ft",
    "rations": "rations_week",
    "sack": "sack",
    "torch": "torch",
    "water_skin": "waterskin",
    "hooded_lantern": "lantern_hooded",
    "bullseye_lantern": "lantern_bullseye",
    "oil": "oil_flask",
    "spellbook": "spellbook",
    "formula_book": "formula_book",
    "caltrops": "caltrops",
    "chain": "chain_10ft",
    "hammer": "hammer",
    "mirror": "mirror_steel",
    "soap": "soap",
    "shovel": "shovel",
    "whistle": "signal_whistle",
    "spike_iron": "spike_iron_10",
    "simple_lock": "lock_simple",
    "good_lock": "lock_good",
    "wooden_holy_symbol": "holy_symbol_wooden",
    "silver_holy_symbol": "holy_symbol_silver",
    "writing_kit": "writing_set",
    "tent": "tent",
    "holywater": "holy_water",
    "holy_water": "holy_water",
    "unholywater": "unholy_water",
    "unholy_water": "unholy_water",
    "minor_healing_potion": "minor_healing_potion",
    "healing_potion_minor": "minor_healing_potion",
    "brindleford_healing_herb": "brindleford_healing_herb",
    "healing_herb": "brindleford_healing_herb",
    "ziele_uzdrawiajace": "brindleford_healing_herb",
    "scroll_common_rank1": "scroll_common_rank1",
    "scroll_of_common_1st_level_spell": "scroll_common_rank1",
    "potency_crystal": "potency_crystal",
}


def normalize_equipment_id(value: object) -> str | None:
    raw = str(value or "").strip().lower()
    if not raw:
        return None
    key = raw.replace("-", "_").replace(" ", "_")
    normalized = _ALIASES.get(key, key)
    if normalized in _EQUIPMENT_DEFS:
        return normalized
    return None


def create_equipment(item_id: object) -> BaseItem | None:
    normalized = normalize_equipment_id(item_id)
    if not normalized:
        return None
    data = dict(_EQUIPMENT_DEFS.get(normalized) or {})
    if not data:
        return None
    item = BaseItem(
        item_id=normalized,
        name=str(data.get("name") or normalized.replace("_", " ").title()),
        category=str(data.get("category") or "gear"),
        description=str(data.get("description") or ""),
        traits=tuple(data.get("traits") or ()),
        price_cp=int(data.get("price_cp") or 0),
        bulk=data.get("bulk", "-"),
    )
    if "ammo_count" in data:
        try:
            setattr(item, "ammo_count", max(0, int(data.get("ammo_count") or 0)))
        except Exception:
            pass
    if "event_name" in data:
        try:
            setattr(item, "event_name", str(data.get("event_name") or "").strip().lower())
        except Exception:
            pass
    if "preparation_counter" in data:
        try:
            setattr(item, "preparation_counter", max(0, int(data.get("preparation_counter") or 0)))
        except Exception:
            pass
    return item


def list_equipment_ids() -> list[str]:
    return sorted(_EQUIPMENT_DEFS.keys())


__all__ = [
    "create_equipment",
    "list_equipment_ids",
    "normalize_equipment_id",
]
