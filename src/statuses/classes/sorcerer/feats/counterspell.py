from __future__ import annotations

from statuses.base import Status

COUNTERSPELL_DESCRIPTION = (
    "Counterspell (Reaction): gdy widzisz jak przeciwnik rzuca czar, "
    "mozesz probowac go skontrowac. Musisz miec DOKLADNIE ten sam czar "
    "i zuzyc odpowiedni slot. Potem wykonujesz counteract check przeciw DC "
    "czaru przeciwnika; sukces anuluje czar."
)


def CounterspellStatus() -> Status:
    return Status(
        id="counterspell",
        label="Counterspell",
        data={
            "ui_description": COUNTERSPELL_DESCRIPTION,
            "ui_prompt": COUNTERSPELL_DESCRIPTION,
        },
    )


COUNTERSPELL_STATUS = CounterspellStatus()

__all__ = [
    "COUNTERSPELL_DESCRIPTION",
    "CounterspellStatus",
    "COUNTERSPELL_STATUS",
]
