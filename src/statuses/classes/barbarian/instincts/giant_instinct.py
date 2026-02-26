from __future__ import annotations

from statuses.base import Status

GIANT_INSTINCT_PROMPT = (
    "Giant Instinct: podczas Rage zadajesz +6 obrażeń zamiast +2, "
    "ale otrzymujesz status clumsy."
)


def GiantInstinctStatus() -> Status:
    """Barbarian Instinct: Giant."""
    return Status(
        id="giant_instinct",
        label="Giant Instinct",
        data={"ui_prompt": GIANT_INSTINCT_PROMPT},
    )


def GiantInstinctActiveStatus(*, duration: int | None = None) -> Status:
    """Aktywny instynkt podczas Rage (bonus +6)."""
    return Status(
        id="giant_instinct_active",
        label="Giant Instinct",
        duration=duration,
        data={
            "rage_damage_bonus_override": 6,
            "effect_tags": ["rage"],
        },
    )


GIANT_INSTINCT_STATUS = GiantInstinctStatus()

__all__ = [
    "GIANT_INSTINCT_PROMPT",
    "GiantInstinctStatus",
    "GiantInstinctActiveStatus",
    "GIANT_INSTINCT_STATUS",
]
