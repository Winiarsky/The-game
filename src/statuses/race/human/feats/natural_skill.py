from __future__ import annotations

from statuses.base import Status

NATURAL_SKILL_DESCRIPTION = (
    "Twoja pomysłowość pozwala szybko opanować wiele dziedzin.\n"
    "Zyskujesz trained w 2 skillach wybranych przez siebie."
)


def NaturalSkillStatus() -> Status:
    """Feat: Natural Skill."""
    return Status(
        id="natural_skill",
        label="Natural Skill",
        data={
            "ui_description": NATURAL_SKILL_DESCRIPTION,
            "ui_choice_kind": "natural_skill",
            "trained_skills": [],
            "natural_skill_choices_count": 2,
        },
    )


NATURAL_SKILL_STATUS = NaturalSkillStatus()

__all__ = ["NaturalSkillStatus", "NATURAL_SKILL_STATUS", "NATURAL_SKILL_DESCRIPTION"]
