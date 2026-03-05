from __future__ import annotations

from statuses.base import Status

DISTRACTING_SHADOWS_DESCRIPTION = (
    "Możesz używać stworzeń co najmniej o 1 rozmiar większych jako cover "
    "dla akcji Hide i Sneak.\n"
    "W tym silniku działa to jako uproszczenie: stojąc obok sojusznika "
    "możesz ukrywać się i korzystać z bonusu do Stealth, jakbyś miał osłonę."
)


def DistractingShadowsStatus() -> Status:
    """Feat: Distracting Shadows (opis do UI)."""
    return Status(
        id="distracting_shadows",
        label="Distracting Shadows",
        data={
            "ui_description": DISTRACTING_SHADOWS_DESCRIPTION,
            "distracting_shadows_cover_for_hide_sneak": True,
        },
    )


DISTRACTING_SHADOWS_STATUS = DistractingShadowsStatus()

__all__ = [
    "DistractingShadowsStatus",
    "DISTRACTING_SHADOWS_STATUS",
    "DISTRACTING_SHADOWS_DESCRIPTION",
]
