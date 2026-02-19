from __future__ import annotations

from statuses.base import Status

NATURAL_AMBITION_DESCRIPTION = (
    "Zyskujesz 1. poziomowy class feat (UI placeholder)."
)


def NaturalAmbitionStatus() -> Status:
    """Feat: Natural Ambition (UI placeholder)."""
    return Status(
        id="natural_ambition",
        label="Natural Ambition",
        data={"ui_description": NATURAL_AMBITION_DESCRIPTION, "class_feat": None},
    )


NATURAL_AMBITION_STATUS = NaturalAmbitionStatus()

__all__ = ["NaturalAmbitionStatus", "NATURAL_AMBITION_STATUS", "NATURAL_AMBITION_DESCRIPTION"]
