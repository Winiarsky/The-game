from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

WHISPER_ELF_DESCRIPTION = (
    "otrzymujesz  premie +4 do Percepcji i jestes odpowrny na status Blind"
)


def WhisperElfStatus() -> Status:
    """Heritage: Whisper Elf."""
    return Status(
        id="whisper_elf",
        label="Whisper Elf",
        data={
            "ui_description": WHISPER_ELF_DESCRIPTION,
            "immune_status_ids": ["blinded"],
        },
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=[Skill.PERCEPTION.value],
                bonus_effects=[
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=4,
                        tag=Skill.PERCEPTION.value,
                        source="status:whisper_elf",
                        label="whisper elf +4",
                    )
                ],
                prompt_notes=["Whisper Elf: +4 do Perception."],
            )
        ],
    )


WHISPER_ELF_STATUS = WhisperElfStatus()

__all__ = ["WhisperElfStatus", "WHISPER_ELF_STATUS", "WHISPER_ELF_DESCRIPTION"]
