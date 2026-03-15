from __future__ import annotations

from statuses.base import Status

ELF_ATAVISM_DESCRIPTION = (
    "Mechanika: wybierasz 1 elfie heritage i zyskujesz jego efekt.\n"
    "Specjalne: tylko na 1. poziomie; bez retrainu."
)


def ElfAtavismStatus() -> Status:
    """Feat: Elf Atavism."""
    return Status(
        id="elf_atavism",
        label="Elficki atawizm",
        data={
            "ui_description": ELF_ATAVISM_DESCRIPTION,
            "ui_choice_kind": "elf_atavism",
            "elf_atavism_choices": [
                "arctic_elf",
                "cavern_elf",
                "seer_elf",
                "whisper_elf",
                "woodland_elf",
            ],
            "elf_atavism_choice": None,
            "requires_level_max": 1,
        },
    )


ELF_ATAVISM_STATUS = ElfAtavismStatus()

__all__ = ["ElfAtavismStatus", "ELF_ATAVISM_STATUS", "ELF_ATAVISM_DESCRIPTION"]
