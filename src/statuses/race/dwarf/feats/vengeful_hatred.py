from __future__ import annotations

from typing import Any

from statuses.base import Status

VENGEFUL_HATRED_DESCRIPTION = (
    "Wybierz typ przeciwnika, wszystkie obrazenia zadawane przez Ciebie "
    "przeciwnikom wybranego typu zostaja zwiekszone o 1."
)


def VengefulHatredStatus(enemy_type: Any) -> Status:
    """Feat: Vengeful Hatred.

    enemy_type: typ przeciwnika (wartosc z EnemyType albo string).
    """
    return Status(
        id="vengeful_hatred",
        label="Vengeful Hatred",
        data={
            "ui_description": VENGEFUL_HATRED_DESCRIPTION,
            "enemy_type": enemy_type,
            "damage_bonus": 1,
        },
    )


__all__ = ["VengefulHatredStatus", "VENGEFUL_HATRED_DESCRIPTION"]
