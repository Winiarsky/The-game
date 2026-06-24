from __future__ import annotations

from statuses.base import Status

NATURAL_SKILL_DESCRIPTION = (
    "Mechanika: wybierasz 2 dowolne skille i zyskujesz w nich trained.\n"
    "Wybrane skille sa zapisywane w statusie i trafiaja do rankingu umiejetnosci bohatera."
)


def NaturalSkillStatus() -> Status:
    """Feat: Natural Skill."""
    return Status(
        id="natural_skill",
        label="Naturalny talent",
        data={
            "ui_description": NATURAL_SKILL_DESCRIPTION,
            "ui_choice_kind": "natural_skill",
            "trained_skills": [],
            "natural_skill_choices_count": 2,
        },
    )


NATURAL_SKILL_STATUS = NaturalSkillStatus()

__all__ = ["NaturalSkillStatus", "NATURAL_SKILL_STATUS", "NATURAL_SKILL_DESCRIPTION"]
