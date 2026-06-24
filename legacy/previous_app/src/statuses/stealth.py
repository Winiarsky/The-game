from __future__ import annotations

from statuses.base import Status


def StealthStatus(*, detection_dc: int | None = None, stealth_bonus: int = 0) -> Status:
    """
    Status: bohater jest ukryty.

    - detection_dc: wartość przeciwko próbom wykrycia (przeniesiona z pól bohatera).
    - stealth_bonus: zapamiętana premia z rzutu stealth (np. +1/+2 za wysokie wyniki).
    """
    return Status(
        id="stealth",
        label="Stealth",
        data={"stealth_detection_dc": detection_dc, "stealth_bonus": stealth_bonus},
    )


def ObservableStatus() -> Status:
    """Status: łatwy do zauważenia po wykryciu ukrycia."""
    return Status(id="observable", label="Observable")


STEALTH_STATUS = StealthStatus()
OBSERVABLE_STATUS = ObservableStatus()

__all__ = [
    "StealthStatus",
    "STEALTH_STATUS",
    "ObservableStatus",
    "OBSERVABLE_STATUS",
]
