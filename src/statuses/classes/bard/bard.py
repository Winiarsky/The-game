from __future__ import annotations

from statuses.base import Status

BARD_PROMPT = (
    "KEY ABILITY: CHARISMA\n"
    "At 1st level, your class gives you an ability boost to Charisma.\n"
    "HIT POINTS: 8 plus your Constitution Modifier\n\n"
    "INITIAL PROFICIENCIES:\n"
    "PERCEPTION\n"
    "Expert in Perception\n"
    "SAVING THROWS\n"
    "Trained in Fortitude\n"
    "Trained in Reflex\n"
    "Expert in Will\n"
    "SKILLS\n"
    "Trained in Performance\n"
    "Trained in a number of additional skills equal to 4 plus your Intelligence modifier\n"
    "SPELLS\n"
    "Occult spellcasting\n"
    "Focus Pool: 1 Focus Point"
)


def BardStatus() -> Status:
    """Class: Bard (opis do UI prompta)."""
    return Status(
        id="bard",
        label="Bard",
        data={
            "ui_prompt": BARD_PROMPT,
            "set_actor_attrs": {"focus_point": 1},
        },
    )


BARD_STATUS = BardStatus()

__all__ = [
    "BARD_PROMPT",
    "BardStatus",
    "BARD_STATUS",
]

