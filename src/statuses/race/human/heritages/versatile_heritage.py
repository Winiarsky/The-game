from __future__ import annotations

from statuses.base import Status
from statuses.race.human.feats.general_training import GENERAL_TRAINING_CHOICES

VERSATILE_HERITAGE_DESCRIPTION = (
    "Humanity's versatility and ambition have fueled its\n"
    "ascendance to be the most common ancestry in most\n"
    "nations throughout the world. Select a general feat of\n"
    "your choice for which you meet the prerequisites (as\n"
    "with your ancestry feat, you can select this general feat\n"
    "at any point during character creation)."
)


def VersatileHeritageStatus() -> Status:
    """Heritage: Versatile Heritage (prompt only)."""
    return Status(
        id="versatile_heritage",
        label="Versatile Heritage",
        data={
            "ui_description": VERSATILE_HERITAGE_DESCRIPTION,
            "ui_choice_kind": "versatile_heritage",
            "general_feat_choices": list(GENERAL_TRAINING_CHOICES),
            "general_feat": None,
        },
    )


VERSATILE_HERITAGE_STATUS = VersatileHeritageStatus()

__all__ = [
    "VersatileHeritageStatus",
    "VERSATILE_HERITAGE_STATUS",
    "VERSATILE_HERITAGE_DESCRIPTION",
]
