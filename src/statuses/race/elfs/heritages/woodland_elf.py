from __future__ import annotations

from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

WOODLAND_ELF_DESCRIPTION = (
    "Jesteś przystosowany do życia w lesie i dżungli.\n"
    "Możesz użyć Take Cover na terenie forest nawet bez przeszkody obok.\n"
    "Dodatkowy hook: testy Climb w foliage (trees/vines/foliage) dostają "
    "promocję stopnia sukcesu."
)


def WoodlandElfStatus() -> Status:
    """Heritage: Woodland Elf."""
    return Status(
        id="woodland_elf",
        label="Woodland Elf",
        data={
            "ui_description": WOODLAND_ELF_DESCRIPTION,
            "allow_take_cover_terrain_tags": ["forest"],
            "woodland_climb_in_foliage": True,
        },
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.ATHLETICS.value],
                tags_required=["climb", "foliage"],
                promote=1,
                promote_on=["success"],
                prompt_notes=["Woodland Elf: sukces Climb w foliage -> krytyczny sukces."],
            )
        ],
    )


WOODLAND_ELF_STATUS = WoodlandElfStatus()

__all__ = ["WoodlandElfStatus", "WOODLAND_ELF_STATUS", "WOODLAND_ELF_DESCRIPTION"]
