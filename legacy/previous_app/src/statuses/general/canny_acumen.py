from __future__ import annotations

from statuses.base import Status

CANNY_ACUMEN_DESCRIPTION = (
    "Wybierz Fortitude/Reflex/Will lub Perception: stajesz sie ekspertem. "
    "Na 17 poziomie master (na razie notatka UI)."
)


def CannyAcumenStatus() -> Status:
    """Feat: Canny Acumen."""
    return Status(
        id="canny_acumen",
        label="Canny Acumen",
        data={
            "ui_description": CANNY_ACUMEN_DESCRIPTION,
            "ui_choice_kind": "canny_acumen",
            "canny_acumen_choices": ["fortitude", "reflex", "will", "perception"],
            "canny_acumen_choice": None,
            "canny_acumen_rank": "expert",
            "canny_acumen_rank_at_17": "master",
        },
    )


CANNY_ACUMEN_STATUS = CannyAcumenStatus()

__all__ = ["CannyAcumenStatus", "CANNY_ACUMEN_STATUS", "CANNY_ACUMEN_DESCRIPTION"]
