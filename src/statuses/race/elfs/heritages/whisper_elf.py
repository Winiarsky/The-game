from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

WHISPER_ELF_DESCRIPTION = (
    "Whisper Elf:\n"
    "- Przy akcji Seek zwiekszasz zasieg przeszukiwania z 30 do 60 stop.\n"
    "- Otrzymujesz +2 circumstance do namierzania niewykrytych stworzen, ktore slyszysz, "
    "w obrebie 30 stop (tagi: seek + undetected + auditory)."
)


def WhisperElfStatus() -> Status:
    """Heritage: Whisper Elf."""
    return Status(
        id="whisper_elf",
        label="Whisper Elf",
        data={
            "ui_description": WHISPER_ELF_DESCRIPTION,
            "seek_sense_radius_feet": 60,
            "seek_audio_locate_bonus_within_feet": 30,
        },
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.PERCEPTION.value],
                tags_required=["seek", "undetected", "auditory"],
                bonus_effects=[
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=2,
                        tag=Skill.PERCEPTION.value,
                        source="status:whisper_elf",
                        label="whisper elf +2",
                    )
                ],
                prompt_notes=["Whisper Elf: +2 do audio Seek vs undetected."],
            )
        ],
    )


WHISPER_ELF_STATUS = WhisperElfStatus()

__all__ = ["WhisperElfStatus", "WHISPER_ELF_STATUS", "WHISPER_ELF_DESCRIPTION"]
