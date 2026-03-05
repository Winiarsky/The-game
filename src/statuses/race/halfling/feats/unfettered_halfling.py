from __future__ import annotations

from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

UNFETTERED_HALFLING_DESCRIPTION = (
    "Gdy osiągniesz sukces na check to Escape lub save vs grabbed/restrained, "
    "otrzymujesz krytyczny sukces.\n"
    "Gdy przeciwnik obleje check to Grapple przeciw tobie, traktuje to jako krytyczną porażkę.\n"
    "Grab nie działa na tobie automatycznie - wymaga checka Athletics."
)


def UnfetteredHalflingStatus() -> Status:
    """Feat: Unfettered Halfling."""
    return Status(
        id="unfettered_halfling",
        label="Unfettered Halfling",
        data={
            "ui_description": UNFETTERED_HALFLING_DESCRIPTION,
            "grab_requires_check_against_actor": True,
        },
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.ACROBATICS.value, Skill.ATHLETICS.value],
                tags_required=["escape"],
                promote=1,
                promote_on=["success"],
                prompt_notes=["Unfettered Halfling: sukces na Escape -> krytyczny sukces."],
            ),
            CheckEffect(
                applies_to="source",
                skills=[Skill.FORTITUDE.value, Skill.REFLEX.value, Skill.WILL.value],
                tags_required=["grabbed"],
                promote=1,
                promote_on=["success"],
                prompt_notes=["Unfettered Halfling: sukces save vs grabbed -> krytyczny sukces."],
            ),
            CheckEffect(
                applies_to="source",
                skills=[Skill.FORTITUDE.value, Skill.REFLEX.value, Skill.WILL.value],
                tags_required=["restrained"],
                promote=1,
                promote_on=["success"],
                prompt_notes=["Unfettered Halfling: sukces save vs restrained -> krytyczny sukces."],
            ),
            CheckEffect(
                applies_to="target",
                skills=[Skill.ATHLETICS.value],
                tags_required=["grapple"],
                demote=1,
                demote_on=["failure"],
                prompt_notes=["Unfettered Halfling: failure on Grapple -> critical failure."],
            ),
        ],
    )


UNFETTERED_HALFLING_STATUS = UnfetteredHalflingStatus()

__all__ = ["UnfetteredHalflingStatus", "UNFETTERED_HALFLING_STATUS", "UNFETTERED_HALFLING_DESCRIPTION"]
