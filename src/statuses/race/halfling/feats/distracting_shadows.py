from __future__ import annotations

from statuses.base import Status

DISTRACTING_SHADOWS_DESCRIPTION = (
    "+2 circumstance do Stealth, gdy stoisz obok sojusznika. "
    "Możesz ukryć się nawet w pomieszczeniu z watchful." 
    "(Obsługiwane w akcji Stealth)"
)


def DistractingShadowsStatus() -> Status:
    """Feat: Distracting Shadows (opis do UI)."""
    return Status(
        id="distracting_shadows",
        label="Distracting Shadows",
        data={"ui_description": DISTRACTING_SHADOWS_DESCRIPTION},
    )


DISTRACTING_SHADOWS_STATUS = DistractingShadowsStatus()

__all__ = [
    "DistractingShadowsStatus",
    "DISTRACTING_SHADOWS_STATUS",
    "DISTRACTING_SHADOWS_DESCRIPTION",
]
