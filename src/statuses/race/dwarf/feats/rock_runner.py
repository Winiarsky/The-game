from __future__ import annotations

from statuses.base import Status

ROCK_RUNNER_DESCRIPTION = "Ignorujesz kary do ruchu za trudny kamienisty teren."


def RockRunnerStatus() -> Status:
    """Feat: Rock Runner."""
    return Status(
        id="rock_runner",
        label="Rock Runner",
        data={
            "ui_description": ROCK_RUNNER_DESCRIPTION,
            "ignore_move_cost_terrain_tags": ["rumble"],
        },
    )


ROCK_RUNNER_STATUS = RockRunnerStatus()

__all__ = ["RockRunnerStatus", "ROCK_RUNNER_STATUS", "ROCK_RUNNER_DESCRIPTION"]
