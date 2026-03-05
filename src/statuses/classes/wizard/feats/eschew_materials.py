from __future__ import annotations

from statuses.base import Status

ESCHEW_MATERIALS_DESCRIPTION = (
    "Eschew Materials: możesz zastąpić standardowe komponenty materialne "
    "gestami sigili (nadal wymaga wolnej ręki i nie działa na komponenty z kosztem)."
)


def EschewMaterialsStatus() -> Status:
    return Status(
        id="eschew_materials",
        label="Eschew Materials",
        data={
            "ui_description": ESCHEW_MATERIALS_DESCRIPTION,
            "ui_prompt": ESCHEW_MATERIALS_DESCRIPTION,
        },
    )


ESCHEW_MATERIALS_STATUS = EschewMaterialsStatus()

__all__ = [
    "ESCHEW_MATERIALS_DESCRIPTION",
    "EschewMaterialsStatus",
    "ESCHEW_MATERIALS_STATUS",
]
