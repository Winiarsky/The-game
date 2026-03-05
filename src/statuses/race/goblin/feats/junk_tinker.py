from __future__ import annotations

from statuses.base import Status

JUNK_TINKER_DESCRIPTION = (
    "Potrafisz tworzyć użyteczne rzeczy ze złomu.\n"
    "Przy Crafting możesz tworzyć level 0 items (w tym broń, ale nie armor) ze złomu "
    "za 1/4 ceny; wynik to shoddy item.\n"
    "Nie dostajesz kary za używanie shoddy items, które sam wytworzyłeś.\n"
    "Przy dowolnym Craft możesz też użyć złomu, co daje dodatkową redukcję ceny "
    "jak za 1 dzień pracy więcej."
)


def JunkTinkerStatus() -> Status:
    """Feat: Junk Tinker."""
    return Status(
        id="junk_tinker",
        label="Junk Tinker",
        data={
            "ui_description": JUNK_TINKER_DESCRIPTION,
            "junk_tinker_can_craft_level0_from_junk": True,
            "junk_tinker_allows_weapons_not_armor": True,
            "junk_tinker_price_multiplier_level0": 0.25,
            "junk_tinker_result_is_shoddy": True,
            "junk_tinker_ignore_selfmade_shoddy_penalty": True,
            "junk_tinker_extra_discount_days": 1,
        },
    )


JUNK_TINKER_STATUS = JunkTinkerStatus()

__all__ = ["JunkTinkerStatus", "JUNK_TINKER_STATUS", "JUNK_TINKER_DESCRIPTION"]
