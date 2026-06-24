from __future__ import annotations

from statuses.base import Status

SNEAK_ATTACK_DESCRIPTION = (
    "Sneak Attack: przy trafieniu odpowiednim atakiem przeciw flat-footed "
    "zadajesz dodatkowe precision damage (1k6 na 1. poziomie, skaluje się z levelem)."
)


def SneakAttackStatus() -> Status:
    return Status(
        id="sneak_attack",
        label="Sneak Attack",
        data={
            "ui_description": SNEAK_ATTACK_DESCRIPTION,
            "ui_prompt": SNEAK_ATTACK_DESCRIPTION,
            "allowed_classes": ["rogue"],
        },
    )


SNEAK_ATTACK_STATUS = SneakAttackStatus()

__all__ = ["SNEAK_ATTACK_DESCRIPTION", "SneakAttackStatus", "SNEAK_ATTACK_STATUS"]
