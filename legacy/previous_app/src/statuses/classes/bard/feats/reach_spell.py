from __future__ import annotations

from statuses.base import Status

REACH_SPELL_DESCRIPTION = (
    "Reach Spell: zyskujesz akcje 'reach_spell'. "
    "Nastepny rzucony czar z zasiegiem ma +30 ft "
    "(dla touch zasieg wynosi 30 ft)."
)


def ReachSpellStatus() -> Status:
    """Feat: Reach Spell."""
    return Status(
        id="reach_spell",
        label="Reach Spell",
        data={
            "ui_description": REACH_SPELL_DESCRIPTION,
            "ui_prompt": REACH_SPELL_DESCRIPTION,
        },
    )


REACH_SPELL_STATUS = ReachSpellStatus()

__all__ = [
    "REACH_SPELL_DESCRIPTION",
    "ReachSpellStatus",
    "REACH_SPELL_STATUS",
]

