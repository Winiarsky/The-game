from __future__ import annotations

from typing import TYPE_CHECKING

from dnd_board_game.rules import RollModifier, RollModifierType, ability_modifier

if TYPE_CHECKING:
    from .models import Actor

from .proficiency_profile import validate_ability


def ability_roll_modifier(
    actor: Actor,
    ability: str,
    *,
    label: str | None = None,
) -> RollModifier:
    validate_ability(ability)
    value = ability_modifier(getattr(actor.ability_scores, ability))
    return RollModifier(
        label or _ability_label(ability),
        value,
        RollModifierType.ABILITY,
        stacking_key=f"ability:{ability}",
    )


def proficiency_roll_modifier(actor: Actor, *, label: str = "Biegłość") -> RollModifier:
    return RollModifier(
        label,
        actor.proficiency_bonus,
        RollModifierType.PROFICIENCY,
        stacking_key="proficiency",
    )


def saving_throw_roll_modifiers(actor: Actor, ability: str) -> tuple[RollModifier, ...]:
    modifiers = [ability_roll_modifier(actor, ability)]
    if actor.proficiencies.is_save_proficient(ability):
        modifiers.append(proficiency_roll_modifier(actor))
    return tuple(modifiers)


def saving_throw_modifier(actor: Actor, ability: str) -> int:
    return sum(modifier.value for modifier in saving_throw_roll_modifiers(actor, ability))


def attack_roll_modifiers(
    actor: Actor,
    ability: str,
    *,
    proficient: bool,
) -> tuple[RollModifier, ...]:
    modifiers = [ability_roll_modifier(actor, ability)]
    if proficient:
        modifiers.append(proficiency_roll_modifier(actor))
    return tuple(modifiers)


def _ability_label(ability: str) -> str:
    return {
        "strength": "Siła",
        "dexterity": "Zręczność",
        "constitution": "Kondycja",
        "intelligence": "Inteligencja",
        "wisdom": "Mądrość",
        "charisma": "Charyzma",
    }[ability]
