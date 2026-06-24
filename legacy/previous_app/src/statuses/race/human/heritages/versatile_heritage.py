from __future__ import annotations

from statuses.base import Status
from statuses.race.human.feats.general_training import GENERAL_TRAINING_CHOICES

VERSATILE_HERITAGE_DESCRIPTION = (
    "Ludzie sa niezwykle wszechstronni i ambitni.\n"
    "Dzieki temu stali sie najpowszechniejsza ancestry w wielu krainach.\n"
    "Wybierasz jeden general feat, dla ktorego spelnasz wymagania.\n"
    "Tak jak ancestry feat, mozesz go wybrac w dowolnym momencie\n"
    "tworzenia postaci."
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
