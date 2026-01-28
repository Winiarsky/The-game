from __future__ import annotations

from statuses.base import Status


def HideStatus() -> Status:
    """Status ukrycia nadawany np. przez skrzynię."""
    return Status(id="hide", label="ukryty")


HIDE_STATUS = HideStatus()
