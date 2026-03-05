from __future__ import annotations

from statuses.base import Status

GOBLIN_SONG_DESCRIPTION = (
    "Masz akcję Goblin Song.\n"
    "Wykonujesz Performance check przeciw Will DC celów w 30 stóp.\n"
    "Skalowanie liczby celów: 1 / 2 / 4 / 8 (trained/expert/master/legendary).\n"
    "Sukces: -1 status do Perception i Will na 1 rundę.\n"
    "Krytyczny sukces: ten sam debuff na 1 minutę.\n"
    "Krytyczna porażka: cel ma czasową odporność na Goblin Song (1 godzina)."
)


def GoblinSongStatus() -> Status:
    """Feat: Goblin Song (opis do UI)."""
    return Status(
        id="goblin_song",
        label="Goblin Song",
        data={
            "ui_description": GOBLIN_SONG_DESCRIPTION,
            "goblin_song_range_feet": 30,
            "max_targets": 1,
            "goblin_song_max_targets_by_rank": {
                "trained": 1,
                "expert": 2,
                "master": 4,
                "legendary": 8,
            },
            "goblin_song_success_duration_rounds": 1,
            "goblin_song_critical_success_duration_rounds": 10,
            "goblin_song_critical_failure_immunity_rounds": 600,
        },
    )


GOBLIN_SONG_STATUS = GoblinSongStatus()

__all__ = ["GoblinSongStatus", "GOBLIN_SONG_STATUS", "GOBLIN_SONG_DESCRIPTION"]
