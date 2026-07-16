"""Attack-source variants derived from how a weapon can be held."""

from __future__ import annotations

import re
from dataclasses import replace
from typing import Sequence

from dnd_board_game.actors import Actor
from dnd_board_game.inventory import InventoryItem, free_hand_count, normalize_hand_equipment

from .attack_flow import AttackSource, AttackSourceType


VERSATILE_SOURCE_SUFFIX = ":two_handed"
_SINGLE_DAMAGE_DIE = re.compile(r"^1d([1-9][0-9]*)$")


def attack_sources_with_versatile_variants(
    actor: Actor,
    sources: Sequence[AttackSource],
    *,
    reserved_hands: int = 0,
) -> tuple[AttackSource, ...]:
    """Add a two-handed option for each currently legal versatile weapon source."""

    result: list[AttackSource] = []
    known_ids: set[str] = set()
    for source in sources:
        if source.id not in known_ids:
            result.append(source)
            known_ids.add(source.id)
        variant = versatile_two_handed_source(
            actor,
            source,
            reserved_hands=reserved_hands,
        )
        if variant is not None and variant.id not in known_ids:
            result.append(variant)
            known_ids.add(variant.id)
    return tuple(result)


def versatile_two_handed_source(
    actor: Actor,
    source: AttackSource,
    *,
    reserved_hands: int = 0,
) -> AttackSource | None:
    """Return the stronger damage option when the weapon and second hand allow it."""

    if source.source_type != AttackSourceType.WEAPON or source.id.endswith(VERSATILE_SOURCE_SUFFIX):
        return None
    item = _held_item_for_source(actor, source)
    if (
        item is None
        or item.versatile_damage_dice is None
        or len(item.held_in) != 1
        or free_hand_count(actor.inventory, reserved_hands=reserved_hands) < 1
    ):
        return None
    match = _SINGLE_DAMAGE_DIE.fullmatch(item.versatile_damage_dice.strip())
    if match is None:
        raise ValueError(
            f"Versatile damage for item {item.id} must use the supported 1dN format."
        )
    die_sides = int(match.group(1))
    damage_hint = _damage_hint(die_sides, source.damage_modifier, source.damage_type)
    return replace(
        source,
        id=f"{source.id}{VERSATILE_SOURCE_SUFFIX}",
        name=f"{source.name} (oburącz)",
        damage_fixed=None,
        damage_die_sides=die_sides,
        damage_hint=f"{damage_hint} (broń versatile trzymana oburącz)",
    )


def versatile_two_handed_source_is_legal(
    actor: Actor,
    source: AttackSource,
    *,
    reserved_hands: int = 0,
) -> bool:
    """Validate a previously selected two-handed variant against current hands."""

    if not source.id.endswith(VERSATILE_SOURCE_SUFFIX):
        return True
    item = _held_item_for_source(actor, source)
    if (
        item is None
        or item.versatile_damage_dice is None
        or len(item.held_in) != 1
        or free_hand_count(actor.inventory, reserved_hands=reserved_hands) < 1
    ):
        return False
    match = _SINGLE_DAMAGE_DIE.fullmatch(item.versatile_damage_dice.strip())
    return match is not None and source.damage_die_sides == int(match.group(1))


def _held_item_for_source(actor: Actor, source: AttackSource) -> InventoryItem | None:
    if source.source_item_id is None:
        return None
    return next(
        (
            item
            for item in normalize_hand_equipment(actor.inventory)
            if item.available
            and item.equipped
            and (item.id == source.source_item_id or item.source_ref == source.source_item_id)
        ),
        None,
    )


def _damage_hint(die_sides: int, modifier: int, damage_type: str) -> str:
    base = f"1d{die_sides}"
    if modifier > 0:
        base += f" + {modifier}"
    elif modifier < 0:
        base += f" - {abs(modifier)}"
    return f"{base} {damage_type}"


__all__ = [
    "VERSATILE_SOURCE_SUFFIX",
    "attack_sources_with_versatile_variants",
    "versatile_two_handed_source",
    "versatile_two_handed_source_is_legal",
]
