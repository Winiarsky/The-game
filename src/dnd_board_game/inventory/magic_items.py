"""Composable passive effects granted by magic inventory items."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dnd_board_game.actors import Actor


class MagicItemEffectKind(StrEnum):
    STRENGTH_SCORE_BONUS = "strength_score_bonus"
    ARMOR_CLASS_BONUS = "armor_class_bonus"
    SAVING_THROW_BONUS = "saving_throw_bonus"
    ABILITY_CHECK_BONUS = "ability_check_bonus"
    ATTACK_ROLL_BONUS = "attack_roll_bonus"
    SPEED_BONUS_FEET = "speed_bonus_feet"


@dataclass(frozen=True, slots=True)
class MagicItemEffect:
    id: str
    kind: MagicItemEffectKind
    value: int
    requires_equipped: bool = True

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Magic item effect id cannot be empty.")
        if self.value == 0:
            raise ValueError("Magic item effect value cannot be zero.")


@dataclass(frozen=True, slots=True)
class MagicItemEffectContribution:
    item_id: str
    item_name: str
    effect: MagicItemEffect


def active_magic_item_effects(
    actor: Actor,
    kind: MagicItemEffectKind | str,
) -> tuple[MagicItemEffectContribution, ...]:
    """Return active effects with item provenance in stable inventory order."""

    from .attunement import item_power_available

    effect_kind = MagicItemEffectKind(kind)
    return tuple(
        MagicItemEffectContribution(item.id, item.name, effect)
        for item in actor.inventory
        if item_power_available(item)
        for effect in item.magic_effects
        if effect.kind == effect_kind
        and (not effect.requires_equipped or item.equipped)
    )


def magic_item_effect_total(
    actor: Actor,
    kind: MagicItemEffectKind | str,
) -> int:
    return sum(
        contribution.effect.value
        for contribution in active_magic_item_effects(actor, kind)
    )


def effective_ability_score(actor: Actor, ability: str) -> int:
    """Equipment changes the effective score, never the persisted base score."""
    from dnd_board_game.actors.proficiency_profile import validate_ability
    validate_ability(ability)
    bonus = magic_item_effect_total(actor, MagicItemEffectKind.STRENGTH_SCORE_BONUS) if ability == 'strength' else 0
    return getattr(actor.ability_scores, ability) + bonus


def effective_ability_modifier(actor: Actor, ability: str) -> int:
    from dnd_board_game.rules import ability_modifier
    return ability_modifier(effective_ability_score(actor, ability))


def magic_item_roll_modifiers(
    actor: Actor,
    kind: MagicItemEffectKind | str,
) -> tuple["RollModifier", ...]:
    from dnd_board_game.rules import RollModifier, RollModifierType

    return tuple(
        RollModifier(
            label=contribution.item_name,
            value=contribution.effect.value,
            modifier_type=RollModifierType.ITEM,
            stacking_key=f"magic_item_effect:{contribution.item_id}:{contribution.effect.id}",
        )
        for contribution in active_magic_item_effects(actor, kind)
    )


if TYPE_CHECKING:
    from dnd_board_game.rules import RollModifier


__all__ = [
    "MagicItemEffect",
    "MagicItemEffectContribution",
    "MagicItemEffectKind",
    "active_magic_item_effects",
    "magic_item_effect_total",
    "magic_item_roll_modifiers",
]
