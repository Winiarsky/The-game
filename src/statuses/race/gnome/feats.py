from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

_GNOME_FEAT_DATA = {"ancestry": "gnome", "feat": True, "traits": ["gnome", "feat"]}


def AnimalAccompliceStatus() -> Status:
    """Informacja: otrzymujesz zwierzęcego towarzysza."""
    return Status(
        id="feat_animal_accomplice",
        label="Animal Accomplice",
        data={
            **_GNOME_FEAT_DATA,
            "prompt_notes": ["Otrzymujesz zwierzęcego towarzysza (mechanika dojdzie później)."],
        },
    )


ANIMAL_ACCOMPLICE_STATUS = AnimalAccompliceStatus()


def FeyFellowshipStatus() -> Status:
    """+2 circumstance do Perception vs fey."""
    bonus = BonusEffect(
        type=BonusType.CIRCUMSTANCE,
        value=2,
        tag=Skill.PERCEPTION.value,
        source="feat:fey_fellowship",
        label="+2 Perception vs fey",
    )
    return Status(
        id="feat_fey_fellowship",
        label="Fey Fellowship",
        data={**_GNOME_FEAT_DATA},
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.PERCEPTION.value],
                tags_required=["fey"],
                bonus_effects=[bonus],
                prompt_notes=["+2 circumstance do testów Perception na eventach z tagiem fey."],
            )
        ],
    )


FEY_FELLOWSHIP_STATUS = FeyFellowshipStatus()


def FirstWorldMagicStatus() -> Status:
    """Informacja: cantrip z listy primal."""
    return Status(
        id="feat_first_world_magic",
        label="First World Magic",
        data={
            **_GNOME_FEAT_DATA,
            "prompt_notes": ["Wybierz jedną sztuczkę (cantrip) z listy primal i możesz ją rzucać."],
        },
    )


FIRST_WORLD_MAGIC_STATUS = FirstWorldMagicStatus()


def GnomeObsessionStatus() -> Status:
    """Informacja o progresji biegłości w wybranym Lore."""
    return Status(
        id="feat_gnome_obsession",
        label="Gnome Obsession",
        data={
            **_GNOME_FEAT_DATA,
            "prompt_notes": [
                "Wybierz Lore: trained teraz; na 2. poziomie expert w tym Lore i z tła; "
                "na 7. master w obu; na 15. legendary w obu.",
            ],
        },
    )


GNOME_OBSESSION_STATUS = GnomeObsessionStatus()


def GnomeWeaponFamiliarityStatus() -> Status:
    """Informacja o biegłości w gnome weapons."""
    return Status(
        id="feat_gnome_weapon_familiarity",
        label="Gnome Weapon Familiarity",
        data={
            **_GNOME_FEAT_DATA,
            "prompt_notes": [
                "Jesteś trained w glaive i kukri. Masz dostęp do kukri oraz wszystkich uncommon gnome weapons. "
                "Dla biegłości: martial gnome weapons traktuj jak simple, advanced gnome weapons jak martial.",
            ],
        },
    )


GNOME_WEAPON_FAMILIARITY_STATUS = GnomeWeaponFamiliarityStatus()


def IllusionSenseStatus() -> Status:
    """+1 circumstance do Perception/Will vs illusion."""
    bonus_perception = BonusEffect(
        type=BonusType.CIRCUMSTANCE,
        value=1,
        tag=Skill.PERCEPTION.value,
        source="feat:illusion_sense",
        label="+1 Perception vs illusion",
    )
    bonus_will = BonusEffect(
        type=BonusType.CIRCUMSTANCE,
        value=1,
        tag=Skill.WILL.value,
        source="feat:illusion_sense",
        label="+1 Will vs illusion",
    )
    return Status(
        id="feat_illusion_sense",
        label="Illusion Sense",
        data={**_GNOME_FEAT_DATA},
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.PERCEPTION.value],
                tags_required=["illusion"],
                bonus_effects=[bonus_perception],
                prompt_notes=["+1 circumstance do Perception lub Will na eventach z tagiem illusion."],
            ),
            CheckEffect(
                applies_to="source",
                skills=[Skill.WILL.value],
                tags_required=["illusion"],
                bonus_effects=[bonus_will],
                prompt_notes=["+1 circumstance do Perception lub Will na eventach z tagiem illusion."],
            ),
        ],
    )


ILLUSION_SENSE_STATUS = IllusionSenseStatus()


__all__ = [
    "AnimalAccompliceStatus",
    "ANIMAL_ACCOMPLICE_STATUS",
    "FeyFellowshipStatus",
    "FEY_FELLOWSHIP_STATUS",
    "FirstWorldMagicStatus",
    "FIRST_WORLD_MAGIC_STATUS",
    "GnomeObsessionStatus",
    "GNOME_OBSESSION_STATUS",
    "GnomeWeaponFamiliarityStatus",
    "GNOME_WEAPON_FAMILIARITY_STATUS",
    "IllusionSenseStatus",
    "ILLUSION_SENSE_STATUS",
]
