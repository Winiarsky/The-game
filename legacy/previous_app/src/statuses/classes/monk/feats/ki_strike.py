from __future__ import annotations

from statuses.base import Status

KI_STRIKE_DAMAGE_TYPE_CHOICES = ["force", "lawful", "negative", "positive"]

KI_STRIKE_DESCRIPTION = (
    "Ki Strike (Focus 1): unarmed Strike albo Flurry of Blows z +1 status do ataku i +1k6 extra damage "
    "(force/lawful/negative/positive)."
)


def KiStrikeStatus() -> Status:
    return Status(
        id="ki_strike",
        label="Ki Strike",
        data={
            "ui_description": KI_STRIKE_DESCRIPTION,
            "ui_prompt": KI_STRIKE_DESCRIPTION,
            "ki_strike_damage_type_choices": list(KI_STRIKE_DAMAGE_TYPE_CHOICES),
            "set_actor_attrs": {"focus_point": 1},
        },
    )


KI_STRIKE_STATUS = KiStrikeStatus()

__all__ = [
    "KiStrikeStatus",
    "KI_STRIKE_STATUS",
    "KI_STRIKE_DESCRIPTION",
    "KI_STRIKE_DAMAGE_TYPE_CHOICES",
]
