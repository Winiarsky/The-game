from __future__ import annotations

from statuses.base import Status

TITAN_SLINGER_DESCRIPTION = (
    "Gdy trafisz atakiem slingiem Large lub większe stworzenie, "
    "zwiększasz kość obrażeń broni o 1 krok.\n"
    "W tym silniku efekt jest zapisany jako hook danych dla ataków slingiem."
)


def TitanSlingerStatus() -> Status:
    """Feat: Titan Slinger."""
    return Status(
        id="titan_slinger",
        label="Titan Slinger",
        data={
            "ui_description": TITAN_SLINGER_DESCRIPTION,
            "titan_slinger_weapon_ids": ["sling", "halfling_sling_staff"],
            "titan_slinger_min_target_size": "large",
            "titan_slinger_damage_die_step_increase": 1,
        },
    )


TITAN_SLINGER_STATUS = TitanSlingerStatus()

__all__ = ["TitanSlingerStatus", "TITAN_SLINGER_STATUS", "TITAN_SLINGER_DESCRIPTION"]
