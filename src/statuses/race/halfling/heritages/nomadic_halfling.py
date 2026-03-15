from __future__ import annotations

from statuses.base import Status

NOMADIC_HALFLING_DESCRIPTION = (
    "Twoi przodkowie przez pokolenia podróżowali z miejsca na miejsce.\n"
    "Zyskujesz 2 dodatkowe jezyki (dowolne powszechne/rzadkie, do ktorych masz dostep).\n"
    "Za kazdym razem, gdy bierzesz feat Multilingual, zyskujesz 1 dodatkowy jezyk wiecej."
)


def NomadicHalflingStatus() -> Status:
    """Heritage: Nomadic Halfling."""
    return Status(
        id="nomadic_halfling",
        label="Nomadic Halfling",
        data={
            "ui_description": NOMADIC_HALFLING_DESCRIPTION,
            "additional_languages": 2,
            "multilingual_bonus_languages": 1,
        },
    )


NOMADIC_HALFLING_STATUS = NomadicHalflingStatus()

__all__ = ["NomadicHalflingStatus", "NOMADIC_HALFLING_STATUS", "NOMADIC_HALFLING_DESCRIPTION"]
