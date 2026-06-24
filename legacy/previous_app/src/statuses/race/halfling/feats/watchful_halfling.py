from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

WATCHFUL_HALFLING_DESCRIPTION = (
    "Fluff: Watchful Halfling oddaje czujnosc niziolka, ktory szybko wychwytuje niepokojace sygnaly i manipulacje w zachowaniu innych.\n"
    "Mechanika:\n"
    "- Kiedy: Gdy wykonujesz Sense Motive albo bronisz sie przed subtelna manipulacja.\n"
    "- Efekt:\n"
    "  - Masz +2 circumstance do Perception checks z tagiem Sense Motive.\n"
    "  - Feat jest przeznaczony do wylapywania enchantment i possession.\n"
    "  - Status zapisuje tez hooki pod pasywny secret check z kara -2 oraz Aid przeciw enchantment/possession.\n"
    "  - Przykład: podejrzewasz, ze NPC jest magicznie zmanipulowany, uzywasz Sense Motive i dostajesz +2 do testu."
)


def WatchfulHalflingStatus() -> Status:
    """Feat: Watchful Halfling."""
    return Status(
        id="watchful_halfling",
        label="Watchful Halfling",
        data={
            "ui_description": WATCHFUL_HALFLING_DESCRIPTION,
            "watchful_halfling_passive_secret_check_penalty": -2,
            "watchful_halfling_aid_vs_enchantment_or_possession": True,
        },
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.PERCEPTION.value],
                tags_required=["sense_motive"],
                bonus_effects=[
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=2,
                        tag=Skill.PERCEPTION.value,
                        source="status:watchful_halfling",
                        label="watchful +2",
                    )
                ],
                prompt_notes=["Watchful Halfling: +2 do Sense Motive."],
            )
        ],
    )


WATCHFUL_HALFLING_STATUS = WatchfulHalflingStatus()

__all__ = ["WatchfulHalflingStatus", "WATCHFUL_HALFLING_STATUS", "WATCHFUL_HALFLING_DESCRIPTION"]
