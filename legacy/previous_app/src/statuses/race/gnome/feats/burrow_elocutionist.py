from __future__ import annotations

from statuses.base import Status

BURROW_ELOCUTIONIST_DESCRIPTION = (
    "Rozumiesz jezyk zwierzat kopiaczych i latwiej z nimi negocjujesz.\n"
    "Kiedy: podczas interakcji spolecznych ze zwierzetami kopiacymi nory "
    "(np. borsuk, kret, susel).\n"
    "Efekt: mozesz sie z nimi komunikowac i wykonywac testy Diplomacy "
    "zamiast traktowac je jako niemozliwe; w silniku jest to flaga capability "
    "(can_talk_to_burrow_animals + burrow_elocutionist_uses_diplomacy)."
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
