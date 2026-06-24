"""Magic traditions available to spells and effects."""

from __future__ import annotations

from enum import Enum


class SpellTradition(str, Enum):
    """Supported spell traditions.

    Values mirror the tradition identifiers used across the ruleset.
    """

    ARCANA = "arcana"
    PRIMAL = "primal"
    OCCULT = "occult"
    DIVINE = "divine"
