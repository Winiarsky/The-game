from __future__ import annotations

from statuses.base import Status

MOMENT_OF_CLARITY_PROMPT = (
    "Moment of Clarity: odblokowuje akcję specjalną Moment of Clarity.\n"
    "Po użyciu akcji możesz do końca tury wykonywać akcje z tagiem manipulate podczas Rage."
)


def MomentOfClarityStatus() -> Status:
    """Feat: Moment of Clarity (wymagany do użycia akcji)."""
    return Status(
        id="moment_of_clarity",
        label="Moment of Clarity",
        data={
            "ui_prompt": MOMENT_OF_CLARITY_PROMPT,
            "ui_description": MOMENT_OF_CLARITY_PROMPT,
        },
    )


def MomentOfClarityActiveStatus(*, duration: int | None = None) -> Status:
    """Status tymczasowy po użyciu akcji Moment of Clarity."""
    return Status(
        id="moment_of_clarity_active",
        label="Moment of Clarity (aktywne)",
        duration=duration,
        data={
            "ui_prompt": "Moment of Clarity aktywne do końca tury.",
            "allow_rage_manipulate": True,
        },
    )


MOMENT_OF_CLARITY_STATUS = MomentOfClarityStatus()


__all__ = [
    "MomentOfClarityStatus",
    "MomentOfClarityActiveStatus",
    "MOMENT_OF_CLARITY_PROMPT",
    "MOMENT_OF_CLARITY_STATUS",
]
