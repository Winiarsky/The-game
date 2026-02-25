from __future__ import annotations

from statuses.base import Status

FAR_LOBBER_DESCRIPTION = (
    "Alchemical bombs mają zasięg zwiększony o 10 stóp (zwykle 20 -> 30)."
)


def FarLobberStatus() -> Status:
    """Feat: Far Lobber."""
    return Status(
        id="far_lobber",
        label="Far Lobber",
        data={
            "ui_description": FAR_LOBBER_DESCRIPTION,
            "bomb_range_bonus": 10,
        },
    )


FAR_LOBBER_STATUS = FarLobberStatus()

__all__ = [
    "FAR_LOBBER_DESCRIPTION",
    "FarLobberStatus",
    "FAR_LOBBER_STATUS",
]
