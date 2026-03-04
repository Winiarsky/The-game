from __future__ import annotations

from statuses.base import Status

TWIN_FEINT_DESCRIPTION = (
    "Twin Feint: wykonaj 2 melee Strikes dwiema broniami przeciw temu samemu celowi. "
    "Cel jest automatycznie flat-footed przeciw drugiemu atakowi."
)


def TwinFeintStatus() -> Status:
    return Status(
        id="twin_feint",
        label="Twin Feint",
        data={
            "ui_description": TWIN_FEINT_DESCRIPTION,
            "ui_prompt": TWIN_FEINT_DESCRIPTION,
            "allowed_classes": ["rogue"],
        },
    )


TWIN_FEINT_STATUS = TwinFeintStatus()

__all__ = ["TWIN_FEINT_DESCRIPTION", "TwinFeintStatus", "TWIN_FEINT_STATUS"]
