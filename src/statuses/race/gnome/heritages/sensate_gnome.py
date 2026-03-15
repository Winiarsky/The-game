from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

SENSATE_GNOME_DESCRIPTION = (
    "Masz ponadprzecietnie czuly, niedokladny zmysl wechu.\n"
    "Kiedy: wykonujesz Seek przeciw niewykrytemu celowi z uzyciem wechu "
    "(tagi seek + undetected + scent), w zasiegu 30 stop.\n"
    "Efekt: dostajesz imprecise scent 30 ft oraz +2 circumstance bonus do "
    "odpowiednich testow Perception."
)


def SensateGnomeStatus() -> Status:
    """Heritage: Sensate Gnome."""
    return Status(
        id="sensate_gnome",
        label="Sensate Gnome",
        data={
            "ui_description": SENSATE_GNOME_DESCRIPTION,
            "imprecise_scent_range_feet": 30,
            "seek_scent_locate_bonus_within_feet": 30,
        },
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.PERCEPTION.value],
                tags_required=["seek", "undetected", "scent"],
                bonus_effects=[
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=2,
                        tag=Skill.PERCEPTION.value,
                        source="status:sensate_gnome",
                        label="sensate gnome +2",
                    )
                ],
                prompt_notes=[
                    "Sensate Gnome: +2 do scent-based Seek vs undetected."
                ],
            ),
        ],
    )


SENSATE_GNOME_STATUS = SensateGnomeStatus()

__all__ = ["SensateGnomeStatus", "SENSATE_GNOME_STATUS", "SENSATE_GNOME_DESCRIPTION"]
