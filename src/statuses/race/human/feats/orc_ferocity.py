from __future__ import annotations

from statuses.base import Status

ORC_FEROCITY_DESCRIPTION = (
    "Frequency: raz dziennie.\n"
    "Trigger: miałbyś spaść do 0 HP, ale nie zostać natychmiast zabity.\n"
    "Pozostajesz przy 1 HP i twój wounded wzrasta o 1."
)


def OrcFerocityStatus() -> Status:
    """Feat: Orc Ferocity (opis do UI)."""
    return Status(
        id="orc_ferocity",
        label="Orc Ferocity",
        data={
            "ui_description": ORC_FEROCITY_DESCRIPTION,
            "used_today": False,
            "frequency_per_day": 1,
        },
    )


ORC_FEROCITY_STATUS = OrcFerocityStatus()

__all__ = ["OrcFerocityStatus", "ORC_FEROCITY_STATUS", "ORC_FEROCITY_DESCRIPTION"]
