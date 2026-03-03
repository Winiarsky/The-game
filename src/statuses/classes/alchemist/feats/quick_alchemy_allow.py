from __future__ import annotations

from statuses.base import Status

QUICK_ALCHEMY_ALLOW_DESCRIPTION = (
    "Quick Alchemy: możesz w walce tworzyć przedmiot alchemiczny akcją quick_alchemy (koszt 1 akcja)."
)


def QuickAlchemyAllowStatus() -> Status:
    return Status(
        id="quick_alchemy_allow",
        label="Quick Alchemy",
        data={"ui_description": QUICK_ALCHEMY_ALLOW_DESCRIPTION},
    )


QUICK_ALCHEMY_ALLOW_STATUS = QuickAlchemyAllowStatus()

__all__ = [
    "QUICK_ALCHEMY_ALLOW_DESCRIPTION",
    "QuickAlchemyAllowStatus",
    "QUICK_ALCHEMY_ALLOW_STATUS",
]
