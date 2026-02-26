from __future__ import annotations

from damage_types import DamageType
from statuses.base import Status

SPIRIT_INSTINCT_TYPES = [
    "weapon",
    DamageType.POSITIVE.value,
    DamageType.NEGATIVE.value,
]

SPIRIT_INSTINCT_PROMPT = (
    "Spirit Instinct: wybierz typ obrażeń (positive/negative) albo pozostaw typ broni.\n"
    "Podczas Rage możesz wybrać główny typ obrażeń: broń lub wybrany typ spirytualny."
)


def SpiritInstinctStatus() -> Status:
    """Barbarian Instinct: Spirit (wybór typu w UI)."""
    return Status(
        id="spirit_instinct",
        label="Spirit Instinct",
        data={
            "ui_prompt": SPIRIT_INSTINCT_PROMPT,
            "ui_choice_kind": "spirit_instinct",
            "spirit_instinct_choices": list(SPIRIT_INSTINCT_TYPES),
        },
    )


def SpiritInstinctActiveStatus(*, spirit_type: str, duration: int | None = None) -> Status:
    """Aktywny instynkt podczas Rage (typ + bonus)."""
    return Status(
        id="spirit_instinct_active",
        label="Spirit Instinct",
        duration=duration,
        data={
            "spirit_damage_type": str(spirit_type),
            "rage_damage_bonus_override": 3,
            "effect_tags": ["rage"],
        },
    )


SPIRIT_INSTINCT_STATUS = SpiritInstinctStatus()

__all__ = [
    "SPIRIT_INSTINCT_TYPES",
    "SPIRIT_INSTINCT_PROMPT",
    "SpiritInstinctStatus",
    "SpiritInstinctActiveStatus",
    "SPIRIT_INSTINCT_STATUS",
]
