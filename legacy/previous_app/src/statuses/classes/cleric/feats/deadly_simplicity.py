from __future__ import annotations

from statuses.base import Status

DEADLY_SIMPLICITY_DESCRIPTION = (
    "Deadly Simplicity: gdy atakujesz favored weapon od deity, "
    "zwiekszasz kosc obrazen o 1 stopien. "
    "Dla unarmed minimum d6."
)


def DeadlySimplicityStatus() -> Status:
    return Status(
        id="deadly_simplicity",
        label="Deadly Simplicity",
        data={
            "ui_description": DEADLY_SIMPLICITY_DESCRIPTION,
            "ui_prompt": DEADLY_SIMPLICITY_DESCRIPTION,
        },
    )


DEADLY_SIMPLICITY_STATUS = DeadlySimplicityStatus()

__all__ = [
    "DEADLY_SIMPLICITY_DESCRIPTION",
    "DeadlySimplicityStatus",
    "DEADLY_SIMPLICITY_STATUS",
]
