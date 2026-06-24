from __future__ import annotations

from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

SURE_FEET_DESCRIPTION = (
    "Fluff: Sure Feet odzwierciedla lekki krok niziolka, ktory pewnie trzyma rownowage i wspina sie bez utraty kontroli.\n"
    "Mechanika:\n"
    "- Kiedy: Gdy wykonujesz Balance albo Climb.\n"
    "- Efekt:\n"
    "  - Sukces na Acrobatics check do Balance staje sie krytycznym sukcesem.\n"
    "  - Sukces na Athletics check do Climb staje sie krytycznym sukcesem.\n"
    "  - Podczas prob Balance i Climb nie jestes flat-footed.\n"
    "  - Przykład: zdajesz Balance na waskiej belce zwyklym sukcesem, a dzieki Sure Feet gra traktuje to jako krytyczny sukces."
)


def SureFeetStatus() -> Status:
    """Feat: Sure Feet."""
    return Status(
        id="sure_feet",
        label="Sure Feet",
        data={
            "ui_description": SURE_FEET_DESCRIPTION,
            "not_flat_footed_while_balance_or_climb": True,
        },
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.ACROBATICS.value],
                tags_required=["balance"],
                promote=1,
                promote_on=["success"],
                prompt_notes=["Sure Feet: sukces Balance -> krytyczny sukces."],
            ),
            CheckEffect(
                applies_to="source",
                skills=[Skill.ATHLETICS.value],
                tags_required=["climb"],
                promote=1,
                promote_on=["success"],
                prompt_notes=["Sure Feet: sukces Climb -> krytyczny sukces."],
            ),
        ],
    )


SURE_FEET_STATUS = SureFeetStatus()

__all__ = ["SureFeetStatus", "SURE_FEET_STATUS", "SURE_FEET_DESCRIPTION"]
