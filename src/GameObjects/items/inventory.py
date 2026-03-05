from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from GameObjects.items.alchemical_item import AlchemicalItem, alchemical_item_name_from_event
from GameObjects.items.armor import create_armor, normalize_armor_id
from GameObjects.items.base_item import BaseItem
from GameObjects.items.shield import create_shield, normalize_shield_id
from GameObjects.items.weapon import BaseWeapon, create_weapon, normalize_weapon_id


_DEFAULT_WEAPON_IDS: tuple[str, ...] = ("sword", "dagger", "longbow", "unarmed")
_CATEGORY_PRIORITY: dict[str, int] = {
    "weapon": 0,
    "shield": 1,
    "armor": 2,
    "potion": 3,
}


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


def toggle_item_activation(actor, item) -> tuple[bool, str]:
    ensure_actor_inventory(actor)
    category = _item_category(item)
    if category == "weapon":
        return _toggle_weapon(actor, item)
    if category == "shield":
        return _toggle_shield(actor, item)
    if category == "armor":
        return _toggle_armor(actor, item)
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
    used_hands = _active_hands_cost(actor)
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
        return True, f"Zdjęto pancerz: {_item_label(armor)}."
    try:
        setattr(actor, "equipped_armor_item_id", iid)
    except Exception:
        return False, "Nie udało się założyć pancerza."
    return True, f"Założono pancerz: {_item_label(armor)}."


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
    return True


def add_item(actor, item) -> None:
    inventory = ensure_actor_inventory(actor)
    if item not in inventory:
        inventory.append(item)
    try:
        setattr(actor, "inventory", inventory)
    except Exception:
        pass
    _sync_legacy_weapon_attrs(actor)


def transfer_item(source_actor, target_actor, item) -> tuple[bool, str]:
    if source_actor is None or target_actor is None:
        return False, "Brak źródła lub celu przekazania."
    if not remove_item(source_actor, item):
        return False, "Nie udało się zdjąć przedmiotu ze źródła."
    add_item(target_actor, item)
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


def item_description(item) -> str:
    formatter = getattr(item, "ui_description", None)
    if callable(formatter):
        try:
            return str(formatter())
        except Exception:
            pass
    desc = str(getattr(item, "description", "") or "").strip()
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
    preparation_counter: int = 0,
    prepared_by_quick_alchemy: bool = False,
    prepared_by_advanced_alchemy: bool = False,
) -> object:
    inventory = ensure_actor_inventory(actor)
    item = AlchemicalItem(
        item_id=f"alchemical:{event_name}",
        name=alchemical_item_name_from_event(event_name),
        event_name=str(event_name),
        preparation_counter=max(0, int(preparation_counter or 0)),
        prepared_by_quick_alchemy=bool(prepared_by_quick_alchemy),
        prepared_by_advanced_alchemy=bool(prepared_by_advanced_alchemy),
    )
    inventory.append(item)
    try:
        setattr(actor, "inventory", inventory)
    except Exception:
        pass
    return item


def _alchemical_items_for_event(actor, event_name: str) -> list[object]:
    event_key = str(event_name or "").strip().lower()
    if not event_key:
        return []
    items: list[object] = []
    for item in ensure_actor_inventory(actor):
        if not isinstance(item, AlchemicalItem):
            continue
        if str(getattr(item, "event_name", "") or "").strip().lower() != event_key:
            continue
        items.append(item)
    return items


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
    inventory = ensure_actor_inventory(actor)
    event_key = str(event_name or "").strip().lower()
    for item in list(inventory):
        if not isinstance(item, AlchemicalItem):
            continue
        if str(getattr(item, "event_name", "") or "").strip().lower() != event_key:
            continue
        if int(getattr(item, "preparation_counter", 0) or 0) > 0:
            continue
        inventory.remove(item)
        try:
            setattr(actor, "inventory", inventory)
        except Exception:
            pass
        return True
    return False


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
    "consume_ready_alchemical_item",
    "default_weapon_ids_for_actor",
    "ensure_actor_inventory",
    "get_equipped_weapons",
    "has_ready_alchemical_item",
    "inventory_index_of",
    "is_item_active",
    "item_category",
    "item_description",
    "item_label",
    "missing_alchemical_item_reason",
    "remove_item",
    "set_equipped_weapons",
    "tick_alchemical_preparation",
    "toggle_item_activation",
    "transfer_item",
]
