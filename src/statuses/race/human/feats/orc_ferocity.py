from __future__ import annotations

from statuses.base import Status

ORC_FEROCITY_DESCRIPTION = (
    "Raz dziennie, gdy mialbys spasc do 0 HP (i nie giniesz natychmiast), "
    "zostajesz na 1 HP, a twoj wounded wzrasta o 1. "
    "Na razie licz recznie (brak pelnej mechaniki HP/wounded)."
)


def OrcFerocityStatus() -> Status:
    """Feat: Orc Ferocity (opis do UI)."""
    return Status(
        id="orc_ferocity",
        label="Orc Ferocity",
        data={"ui_description": ORC_FEROCITY_DESCRIPTION},
    )


ORC_FEROCITY_STATUS = OrcFerocityStatus()

__all__ = ["OrcFerocityStatus", "ORC_FEROCITY_STATUS", "ORC_FEROCITY_DESCRIPTION"]
