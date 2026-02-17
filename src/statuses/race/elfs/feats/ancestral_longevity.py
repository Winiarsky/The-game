from __future__ import annotations

from statuses.base import Status

ANCESTRAL_LONGEVITY_DESCRIPTION = (
    "na poczatku kazdego scenariusza wybierz jedna z umiejetnosci, "
    "otrzymujesz poziom trained dla tej umiejetnosci, mozez je zmieniac "
    "miedzy scenariuszami"
)


def AncestralLongevityStatus() -> Status:
    """Feat: Ancestral Longevity (opis do UI)."""
    return Status(
        id="ancestral_longevity",
        label="Ancestral Longevity",
        data={"ui_description": ANCESTRAL_LONGEVITY_DESCRIPTION},
    )


ANCESTRAL_LONGEVITY_STATUS = AncestralLongevityStatus()

__all__ = [
    "AncestralLongevityStatus",
    "ANCESTRAL_LONGEVITY_STATUS",
    "ANCESTRAL_LONGEVITY_DESCRIPTION",
]
