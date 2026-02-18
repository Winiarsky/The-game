from __future__ import annotations

from statuses.base import Status

GOBLIN_SONG_DESCRIPTION = (
    "Masz akcję Goblin Song. Test Performance wyznacza DC. "
    "Wybierz cele w 30 stóp (1 / 2 / 4 / 8 dla biegłości). "
    "Sukces: -1 status do Perception i Will na 1 rundę. Krytyk: 5 rund."
)


def GoblinSongStatus() -> Status:
    """Feat: Goblin Song (opis do UI)."""
    return Status(
        id="goblin_song",
        label="Goblin Song",
        data={"ui_description": GOBLIN_SONG_DESCRIPTION},
    )


GOBLIN_SONG_STATUS = GoblinSongStatus()

__all__ = ["GoblinSongStatus", "GOBLIN_SONG_STATUS", "GOBLIN_SONG_DESCRIPTION"]
