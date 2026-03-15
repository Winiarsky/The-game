from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from GameObjects.items.alchemical_item import (
    AlchemicalItem,
    alchemical_item_defaults,
    alchemical_item_name_from_event,
    normalize_alchemical_event_id,
)
from GameObjects.items.armor import create_armor, normalize_armor_id
from GameObjects.items.base_item import BaseItem
from GameObjects.items.shield import create_shield, normalize_shield_id
from GameObjects.items.weapon import BaseWeapon, create_weapon, normalize_weapon_id
from localization import localize_term_pl


_DEFAULT_WEAPON_IDS: tuple[str, ...] = ("sword", "dagger", "longbow", "unarmed")
_CATEGORY_PRIORITY: dict[str, int] = {
    "weapon": 0,
    "shield": 1,
    "armor": 2,
    "potion": 3,
    "ammo": 4,
    "gear": 5,
}
_HAND_LEFT = "left"
_HAND_RIGHT = "right"
_HAND_SHIELD_MARKER = "__shield__"


def _refresh_bulk(actor, *, inventory: list[object] | None = None) -> None:
    try:
        from economy import refresh_actor_bulk_state

        refresh_actor_bulk_state(actor, inventory=inventory)
    except Exception:
        return


def _refresh_actor_ac(actor) -> None:
    try:
        from character_creation.mechanics import refresh_actor_ac

        refresh_actor_ac(actor)
    except Exception:
        return


def _has_status(actor, status_id: str) -> bool:
    checker = getattr(actor, "has_status", None)
    if callable(checker):
        try:
            return bool(checker(status_id))
        except Exception:
            return False
    for status in getattr(actor, "statuses", []) or []:
        if getattr(status, "id", status) == status_id:
            return True
    return False


def default_weapon_ids_for_actor(actor) -> list[str]:
    default = list(_DEFAULT_WEAPON_IDS)
    if _has_status(actor, "razortooth_goblin"):
        default.append("razortooth_jaws")
    return default


def _item_category(item) -> str:
    return str(getattr(item, "category", "misc") or "misc").strip().lower()


def _is_weapon(item) -> bool:
    if isinstance(item, BaseWeapon):
        return True
    return _item_category(item) == "weapon"


def _is_shield(item) -> bool:
    return _item_category(item) == "shield"


def _is_armor(item) -> bool:
    return _item_category(item) == "armor"


def _is_base_item(item) -> bool:
    return isinstance(item, BaseItem)


def _normalize_inventory(raw) -> list[object]:
    if not isinstance(raw, list):
        return []
    normalized: list[object] = []
    for item in raw:
        if item is None:
            continue
        normalized.append(item)
    return normalized


def _item_instance_id(item) -> str:
    iid = str(getattr(item, "instance_id", "") or "").strip()
    if iid:
        return iid
    return str(getattr(item, "item_id", "") or id(item))


def _item_label(item) -> str:
    name = str(getattr(item, "name", "") or "").strip()
    if name:
        return name
    item_id = str(getattr(item, "item_id", "") or "").strip()
    if item_id:
        return item_id.replace("_", " ").title()
    return str(item)


def _item_id(item) -> str:
    return str(getattr(item, "item_id", "") or "").strip().lower()


def _normalize_event_name(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _to_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _is_ammo_item(item) -> bool:
    category = _item_category(item)
    if category in {"ammo", "ammunition"}:
        return True
    traits = {
        str(tag or "").strip().lower().replace("-", "_").replace(" ", "_")
        for tag in (getattr(item, "traits", None) or ())
    }
    return "ammunition" in traits


def _ammo_default_count(item) -> int:
    item_id = _item_id(item)
    if item_id in {"arrows", "bolts", "sling_bullets"}:
        return 10
    return 1


def _ammo_count(item) -> int:
    current = getattr(item, "ammo_count", None)
    if current is None:
        return _ammo_default_count(item)
    return max(0, _to_int(current, _ammo_default_count(item)))


def _set_ammo_count(item, value: int) -> None:
    try:
        setattr(item, "ammo_count", max(0, int(value)))
    except Exception:
        pass


def _weapon_ammo_id(weapon) -> str | None:
    weapon_id = normalize_weapon_id(getattr(weapon, "item_id", None)) or _item_id(weapon)
    if not weapon_id:
        return None
    traits = {
        str(tag or "").strip().lower().replace("-", "_").replace(" ", "_")
        for tag in (getattr(weapon, "traits", None) or ())
    }
    group = str(getattr(weapon, "weapon_group", "") or "").strip().lower()
    if weapon_id in {"shortbow", "longbow", "composite_shortbow", "composite_longbow"} or group == "bow":
        return "arrows"
    if "crossbow" in weapon_id or "crossbow" in traits or group == "crossbow":
        return "bolts"
    if weapon_id in {"sling", "halfling_sling_staff"} or group == "sling":
        return "sling_bullets"
    return None


def weapon_ammo_label(weapon) -> str | None:
    mapping = {
        "arrows": "Strzaly (10)",
        "bolts": "Belty (10)",
        "sling_bullets": "Pociski do procy (10)",
    }
    ammo_id = _weapon_ammo_id(weapon)
    if not ammo_id:
        return None
    return mapping.get(ammo_id, ammo_id)


def _normalize_hand(hand: object) -> str:
    raw = str(hand or "").strip().lower()
    if raw in {"l", "left", "lewa", "main", "primary", "main_hand"}:
        return _HAND_LEFT
    if raw in {"r", "right", "prawa", "off", "off_hand", "secondary"}:
        return _HAND_RIGHT
    return _HAND_RIGHT


def _other_hand(hand: str) -> str:
    return _HAND_RIGHT if hand == _HAND_LEFT else _HAND_LEFT


def _shield_hand(actor) -> str:
    hand = _normalize_hand(getattr(actor, "equipped_shield_hand", _HAND_RIGHT))
    return hand


def _set_shield_hand(actor, hand: str) -> None:
    try:
        setattr(actor, "equipped_shield_hand", _normalize_hand(hand))
    except Exception:
        pass


def _empty_hand_slot() -> dict[str, str | None]:
    return {"kind": "empty", "label": "Pusta ręka", "item_id": None, "instance_id": None}


def _weapon_slot_payload(item) -> dict[str, str | None]:
    return {
        "kind": "weapon",
        "label": _item_label(item),
        "item_id": str(getattr(item, "item_id", "") or ""),
        "instance_id": _item_instance_id(item),
    }


def _shield_slot_payload(item) -> dict[str, str | None]:
    return {
        "kind": "shield",
        "label": _item_label(item),
        "item_id": str(getattr(item, "item_id", "") or ""),
        "instance_id": _item_instance_id(item),
    }


def _sort_categories(category: str) -> tuple[int, str]:
    return (_CATEGORY_PRIORITY.get(category, 100), category)


def _sort_items(actor, item) -> tuple[int, str]:
    active_rank = 0 if is_item_active(actor, item) else 1
    return (active_rank, _item_label(item).lower(), _item_instance_id(item))


def ensure_actor_inventory(actor) -> list[object]:
    if actor is None:
        return []

    inventory = _normalize_inventory(getattr(actor, "inventory", None))
    if not inventory:
        weapon_ids = []
        raw_loadout = getattr(actor, "weapon_loadout", None)
        if isinstance(raw_loadout, Iterable) and not isinstance(raw_loadout, (str, bytes)):
            for raw in raw_loadout:
                wid = normalize_weapon_id(raw)
                if wid and wid not in weapon_ids:
                    weapon_ids.append(wid)
        if not weapon_ids:
            weapon_ids = default_weapon_ids_for_actor(actor)
        for weapon_id in weapon_ids:
            weapon = create_weapon(weapon_id)
            if weapon is not None:
                inventory.append(weapon)

        armor_ids: list[str] = []
        raw_armor_loadout = getattr(actor, "armor_loadout", None)
        if isinstance(raw_armor_loadout, Iterable) and not isinstance(raw_armor_loadout, (str, bytes)):
            for raw in raw_armor_loadout:
                aid = normalize_armor_id(raw)
                if aid and aid not in armor_ids:
                    armor_ids.append(aid)
        for armor_id in armor_ids:
            armor = create_armor(armor_id)
            if armor is not None:
                inventory.append(armor)

        shield_ids: list[str] = []
        raw_shield_loadout = getattr(actor, "shield_loadout", None)
        if isinstance(raw_shield_loadout, Iterable) and not isinstance(raw_shield_loadout, (str, bytes)):
            for raw in raw_shield_loadout:
                sid = normalize_shield_id(raw)
                if sid and sid not in shield_ids:
                    shield_ids.append(sid)
        for shield_id in shield_ids:
            shield = create_shield(shield_id)
            if shield is not None:
                inventory.append(shield)

        legacy_armor = getattr(actor, "equipped_armor", None)
        if legacy_armor is not None and _is_armor(legacy_armor):
            inventory.append(legacy_armor)
        legacy_shield = getattr(actor, "equipped_shield", None)
        if legacy_shield is not None:
            inventory.append(legacy_shield)
    else:
        # Uzupełnij brakujące metadata na starszych obiektach itemów.
        for item in inventory:
            if _is_shield(item):
                if not getattr(item, "name", None):
                    try:
                        setattr(item, "name", "Shield")
                    except Exception:
                        pass
            if _item_category(item) == "misc" and _is_base_item(item):
                try:
                    setattr(item, "category", str(getattr(item, "category", "misc") or "misc"))
                except Exception:
                    pass

    # Zapewnij unarmed jako fallback item (nie musi być aktywny).
    has_unarmed = any(_is_weapon(item) and normalize_weapon_id(getattr(item, "item_id", None)) == "unarmed" for item in inventory)
    if not has_unarmed:
        unarmed = create_weapon("unarmed")
        if unarmed is not None:
            inventory.append(unarmed)

    try:
        setattr(actor, "inventory", inventory)
    except Exception:
        pass

    _ensure_equipment_state(actor)
    _refresh_bulk(actor, inventory=inventory)
    return inventory


def _weapon_map(actor) -> dict[str, object]:
    mapping: dict[str, object] = {}
    for item in _normalize_inventory(getattr(actor, "inventory", None)):
        if not _is_weapon(item):
            continue
        mapping[_item_instance_id(item)] = item
    return mapping


def _ensure_equipment_state(actor) -> None:
    weapons = _weapon_map(actor)
    equipped_ids = list(getattr(actor, "equipped_weapon_item_ids", []) or [])
    equipped_ids = [wid for wid in equipped_ids if wid in weapons]

    if not equipped_ids:
        legacy = normalize_weapon_id(getattr(actor, "active_weapon", None))
        if legacy:
            for iid, item in weapons.items():
                if normalize_weapon_id(getattr(item, "item_id", None)) == legacy:
                    equipped_ids = [iid]
                    break

    if not equipped_ids:
        for iid, item in weapons.items():
            if normalize_weapon_id(getattr(item, "item_id", None)) == "sword":
                equipped_ids = [iid]
                break

    try:
        setattr(actor, "equipped_weapon_item_ids", equipped_ids)
    except Exception:
        pass

    _sync_legacy_weapon_attrs(actor)

    equipped_shield = getattr(actor, "equipped_shield", None)
    if equipped_shield is not None:
        _set_shield_hand(actor, _shield_hand(actor))
        inventory = list(getattr(actor, "inventory", []) or [])
        if equipped_shield not in inventory:
            inventory.append(equipped_shield)
            try:
                setattr(actor, "inventory", inventory)
            except Exception:
                pass

    inventory = list(getattr(actor, "inventory", []) or [])
    armor_items = [item for item in inventory if _is_armor(item)]
    armor_map = {_item_instance_id(item): item for item in armor_items}
    equipped_armor_id = str(getattr(actor, "equipped_armor_item_id", "") or "")
    if equipped_armor_id and equipped_armor_id not in armor_map:
        equipped_armor_id = ""
    if not equipped_armor_id:
        legacy_armor = getattr(actor, "equipped_armor", None)
        if legacy_armor is not None and _is_armor(legacy_armor):
            iid = _item_instance_id(legacy_armor)
            if iid in armor_map:
                equipped_armor_id = iid
    if equipped_armor_id:
        try:
            setattr(actor, "equipped_armor_item_id", equipped_armor_id)
        except Exception:
            pass


def _sync_legacy_weapon_attrs(actor) -> None:
    inventory = _normalize_inventory(getattr(actor, "inventory", None))
    weapon_by_id = {
        _item_instance_id(item): item
        for item in inventory
        if _is_weapon(item)
    }
    equipped_ids = list(getattr(actor, "equipped_weapon_item_ids", []) or [])
    equipped = [weapon_by_id[iid] for iid in equipped_ids if iid in weapon_by_id]
    primary = equipped[0] if equipped else None
    legacy = normalize_weapon_id(getattr(primary, "item_id", None)) if primary is not None else None
    try:
        setattr(actor, "active_weapon", legacy)
    except Exception:
        pass

    loadout = []
    for item in inventory:
        if not _is_weapon(item):
            continue
        weapon_id = normalize_weapon_id(getattr(item, "item_id", None))
        if weapon_id and weapon_id not in loadout:
            loadout.append(weapon_id)
    if loadout:
        try:
            setattr(actor, "weapon_loadout", loadout)
        except Exception:
            pass


def get_equipped_weapons(actor) -> list[object]:
    ensure_actor_inventory(actor)
    weapons = _weapon_map(actor)
    equipped_ids = list(getattr(actor, "equipped_weapon_item_ids", []) or [])
    result = [weapons[iid] for iid in equipped_ids if iid in weapons]
    return result


def set_equipped_weapons(actor, weapons: list[object]) -> None:
    ensure_actor_inventory(actor)
    ids: list[str] = []
    allowed = _weapon_map(actor)
    for item in weapons:
        iid = _item_instance_id(item)
        if iid in allowed and iid not in ids:
            ids.append(iid)
    try:
        setattr(actor, "equipped_weapon_item_ids", ids)
    except Exception:
        pass
    _enforce_hand_limits(actor)
    _sync_legacy_weapon_attrs(actor)


def _enforce_hand_limits(actor) -> None:
    equipped = get_equipped_weapons(actor)
    if not equipped:
        return
    zero_h = [item for item in equipped if _weapon_hands(item) <= 0]
    two_h = [item for item in equipped if _weapon_hands(item) >= 2]
    if two_h:
        chosen = two_h[0]
        try:
            setattr(actor, "equipped_weapon_item_ids", [_item_instance_id(item) for item in (zero_h + [chosen])])
        except Exception:
            pass
        if getattr(actor, "equipped_shield", None) is not None:
            try:
                setattr(actor, "equipped_shield", None)
            except Exception:
                pass
        return
    one_h = [item for item in equipped if _weapon_hands(item) == 1]
    shield_active = getattr(actor, "equipped_shield", None) is not None
    limit = 1 if shield_active else 2
    if len(one_h) > limit:
        one_h = one_h[:limit]
        try:
            setattr(actor, "equipped_weapon_item_ids", [_item_instance_id(item) for item in (zero_h + one_h)])
        except Exception:
            pass


def all_inventory_sections(actor) -> list[tuple[str, list[object]]]:
    grouped: dict[str, list[object]] = defaultdict(list)
    for item in ensure_actor_inventory(actor):
        grouped[_item_category(item)].append(item)
    sections: list[tuple[str, list[object]]] = []
    for category in sorted(grouped.keys(), key=_sort_categories):
        entries = sorted(grouped[category], key=lambda item: _sort_items(actor, item))
        sections.append((category, entries))
    return sections


def is_item_active(actor, item) -> bool:
    category = _item_category(item)
    if category == "weapon":
        active_ids = set(str(iid) for iid in getattr(actor, "equipped_weapon_item_ids", []) or [])
        return _item_instance_id(item) in active_ids
    if category == "shield":
        return getattr(actor, "equipped_shield", None) is item
    if category == "armor":
        return str(getattr(actor, "equipped_armor_item_id", "") or "") == _item_instance_id(item)
    return False


def _weapon_hands(item) -> int:
    traits = {
        str(tag or "").strip().lower().replace("-", "_").replace(" ", "_")
        for tag in (getattr(item, "traits", None) or ())
    }
    if "free_hand" in traits:
        return 0
    try:
        hands = int(getattr(item, "hands_required", 1) or 1)
    except Exception:
        hands = 1
    return 2 if hands >= 2 else 1


def _active_hands_cost(actor, *, exclude_item_id: str | None = None) -> int:
    hands = 0
    for weapon in get_equipped_weapons(actor):
        if exclude_item_id and _item_instance_id(weapon) == exclude_item_id:
            continue
        hands += _weapon_hands(weapon)
    if getattr(actor, "equipped_shield", None) is not None:
        hands += 1
    return hands


def _hands_cost_for_items(actor, items: list[object]) -> int:
    """Koszt rąk dla podanej listy aktywnych broni + ewentualnej tarczy aktora."""
    hands = sum(_weapon_hands(item) for item in list(items or []))
    if getattr(actor, "equipped_shield", None) is not None:
        hands += 1
    return int(hands)


def _current_slots(actor) -> dict[str, tuple[str, object] | None]:
    """Bieżąca okupacja slotów rąk (bez broni free_hand)."""
    slots: dict[str, tuple[str, object] | None] = {
        _HAND_LEFT: None,
        _HAND_RIGHT: None,
    }
    shield = getattr(actor, "equipped_shield", None)
    if shield is not None:
        slots[_shield_hand(actor)] = (_HAND_SHIELD_MARKER, shield)

    one_h = [item for item in get_equipped_weapons(actor) if _weapon_hands(item) == 1]
    for weapon in one_h:
        for hand in (_HAND_LEFT, _HAND_RIGHT):
            if slots[hand] is None:
                slots[hand] = ("weapon", weapon)
                break
    return slots


def _commit_slots(actor, slots: dict[str, tuple[str, object] | None], *, zero_h_weapons: list[object] | None = None) -> None:
    """Zapisuje sloty do stanu aktora, dbając o zgodność z istniejącą logiką ekwipunku."""
    if zero_h_weapons is None:
        zero_h_weapons = [item for item in get_equipped_weapons(actor) if _weapon_hands(item) <= 0]
    shield = None
    shield_hand = _HAND_RIGHT
    one_h_weapons: list[object] = []

    for hand in (_HAND_LEFT, _HAND_RIGHT):
        payload = slots.get(hand)
        if not payload:
            continue
        kind, item = payload
        if kind == _HAND_SHIELD_MARKER:
            shield = item
            shield_hand = hand
            continue
        if kind == "weapon":
            one_h_weapons.append(item)

    try:
        setattr(actor, "equipped_shield", shield)
    except Exception:
        pass
    _set_shield_hand(actor, shield_hand)

    merged: list[object] = []
    for item in list(one_h_weapons) + list(zero_h_weapons or []):
        if item not in merged:
            merged.append(item)
    set_equipped_weapons(actor, merged)


def toggle_item_activation(actor, item) -> tuple[bool, str]:
    ensure_actor_inventory(actor)
    category = _item_category(item)
    if category == "weapon":
        return _toggle_weapon(actor, item)
    if category == "shield":
        return _toggle_shield(actor, item)
    if category == "armor":
        return _toggle_armor(actor, item)
    event_name = _normalize_event_name(getattr(item, "event_name", ""))
    if event_name:
        event_label = localize_term_pl(event_name)
        route = "Alchemia" if isinstance(item, AlchemicalItem) else "Specjalne/Magia"
        prep_counter = max(0, int(getattr(item, "preparation_counter", 0) or 0))
        if prep_counter > 0:
            readiness = f"Przedmiot nie jest jeszcze gotowy ({prep_counter} tur przygotowania)."
        else:
            readiness = "Przedmiot jest gotowy."
        return (
            False,
            f"{_item_label(item)}: użyj przez Akcje -> {route} -> {event_label} (event: {event_name}). {readiness}",
        )
    return False, f"{_item_label(item)}: tej kategorii nie da się aktywować."


def _toggle_weapon(actor, weapon) -> tuple[bool, str]:
    equipped = get_equipped_weapons(actor)
    weapon_id = _item_instance_id(weapon)
    is_active = any(_item_instance_id(item) == weapon_id for item in equipped)
    if is_active:
        equipped = [item for item in equipped if _item_instance_id(item) != weapon_id]
        set_equipped_weapons(actor, equipped)
        return True, f"Dezaktywowano broń: {_item_label(weapon)}."

    hands = _weapon_hands(weapon)
    if hands >= 2:
        # 2H resetuje bronie jednoręczne i tarczę.
        set_equipped_weapons(actor, [weapon])
        if getattr(actor, "equipped_shield", None) is not None:
            try:
                setattr(actor, "equipped_shield", None)
            except Exception:
                pass
        return True, f"Aktywowano broń 2H: {_item_label(weapon)}."

    # Aktywacja 1H: zdejmij ewentualną broń 2H.
    equipped = [item for item in equipped if _weapon_hands(item) < 2]
    # Uwaga: liczymy ręce z lokalnego stanu po zdjęciu 2H, a nie ze starego stanu aktora.
    used_hands = _hands_cost_for_items(actor, equipped)
    if used_hands >= 2:
        return False, "Brak wolnej ręki na kolejną broń 1H."
    one_h_count = sum(1 for item in equipped if _weapon_hands(item) == 1)
    if one_h_count >= 2:
        return False, "Masz już aktywne dwie bronie 1H."
    equipped.append(weapon)
    set_equipped_weapons(actor, equipped)
    return True, f"Aktywowano broń: {_item_label(weapon)}."


def _toggle_shield(actor, shield) -> tuple[bool, str]:
    current = getattr(actor, "equipped_shield", None)
    if current is shield:
        try:
            setattr(actor, "equipped_shield", None)
        except Exception:
            return False, "Nie udało się dezaktywować tarczy."
        return True, f"Dezaktywowano tarczę: {_item_label(shield)}."

    for weapon in get_equipped_weapons(actor):
        if _weapon_hands(weapon) >= 2:
            return False, "Nie możesz aktywować tarczy z aktywną bronią 2H."
    if _active_hands_cost(actor) >= 2:
        return False, "Nie masz wolnej ręki na tarczę (dwie bronie 1H aktywne)."
    try:
        setattr(actor, "equipped_shield", shield)
        _set_shield_hand(actor, _HAND_RIGHT)
    except Exception:
        return False, "Nie udało się aktywować tarczy."
    return True, f"Aktywowano tarczę: {_item_label(shield)}."


def _toggle_armor(actor, armor) -> tuple[bool, str]:
    iid = _item_instance_id(armor)
    current = str(getattr(actor, "equipped_armor_item_id", "") or "")
    if current == iid:
        try:
            setattr(actor, "equipped_armor_item_id", None)
        except Exception:
            return False, "Nie udało się zdjąć pancerza."
        _refresh_actor_ac(actor)
        return True, f"Zdjęto pancerz: {_item_label(armor)}."
    try:
        setattr(actor, "equipped_armor_item_id", iid)
    except Exception:
        return False, "Nie udało się założyć pancerza."
    _refresh_actor_ac(actor)
    return True, f"Założono pancerz: {_item_label(armor)}."


def assign_item_to_hand(actor, item, hand: str) -> tuple[bool, str]:
    """Przypisz przedmiot do konkretnej ręki (lewa/prawa), jeśli to możliwe."""
    ensure_actor_inventory(actor)
    target_hand = _normalize_hand(hand)
    other = _other_hand(target_hand)
    category = _item_category(item)

    if category not in {"weapon", "shield"}:
        return False, f"{_item_label(item)}: ten przedmiot nie zajmuje slotu ręki."

    equipped = get_equipped_weapons(actor)
    zero_h = [weapon for weapon in equipped if _weapon_hands(weapon) <= 0]
    two_h = [weapon for weapon in equipped if _weapon_hands(weapon) >= 2]
    slots = _current_slots(actor)

    if category == "shield":
        if two_h:
            return False, "Nie możesz aktywować tarczy z aktywną bronią 2H."
        if getattr(actor, "equipped_shield", None) is not item:
            try:
                setattr(actor, "equipped_shield", item)
            except Exception:
                return False, "Nie udało się aktywować tarczy."
        # Usuń tarczę z obu slotów i przypnij w nowym.
        for h in (_HAND_LEFT, _HAND_RIGHT):
            payload = slots.get(h)
            if payload and payload[0] == _HAND_SHIELD_MARKER:
                slots[h] = None
        # Zajęty slot -> spróbuj przesunąć occupant na drugą rękę.
        occupied = slots.get(target_hand)
        if occupied is not None:
            if slots.get(other) is None:
                slots[other] = occupied
            else:
                slots[target_hand] = None
        slots[target_hand] = (_HAND_SHIELD_MARKER, item)
        _commit_slots(actor, slots, zero_h_weapons=zero_h)
        hand_label = "lewą" if target_hand == _HAND_LEFT else "prawą"
        return True, f"Przypięto tarczę '{_item_label(item)}' na {hand_label} rękę."

    hands = _weapon_hands(item)
    if hands <= 0:
        # Broń free-hand: tylko aktywacja/dezaktywacja, bez slotu.
        return _toggle_weapon(actor, item)
    if hands >= 2:
        set_equipped_weapons(actor, [item] + list(zero_h))
        if getattr(actor, "equipped_shield", None) is not None:
            try:
                setattr(actor, "equipped_shield", None)
            except Exception:
                pass
        _set_shield_hand(actor, _HAND_RIGHT)
        return True, f"Aktywowano broń 2H: {_item_label(item)}."

    # Jednoręczna broń: przestaw item na konkretną rękę.
    if any(_weapon_hands(wpn) >= 2 for wpn in equipped):
        equipped = [wpn for wpn in equipped if _weapon_hands(wpn) <= 0]
        set_equipped_weapons(actor, equipped)
        slots = _current_slots(actor)

    # Usuń z obu slotów starą pozycję tej broni.
    for h in (_HAND_LEFT, _HAND_RIGHT):
        payload = slots.get(h)
        if payload and payload[0] == "weapon" and payload[1] is item:
            slots[h] = None

    occupied = slots.get(target_hand)
    if occupied is not None:
        if slots.get(other) is None:
            slots[other] = occupied
        elif occupied[0] == "weapon":
            slots[target_hand] = None
        else:
            # Tarcza na obu rękach zajęta + broń 1H -> brak miejsca.
            return False, "Brak miejsca na broń 1H (oba sloty zajęte)."

    slots[target_hand] = ("weapon", item)
    _commit_slots(actor, slots, zero_h_weapons=zero_h)
    hand_label = "lewą" if target_hand == _HAND_LEFT else "prawą"
    return True, f"Przypięto broń '{_item_label(item)}' na {hand_label} rękę."


def hand_slots_snapshot(actor) -> dict[str, object]:
    """Zwraca czytelny snapshot zajętości rąk aktora dla UI i debugowania."""
    ensure_actor_inventory(actor)

    left = _empty_hand_slot()
    right = _empty_hand_slot()
    shield = getattr(actor, "equipped_shield", None)
    equipped = list(get_equipped_weapons(actor))
    zero_h = [item for item in equipped if _weapon_hands(item) <= 0]
    one_h = [item for item in equipped if _weapon_hands(item) == 1]
    two_h = [item for item in equipped if _weapon_hands(item) >= 2]

    mode = "unarmed"
    mode_label = "Bez broni"

    if two_h:
        primary = two_h[0]
        payload = _weapon_slot_payload(primary)
        left = dict(payload)
        right = dict(payload)
        mode = "two_handed"
        mode_label = "Broń dwuręczna"
    else:
        slots = _current_slots(actor)
        left_payload = slots.get(_HAND_LEFT)
        right_payload = slots.get(_HAND_RIGHT)
        if left_payload and left_payload[0] == "weapon":
            left = _weapon_slot_payload(left_payload[1])
        elif left_payload and left_payload[0] == _HAND_SHIELD_MARKER:
            left = _shield_slot_payload(left_payload[1])

        if right_payload and right_payload[0] == "weapon":
            right = _weapon_slot_payload(right_payload[1])
        elif right_payload and right_payload[0] == _HAND_SHIELD_MARKER:
            right = _shield_slot_payload(right_payload[1])

        left_kind = str(left.get("kind", "empty"))
        right_kind = str(right.get("kind", "empty"))
        if left_kind == "weapon" and right_kind == "weapon":
            mode = "dual_wield"
            mode_label = "Dwie bronie 1R"
        elif "shield" in {left_kind, right_kind} and "weapon" in {left_kind, right_kind}:
            mode = "weapon_and_shield"
            mode_label = "Broń 1R + tarcza"
        elif left_kind == "shield" or right_kind == "shield":
            mode = "shield_only"
            mode_label = "Tarcza"
        elif left_kind == "weapon" or right_kind == "weapon":
            mode = "single_weapon"
            mode_label = "Jedna broń 1R"

    if mode == "unarmed" and zero_h:
        mode = "free_hand_weapon"
        mode_label = "Broń wolnej ręki"
    if mode != "two_handed" and mode != "dual_wield" and shield is None and len(one_h) >= 2:
        mode = "dual_wield"
        mode_label = "Dwie bronie 1R"

    free_hands = 0
    for slot in (left, right):
        if str(slot.get("kind", "")) == "empty":
            free_hands += 1

    active_weapon_labels = [_item_label(item) for item in equipped]
    active_free_hand_labels = [_item_label(item) for item in zero_h]
    shield_label = _item_label(shield) if shield is not None else None

    return {
        _HAND_LEFT: left,
        _HAND_RIGHT: right,
        "mode": mode,
        "mode_label": mode_label,
        "free_hands": int(free_hands),
        "active_weapons": active_weapon_labels,
        "active_free_hand_weapons": active_free_hand_labels,
        "active_shield": shield_label,
    }


def inventory_index_of(actor, item) -> int:
    inventory = ensure_actor_inventory(actor)
    for idx, current in enumerate(inventory):
        if current is item:
            return idx
    return -1


def remove_item(actor, item) -> bool:
    inventory = ensure_actor_inventory(actor)
    if item not in inventory:
        return False
    _deactivate_item_before_move(actor, item)
    inventory.remove(item)
    try:
        setattr(actor, "inventory", inventory)
    except Exception:
        pass
    _sync_legacy_weapon_attrs(actor)
    _refresh_bulk(actor, inventory=inventory)
    return True


def count_ammo(actor, ammo_item_id: str) -> int:
    ammo_id = str(ammo_item_id or "").strip().lower()
    if not ammo_id:
        return 0
    total = 0
    for item in ensure_actor_inventory(actor):
        if _item_id(item) != ammo_id:
            continue
        if not _is_ammo_item(item):
            continue
        total += _ammo_count(item)
    return max(0, int(total))


def consume_ammo(actor, ammo_item_id: str, *, amount: int = 1) -> tuple[bool, str]:
    ammo_id = str(ammo_item_id or "").strip().lower()
    to_spend = max(0, int(amount or 0))
    if not ammo_id or to_spend <= 0:
        return True, ""
    inventory = ensure_actor_inventory(actor)
    available = count_ammo(actor, ammo_id)
    if available < to_spend:
        return False, f"Brak amunicji: {ammo_id} ({available}/{to_spend})."

    for item in list(inventory):
        if to_spend <= 0:
            break
        if _item_id(item) != ammo_id or not _is_ammo_item(item):
            continue
        stack = _ammo_count(item)
        if stack <= 0:
            continue
        use_now = min(stack, to_spend)
        left = stack - use_now
        to_spend -= use_now
        if left <= 0:
            try:
                inventory.remove(item)
            except ValueError:
                pass
        else:
            _set_ammo_count(item, left)
    try:
        setattr(actor, "inventory", inventory)
    except Exception:
        pass
    _sync_legacy_weapon_attrs(actor)
    _refresh_bulk(actor, inventory=inventory)
    left_after = count_ammo(actor, ammo_id)
    return True, f"Zuzyto amunicje: {ammo_id} (pozostalo: {left_after})."


def consume_ammo_for_weapon(actor, weapon, *, amount: int = 1) -> tuple[bool, str]:
    ammo_id = _weapon_ammo_id(weapon)
    if not ammo_id:
        return True, ""
    ok, msg = consume_ammo(actor, ammo_id, amount=amount)
    if ok:
        return True, msg
    label = weapon_ammo_label(weapon) or ammo_id
    available = count_ammo(actor, ammo_id)
    needed = max(1, int(amount or 1))
    return False, f"Brak amunicji do {item_label(weapon)}: {label} ({available}/{needed})."


def add_item(actor, item) -> None:
    inventory = ensure_actor_inventory(actor)
    if _is_ammo_item(item):
        incoming_count = _ammo_count(item)
        for current in inventory:
            if current is item:
                continue
            if _item_id(current) != _item_id(item):
                continue
            if not _is_ammo_item(current):
                continue
            _set_ammo_count(current, _ammo_count(current) + incoming_count)
            try:
                setattr(actor, "inventory", inventory)
            except Exception:
                pass
            _sync_legacy_weapon_attrs(actor)
            _refresh_bulk(actor, inventory=inventory)
            return
    if item not in inventory:
        inventory.append(item)
    if _is_ammo_item(item):
        _set_ammo_count(item, _ammo_count(item))
    try:
        setattr(actor, "inventory", inventory)
    except Exception:
        pass
    _sync_legacy_weapon_attrs(actor)
    _refresh_bulk(actor, inventory=inventory)


def transfer_item(source_actor, target_actor, item) -> tuple[bool, str]:
    if source_actor is None or target_actor is None:
        return False, "Brak źródła lub celu przekazania."
    if not remove_item(source_actor, item):
        return False, "Nie udało się zdjąć przedmiotu ze źródła."
    add_item(target_actor, item)
    _refresh_bulk(source_actor)
    _refresh_bulk(target_actor)
    return True, f"Przekazano {_item_label(item)} do {getattr(target_actor, 'name', 'bohatera')}."


def _deactivate_item_before_move(actor, item) -> None:
    category = _item_category(item)
    if category == "weapon":
        equipped = [w for w in get_equipped_weapons(actor) if w is not item]
        set_equipped_weapons(actor, equipped)
        return
    if category == "shield":
        if getattr(actor, "equipped_shield", None) is item:
            try:
                setattr(actor, "equipped_shield", None)
            except Exception:
                pass
        return
    if category == "armor":
        iid = _item_instance_id(item)
        if str(getattr(actor, "equipped_armor_item_id", "") or "") == iid:
            try:
                setattr(actor, "equipped_armor_item_id", None)
            except Exception:
                pass
            _refresh_actor_ac(actor)


def item_use_description(item) -> str:
    """Techniczny skrót akcji użycia przedmiotu (do podglądu w UI)."""
    category = _item_category(item)
    if category == "weapon":
        is_ranged = bool(getattr(item, "ranged", False))
        distance_ft = int(getattr(item, "range_increment_ft", 0) or 0)
        attack_type = "atak dystansowy" if is_ranged else "atak wręcz"
        range_part = f", zasięg {distance_ft} stóp" if is_ranged and distance_ft > 0 else ""
        damage_prompt = str(getattr(item, "damage_prompt", "1k4") or "1k4")
        damage_type = str(getattr(item, "damage_type", "normalne") or "normalne")
        ammo_note = ""
        ammo_label = weapon_ammo_label(item)
        if ammo_label:
            ammo_note = f", wymaga amunicji: {ammo_label}"
        return f"Użyj: {attack_type}{range_part}{ammo_note}, obrażenia {damage_prompt} ({damage_type})."

    if category == "shield":
        ac_bonus = int(getattr(item, "ac_bonus", 0) or 0)
        hardness = int(getattr(item, "hardness", 0) or 0)
        hp = int(getattr(item, "current_hp", getattr(item, "max_hp", 0)) or 0)
        max_hp = int(getattr(item, "max_hp", hp) or hp)
        return (
            "Użyj: Raise Shield "
            f"(+{ac_bonus} AC) / Shield Block (Hardness {hardness}, HP tarczy {hp}/{max_hp})."
        )

    item_id = str(getattr(item, "item_id", "") or "").strip().lower()
    if item_id in {"healer_tools"}:
        return "Uzyj: narzedzie wymagane do Battle Medicine i Treat Wounds."
    if item_id in {"thieves_tools"}:
        return "Uzyj: narzedzie do akcji Disable Device i otwierania zamkow."
    if item_id in {"repair_kit"}:
        return "Uzyj: narzedzie do akcji Repair (naprawa przedmiotow)."
    if item_id in {"torch"}:
        return "Uzyj: Interact (zapalenie). Swiatlo terenowe, zuzywalne."
    if item_id in {"lantern_hooded", "lantern_bullseye"}:
        return "Uzyj: Interact (zapalenie/zgaszenie). Wymaga oleju."
    if item_id in {"oil_flask"}:
        return "Uzyj: paliwo do latarni lub pochodni (zuzywalne)."
    if _is_ammo_item(item):
        return f"Amunicja: {_ammo_count(item)} szt. w tym stacku."

    event_name = str(getattr(item, "event_name", "") or "").strip()
    if event_name:
        from GameObjects.events.registry import get_event_cls

        try:
            event_cls = get_event_cls(event_name)
        except Exception:
            event_cls = None
        if event_cls is not None:
            range_feet = int(getattr(event_cls, "range_feet", 0) or 0)
            prompt_desc = str(getattr(event_cls, "prompt_description", "") or "").strip()
            one_line_desc = " ".join(line.strip() for line in prompt_desc.splitlines() if line.strip())
            if len(one_line_desc) > 220:
                one_line_desc = one_line_desc[:217] + "..."
            route = "Alchemia" if isinstance(item, AlchemicalItem) else "Specjalne/Magia"
            event_label = localize_term_pl(event_name)
            prep_counter = max(0, int(getattr(item, "preparation_counter", 0) or 0))
            ready_note = (
                "Gotowe do użycia."
                if prep_counter <= 0
                else f"Gotowe za {prep_counter} tur."
            )
            range_part = f", zasięg {range_feet} stóp" if range_feet > 0 else ""
            if one_line_desc:
                return f"Użyj: Akcje -> {route} -> {event_label}{range_part}. {ready_note} {one_line_desc}"
            return f"Użyj: Akcje -> {route} -> {event_label}{range_part}. {ready_note}"

    if item_id == "goodberry":
        return "Użyj: zjedz Goodberry, leczenie 1k6+4 HP (zużywa przedmiot)."

    return "Użyj: brak bezpośredniej akcji z ekwipunku (aktywacja opisowa)."


def item_description(item) -> str:
    formatter = getattr(item, "ui_description", None)
    if callable(formatter):
        try:
            base_desc = str(formatter())
            use_desc = item_use_description(item)
            if use_desc and use_desc not in base_desc:
                return f"{use_desc}\n{base_desc}"
            return base_desc
        except Exception:
            pass
    desc = str(getattr(item, "description", "") or "").strip()
    use_desc = item_use_description(item)
    if use_desc and desc:
        return f"{use_desc}\n{desc}"
    if use_desc:
        return use_desc
    if desc:
        return desc
    return _item_label(item)


def item_label(item) -> str:
    return _item_label(item)


def item_category(item) -> str:
    return _item_category(item)


def add_alchemical_item(
    actor,
    *,
    event_name: str,
    alchemical_tier: str | None = None,
    preparation_counter: int = 0,
    prepared_by_quick_alchemy: bool = False,
    prepared_by_advanced_alchemy: bool = False,
) -> object:
    inventory = ensure_actor_inventory(actor)
    raw_event = str(event_name or "").strip().lower().replace("-", "_").replace(" ", "_")
    normalized_event = normalize_alchemical_event_id(event_name)
    resolved_tier = str(alchemical_tier or "").strip().lower().replace("-", "_").replace(" ", "_")
    if resolved_tier not in {"lesser", "moderate", "greater", "major"}:
        if "moderate" in raw_event:
            resolved_tier = "moderate"
        elif "greater" in raw_event:
            resolved_tier = "greater"
        elif "major" in raw_event:
            resolved_tier = "major"
        else:
            resolved_tier = "lesser"
    defaults = alchemical_item_defaults(normalized_event)
    item = AlchemicalItem(
        item_id=f"alchemical:{normalized_event}",
        name=alchemical_item_name_from_event(normalized_event),
        event_name=str(normalized_event),
        alchemical_tier=resolved_tier,
        preparation_counter=max(0, int(preparation_counter or 0)),
        prepared_by_quick_alchemy=bool(prepared_by_quick_alchemy),
        prepared_by_advanced_alchemy=bool(prepared_by_advanced_alchemy),
        price_cp=max(0, int(defaults.get("price_cp", 0) or 0)),
        bulk=defaults.get("bulk", "L"),
    )
    inventory.append(item)
    try:
        setattr(actor, "inventory", inventory)
    except Exception:
        pass
    return item


def _alchemical_items_for_event(actor, event_name: str) -> list[object]:
    event_key = normalize_alchemical_event_id(event_name)
    if not event_key:
        return []
    items: list[object] = []
    for item in ensure_actor_inventory(actor):
        if not isinstance(item, AlchemicalItem):
            continue
        item_event = normalize_alchemical_event_id(getattr(item, "event_name", ""))
        if item_event != event_key:
            continue
        items.append(item)
    return items


def _items_for_event(actor, event_name: str) -> list[object]:
    event_key = _normalize_event_name(event_name)
    if not event_key:
        return []
    items: list[object] = []
    for item in ensure_actor_inventory(actor):
        item_event = _normalize_event_name(getattr(item, "event_name", ""))
        if item_event != event_key:
            continue
        items.append(item)
    return items


def ready_event_items(actor, event_name: str) -> list[object]:
    ready: list[object] = []
    for item in _items_for_event(actor, event_name):
        if int(getattr(item, "preparation_counter", 0) or 0) > 0:
            continue
        ready.append(item)
    return ready


def has_ready_event_item(actor, event_name: str) -> bool:
    for item in _items_for_event(actor, event_name):
        if int(getattr(item, "preparation_counter", 0) or 0) <= 0:
            return True
    return False


def missing_event_item_reason(actor, event_name: str) -> str:
    event_key = _normalize_event_name(event_name)
    if not event_key:
        return "Brak poprawnego event_name przedmiotu."
    items = _items_for_event(actor, event_key)
    if not items:
        return f"Brak przedmiotu do akcji '{event_key}' w ekwipunku."
    min_counter = min(max(0, int(getattr(item, "preparation_counter", 0) or 0)) for item in items)
    if min_counter > 0:
        return f"Przedmiot '{event_key}' nie jest jeszcze gotowy (pozostało tur: {min_counter})."
    return f"Brak gotowego przedmiotu dla akcji '{event_key}'."


def consume_ready_event_item(actor, event_name: str) -> bool:
    inventory = ensure_actor_inventory(actor)
    event_key = _normalize_event_name(event_name)
    if not event_key:
        return False
    for item in list(inventory):
        item_event = _normalize_event_name(getattr(item, "event_name", ""))
        if item_event != event_key:
            continue
        if int(getattr(item, "preparation_counter", 0) or 0) > 0:
            continue
        inventory.remove(item)
        try:
            setattr(actor, "inventory", inventory)
        except Exception:
            pass
        _refresh_bulk(actor, inventory=inventory)
        return True
    return False


def consume_item_instance(actor, item) -> bool:
    inventory = ensure_actor_inventory(actor)
    if item not in inventory:
        return False
    inventory.remove(item)
    try:
        setattr(actor, "inventory", inventory)
    except Exception:
        pass
    _refresh_bulk(actor, inventory=inventory)
    return True


def has_ready_alchemical_item(actor, event_name: str) -> bool:
    for item in _alchemical_items_for_event(actor, event_name):
        if int(getattr(item, "preparation_counter", 0) or 0) <= 0:
            return True
    return False


def missing_alchemical_item_reason(actor, event_name: str) -> str:
    items = _alchemical_items_for_event(actor, event_name)
    if not items:
        return f"Brak przedmiotu alchemicznego '{event_name}' w ekwipunku."
    min_counter = min(max(0, int(getattr(item, "preparation_counter", 0) or 0)) for item in items)
    if min_counter > 0:
        return (
            f"Przedmiot alchemiczny '{event_name}' nie jest jeszcze gotowy "
            f"(pozostało tur: {min_counter})."
        )
    return f"Brak gotowego przedmiotu alchemicznego '{event_name}'."


def consume_ready_alchemical_item(actor, event_name: str) -> bool:
    return consume_ready_event_item(actor, normalize_alchemical_event_id(event_name))


def tick_alchemical_preparation(actor) -> int:
    changed = 0
    inventory = ensure_actor_inventory(actor)
    for item in inventory:
        if not isinstance(item, AlchemicalItem):
            continue
        current = max(0, int(getattr(item, "preparation_counter", 0) or 0))
        if current <= 0:
            continue
        try:
            setattr(item, "preparation_counter", current - 1)
            changed += 1
        except Exception:
            continue
    return changed


__all__ = [
    "add_alchemical_item",
    "add_item",
    "all_inventory_sections",
    "assign_item_to_hand",
    "consume_ammo",
    "consume_ammo_for_weapon",
    "consume_ready_event_item",
    "consume_item_instance",
    "consume_ready_alchemical_item",
    "count_ammo",
    "default_weapon_ids_for_actor",
    "ensure_actor_inventory",
    "get_equipped_weapons",
    "hand_slots_snapshot",
    "has_ready_alchemical_item",
    "has_ready_event_item",
    "inventory_index_of",
    "is_item_active",
    "item_category",
    "item_description",
    "item_label",
    "item_use_description",
    "missing_alchemical_item_reason",
    "missing_event_item_reason",
    "ready_event_items",
    "remove_item",
    "set_equipped_weapons",
    "tick_alchemical_preparation",
    "toggle_item_activation",
    "transfer_item",
    "weapon_ammo_label",
]
