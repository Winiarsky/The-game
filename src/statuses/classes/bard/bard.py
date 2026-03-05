from __future__ import annotations

from statuses.base import Status
from statuses.classes.bard.feats.reach_spell import REACH_SPELL_STATUS
from statuses.classes.bard.inspiration import INSPIRATION_STATUS

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
            "class_hp": 8,
            "set_actor_attrs": {"focus_point": 1, "class_name": "bard"},
            "grants_statuses": [INSPIRATION_STATUS, REACH_SPELL_STATUS],
        },
    )


BARD_STATUS = BardStatus()

__all__ = [
    "BARD_PROMPT",
    "BardStatus",
    "BARD_STATUS",
]
