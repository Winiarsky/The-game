from __future__ import annotations

from statuses.base import Status

ADAPTED_CANTRIP_DESCRIPTION = (
    "Wybierz cantrip z innej tradycji; traktujesz go jako swój. (UI only)"
)

ADAPTED_CANTRIP_TRADITIONS = ["arcane", "divine", "occult", "primal"]

ADAPTED_CANTRIP_CHOICES = {
    "arcane": ["detect_magic", "daze", "ray_of_frost", "light", "shield"],
    "divine": ["detect_magic", "guidance", "light", "daze", "shield"],
    "occult": ["detect_magic", "daze", "guidance", "light", "shield"],
    "primal": ["detect_magic", "guidance", "ray_of_frost", "light", "shield"],
}

ADAPTED_CANTRIP_REPLACED_CHOICES = ["detect_magic", "daze", "ray_of_frost", "light", "guidance", "shield"]


def AdaptedCantripStatus() -> Status:
    """Feat: Adapted Cantrip (UI prompt)."""
    return Status(
        id="adapted_cantrip",
        label="Adapted Cantrip",
        data={
            "ui_description": ADAPTED_CANTRIP_DESCRIPTION,
            "requires_spellcasting_class_feature": True,
            "ui_choice_kind": "adapted_cantrip",
            "adapted_cantrip_traditions": list(ADAPTED_CANTRIP_TRADITIONS),
            "adapted_cantrip_choices": {key: list(values) for key, values in ADAPTED_CANTRIP_CHOICES.items()},
            "replaced_cantrip_choices": list(ADAPTED_CANTRIP_REPLACED_CHOICES),
            "adapted_cantrip": None,
            "adapted_tradition": None,
            "replaced_cantrip": None,
        },
    )


ADAPTED_CANTRIP_STATUS = AdaptedCantripStatus()

__all__ = [
    "ADAPTED_CANTRIP_DESCRIPTION",
    "ADAPTED_CANTRIP_TRADITIONS",
    "ADAPTED_CANTRIP_CHOICES",
    "ADAPTED_CANTRIP_REPLACED_CHOICES",
    "AdaptedCantripStatus",
    "ADAPTED_CANTRIP_STATUS",
]
