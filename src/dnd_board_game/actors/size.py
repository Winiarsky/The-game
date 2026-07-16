"""D&D 5e creature-size ordering and size-based eligibility rules."""

from __future__ import annotations

from enum import StrEnum


class CreatureSize(StrEnum):
    TINY = "tiny"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    HUGE = "huge"
    GARGANTUAN = "gargantuan"


CREATURE_SIZE_ORDER = (
    CreatureSize.TINY,
    CreatureSize.SMALL,
    CreatureSize.MEDIUM,
    CreatureSize.LARGE,
    CreatureSize.HUGE,
    CreatureSize.GARGANTUAN,
)

_SIZE_LABELS_PL = {
    CreatureSize.TINY: "malutki",
    CreatureSize.SMALL: "mały",
    CreatureSize.MEDIUM: "średni",
    CreatureSize.LARGE: "duży",
    CreatureSize.HUGE: "ogromny",
    CreatureSize.GARGANTUAN: "kolosalny",
}


def creature_size_rank(size: CreatureSize) -> int:
    return CREATURE_SIZE_ORDER.index(size)


def creature_size_label_pl(size: CreatureSize) -> str:
    return _SIZE_LABELS_PL[size]


def can_grapple_or_shove_size(attacker: CreatureSize, target: CreatureSize) -> bool:
    """A target can be no more than one size category larger than the attacker."""

    return creature_size_rank(target) <= creature_size_rank(attacker) + 1


def largest_grapple_or_shove_target(attacker: CreatureSize) -> CreatureSize:
    return CREATURE_SIZE_ORDER[min(len(CREATURE_SIZE_ORDER) - 1, creature_size_rank(attacker) + 1)]


__all__ = [
    "CREATURE_SIZE_ORDER",
    "CreatureSize",
    "can_grapple_or_shove_size",
    "creature_size_label_pl",
    "creature_size_rank",
    "largest_grapple_or_shove_target",
]
