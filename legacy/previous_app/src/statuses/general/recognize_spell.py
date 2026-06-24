from __future__ import annotations

from statuses.base import Status

RECOGNIZE_SPELL_DESCRIPTION = (
    "Uproszczenie: gdy uzywasz Detect Magic w walce, otrzymujesz +1 circumstance "
    "do AC przeciwko magicznym atakom wymierzonym w ciebie (na 1 ture)."
)


def RecognizeSpellStatus() -> Status:
    """Feat: Recognize Spell (opis do UI)."""
    return Status(
        id="recognize_spell",
        label="Recognize Spell",
        data={"ui_description": RECOGNIZE_SPELL_DESCRIPTION},
    )


RECOGNIZE_SPELL_STATUS = RecognizeSpellStatus()

__all__ = [
    "RecognizeSpellStatus",
    "RECOGNIZE_SPELL_STATUS",
    "RECOGNIZE_SPELL_DESCRIPTION",
]
