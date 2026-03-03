from __future__ import annotations

from statuses.base import Status

DOUBLE_SLICE_DESCRIPTION = (
    "Double Slice: 2 akcje, dwa Strikes dwiema broniami melee 1H. "
    "Uproszczenie v1: obrażenia rozliczane osobno, ale oba ataki używają tego samego MAP bazowego."
)


def DoubleSliceStatus() -> Status:
    return Status(
        id="double_slice",
        label="Double Slice",
        data={"ui_description": DOUBLE_SLICE_DESCRIPTION, "ui_prompt": DOUBLE_SLICE_DESCRIPTION},
    )


DOUBLE_SLICE_STATUS = DoubleSliceStatus()

__all__ = ["DoubleSliceStatus", "DOUBLE_SLICE_STATUS", "DOUBLE_SLICE_DESCRIPTION"]
