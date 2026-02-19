from __future__ import annotations

from statuses.base import Status

COOPERATIVE_NATURE_DESCRIPTION = (
    "Gdy używasz Aid, twoja pomoc daje +2 circumstance zamiast +1."
)


def CooperativeNatureStatus() -> Status:
    """Feat: Cooperative Nature."""
    return Status(
        id="cooperative_nature",
        label="Cooperative Nature",
        data={"ui_description": COOPERATIVE_NATURE_DESCRIPTION, "aid_bonus": 2},
    )


COOPERATIVE_NATURE_STATUS = CooperativeNatureStatus()

__all__ = [
    "CooperativeNatureStatus",
    "COOPERATIVE_NATURE_STATUS",
    "COOPERATIVE_NATURE_DESCRIPTION",
]
