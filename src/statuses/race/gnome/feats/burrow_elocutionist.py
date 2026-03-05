from __future__ import annotations

from statuses.base import Status

BURROW_ELOCUTIONIST_DESCRIPTION = (
    "Rozumiesz mowę zwierząt kopiących nory (np. borsuki, krety, susły) "
    "i możesz prowadzić z nimi rozmowę oraz używać Diplomacy.\n"
    "W tym silniku efekt jest oznaczony opisowo jako capability."
)


def BurrowElocutionistStatus() -> Status:
    """Feat: Burrow Elocutionist."""
    return Status(
        id="burrow_elocutionist",
        label="Burrow Elocutionist",
        data={
            "ui_description": BURROW_ELOCUTIONIST_DESCRIPTION,
            "can_talk_to_burrow_animals": True,
            "burrow_elocutionist_uses_diplomacy": True,
        },
    )


BURROW_ELOCUTIONIST_STATUS = BurrowElocutionistStatus()

__all__ = [
    "BurrowElocutionistStatus",
    "BURROW_ELOCUTIONIST_STATUS",
    "BURROW_ELOCUTIONIST_DESCRIPTION",
]
