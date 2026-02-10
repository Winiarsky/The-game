from __future__ import annotations

from statuses.base import Status
from statuses.check_effects import CheckEffect
from bonuses import BonusEffect, BonusType


def HideStatus() -> Status:
    """Status ukrycia nadawany np. przez skrzynię."""
    return Status(
        id="hide",
        label="ukryty",
        data={"stealth_bonus": 2},
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=["stealth"],
                tags_required=["try_stealth"],
                bonus_effects=[
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=2,
                        tag="stealth",
                        source="status:hide",
                        label="ukrycie +2",
                    )
                ],
            )
        ],
    )


HIDE_STATUS = HideStatus()
