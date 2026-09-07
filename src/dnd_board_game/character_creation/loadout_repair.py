"""Repair the retired Mira starter package; preserve earned items and actor state."""

from dataclasses import replace
from functools import lru_cache
from pathlib import Path

from dnd_board_game.actors import Actor
from dnd_board_game.actors.resources import uses_physical_mana
from dnd_board_game.inventory import InventoryItem


@lru_cache(maxsize=1)
def _knife_template() -> InventoryItem:
    from .content import load_character_catalog, load_character_resources

    root = Path(__file__).resolve().parents[3]
    catalog = load_character_catalog(root / "content/character_creation/catalog.json")
    item = load_character_resources(catalog, root / "content").inventory_item("throwing_knife")
    assert item is not None
    return item


def repair_mira_loadout(actor: Actor) -> Actor:
    if str(actor.id) != "mira" or not uses_physical_mana(actor):
        return actor
    ids = {item.id for item in actor.inventory}
    # Only the identifiable obsolete starter package, never arbitrary looted bows.
    if not {"rapier", "shortbow", "arrow"} <= ids or any(
        item.source_ref == "throwing_knife" for item in actor.inventory
    ):
        return actor
    retired = {"shortbow", "arrow", "dagger", "dagger_1", "dagger_2", "dagger:1", "dagger:2"}
    inventory = tuple(item for item in actor.inventory if item.id not in retired)
    knives = tuple(
        replace(
            _knife_template(),
            id=f"throwing_knife:{i}",
            quantity=1,
            source_ref="throwing_knife",
            equipped=False,
            held_in=(),
        )
        for i in range(1, 5)
    )
    return replace(actor, inventory=(*inventory, *knives))
