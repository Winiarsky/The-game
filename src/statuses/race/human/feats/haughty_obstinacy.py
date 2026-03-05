from __future__ import annotations

from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

HAUGHTY_OBSTINACY_DESCRIPTION = (
    "Twój upór utrudnia innym przejmowanie nad tobą kontroli.\n"
    "Jeśli osiągniesz sukces na save przeciw mental effect, który bezpośrednio "
    "kontroluje twoje działania, otrzymujesz krytyczny sukces.\n"
    "Jeśli przeciwnik obleje check to Coerce przeciw tobie, traktuje to jako "
    "krytyczną porażkę."
)


def HaughtyObstinacyStatus() -> Status:
    """Feat: Haughty Obstinacy."""
    return Status(
        id="haughty_obstinacy",
        label="Haughty Obstinacy",
        data={"ui_description": HAUGHTY_OBSTINACY_DESCRIPTION},
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.FORTITUDE.value, Skill.REFLEX.value, Skill.WILL.value],
                tags_required=["mental", "control"],
                promote=1,
                promote_on=["success"],
                prompt_notes=["Haughty Obstinacy: success vs mental control -> critical success."],
            ),
            CheckEffect(
                applies_to="target",
                skills=[Skill.INTIMIDATION.value],
                tags_required=["coerce"],
                demote=1,
                demote_on=["failure"],
                prompt_notes=["Haughty Obstinacy: failure on Coerce -> critical failure."],
            ),
        ],
    )


HAUGHTY_OBSTINACY_STATUS = HaughtyObstinacyStatus()

__all__ = ["HaughtyObstinacyStatus", "HAUGHTY_OBSTINACY_STATUS", "HAUGHTY_OBSTINACY_DESCRIPTION"]
