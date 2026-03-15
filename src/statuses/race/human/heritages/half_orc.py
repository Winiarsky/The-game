from __future__ import annotations

from statuses.base import Status
from statuses.dim_light_vision import DIM_LIGHT_VISION_STATUS

HALF_ORC_DESCRIPTION = (
    "Co najmniej jedno z twoich rodzicow jest orkiem lub polorkiem.\n"
    "Noszisz wyrazne oznaki orkowego pochodzenia.\n"
    "Zyskujesz cechy orc i half-orc oraz widzenie w polmroku.\n"
    "Dodatkowo przy wyborze ancestry featow mozesz wybierac featy\n"
    "z listy orc, half-orc i human."
)


def HalfOrcStatus() -> Status:
    """Heritage: Half-Orc."""
    return Status(
        id="half_orc",
        label="Half-Orc",
        data={
            "ui_description": HALF_ORC_DESCRIPTION,
            "ancestry_extra_traits": ["orc", "half_orc"],
            "ancestry_feat_access": ["orc", "half_orc", "human"],
            "grants_statuses": [DIM_LIGHT_VISION_STATUS],
        },
    )


HALF_ORC_STATUS = HalfOrcStatus()

__all__ = ["HalfOrcStatus", "HALF_ORC_STATUS", "HALF_ORC_DESCRIPTION"]
