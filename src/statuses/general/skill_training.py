from __future__ import annotations

from statuses.base import Status

SKILL_TRAINING_DESCRIPTION = (
    "Prereq: INT 12. Wybierz skill i stajesz sie trained. "
    "Mozna brac wiele razy (inny skill). Na razie recznie."
)


def SkillTrainingStatus() -> Status:
    """Feat: Skill Training (opis do UI)."""
    return Status(
        id="skill_training",
        label="Skill Training",
        data={"ui_description": SKILL_TRAINING_DESCRIPTION},
    )


SKILL_TRAINING_STATUS = SkillTrainingStatus()

__all__ = ["SkillTrainingStatus", "SKILL_TRAINING_STATUS", "SKILL_TRAINING_DESCRIPTION"]
