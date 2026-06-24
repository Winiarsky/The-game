from __future__ import annotations

from statuses.base import Status

YOURE_NEXT_DESCRIPTION = (
    "You're Next (Reaction-like trigger): gdy zredukujesz przeciwnika do 0 HP, "
    "próbujesz Demoralize innego widocznego celu z +2 circumstance."
)


def YoureNextStatus() -> Status:
    return Status(
        id="youre_next",
        label="You're Next",
        data={
            "ui_description": YOURE_NEXT_DESCRIPTION,
            "ui_prompt": YOURE_NEXT_DESCRIPTION,
            "allowed_classes": ["rogue"],
            "requires_trained_skills": ["intimidation"],
            "todo_notes": [
                "Legendary Intimidation -> free action wariant do dodania, gdy pojawi się system rang skilli."
            ],
        },
    )


YOURE_NEXT_STATUS = YoureNextStatus()

__all__ = ["YOURE_NEXT_DESCRIPTION", "YoureNextStatus", "YOURE_NEXT_STATUS"]
