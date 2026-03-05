from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

ROUGH_RIDER_DESCRIPTION = (
    "Jesteś wyjątkowo dobry w jeździe na tradycyjnych goblińskich wierzchowcach.\n"
    "Zyskujesz Ride feat (nawet bez spełnienia prereq).\n"
    "Masz +1 circumstance do Nature checks na Command an Animal dla "
    "goblin dog lub wolf mount.\n"
    "Możesz zawsze wybrać wolf jako animal companion."
)


def RoughRiderStatus() -> Status:
    """Feat: Rough Rider."""
    return Status(
        id="rough_rider",
        label="Rough Rider",
        data={
            "ui_description": ROUGH_RIDER_DESCRIPTION,
            "granted_feat_ids": ["ride"],
            "rough_rider_allows_wolf_companion": True,
        },
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.NATURE.value],
                tags_required=["command_animal", "goblin_dog_or_wolf_mount"],
                bonus_effects=[
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=1,
                        tag=Skill.NATURE.value,
                        source="status:rough_rider",
                        label="rough rider +1",
                    )
                ],
                prompt_notes=["Rough Rider: +1 do Command an Animal (goblin dog/wolf mount)."],
            )
        ],
    )


ROUGH_RIDER_STATUS = RoughRiderStatus()

__all__ = ["RoughRiderStatus", "ROUGH_RIDER_STATUS", "ROUGH_RIDER_DESCRIPTION"]
