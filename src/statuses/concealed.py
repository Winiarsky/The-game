from __future__ import annotations

from statuses.base import Status


def ConcealedStatus() -> Status:
    """Status: cel jest zamaskowany (wymaga flat check DC 5 przed atakiem)."""
    return Status(id="concealed", label="Concealed", data={"effect_tags": ["concealment"]})


CONCEALED_STATUS = ConcealedStatus()

__all__ = ["ConcealedStatus", "CONCEALED_STATUS"]
