from __future__ import annotations

from dnd_board_game.rules import RollModifier, RollModifierType, ability_modifier

from .models import Actor
from .proficiencies import ability_roll_modifier, proficiency_roll_modifier


SKILL_ABILITIES: dict[str, str] = {
    "acrobatics": "dexterity",
    "animal_handling": "wisdom",
    "arcana": "intelligence",
    "athletics": "strength",
    "deception": "charisma",
    "history": "intelligence",
    "insight": "wisdom",
    "intimidation": "charisma",
    "investigation": "intelligence",
    "medicine": "wisdom",
    "nature": "intelligence",
    "perception": "wisdom",
    "performance": "charisma",
    "persuasion": "charisma",
    "religion": "intelligence",
    "sleight_of_hand": "dexterity",
    "stealth": "dexterity",
    "survival": "wisdom",
}


def skill_modifier(actor: Actor, skill: str) -> int:
    """Return the D&D 5e ability + proficiency contribution for a skill."""

    ability = SKILL_ABILITIES.get(skill)
    if ability is None:
        raise ValueError(f"Unknown skill: {skill}.")
    result = ability_modifier(getattr(actor.ability_scores, ability))
    if skill in actor.skill_expertise:
        return result + 2 * actor.proficiency_bonus
    if skill in actor.skill_proficiencies:
        return result + actor.proficiency_bonus
    return result


def passive_skill_score(actor: Actor, skill: str) -> int:
    return 10 + skill_modifier(actor, skill)


def skill_roll_modifiers(
    actor: Actor,
    skill: str,
    *,
    ability: str | None = None,
) -> tuple[RollModifier, ...]:
    return ability_check_roll_modifiers(actor, ability or SKILL_ABILITIES.get(skill, ""), skill=skill)


def ability_check_roll_modifiers(
    actor: Actor,
    ability: str,
    *,
    skill: str | None = None,
    tool: str | None = None,
) -> tuple[RollModifier, ...]:
    """Build one D&D ability-check modifier set with non-stacking proficiency sources."""

    modifiers = [ability_roll_modifier(actor, ability)]
    if skill in actor.skill_expertise:
        modifiers.append(
            RollModifier(
                "Expertise",
                actor.proficiency_bonus * 2,
                RollModifierType.EXPERTISE,
                stacking_key="proficiency",
            )
        )
    elif skill in actor.skill_proficiencies:
        modifiers.append(proficiency_roll_modifier(actor))
    if tool is not None and tool in actor.proficiencies.tools:
        tool_label = next(
            (
                item.name
                for item in actor.inventory
                if item.id == tool or item.source_ref == tool
            ),
            tool,
        )
        modifiers.append(
            proficiency_roll_modifier(actor, label=f"Biegłość: {tool_label}")
        )
    return tuple(modifiers)
