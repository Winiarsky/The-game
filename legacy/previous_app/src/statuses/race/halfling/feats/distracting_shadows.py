from __future__ import annotations

from statuses.base import Status

DISTRACTING_SHADOWS_DESCRIPTION = (
    "Fluff: Niziolki potrafia znikac w cieniu wiekszych towarzyszy i wykorzystywac ich sylwetki jako ruchoma oslone.\n"
    "Mechanika:\n"
    "- Kiedy: Po wybraniu tej opcji.\n"
    "- Efekt:\n"
    "  - Mozesz uzywac wiekszych stworzen jako cover dla Hide i Sneak.\n"
    "  - W tym silniku dziala to jako uproszczenie: stojac obok sojusznika mozesz wejsc w stealth tak, jakbys mial oslone.\n"
    "  - Dostajesz wtedy bonus do Stealth jak z cover i latwiej omijasz watcherow blokujacych ukrycie.\n"
    "  - Przykład: stoisz obok frontlinera, przeciwnik patrzy w twoja strone, ale nadal mozesz wejsc w stealth dzieki Distracting Shadows."
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
