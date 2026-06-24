from __future__ import annotations

from statuses.base import Status

ORC_FEROCITY_DESCRIPTION = (
    "Mechanika: raz dziennie, gdy mialbys spasc do 0 HP (i nie giniesz natychmiast), "
    "zostajesz na 1 HP.\n"
    "Efekt uboczny: twoj wounded wzrasta o 1."
)


def OrcFerocityStatus() -> Status:
    """Feat: Orc Ferocity (opis do UI)."""
    return Status(
        id="orc_ferocity",
        label="Orcza zajadlosc",
        data={
            "ui_description": ORC_FEROCITY_DESCRIPTION,
            "used_today": False,
            "frequency_per_day": 1,
        },
    )


ORC_FEROCITY_STATUS = OrcFerocityStatus()

__all__ = ["OrcFerocityStatus", "ORC_FEROCITY_STATUS", "ORC_FEROCITY_DESCRIPTION"]
