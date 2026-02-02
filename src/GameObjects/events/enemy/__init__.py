"""Enemy-controlled events."""

from .enemy_move_event import EnemyMoveEvent  # noqa: F401
from .enemy_attack_melee_event import EnemyAttackMeleeEvent  # noqa: F401

__all__ = [
    "EnemyMoveEvent",
    "EnemyAttackMeleeEvent",
    "enemy_move_event",
    "enemy_attack_melee_event",
]

from . import enemy_move_event  # type: ignore  # noqa: F401,E402
from . import enemy_attack_melee_event  # type: ignore  # noqa: F401,E402
