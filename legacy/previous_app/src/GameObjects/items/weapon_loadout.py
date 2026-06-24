from __future__ import annotations

from GameObjects.items.inventory import (
    ensure_actor_inventory,
    get_equipped_weapons,
    item_label,
    set_equipped_weapons,
)
from GameObjects.items.weapon import create_weapon, normalize_weapon_id


def default_weapons_for_actor(actor) -> list[str]:
    ensure_actor_inventory(actor)
    return list(getattr(actor, "weapon_loadout", []) or [])


def available_weapons_for_actor(actor) -> list[str]:
    ensure_actor_inventory(actor)
    return list(getattr(actor, "weapon_loadout", []) or [])


def get_equipped_weapon_items(actor) -> list[object]:
    return get_equipped_weapons(actor)


def get_active_weapon(actor, *, ensure_default: bool = True) -> str | None:
    ensure_actor_inventory(actor)
    equipped = get_equipped_weapons(actor)
    if equipped:
        return normalize_weapon_id(getattr(equipped[0], "item_id", None))
    if not ensure_default:
        return None
    # Aktywuj domyślną broń 1:1 ze starym kontraktem.
    loadout = list(getattr(actor, "weapon_loadout", []) or [])
    for weapon_id in loadout:
        if set_active_weapon(actor, weapon_id):
            return normalize_weapon_id(weapon_id)
    return None


def set_active_weapon(actor, weapon_id: object) -> bool:
    ensure_actor_inventory(actor)
    normalized = normalize_weapon_id(weapon_id)
    if not normalized:
        return False
    inventory = list(getattr(actor, "inventory", []) or [])
    selected = None
    for item in inventory:
        if normalize_weapon_id(getattr(item, "item_id", None)) == normalized:
            selected = item
            break
    if selected is None:
        created = create_weapon(normalized)
        if created is None:
            return False
        inventory.append(created)
        try:
            setattr(actor, "inventory", inventory)
        except Exception:
            pass
        selected = created
    set_equipped_weapons(actor, [selected])
    return True


def normalize_weapon_label(value: object) -> str | None:
    return normalize_weapon_id(value)


def weapon_label(weapon_id: object) -> str:
    normalized = normalize_weapon_id(weapon_id)
    if not normalized:
        return str(weapon_id or "Weapon")
    probe = create_weapon(normalized)
    if probe is None:
        return normalized.replace("_", " ").title()
    return item_label(probe)


__all__ = [
    "available_weapons_for_actor",
    "default_weapons_for_actor",
    "get_active_weapon",
    "get_equipped_weapon_items",
    "normalize_weapon_id",
    "normalize_weapon_label",
    "set_active_weapon",
    "weapon_label",
]
