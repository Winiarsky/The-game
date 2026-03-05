from __future__ import annotations

from statuses.base import Status

BARBARIAN_PROMPT = (
    "KEY ABILITY: STRENGTH\n"
    "At 1st level, your class gives you an ability boost to Strength.\n"
    "HIT POINTS: 12 plus your Constitution Modifier\n"
    "You increase your maximum number of HP by this number at 1st level and every level thereafter.\n\n"
    "INITIAL PROFICIENCIES:\n"
    "PERCEPTION\n"
    "Expert in Perception\n"
    "SAVING THROWS\n"
    "Expert in Fortitude\n"
    "Trained in Reflex\n"
    "Expert in Will\n"
    "SKILLS\n"
    "Trained in Athletics\n"
    "Trained in a number of additional skills equal to 3 plus your Intelligence modifier\n"
    "ATTACKS\n"
    "Trained in simple weapons\n"
    "Trained in martial weapons\n"
    "Trained in unarmed attacks\n"
    "DEFENSES\n"
    "Trained in light armor\n"
    "Trained in medium armor\n"
    "Trained in unarmored defense"
)


def BarbarianStatus() -> Status:
    """Class: Barbarian (opis do UI prompta)."""
    return Status(
        id="barbarian",
        label="Barbarian",
        data={
            "ui_prompt": BARBARIAN_PROMPT,
            "class_hp": 12,
            "set_actor_attrs": {"class_name": "barbarian"},
        },
    )


BARBARIAN_STATUS = BarbarianStatus()

__all__ = [
    "BARBARIAN_PROMPT",
    "BarbarianStatus",
    "BARBARIAN_STATUS",
]
