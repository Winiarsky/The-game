from __future__ import annotations

from statuses.base import Status

GOBLIN_SONG_DESCRIPTION = (
    "Wydajesz akcję Goblińska Pieśń i rozpraszasz przeciwników kakofonią.\n"
    "Kiedy: używasz akcji Goblin Song (zasięg 30 stóp, test Performance przeciw Will DC).\n"
    "Efekt: liczba celów skaluje się z biegłością Performance: trained=1, expert=2, "
    "master=4, legendary=8. Sukces: -1 status do Perception i Will na 1 rundę. "
    "Krytyczny sukces: ten sam efekt na 10 rund. Krytyczna porażka celu: "
    "odporność na Goblin Song na 1 godzinę."
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
