"""Starter equipment for rune adventures, without spare weapons."""
from __future__ import annotations

from dataclasses import replace

from dnd_board_game.actors import Actor


def basic_rune_loadout(actor: Actor) -> Actor:
    weapon = next((item for item in actor.inventory if item.kind == "weapon" and item.equipped), None)
    armor = next((item for item in actor.inventory if item.kind == "armor" and item.equipped), None)
    shield = next((item for item in actor.inventory if item.kind == "shield" and item.equipped), None)
    kept = {item.id for item in (weapon, armor, shield) if item is not None}
    ammunition = {"longbow": "arrow", "hand_crossbow": "crossbow_bolt", "crossbow": "crossbow_bolt"}.get(
        (weapon.source_ref or weapon.id) if weapon else "")
    inventory = tuple(
        replace(item, quantity=1) if item.kind in {"weapon", "armor", "shield", "focus"} else item
        for item in actor.inventory
        if (item.kind not in {"weapon", "armor", "shield"} or item.id in kept)
        and (item.kind != "ammunition" or (item.source_ref or item.id) == ammunition)
        and item.id != "small_knife"
    )
    return replace(actor, inventory=inventory)
