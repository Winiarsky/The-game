from __future__ import annotations

from statuses.base import Status

HAND_OF_THE_APPRENTICE_DESCRIPTION = (
    "Hand of the Apprentice (Universalist): focus spell universalisty. "
    "Gra nadaje go automatycznie przy Arcane Study = Universalist; nie jest zwyklym wyborem class feat. "
    "Pozwala rzucic trzymana bronia w cel i natychmiast ja przywolac."
)


def HandOfTheApprenticeStatus() -> Status:
    return Status(
        id="hand_of_the_apprentice",
        label="Hand of the Apprentice",
        data={
            "ui_description": HAND_OF_THE_APPRENTICE_DESCRIPTION,
            "ui_prompt": HAND_OF_THE_APPRENTICE_DESCRIPTION,
            "requires_wizard_arcane_study": "universalist",
            "add_actor_attrs": {"focus_point": 1},
            "wizard_focus_spell": "hand_of_the_apprentice",
        },
    )


HAND_OF_THE_APPRENTICE_STATUS = HandOfTheApprenticeStatus()

__all__ = [
    "HAND_OF_THE_APPRENTICE_DESCRIPTION",
    "HandOfTheApprenticeStatus",
    "HAND_OF_THE_APPRENTICE_STATUS",
]
