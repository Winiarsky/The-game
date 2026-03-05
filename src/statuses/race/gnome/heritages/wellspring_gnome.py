from __future__ import annotations

from statuses.base import Status

WELLSPRING_GNOME_DESCRIPTION = (
    "Masz silniejsze powiązanie z innym źródłem magii niż primal dziedzictwo fey.\n"
    "Wybierasz tradycję: arcane, divine albo occult i zyskujesz 1 cantrip tej tradycji "
    "jako innate spell at-will.\n"
    "Dodatkowo każdy primal innate spell otrzymany z gnome ancestry featów jest "
    "traktowany jako spell wybranej tradycji.\n"
    "W tym silniku wybór tradycji/cantripa jest ustawiany przy nadaniu statusu."
)


def WellspringGnomeStatus() -> Status:
    """Heritage: Wellspring Gnome."""
    return Status(
        id="wellspring_gnome",
        label="Wellspring Gnome",
        data={
            "ui_description": WELLSPRING_GNOME_DESCRIPTION,
            "ui_choice_kind": "wellspring_gnome",
            "wellspring_tradition_choices": ["arcane", "divine", "occult"],
            "wellspring_cantrip_choices": {
                "arcane": [
                    "detect_magic",
                    "daze",
                    "light",
                    "mage_hand",
                    "shield",
                    "ray_of_frost",
                    "telekinetic_projectile",
                    "produce_flame",
                    "ghost_sound",
                    "message",
                ],
                "divine": [
                    "detect_magic",
                    "light",
                    "guidance",
                    "stabilize",
                    "disrupt_undead",
                    "divine_lance",
                    "forbidding_ward",
                    "know_direction",
                    "read_aura",
                    "shield",
                ],
                "occult": [
                    "detect_magic",
                    "daze",
                    "ghost_sound",
                    "mage_hand",
                    "message",
                    "shield",
                    "telekinetic_projectile",
                    "light",
                    "read_aura",
                    "guidance",
                ],
            },
            "wellspring_tradition": None,
            "wellspring_cantrip": None,
            "granted_cantrips": [],
            "innate_magic_tradition": None,
            "override_gnome_primal_innate_tradition": True,
        },
    )


WELLSPRING_GNOME_STATUS = WellspringGnomeStatus()

__all__ = ["WellspringGnomeStatus", "WELLSPRING_GNOME_STATUS", "WELLSPRING_GNOME_DESCRIPTION"]
