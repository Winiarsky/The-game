from __future__ import annotations

from statuses.base import Status

HALFLING_LUCK_DESCRIPTION = (
    "Frequency: raz dziennie.\n"
    "Trigger: oblejesz skill check albo saving throw.\n"
    "Możesz wykonać przerzut, ale musisz użyć nowego wyniku."
)


def HalflingLuckStatus() -> Status:
    """Feat: Halfling Luck."""
    return Status(
        id="halfling_luck",
        label="Halfling Luck",
        data={
            "ui_description": HALFLING_LUCK_DESCRIPTION,
            "frequency_per_day": 1,
            "fortune": True,
            "trigger_on_failure_skills_and_saves": True,
        },
    )


HALFLING_LUCK_STATUS = HalflingLuckStatus()

__all__ = ["HalflingLuckStatus", "HALFLING_LUCK_STATUS", "HALFLING_LUCK_DESCRIPTION"]
