from __future__ import annotations

from statuses.base import Status

BARD_MUSE_CHOICES = [
    "enigma",
    "maestro",
    "polymath",
]

BARD_MUSE_EFFECTS = {
    "enigma": {
        "effect": "Odkrywasz tajemnice i sekrety rzeczywistosci.",
        "feat": "bardic_lore",
        "feat_label": "Bardyczna wiedza",
        "spell": "true_strike",
        "spell_label": "Prawdziwy cios",
    },
    "maestro": {
        "effect": "Inspirujesz sojusznikow i doskonalisz wystepy.",
        "feat": "lingering_composition",
        "feat_label": "Trwala kompozycja",
        "spell": "soothe",
        "spell_label": "Ukojenie",
    },
    "polymath": {
        "effect": "Laczysz wiele talentow i zainteresowan.",
        "feat": "versatile_performance",
        "feat_label": "Wszechstronny wystep",
        "spell": "unseen_servant",
        "spell_label": "Niewidzialny sluga",
    },
}


def InspirationStatus() -> Status:
    """Bard feature: wybór Muse (Enigma, Maestro, Polymath)."""
    return Status(
        id="inspiration",
        label="Inspiration",
        data={
            "ui_choice_kind": "bard_muse",
            "bard_muse_choices": list(BARD_MUSE_CHOICES),
            "bard_muse_effects": dict(BARD_MUSE_EFFECTS),
        },
    )


INSPIRATION_STATUS = InspirationStatus()

__all__ = [
    "BARD_MUSE_CHOICES",
    "BARD_MUSE_EFFECTS",
    "InspirationStatus",
    "INSPIRATION_STATUS",
]
