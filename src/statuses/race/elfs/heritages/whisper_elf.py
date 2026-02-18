from __future__ import annotations

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
                prompt_notes=["Whisper Elf: +4 do Perception (dolicz ręcznie)."],
            )
        ],
    )


WHISPER_ELF_STATUS = WhisperElfStatus()

__all__ = ["WhisperElfStatus", "WHISPER_ELF_STATUS", "WHISPER_ELF_DESCRIPTION"]
