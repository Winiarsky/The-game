from __future__ import annotations

from dataclasses import dataclass


ABILITY_NAMES = frozenset(
    {
        "strength",
        "dexterity",
        "constitution",
        "intelligence",
        "wisdom",
        "charisma",
    }
)


@dataclass(frozen=True, slots=True)
class ProficiencyProfile:
    """Actor-owned D&D 5e proficiency choices, independent from class content."""

    saving_throws: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()
    expertise: tuple[str, ...] = ()
    weapons: tuple[str, ...] = ()
    armor: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        unknown_saves = set(self.saving_throws) - ABILITY_NAMES
        if unknown_saves:
            raise ValueError(
                f"Unknown saving throw proficiencies: {', '.join(sorted(unknown_saves))}."
            )
        if not set(self.expertise).issubset(self.skills):
            raise ValueError("Skill expertise requires proficiency in the same skill.")
        for label, values in (
            ("saving throw", self.saving_throws),
            ("skill", self.skills),
            ("expertise", self.expertise),
            ("weapon", self.weapons),
            ("armor", self.armor),
            ("tool", self.tools),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate {label} proficiency.")
            if any(not value for value in values):
                raise ValueError(f"Empty {label} proficiency is not allowed.")

    def is_save_proficient(self, ability: str) -> bool:
        _validate_ability(ability)
        return ability in self.saving_throws

    def is_weapon_proficient(self, proficiency_id: str | None) -> bool:
        return proficiency_id is not None and proficiency_id in self.weapons

    def is_armor_proficient(self, proficiency_id: str | None) -> bool:
        return proficiency_id is not None and proficiency_id in self.armor


def validate_ability(ability: str) -> None:
    _validate_ability(ability)


def _validate_ability(ability: str) -> None:
    if ability not in ABILITY_NAMES:
        raise ValueError(f"Unknown ability: {ability}.")
