from __future__ import annotations

from statuses.base import Status

GOBLIN_SCUTTLE_DESCRIPTION = (
    "Masz akcję Goblin Scuttle: przygotuj reakcję na ruch sojusznika. "
    "Gdy sojusznik zakończy ruch obok ciebie, możesz wykonać Step."
)


def GoblinScuttleStatus(*, duration: int | None = 1) -> Status:
    """Status aktywujący Goblin Scuttle na bieżącą turę."""
    return Status(
        id="goblin_scuttle",
        label="Goblin Scuttle",
        duration=duration,
        data={
            "ui_description": GOBLIN_SCUTTLE_DESCRIPTION,
            "ui_prompt": "Goblin Scuttle aktywne: zareagujesz Stepem na ruch sojusznika.",
        },
    )


GOBLIN_SCUTTLE_STATUS = GoblinScuttleStatus()

__all__ = ["GoblinScuttleStatus", "GOBLIN_SCUTTLE_STATUS", "GOBLIN_SCUTTLE_DESCRIPTION"]
