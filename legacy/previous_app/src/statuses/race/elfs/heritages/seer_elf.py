from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

SEER_ELF_DESCRIPTION = (
    "Wrodzona magia: Detect Magic (wrodzony czar tradycji arcane, at-will).\n"
    "Otrzymujesz +1 circumstance do identyfikacji magii i rozszyfrowywania "
    "magicznych zapisow (Arcana, Nature, Occultism, Religion).\n"
    "W tym silniku bonus działa przez tagi checka: identify_magic oraz "
    "decipher_writing+magic."
)


def SeerElfStatus() -> Status:
    """Heritage: Seer Elf."""
    bonus_effects = [
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=1,
            tag=Skill.ARCANA.value,
            source="status:seer_elf",
            label="seer elf",
        ),
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=1,
            tag=Skill.OCCULTISM.value,
            source="status:seer_elf",
            label="seer elf",
        ),
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=1,
            tag=Skill.NATURE.value,
            source="status:seer_elf",
            label="seer elf",
        ),
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=1,
            tag=Skill.RELIGION.value,
            source="status:seer_elf",
            label="seer elf",
        ),
    ]
    return Status(
        id="seer_elf",
        label="Seer Elf",
        data={
            "ui_description": SEER_ELF_DESCRIPTION,
            "granted_cantrips": ["detect_magic"],
            "innate_magic_tradition": "arcane",
        },
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[
                    Skill.ARCANA.value,
                    Skill.NATURE.value,
                    Skill.OCCULTISM.value,
                    Skill.RELIGION.value,
                ],
                tags_required=["identify_magic"],
                bonus_effects=bonus_effects,
                prompt_notes=["Seer Elf: +1 do Identify Magic."],
            ),
            CheckEffect(
                applies_to="source",
                skills=[
                    Skill.ARCANA.value,
                    Skill.NATURE.value,
                    Skill.OCCULTISM.value,
                    Skill.RELIGION.value,
                ],
                tags_required=["decipher_writing", "magic"],
                bonus_effects=bonus_effects,
                prompt_notes=["Seer Elf: +1 do magicznego Decipher Writing."],
            ),
        ],
    )


SEER_ELF_STATUS = SeerElfStatus()

__all__ = ["SeerElfStatus", "SEER_ELF_STATUS", "SEER_ELF_DESCRIPTION"]
