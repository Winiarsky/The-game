from __future__ import annotations

from statuses.base import Status

SKILL_TRAINING_DESCRIPTION = (
    "Prereq opisowy: INT 12. Wybierz skill i stajesz sie trained. "
    "Mozna brac wiele razy (inny skill)."
)


def SkillTrainingStatus() -> Status:
    """Feat: Skill Training."""
    return Status(
        id="skill_training",
        label="Skill Training",
        data={
            "ui_description": SKILL_TRAINING_DESCRIPTION,
            "ui_choice_kind": "skill_training",
            "skill_training_choices": [
                "athletics",
                "acrobatics",
                "arcana",
                "crafting",
                "deception",
                "diplomacy",
                "intimidation",
                "medicine",
                "nature",
                "occultism",
                "performance",
                "religion",
                "society",
                "stealth",
                "survival",
                "thievery",
            ],
            "skill_training_skill": None,
            "trained_skills": [],
        },
    )


SKILL_TRAINING_STATUS = SkillTrainingStatus()

__all__ = ["SkillTrainingStatus", "SKILL_TRAINING_STATUS", "SKILL_TRAINING_DESCRIPTION"]
