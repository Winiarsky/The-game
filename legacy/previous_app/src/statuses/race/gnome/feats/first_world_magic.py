from __future__ import annotations

from statuses.base import Status

FIRST_WORLD_MAGIC_DESCRIPTION = (
    "Pierwotna magia Pierwszego Swiata budzi w tobie prosty talent czarodziejski.\n"
    "Kiedy: po wybraniu featu wybierasz 1 cantrip z listy First World Magic.\n"
    "Efekt: wybrany cantrip trafia do granted_cantrips jako innate spell at-will; "
    "domyslna tradycja to primal, ale moze zostac nadpisana przez Wellspring Gnome "
    "(jesli aktywny jest override_gnome_primal_innate_tradition)."
)


def FirstWorldMagicStatus() -> Status:
    """Feat: First World Magic (opis do UI)."""
    return Status(
        id="first_world_magic",
        label="First World Magic",
        data={
            "ui_description": FIRST_WORLD_MAGIC_DESCRIPTION,
            "ui_choice_kind": "first_world_magic",
            "first_world_magic_choices": [
                "detect_magic",
                "guidance",
                "ray_of_frost",
                "produce_flame",
                "light",
                "tanglefoot",
                "shield",
                "ghost_sound",
                "stabilize",
                "daze",
            ],
            "first_world_magic_cantrip": None,
            "granted_cantrips": [],
            "innate_magic_tradition": "primal",
            "gnome_primal_innate_source": True,
        },
    )


FIRST_WORLD_MAGIC_STATUS = FirstWorldMagicStatus()

__all__ = [
    "FirstWorldMagicStatus",
    "FIRST_WORLD_MAGIC_STATUS",
    "FIRST_WORLD_MAGIC_DESCRIPTION",
]
