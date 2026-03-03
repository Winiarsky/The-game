from __future__ import annotations

from statuses.base import Status

WIDEN_SPELL_DESCRIPTION = (
    "Widen Spell: zyskujesz akcje 'widen_spell'. Nastepny czar obszarowy "
    "(burst/cone/line bez duration) ma zwiekszony obszar."
)


def WidenSpellStatus() -> Status:
    return Status(
        id="widen_spell",
        label="Widen Spell",
        data={
            "ui_description": WIDEN_SPELL_DESCRIPTION,
            "ui_prompt": WIDEN_SPELL_DESCRIPTION,
        },
    )


WIDEN_SPELL_STATUS = WidenSpellStatus()

__all__ = [
    "WIDEN_SPELL_DESCRIPTION",
    "WidenSpellStatus",
    "WIDEN_SPELL_STATUS",
]
