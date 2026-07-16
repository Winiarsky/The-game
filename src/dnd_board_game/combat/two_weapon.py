"""D&D 5e 2014 two-weapon fighting eligibility and damage rules."""

from __future__ import annotations

from dataclasses import replace
from typing import Sequence

from dnd_board_game.actors import Actor
from dnd_board_game.inventory import InventoryItem, hands_required, normalize_hand_equipment
from dnd_board_game.rules import ability_modifier

from .attack_flow import AttackKind, AttackSource, AttackSourceType


def two_weapon_trigger_item_id(actor: Actor, source: AttackSource) -> str | None:
    item = _held_item_for_source(actor, source)
    return item.id if item is not None and _is_light_melee_source(item, source) else None


def eligible_two_weapon_bonus_sources(
    actor: Actor,
    trigger_item_id: str | None,
    sources: Sequence[AttackSource],
) -> tuple[AttackSource, ...]:
    if trigger_item_id is None:
        return ()
    items = normalize_hand_equipment(actor.inventory)
    trigger = next((item for item in items if item.id == trigger_item_id), None)
    if trigger is None or len(trigger.held_in) != 1 or not trigger.light_weapon:
        return ()
    trigger_slot = trigger.held_in[0]
    options: list[AttackSource] = []
    for source in sources:
        item = _held_item_for_source(actor, source)
        if (
            item is None
            or item.id == trigger.id
            or len(item.held_in) != 1
            or item.held_in[0] == trigger_slot
            or not _is_light_melee_source(item, source)
        ):
            continue
        if all(candidate.id != source.id for candidate in options):
            options.append(source)
    return tuple(options)


def two_weapon_bonus_source_is_legal(
    actor: Actor,
    trigger_item_id: str | None,
    source: AttackSource,
) -> bool:
    return any(
        candidate.id == source.id
        for candidate in eligible_two_weapon_bonus_sources(actor, trigger_item_id, (source,))
    )


def two_weapon_bonus_attack_source(actor: Actor, source: AttackSource) -> AttackSource:
    """Remove only a positive ability modifier from off-hand damage.

    Other configured bonuses remain part of the damage modifier. A negative
    ability modifier is already included in the source and must not be removed.
    """

    modifier = source.damage_modifier
    if source.ability is not None and modifier > 0:
        score = getattr(actor.ability_scores, source.ability)
        positive_ability_modifier = max(0, ability_modifier(score))
        modifier -= min(modifier, positive_ability_modifier)
    elif source.ability is None:
        # Older content can expose only a combined modifier. Without an
        # ability key we cannot prove that any positive part is non-ability.
        modifier = min(0, modifier)
    if source.damage_fixed is not None:
        base = str(source.damage_fixed)
    elif source.damage_die_sides is not None:
        base = f"1d{source.damage_die_sides}"
    else:
        base = "obrażenia"
    if modifier > 0:
        base = f"{base} + {modifier}"
    elif modifier < 0:
        base = f"{base} - {abs(modifier)}"
    hint = f"{base} {source.damage_type} (atak drugą bronią; bez dodatniego modyfikatora cechy)"
    return replace(source, damage_modifier=modifier, damage_hint=hint)


def _held_item_for_source(actor: Actor, source: AttackSource) -> InventoryItem | None:
    if source.source_type != AttackSourceType.WEAPON or source.source_item_id is None:
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


def _is_light_melee_source(item: InventoryItem, source: AttackSource) -> bool:
    return bool(
        item.light_weapon
        and hands_required(item) == 1
        and len(item.held_in) == 1
        and source.source_type == AttackSourceType.WEAPON
        and source.attack_kind == AttackKind.MELEE
    )


__all__ = [
    "eligible_two_weapon_bonus_sources",
    "two_weapon_bonus_attack_source",
    "two_weapon_bonus_source_is_legal",
    "two_weapon_trigger_item_id",
]
