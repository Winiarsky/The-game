from __future__ import annotations

from statuses.base import Status

VERSATILE_PERFORMANCE_DESCRIPTION = (
    "Versatile Performance: mozesz uzyc Performance zamiast Diplomacy "
    "(Make an Impression), Intimidation (Demoralize) oraz Deception (Impersonate)."
)


def VersatilePerformanceStatus() -> Status:
    """Feat: Versatile Performance."""
    return Status(
        id="versatile_performance",
        label="Versatile Performance",
        data={
            "ui_description": VERSATILE_PERFORMANCE_DESCRIPTION,
            "ui_prompt": VERSATILE_PERFORMANCE_DESCRIPTION,
        },
    )


VERSATILE_PERFORMANCE_STATUS = VersatilePerformanceStatus()

__all__ = [
    "VERSATILE_PERFORMANCE_DESCRIPTION",
    "VersatilePerformanceStatus",
    "VERSATILE_PERFORMANCE_STATUS",
]
