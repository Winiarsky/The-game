from __future__ import annotations

from enum import Enum


class EnemyType(str, Enum):
    """Typy przeciwników wykorzystywane przez feat Vengeful Hatred i przyszłe efekty."""

    HUMAN = "human"
    ORC = "orc"
    GOBLIN = "goblin"


__all__ = ["EnemyType"]
