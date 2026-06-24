from __future__ import annotations

from .base import Status


def FlatFootedStatus() -> Status:
    """Status flankowania/flat-footed z karą do AC."""
    return Status(id="flat_footed", label="flankowany", data={"ac_penalty": 2})


FLAT_FOOTED_STATUS = FlatFootedStatus()
