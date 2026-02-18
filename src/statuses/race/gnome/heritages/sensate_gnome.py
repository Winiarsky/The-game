from __future__ import annotations

from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

SENSATE_GNOME_DESCRIPTION = (
    "Otrzymujesz premie +4 circumstance do perception przy seek na tagi: nature, magic, smelly"
)


def SensateGnomeStatus() -> Status:
    """Heritage: Sensate Gnome."""
    return Status(
        id="sensate_gnome",
        label="Sensate Gnome",
        data={"ui_description": SENSATE_GNOME_DESCRIPTION},
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.PERCEPTION.value],
                tags_required=["nature"],
                prompt_notes=[
                    "Sensate Gnome: +4 do Perception przy seek na tagi nature/magic/smelly (dolicz ręcznie)."
                ],
            ),
            CheckEffect(
                applies_to="source",
                skills=[Skill.PERCEPTION.value],
                tags_required=["magic"],
                prompt_notes=[
                    "Sensate Gnome: +4 do Perception przy seek na tagi nature/magic/smelly (dolicz ręcznie)."
                ],
            ),
            CheckEffect(
                applies_to="source",
                skills=[Skill.PERCEPTION.value],
                tags_required=["smelly"],
                prompt_notes=[
                    "Sensate Gnome: +4 do Perception przy seek na tagi nature/magic/smelly (dolicz ręcznie)."
                ],
            ),
        ],
    )


SENSATE_GNOME_STATUS = SensateGnomeStatus()

__all__ = ["SensateGnomeStatus", "SENSATE_GNOME_STATUS", "SENSATE_GNOME_DESCRIPTION"]
