from __future__ import annotations

from statuses.base import Status

FURY_INSTINCT_FEAT_CHOICES = [
    "cute_vision",
    "raging_thrower",
]

FURY_INSTINCT_PROMPT = (
    "Fury Instinct: wybierz jeden z barbarian feats jako bonus podczas Rage."
)


def FuryInstinctStatus() -> Status:
    """Barbarian Instinct: Fury (wybór feata w UI)."""
    return Status(
        id="fury_instinct",
        label="Fury Instinct",
        data={
            "ui_prompt": FURY_INSTINCT_PROMPT,
            "ui_choice_kind": "fury_instinct",
            "fury_instinct_feat_choices": list(FURY_INSTINCT_FEAT_CHOICES),
        },
    )


FURY_INSTINCT_STATUS = FuryInstinctStatus()

__all__ = [
    "FURY_INSTINCT_FEAT_CHOICES",
    "FURY_INSTINCT_PROMPT",
    "FuryInstinctStatus",
    "FURY_INSTINCT_STATUS",
]
