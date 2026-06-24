from __future__ import annotations

from statuses.base import Status

WELLSPRING_GNOME_DESCRIPTION = (
    "Twoja magia plynie z innego zrodla niz typowe gnomie dziedzictwo fey.\n"
    "Kiedy: po wybraniu heritage wskazujesz tradycje (arcane/divine/occult) "
    "oraz 1 cantrip z odpowiedniej listy.\n"
    "Efekt: wybrany cantrip trafia do granted_cantrips jako innate spell at-will "
    "w wybranej tradycji; dodatkowo wszystkie innate primal gnome ancestry spells "
    "moga byc traktowane jako ta wybrana tradycja "
    "(override_gnome_primal_innate_tradition = True)."
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
