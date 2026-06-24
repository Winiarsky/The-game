from __future__ import annotations

from statuses.base import Status

ANCESTRAL_LONGEVITY_DESCRIPTION = (
    "Prerequisite: co najmniej 100 lat.\n"
    "W czasie przygotowań wybierasz 1 skill i stajesz się w nim trained "
    "do następnych przygotowań.\n"
    "W tym silniku: wybór skilla jest zapisywany na statusie i można go "
    "zmieniać przy ponownym wyborze/odświeżeniu statusu."
)


def AncestralLongevityStatus() -> Status:
    """Feat: Ancestral Longevity."""
    return Status(
        id="ancestral_longevity",
        label="Ancestral Longevity",
        data={
            "ui_description": ANCESTRAL_LONGEVITY_DESCRIPTION,
            "ui_choice_kind": "ancestral_longevity",
            "ancestral_longevity_skill": None,
            "trained_skills": [],
            "requires_min_age_years": 100,
        },
    )


ANCESTRAL_LONGEVITY_STATUS = AncestralLongevityStatus()

__all__ = [
    "AncestralLongevityStatus",
    "ANCESTRAL_LONGEVITY_STATUS",
    "ANCESTRAL_LONGEVITY_DESCRIPTION",
]
