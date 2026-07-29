"""Deterministic D&D 5e body-armor rules."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from dnd_board_game.actors import Actor
    from dnd_board_game.rules import D20RollRequest

    from . import InventoryItem


@dataclass(frozen=True, slots=True)
class ArmorUseResult:
    accepted: bool
    actor: Actor
    armor: InventoryItem | None
    elapsed_minutes: int
    message: str


def equipped_body_armor(items: Sequence[InventoryItem]) -> InventoryItem | None:
    active = tuple(
        item
        for item in items
        if item.kind == "armor"
        and item.armor_category is not None
        and item.available
        and item.equipped
    )
    if len(active) > 1:
        raise ValueError("Aktor może mieć założony tylko jeden pancerz.")
    return active[0] if active else None


def body_armor_class(actor: Actor, armor: InventoryItem) -> int:
    from dnd_board_game.rules import ability_modifier

    if armor.armor_base_ac is None or armor.armor_category is None:
        raise ValueError("Przedmiot nie definiuje kompletnej formuły pancerza.")
    dexterity = ability_modifier(actor.ability_scores.dexterity)
    if armor.armor_dexterity_cap is not None:
        dexterity = min(dexterity, armor.armor_dexterity_cap)
    return armor.armor_base_ac + dexterity


def equipped_armor_class_bonus(items: Sequence[InventoryItem]) -> int:
    active = tuple(
        item
        for item in items
        if item.available
        and item.equipped
        and item.armor_class_bonus > 0
        and (item.kind != "shield" or len(item.held_in) == 1)
    )
    shield_bonus = max(
        (item.armor_class_bonus for item in active if item.kind == "shield"),
        default=0,
    )
    return shield_bonus + sum(
        item.armor_class_bonus
        for item in active
        if item.kind not in {"shield", "armor"}
    )


def effective_armor_class(actor: Actor) -> int:
    from .magic_items import MagicItemEffectKind, magic_item_effect_total
    from dnd_board_game.actors import actor_has_feature

    armor = equipped_body_armor(actor.inventory)
    shield_equipped = any(
        item.kind == "shield"
        and item.equipped
        and item.available
        and len(item.held_in) == 1
        for item in actor.inventory
    )
    base = body_armor_class(actor, armor) if armor is not None else actor.ac
    if (
        armor is None
        and shield_equipped
        and actor_has_feature(actor, "unarmored_defense_wisdom")
    ):
        from dnd_board_game.rules import ability_modifier

        base = 10 + ability_modifier(actor.ability_scores.dexterity)
    return (
        base
        + equipped_armor_class_bonus(actor.inventory)
        + (
            1
            if armor is not None
            and actor_has_feature(actor, "fighting_style_defense")
            else 0
        )
        + magic_item_effect_total(actor, MagicItemEffectKind.ARMOR_CLASS_BONUS)
    )


def armor_speed_penalty_feet(actor: Actor) -> int:
    from dnd_board_game.actors import actor_has_feature

    armor = equipped_body_armor(actor.inventory)
    if (
        armor is None
        or armor.armor_strength_requirement is None
        or actor.ability_scores.strength >= armor.armor_strength_requirement
        or actor_has_feature(actor, "dwarven_speed")
    ):
        return 0
    return 10


def effective_speed_feet(actor: Actor) -> int:
    from .magic_items import MagicItemEffectKind, magic_item_effect_total
    from dnd_board_game.actors import actor_has_feature

    armor = equipped_body_armor(actor.inventory)
    shield_equipped = any(
        item.kind == "shield"
        and item.equipped
        and item.available
        for item in actor.inventory
    )
    unarmored_movement = (
        10
        if actor_has_feature(actor, "unarmored_movement_10")
        and armor is None
        and not shield_equipped
        else 0
    )
    speed = max(
        0,
        actor.speed_feet
        - armor_speed_penalty_feet(actor)
        + unarmored_movement
        + magic_item_effect_total(actor, MagicItemEffectKind.SPEED_BONUS_FEET),
    )
    if actor.exhaustion_level >= 5:
        return 0
    if actor.exhaustion_level >= 2:
        return speed // 2
    return speed


def has_stealth_disadvantage(actor: Actor) -> bool:
    armor = equipped_body_armor(actor.inventory)
    return armor is not None and armor.stealth_disadvantage


def armor_skill_roll_request(
    actor: Actor,
    skill: str,
    request: D20RollRequest,
) -> D20RollRequest:
    """Apply armor-caused Stealth disadvantage to an existing d20 request."""

    if skill != "stealth" or not has_stealth_disadvantage(actor):
        return request
    from dnd_board_game.rules import (
        D20RollRequest,
        RollMode,
        RollModifier,
        RollModifierType,
    )

    mode = (
        RollMode.NORMAL
        if request.mode == RollMode.ADVANTAGE
        else RollMode.DISADVANTAGE
    )
    return D20RollRequest(
        mode=mode,
        modifiers=(
            *request.modifiers,
            RollModifier(
                "Utrudnienie: pancerz",
                0,
                RollModifierType.ITEM,
                stacking_key="armor_stealth_disadvantage",
            ),
        ),
    )


def armor_don_time_minutes(armor: InventoryItem) -> int:
    if armor.armor_category is None:
        raise ValueError("Przedmiot nie jest pancerzem.")
    return {"light": 1, "medium": 5, "heavy": 10}[armor.armor_category.value]


def armor_doff_time_minutes(armor: InventoryItem) -> int:
    if armor.armor_category is None:
        raise ValueError("Przedmiot nie jest pancerzem.")
    return {"light": 1, "medium": 1, "heavy": 5}[armor.armor_category.value]


def don_armor(actor: Actor, armor_id: str) -> ArmorUseResult:
    armor = next((item for item in actor.inventory if item.id == armor_id), None)
    if armor is None:
        return ArmorUseResult(False, actor, None, 0, "Tego pancerza nie ma w ekwipunku.")
    if armor.kind != "armor" or armor.armor_category is None or not armor.available:
        return ArmorUseResult(False, actor, armor, 0, "Ten przedmiot nie jest dostępnym pancerzem.")
    if armor.equipped:
        return ArmorUseResult(False, actor, armor, 0, "Ten pancerz jest już założony.")
    proficiency = armor.armor_proficiency or armor.armor_category.value
    if not actor.proficiencies.is_armor_proficient(proficiency):
        return ArmorUseResult(
            False,
            actor,
            armor,
            0,
            f"{actor.name} nie ma biegłości wymaganej przez ten pancerz ({proficiency}).",
        )
    current = equipped_body_armor(actor.inventory)
    if current is not None:
        return ArmorUseResult(
            False,
            actor,
            armor,
            0,
            f"Najpierw trzeba zdjąć: {current.name}.",
        )
    equipped = replace(armor, equipped=True, held_in=())
    updated = replace(
        actor,
        inventory=tuple(equipped if item.id == armor_id else item for item in actor.inventory),
    )
    minutes = armor_don_time_minutes(equipped)
    return ArmorUseResult(
        True,
        updated,
        equipped,
        minutes,
        f"{actor.name} zakłada {armor.name}. Mija {minutes} min.",
    )


def doff_armor(actor: Actor, armor_id: str) -> ArmorUseResult:
    armor = next((item for item in actor.inventory if item.id == armor_id), None)
    if (
        armor is None
        or armor.kind != "armor"
        or armor.armor_category is None
        or not armor.available
        or not armor.equipped
    ):
        return ArmorUseResult(False, actor, armor, 0, "Ten pancerz nie jest obecnie założony.")
    unequipped = replace(armor, equipped=False, held_in=())
    updated = replace(
        actor,
        inventory=tuple(unequipped if item.id == armor_id else item for item in actor.inventory),
    )
    minutes = armor_doff_time_minutes(armor)
    return ArmorUseResult(
        True,
        updated,
        unequipped,
        minutes,
        f"{actor.name} zdejmuje {armor.name}. Mija {minutes} min.",
    )


__all__ = [
    "ArmorUseResult",
    "armor_doff_time_minutes",
    "armor_don_time_minutes",
    "armor_speed_penalty_feet",
    "armor_skill_roll_request",
    "body_armor_class",
    "doff_armor",
    "don_armor",
    "effective_armor_class",
    "effective_speed_feet",
    "equipped_armor_class_bonus",
    "equipped_body_armor",
    "has_stealth_disadvantage",
]
