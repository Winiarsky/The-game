from __future__ import annotations

from statuses.base import Status

OTHERWORLDLY_MAGIC_DESCRIPTION = (
    "wybierz sztuczke ze szkoly arcana, mozesz jej uzywac w dowolnej chwili"
)


def OtherworldlyMagicStatus() -> Status:
    """Feat: Otherworldly Magic (opis do UI)."""
    return Status(
        id="otherworldly_magic",
        label="Otherworldly Magic",
        data={"ui_description": OTHERWORLDLY_MAGIC_DESCRIPTION},
    )


OTHERWORLDLY_MAGIC_STATUS = OtherworldlyMagicStatus()

__all__ = [
    "OtherworldlyMagicStatus",
    "OTHERWORLDLY_MAGIC_STATUS",
    "OTHERWORLDLY_MAGIC_DESCRIPTION",
]
