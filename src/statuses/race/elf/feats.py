from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

_ELF_FEAT_DATA = {"ancestry": "elf", "feat": True, "traits": ["elf", "feat"]}


def AncestralLongevityStatus() -> Status:
    """Info: przed scenariuszem wybierz niewytrenowaną umiejętność -> trained na scenariusz."""
    return Status(
        id="feat_ancestral_longevity",
        label="Ancestral Longevity",
        data={
            **_ELF_FEAT_DATA,
            "prompt_notes": [
                "Przed scenariuszem wybierz niewytrenowaną umiejętność; masz w niej trained do końca scenariusza."
            ],
        },
    )


ANCESTRAL_LONGEVITY_STATUS = AncestralLongevityStatus()


def ElvenLoreStatus() -> Status:
    """Info: trained w Arcana, Nature, Lore."""
    return Status(
        id="feat_elven_lore",
        label="Elven Lore",
        data={
            **_ELF_FEAT_DATA,
            "prompt_notes": ["Masz trained w Arcana, Nature oraz Lore."],
        },
    )


ELVEN_LORE_STATUS = ElvenLoreStatus()


def ElvenWeaponMilitaryStatus() -> Status:
    """Info: trained w łukach i szablach elfickich."""
    return Status(
        id="feat_elven_weapon_military",
        label="Elven Weapon Military",
        data={
            **_ELF_FEAT_DATA,
            "prompt_notes": [
                "Jesteś trained w: długi łuk, kompozytowy długi łuk, długi miecz, rapier, krótki łuk, kompozytowy krótki łuk."
            ],
        },
    )


ELVEN_WEAPON_MILITARY_STATUS = ElvenWeaponMilitaryStatus()


def ForlornStatus() -> Status:
    """+1 circumstance vs saving_throw+emotions; sukces -> krytyk."""
    bonus = BonusEffect(
        type=BonusType.CIRCUMSTANCE,
        value=1,
        tag=None,  # nadamy per-skill
        source="feat:forlorn",
        label="+1 vs emotions",
    )
    effects = [
        CheckEffect(
            applies_to="target",
            skills=[skill],
            tags_required=["saving_throw", "emotions"],
            bonus_effects=[BonusEffect(**{**bonus.__dict__, "tag": skill})],
            promote=1,
            promote_on=["success"],
            prompt_notes=["Forlorn: +1 circumstance i sukces -> krytyczny sukces przeciw emotions."],
        )
        for skill in (Skill.FORTITUDE.value, Skill.REFLEX.value, Skill.WILL.value)
    ]
    return Status(
        id="feat_forlorn",
        label="Forlorn",
        data={**_ELF_FEAT_DATA},
        check_effects=effects,
    )


FORLORN_STATUS = ForlornStatus()


def NimbleElfStatus() -> Status:
    """Info: prędkość +5 stóp."""
    return Status(
        id="feat_nimble_elf",
        label="Nimble Elf",
        data={
            **_ELF_FEAT_DATA,
            "speed_bonus": 5,
            "prompt_notes": ["Twoja prędkość zwiększona o 5 stóp."],
        },
    )


NIMBLE_ELF_STATUS = NimbleElfStatus()


def OtherworldlyMagicStatus() -> Status:
    """Info: możesz rzucać dowolną cantrip (Arcana)."""
    return Status(
        id="feat_otherworldly_magic",
        label="Otherworldly Magic",
        data={
            **_ELF_FEAT_DATA,
            "prompt_notes": ["Możesz rzucać dowolną sztuczkę (cantrip) z listy Arcana."],
        },
    )


OTHERWORLDLY_MAGIC_STATUS = OtherworldlyMagicStatus()


def UnwaveringMienStatus() -> Status:
    """+1 circumstance vs sleep; sukces -> krytyk."""
    bonus = BonusEffect(
        type=BonusType.CIRCUMSTANCE,
        value=1,
        tag=None,
        source="feat:unwavering_mien",
        label="+1 vs sleep",
    )
    effects = [
        CheckEffect(
            applies_to="target",
            skills=[skill],
            tags_required=["sleep"],
            bonus_effects=[BonusEffect(**{**bonus.__dict__, "tag": skill})],
            promote=1,
            promote_on=["success"],
            prompt_notes=["Unwavering Mien: +1 circumstance; sukces przeciw sleep -> krytyczny sukces."],
        )
        for skill in (Skill.FORTITUDE.value, Skill.REFLEX.value, Skill.WILL.value)
    ]
    return Status(
        id="feat_unwavering_mien",
        label="Unwavering Mien",
        data={**_ELF_FEAT_DATA},
        check_effects=effects,
    )


UNWAVERING_MIEN_STATUS = UnwaveringMienStatus()


__all__ = [
    "AncestralLongevityStatus",
    "ANCESTRAL_LONGEVITY_STATUS",
    "ElvenLoreStatus",
    "ELVEN_LORE_STATUS",
    "ElvenWeaponMilitaryStatus",
    "ELVEN_WEAPON_MILITARY_STATUS",
    "ForlornStatus",
    "FORLORN_STATUS",
    "NimbleElfStatus",
    "NIMBLE_ELF_STATUS",
    "OtherworldlyMagicStatus",
    "OTHERWORLDLY_MAGIC_STATUS",
    "UnwaveringMienStatus",
    "UNWAVERING_MIEN_STATUS",
]
