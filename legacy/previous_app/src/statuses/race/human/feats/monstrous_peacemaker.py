from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

MONSTROUS_PEACEMAKER_DESCRIPTION = (
    "Masz +1 circumstance do Diplomacy przeciw inteligentnym non-humanoids "
    "i humanoids marginalizowanym w społeczeństwie ludzkim.\n"
    "Masz też +1 circumstance do Perception przy Sense Motive wobec takich celów.\n"
    "W tym silniku efekt działa przez tag celu: monstrous_peacemaker_target."
)


def MonstrousPeacemakerStatus() -> Status:
    """Feat: Monstrous Peacemaker."""
    return Status(
        id="monstrous_peacemaker",
        label="Monstrous Peacemaker",
        data={"ui_description": MONSTROUS_PEACEMAKER_DESCRIPTION},
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.DIPLOMACY.value],
                tags_required=["monstrous_peacemaker_target"],
                bonus_effects=[
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=1,
                        tag=Skill.DIPLOMACY.value,
                        source="status:monstrous_peacemaker",
                        label="monstrous peacemaker +1",
                    )
                ],
                prompt_notes=["Monstrous Peacemaker: +1 do Diplomacy vs qualifying targets."],
            ),
            CheckEffect(
                applies_to="source",
                skills=[Skill.PERCEPTION.value],
                tags_required=["sense_motive", "monstrous_peacemaker_target"],
                bonus_effects=[
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=1,
                        tag=Skill.PERCEPTION.value,
                        source="status:monstrous_peacemaker",
                        label="monstrous peacemaker +1",
                    )
                ],
                prompt_notes=["Monstrous Peacemaker: +1 do Sense Motive vs qualifying targets."],
            ),
        ],
    )


MONSTROUS_PEACEMAKER_STATUS = MonstrousPeacemakerStatus()

__all__ = [
    "MonstrousPeacemakerStatus",
    "MONSTROUS_PEACEMAKER_STATUS",
    "MONSTROUS_PEACEMAKER_DESCRIPTION",
]
