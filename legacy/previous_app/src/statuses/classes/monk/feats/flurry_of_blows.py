from __future__ import annotations

from statuses.base import Status

FLURRY_OF_BLOWS_DESCRIPTION = (
    "Flurry of Blows (Flourish): wykonaj dwa unarmed Strikes. "
    "Jeśli oba trafiają ten sam cel, łącz obrażenia do rozliczenia resist/weakness."
)


def FlurryOfBlowsStatus() -> Status:
    return Status(
        id="flurry_of_blows",
        label="Flurry of Blows",
        data={
            "ui_description": FLURRY_OF_BLOWS_DESCRIPTION,
            "ui_prompt": FLURRY_OF_BLOWS_DESCRIPTION,
        },
    )


FLURRY_OF_BLOWS_STATUS = FlurryOfBlowsStatus()

__all__ = ["FlurryOfBlowsStatus", "FLURRY_OF_BLOWS_STATUS", "FLURRY_OF_BLOWS_DESCRIPTION"]
