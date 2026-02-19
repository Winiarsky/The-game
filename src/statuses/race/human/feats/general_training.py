from __future__ import annotations

from statuses.base import Status

GENERAL_TRAINING_DESCRIPTION = (
    "Zyskujesz 1. poziomowy general feat (UI placeholder do wyboru)."
)


def GeneralTrainingStatus() -> Status:
    """Feat: General Training (UI placeholder)."""
    return Status(
        id="general_training",
        label="General Training",
        data={"ui_description": GENERAL_TRAINING_DESCRIPTION, "general_feat": None},
    )


GENERAL_TRAINING_STATUS = GeneralTrainingStatus()

__all__ = ["GeneralTrainingStatus", "GENERAL_TRAINING_STATUS", "GENERAL_TRAINING_DESCRIPTION"]
