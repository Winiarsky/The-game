from __future__ import annotations

from GameObjects.items.base_item import BaseItem


_SERVICE_DEFS: dict[str, dict[str, object]] = {
    # Table 6-14: beverages
    "mug_of_ale": {
        "name": "Kufel piwa",
        "price_cp": 1,
        "bulk": "L",
        "hands": 1,
        "description": "Napoje w karczmie. Usluga fabularna, bez osobnej mechaniki bojowej.",
    },
    "keg_of_ale": {
        "name": "Beczka piwa",
        "price_cp": 20,
        "bulk": 2,
        "hands": 2,
        "description": "Wiekszy zakup napoju. Usluga fabularna.",
    },
    "pot_of_coffee_or_tea": {
        "name": "Dzbanek kawy lub herbaty",
        "price_cp": 2,
        "bulk": "L",
        "hands": 1,
        "description": "Napoje gorace. Usluga fabularna.",
    },
    "bottle_of_wine": {
        "name": "Butelka wina",
        "price_cp": 10,
        "bulk": "L",
        "hands": 1,
        "description": "Napoje. Usluga fabularna.",
    },
    "bottle_of_fine_wine": {
        "name": "Butelka dobrego wina",
        "price_cp": 100,
        "bulk": "L",
        "hands": 1,
        "description": "Napoje premium. Usluga fabularna.",
    },
    # Table 6-14: hirelings
    "hireling_unskilled_day": {
        "name": "Najemnik niewykwalifikowany (1 dzien)",
        "price_cp": 10,
        "bulk": "-",
        "hands": 0,
        "description": (
            "Najemnik poziom 0, modyfikator +0. "
            "Przy wyprawie przygodowej koszt zwykle x2."
        ),
    },
    "hireling_skilled_day": {
        "name": "Najemnik wykwalifikowany (1 dzien)",
        "price_cp": 50,
        "bulk": "-",
        "hands": 0,
        "description": (
            "Najemnik poziom 0, +4 w swojej specjalizacji, +0 poza nia. "
            "Przy wyprawie przygodowej koszt zwykle x2."
        ),
    },
    # Table 6-14: lodging
    "lodging_floor_space_day": {
        "name": "Nocleg: miejsce na podlodze (1 dzien)",
        "price_cp": 3,
        "bulk": "-",
        "hands": 0,
        "description": "Podstawowy nocleg. Efekt glownie fabularny.",
    },
    "lodging_bed_day": {
        "name": "Nocleg: lozko (1 osoba, 1 dzien)",
        "price_cp": 10,
        "bulk": "-",
        "hands": 0,
        "description": "Standardowy nocleg. Efekt glownie fabularny.",
    },
    "lodging_private_room_day": {
        "name": "Nocleg: pokoj prywatny (2 osoby, 1 dzien)",
        "price_cp": 80,
        "bulk": "-",
        "hands": 0,
        "description": "Wygodny nocleg. Efekt glownie fabularny.",
    },
    "lodging_extravagant_suite_day": {
        "name": "Nocleg: apartament luksusowy (6 osob, 1 dzien)",
        "price_cp": 1000,
        "bulk": "-",
        "hands": 0,
        "description": "Luksusowy nocleg. Efekt glownie fabularny.",
    },
    # Table 6-14: meals
    "meal_poor": {
        "name": "Posilek ubogi",
        "price_cp": 1,
        "bulk": "L",
        "hands": 2,
        "description": "Posilek podstawowy. Usluga fabularna.",
    },
    "meal_square": {
        "name": "Posilek syty",
        "price_cp": 3,
        "bulk": "L",
        "hands": 2,
        "description": "Posilek standardowy. Usluga fabularna.",
    },
    "meal_fine_dining": {
        "name": "Posilek wykwintny",
        "price_cp": 100,
        "bulk": "L",
        "hands": 2,
        "description": "Posilek premium. Usluga fabularna.",
    },
    # Table 6-14: misc services
    "stabling_day": {
        "name": "Stajnia (1 dzien)",
        "price_cp": 2,
        "bulk": "-",
        "hands": 0,
        "description": "Oplata za stajnie dla wierzchowca.",
    },
    "toll_basic": {
        "name": "Myto drogowe (minimum)",
        "price_cp": 1,
        "bulk": "-",
        "hands": 0,
        "description": "Podstawowa oplata za przejazd/przejscie.",
    },
    "transport_caravan_5_miles": {
        "name": "Transport: karawana (5 mil)",
        "price_cp": 3,
        "bulk": "-",
        "hands": 0,
        "description": "Przewoz standardowy bez udogodnien.",
    },
    "transport_carriage_5_miles": {
        "name": "Transport: powoz (5 mil)",
        "price_cp": 20,
        "bulk": "-",
        "hands": 0,
        "description": "Przewoz standardowy bez udogodnien.",
    },
    "transport_ferry_or_riverboat_5_miles": {
        "name": "Transport: prom/lodz rzeczna (5 mil)",
        "price_cp": 4,
        "bulk": "-",
        "hands": 0,
        "description": "Przewoz standardowy bez udogodnien.",
    },
    "transport_sailing_ship_5_miles": {
        "name": "Transport: statek zeglowy (5 mil)",
        "price_cp": 6,
        "bulk": "-",
        "hands": 0,
        "description": "Przewoz standardowy bez udogodnien.",
    },
    # Table 6-15: spellcasting services
    "spellcasting_service_cantrip": {
        "name": "Usluga rzucenia czaru (cantrip)",
        "price_cp": 100,
        "bulk": "-",
        "hands": 0,
        "description": "Cena domowa (1 gp) dla jednorazowego cantripu od handlarza.",
    },
    "spellcasting_service_rank_1": {
        "name": "Usluga rzucenia czaru (1. ranga)",
        "price_cp": 300,
        "bulk": "-",
        "hands": 0,
        "description": "Cena bazowa. Plus dodatkowe koszty samego czaru.",
    },
    "spellcasting_service_rank_2": {
        "name": "Usluga rzucenia czaru (2. ranga)",
        "price_cp": 700,
        "bulk": "-",
        "hands": 0,
        "description": "Cena bazowa. Plus dodatkowe koszty samego czaru.",
    },
    "spellcasting_service_rank_3": {
        "name": "Usluga rzucenia czaru (3. ranga)",
        "price_cp": 1800,
        "bulk": "-",
        "hands": 0,
        "description": "Cena bazowa. Plus dodatkowe koszty samego czaru.",
    },
    "spellcasting_service_rank_4": {
        "name": "Usluga rzucenia czaru (4. ranga)",
        "price_cp": 4000,
        "bulk": "-",
        "hands": 0,
        "description": "Cena bazowa. Plus dodatkowe koszty samego czaru.",
    },
    "spellcasting_service_rank_5": {
        "name": "Usluga rzucenia czaru (5. ranga)",
        "price_cp": 8000,
        "bulk": "-",
        "hands": 0,
        "description": "Cena bazowa. Plus dodatkowe koszty samego czaru.",
    },
    "spellcasting_service_rank_6": {
        "name": "Usluga rzucenia czaru (6. ranga)",
        "price_cp": 16000,
        "bulk": "-",
        "hands": 0,
        "description": "Cena bazowa. Plus dodatkowe koszty samego czaru.",
    },
    "spellcasting_service_rank_7": {
        "name": "Usluga rzucenia czaru (7. ranga)",
        "price_cp": 36000,
        "bulk": "-",
        "hands": 0,
        "description": "Cena bazowa. Plus dodatkowe koszty samego czaru.",
    },
    "spellcasting_service_rank_8": {
        "name": "Usluga rzucenia czaru (8. ranga)",
        "price_cp": 72000,
        "bulk": "-",
        "hands": 0,
        "description": "Cena bazowa. Plus dodatkowe koszty samego czaru.",
    },
    "spellcasting_service_rank_9": {
        "name": "Usluga rzucenia czaru (9. ranga)",
        "price_cp": 180000,
        "bulk": "-",
        "hands": 0,
        "description": "Cena bazowa. Plus dodatkowe koszty samego czaru.",
    },
    # Table 6-16: cost of living
    "cost_of_living_subsistence_week": {
        "name": "Koszt zycia: skromny (tydzien)",
        "price_cp": 40,
        "bulk": "-",
        "hands": 0,
        "description": "Pokrywa standardowe oplaty zyciowe za tydzien.",
    },
    "cost_of_living_comfortable_week": {
        "name": "Koszt zycia: wygodny (tydzien)",
        "price_cp": 100,
        "bulk": "-",
        "hands": 0,
        "description": "Pokrywa standardowe oplaty zyciowe za tydzien.",
    },
    "cost_of_living_fine_week": {
        "name": "Koszt zycia: wysoki (tydzien)",
        "price_cp": 3000,
        "bulk": "-",
        "hands": 0,
        "description": "Pokrywa standardowe oplaty zyciowe za tydzien.",
    },
    "cost_of_living_extravagant_week": {
        "name": "Koszt zycia: luksusowy (tydzien)",
        "price_cp": 10000,
        "bulk": "-",
        "hands": 0,
        "description": "Pokrywa standardowe oplaty zyciowe za tydzien.",
    },
    # Rozszerzenia mechaniczne (NPC mage/priest)
    "mage_service_mage_armor": {
        "name": "Usluga maga: Mage Armor",
        "price_cp": 300,
        "bulk": "-",
        "hands": 0,
        "description": "Naklada Mage Armor (+1 item AC, uproszczony czas trwania).",
    },
    "mage_service_magic_weapon": {
        "name": "Usluga maga: Magic Weapon",
        "price_cp": 300,
        "bulk": "-",
        "hands": 0,
        "description": "Wzmacnia bron (+1 item do ataku, uproszczony czas trwania).",
    },
    "mage_service_longstrider": {
        "name": "Usluga maga: Longstrider",
        "price_cp": 300,
        "bulk": "-",
        "hands": 0,
        "description": "Zwieksza predkosc celu o +10 ft (uproszczenie).",
    },
    "priest_service_heal_minor": {
        "name": "Usluga kaplana: Leczenie (mniejsze)",
        "price_cp": 300,
        "bulk": "-",
        "hands": 0,
        "description": "Natychmiastowe leczenie obrazen.",
    },
    "priest_service_heal_major": {
        "name": "Usluga kaplana: Leczenie (wieksze)",
        "price_cp": 700,
        "bulk": "-",
        "hands": 0,
        "description": "Silne natychmiastowe leczenie obrazen.",
    },
    "priest_service_bless": {
        "name": "Usluga kaplana: Bless",
        "price_cp": 300,
        "bulk": "-",
        "hands": 0,
        "description": "Buf +1 status do atakow na ograniczony czas.",
    },
    "priest_service_remove_fear": {
        "name": "Usluga kaplana: Usuniecie strachu",
        "price_cp": 300,
        "bulk": "-",
        "hands": 0,
        "description": "Usuwa status frightened i pokrewne efekty strachu.",
    },
}

_ALIASES: dict[str, str] = {
    "ale_mug": "mug_of_ale",
    "coffee_or_tea_pot": "pot_of_coffee_or_tea",
    "hireling_unskilled": "hireling_unskilled_day",
    "hireling_skilled": "hireling_skilled_day",
    "lodging_floor": "lodging_floor_space_day",
    "lodging_bed": "lodging_bed_day",
    "lodging_private_room": "lodging_private_room_day",
    "lodging_extravagant_suite": "lodging_extravagant_suite_day",
    "meal_poor": "meal_poor",
    "meal_square": "meal_square",
    "meal_fine": "meal_fine_dining",
    "stabling": "stabling_day",
    "toll": "toll_basic",
    "caravan_5_miles": "transport_caravan_5_miles",
    "carriage_5_miles": "transport_carriage_5_miles",
    "ferry_5_miles": "transport_ferry_or_riverboat_5_miles",
    "sailing_ship_5_miles": "transport_sailing_ship_5_miles",
    "spellcasting_service_0": "spellcasting_service_cantrip",
    "spellcasting_service_cantrip": "spellcasting_service_cantrip",
    "mage_armor_service": "mage_service_mage_armor",
    "magic_weapon_service": "mage_service_magic_weapon",
    "longstrider_service": "mage_service_longstrider",
    "priest_heal_minor": "priest_service_heal_minor",
    "priest_heal_major": "priest_service_heal_major",
    "priest_bless": "priest_service_bless",
    "priest_remove_fear": "priest_service_remove_fear",
}


def normalize_service_id(value: object) -> str | None:
    raw = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if not raw:
        return None
    normalized = _ALIASES.get(raw, raw)
    if normalized in _SERVICE_DEFS:
        return normalized
    return None


def create_service(service_id: object) -> BaseItem | None:
    normalized = normalize_service_id(service_id)
    if not normalized:
        return None
    data = dict(_SERVICE_DEFS.get(normalized) or {})
    if not data:
        return None
    hands = int(data.get("hands", 0) or 0)
    base_desc = str(data.get("description") or "").strip()
    extra = f"Usluga natychmiastowa. Bulk: {data.get('bulk', '-')}, Hands: {hands}."
    description = f"{base_desc}\n{extra}".strip()
    item = BaseItem(
        item_id=normalized,
        name=str(data.get("name") or normalized.replace("_", " ").title()),
        category="service",
        description=description,
        traits=("service",),
        price_cp=int(data.get("price_cp") or 0),
        bulk=data.get("bulk", "-"),
    )
    try:
        setattr(item, "hands", int(hands))
    except Exception:
        pass
    return item


def list_service_ids() -> list[str]:
    return sorted(_SERVICE_DEFS.keys())


__all__ = [
    "create_service",
    "list_service_ids",
    "normalize_service_id",
]
