from __future__ import annotations

from damage_types import DamageType
from statuses.base import Status

ANIMAL_INSTINCT_PROFILES: dict[str, dict[str, object]] = {
    "ape": {"label": "Ape", "damage_dice": "1k10", "damage_type": DamageType.BLUDGEONING.value, "tags": ["grapple"]},
    "bear": {"label": "Bear", "damage_dice": "1k10", "damage_type": DamageType.PIERCING.value, "tags": ["grapple"]},
    "bull": {"label": "Bull", "damage_dice": "1k10", "damage_type": DamageType.PIERCING.value, "tags": ["shove"]},
    "cat": {"label": "Cat", "damage_dice": "1k10", "damage_type": DamageType.PIERCING.value, "tags": ["finesse"]},
    "deer_antler": {
        "label": "Deer Antler",
        "damage_dice": "1k10",
        "damage_type": DamageType.PIERCING.value,
        "tags": ["grapple"],
    },
    "frog_jaws": {"label": "Frog Jaws", "damage_dice": "1k10", "damage_type": DamageType.BLUDGEONING.value, "tags": []},
    "shark": {"label": "Shark", "damage_dice": "1k10", "damage_type": DamageType.PIERCING.value, "tags": ["grapple"]},
    "snake": {"label": "Snake", "damage_dice": "1k10", "damage_type": DamageType.PIERCING.value, "tags": ["grapple"]},
    "wolf": {"label": "Wolf", "damage_dice": "1k10", "damage_type": DamageType.PIERCING.value, "tags": ["trip"]},
}

ANIMAL_INSTINCT_PROMPT = (
    "Animal Instinct: wybierz zwierzę.\n"
    "Podczas Rage, Unarmed Attack używa profilu zwierzęcia (1k10 + typ obrażeń + cechy) zamiast 1k4.\n"
    "Uwaga: efekty instynktu działają tylko podczas aktywnego Rage."
)


def AnimalInstinctStatus() -> Status:
    """Barbarian Instinct: Animal (wybór profilu w UI)."""
    return Status(
        id="animal_instinct",
        label="Animal Instinct",
        data={
            "ui_prompt": ANIMAL_INSTINCT_PROMPT,
            "ui_choice_kind": "animal_instinct",
            "animal_instinct_choices": list(ANIMAL_INSTINCT_PROFILES.keys()),
        },
    )


def AnimalInstinctActiveStatus(*, profile: dict[str, object], duration: int | None = None) -> Status:
    """Aktywny instynkt podczas Rage (dane do Unarmed Attack)."""
    return Status(
        id="animal_instinct_active",
        label="Animal Instinct",
        duration=duration,
        data={
            "animal_instinct_profile": dict(profile or {}),
            "effect_tags": ["rage"],
        },
    )


ANIMAL_INSTINCT_STATUS = AnimalInstinctStatus()

__all__ = [
    "ANIMAL_INSTINCT_PROFILES",
    "ANIMAL_INSTINCT_PROMPT",
    "AnimalInstinctStatus",
    "AnimalInstinctActiveStatus",
    "ANIMAL_INSTINCT_STATUS",
]
