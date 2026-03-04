from __future__ import annotations

from statuses.base import Status

DANGEROUS_SORCERY_DESCRIPTION = (
    "Dangerous Sorcery: gdy rzucasz czar ze slotu, ktory zadaje damage i nie ma duration, "
    "otrzymuje on status bonus do damage rowny poziomowi czaru (rozliczenie reczne)."
)


def DangerousSorceryStatus() -> Status:
    return Status(
        id="dangerous_sorcery",
        label="Dangerous Sorcery",
        data={
            "ui_description": DANGEROUS_SORCERY_DESCRIPTION,
            "ui_prompt": DANGEROUS_SORCERY_DESCRIPTION,
            "dangerous_sorcery_damage_bonus_per_spell_level": 1,
        },
    )


DANGEROUS_SORCERY_STATUS = DangerousSorceryStatus()

__all__ = [
    "DANGEROUS_SORCERY_DESCRIPTION",
    "DangerousSorceryStatus",
    "DANGEROUS_SORCERY_STATUS",
]
