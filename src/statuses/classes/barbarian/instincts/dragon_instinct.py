from __future__ import annotations

from damage_types import DamageType
from statuses.base import Status

DRAGON_INSTINCT_TYPES = [
    DamageType.COLD.value,
    DamageType.FIRE.value,
    DamageType.ACID.value,
    DamageType.POISON.value,
    DamageType.ELECTRIC.value,
]

DRAGON_INSTINCT_PROMPT = (
    "Dragon Instinct: wybierz typ obrażeń (ice/fire/acid/poison/electricity).\n"
    "Podczas Rage, możesz zamienić główny typ obrażeń broni na wybrany typ smoczy."
)


def DragonInstinctStatus() -> Status:
    """Barbarian Instinct: Dragon (wybór typu w UI)."""
    return Status(
        id="dragon_instinct",
        label="Dragon Instinct",
        data={
            "ui_prompt": DRAGON_INSTINCT_PROMPT,
            "ui_choice_kind": "dragon_instinct",
            "dragon_instinct_choices": list(DRAGON_INSTINCT_TYPES),
        },
    )


def DragonInstinctActiveStatus(*, dragon_type: str, duration: int | None = None) -> Status:
    """Aktywny instynkt podczas Rage (typ smoczy + bonus obrażeń)."""
    return Status(
        id="dragon_instinct_active",
        label="Dragon Instinct",
        duration=duration,
        data={
            "dragon_damage_type": str(dragon_type),
            "rage_damage_bonus_override": 4,
            "effect_tags": ["rage"],
        },
    )


DRAGON_INSTINCT_STATUS = DragonInstinctStatus()

__all__ = [
    "DRAGON_INSTINCT_TYPES",
    "DRAGON_INSTINCT_PROMPT",
    "DragonInstinctStatus",
    "DragonInstinctActiveStatus",
    "DRAGON_INSTINCT_STATUS",
]
