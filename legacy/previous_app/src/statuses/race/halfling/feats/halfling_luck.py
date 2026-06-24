from __future__ import annotations

from statuses.base import Status

HALFLING_LUCK_DESCRIPTION = (
    "Fluff: Halfling Luck oddaje legendarna zdolnosc niziolkow do wychodzenia calo z sytuacji, ktore powinny skonczyc sie katastrofa.\n"
    "Mechanika:\n"
    "- Kiedy: Gdy oblejesz skill check albo saving throw.\n"
    "- Efekt:\n"
    "  - Raz dziennie mozesz aktywowac Halfling Luck i wykonac przerzut.\n"
    "  - Gra pyta wtedy, czy chcesz wykonac przerzut.\n"
    "  - Musisz uzyc nowego wyniku, nawet jesli jest gorszy.\n"
    "  - Po uzyciu feat sie wyczerpuje do kolejnego dnia.\n"
    "  - Przykład: oblewasz Will save przeciw Fear, aktywujesz Halfling Luck i rzucasz ponownie."
)


def HalflingLuckStatus() -> Status:
    """Feat: Halfling Luck."""
    return Status(
        id="halfling_luck",
        label="Halfling Luck",
        data={
            "ui_description": HALFLING_LUCK_DESCRIPTION,
            "frequency_per_day": 1,
            "fortune": True,
            "trigger_on_failure_skills_and_saves": True,
        },
    )


HALFLING_LUCK_STATUS = HalflingLuckStatus()

__all__ = ["HalflingLuckStatus", "HALFLING_LUCK_STATUS", "HALFLING_LUCK_DESCRIPTION"]
