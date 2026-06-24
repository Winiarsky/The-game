from __future__ import annotations

from statuses.base import Status

UNIMPEDED_STEP_DESCRIPTION = (
    "Unimpeded Step: ruch sojusznika z Liberating Step ignoruje terrain penalties "
    "(difficult terrain, greater difficult terrain, narrow surfaces i uneven ground)."
)


def UnimpededStepStatus() -> Status:
    return Status(
        id="unimpeded_step",
        label="Unimpeded Step",
        data={
            "ui_description": UNIMPEDED_STEP_DESCRIPTION,
            "ui_prompt": UNIMPEDED_STEP_DESCRIPTION,
            "requires_champion_cause": "liberator",
        },
    )


UNIMPEDED_STEP_STATUS = UnimpededStepStatus()

__all__ = [
    "UNIMPEDED_STEP_DESCRIPTION",
    "UnimpededStepStatus",
    "UNIMPEDED_STEP_STATUS",
]
