from __future__ import annotations

from statuses.base import Status

MONSTROUS_PEACEMAKER_DESCRIPTION = (
    "+1 circumstance do Diplomacy przeciwko inteligentnym nie-humanoidom oraz "
    "zmarginalizowanym humanoidom (wedlug MG). "
    "+1 circumstance do Perception w Sense Motive przeciwko nim. "
    "Na razie licz recznie (brak tagow celu)."
)


def MonstrousPeacemakerStatus() -> Status:
    """Feat: Monstrous Peacemaker (opis do UI)."""
    return Status(
        id="monstrous_peacemaker",
        label="Monstrous Peacemaker",
        data={"ui_description": MONSTROUS_PEACEMAKER_DESCRIPTION},
    )


MONSTROUS_PEACEMAKER_STATUS = MonstrousPeacemakerStatus()

__all__ = [
    "MonstrousPeacemakerStatus",
    "MONSTROUS_PEACEMAKER_STATUS",
    "MONSTROUS_PEACEMAKER_DESCRIPTION",
]
