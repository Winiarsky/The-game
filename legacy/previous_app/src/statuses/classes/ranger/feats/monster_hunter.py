from __future__ import annotations

from statuses.base import Status

MONSTER_HUNTER_DESCRIPTION = (
    "Monster Hunter: podczas Hunt Prey możesz wykonać Recall Knowledge o celu. "
    "Przy critical success dajesz +1 circumstance do następnego ataku przeciw temu celowi "
    "(raz dziennie na konkretną istotę)."
)


def MonsterHunterStatus() -> Status:
    return Status(
        id="monster_hunter",
        label="Monster Hunter",
        data={
            "ui_description": MONSTER_HUNTER_DESCRIPTION,
            "ui_prompt": MONSTER_HUNTER_DESCRIPTION,
            "allowed_classes": ["ranger"],
        },
    )


MONSTER_HUNTER_STATUS = MonsterHunterStatus()

__all__ = ["MONSTER_HUNTER_DESCRIPTION", "MonsterHunterStatus", "MONSTER_HUNTER_STATUS"]
