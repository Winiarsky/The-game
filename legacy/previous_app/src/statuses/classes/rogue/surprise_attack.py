from __future__ import annotations

from statuses.base import Status

SURPRISE_ATTACK_DESCRIPTION = (
    "Surprise Attack: w 1. rundzie walki przeciwnicy, którzy jeszcze nie mieli tury, "
    "są flat-footed przeciw twoim atakom."
)


def SurpriseAttackStatus() -> Status:
    return Status(
        id="surprise_attack",
        label="Surprise Attack",
        data={
            "ui_description": SURPRISE_ATTACK_DESCRIPTION,
            "ui_prompt": SURPRISE_ATTACK_DESCRIPTION,
            "allowed_classes": ["rogue"],
        },
    )


SURPRISE_ATTACK_STATUS = SurpriseAttackStatus()

__all__ = ["SURPRISE_ATTACK_DESCRIPTION", "SurpriseAttackStatus", "SURPRISE_ATTACK_STATUS"]
