from __future__ import annotations

from statuses.classes.alchemist.alchemist import (
    ALCHEMIST_PROMPT,
    ALCHEMIST_STATUS,
    AlchemistStatus,
)

# Backward-compat alias for legacy typo: "alchemsit".
ALCHEMSIT_PROMPT = ALCHEMIST_PROMPT
ALCHEMSIT_STATUS = ALCHEMIST_STATUS


def AlchemsitStatus():
    return AlchemistStatus()


__all__ = [
    "ALCHEMIST_PROMPT",
    "AlchemistStatus",
    "ALCHEMIST_STATUS",
    "ALCHEMSIT_PROMPT",
    "AlchemsitStatus",
    "ALCHEMSIT_STATUS",
]
