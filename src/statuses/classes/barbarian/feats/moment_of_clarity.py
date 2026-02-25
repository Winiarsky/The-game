from __future__ import annotations

from statuses.base import Status

MOMENT_OF_CLARITY_PROMPT = (
    "Moment of Clarity: do końca tury możesz używać akcji z tagiem manipulate w trakcie Rage."
)


def MomentOfClarityStatus(*, duration: int | None = None) -> Status:
    """Feat: Moment of Clarity (status tymczasowy)."""
    return Status(
        id="moment_of_clarity",
        label="Moment of Clarity",
        duration=duration,
        data={
            "ui_prompt": MOMENT_OF_CLARITY_PROMPT,
            "allow_rage_manipulate": True,
        },
    )


__all__ = ["MomentOfClarityStatus", "MOMENT_OF_CLARITY_PROMPT"]
