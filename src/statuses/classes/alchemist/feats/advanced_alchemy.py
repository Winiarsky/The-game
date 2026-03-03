from __future__ import annotations

from statuses.base import Status

ADVANCED_ALCHEMY_DESCRIPTION = (
    "Advanced Alchemy: w fazie startowej możesz przeznaczyć reagenty na tworzenie "
    "przedmiotów alchemicznych (2 sztuki za 1 reagent)."
)


def AdvancedAlchemyStatus() -> Status:
    return Status(
        id="advanced_alchemy",
        label="Advanced Alchemy",
        data={"ui_description": ADVANCED_ALCHEMY_DESCRIPTION},
    )


ADVANCED_ALCHEMY_STATUS = AdvancedAlchemyStatus()

__all__ = [
    "ADVANCED_ALCHEMY_DESCRIPTION",
    "AdvancedAlchemyStatus",
    "ADVANCED_ALCHEMY_STATUS",
]
