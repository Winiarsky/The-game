from __future__ import annotations

from statuses.base import Status


def InDarkStatus() -> Status:
    """Status ciemności – na razie bez efektów (placeholder)."""
    return Status(id="in_dark", label="In Dark")


IN_DARK_STATUS = InDarkStatus()

__all__ = ["InDarkStatus", "IN_DARK_STATUS"]
