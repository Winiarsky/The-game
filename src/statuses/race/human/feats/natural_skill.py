from __future__ import annotations

from statuses.base import Status

NATURAL_SKILL_DESCRIPTION = (
    "Zyskujesz trained w dwóch wybranych skillach. (UI only)"
)


def NaturalSkillStatus() -> Status:
    """Feat: Natural Skill (UI only)."""
    return Status(
        id="natural_skill",
        label="Natural Skill",
        data={"ui_description": NATURAL_SKILL_DESCRIPTION, "trained_skills": []},
    )


NATURAL_SKILL_STATUS = NaturalSkillStatus()

__all__ = ["NaturalSkillStatus", "NATURAL_SKILL_STATUS", "NATURAL_SKILL_DESCRIPTION"]
