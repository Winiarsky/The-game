from __future__ import annotations

from statuses.base import Status

LINGERING_COMPOSITION_DESCRIPTION = (
    "Lingering Composition: 1 akcja i 1 Focus Point. Wykonujesz test Performance; "
    "na sukces nastepny composition cantrip w tej turze trwa 3 rundy, "
    "na krytyczny sukces 4 rundy."
)

LINGERING_COMPOSITION_PROMPT = (
    "Lingering Composition: odblokowujesz osobna akcje metamagiczna dla barda "
    "i zwiekszasz Focus Pool o 1."
)


def LingeringCompositionStatus() -> Status:
    """Feat: Lingering Composition."""
    return Status(
        id="lingering_composition",
        label="Lingering Composition",
        data={
            "ui_description": LINGERING_COMPOSITION_DESCRIPTION,
            "ui_prompt": LINGERING_COMPOSITION_PROMPT,
            "add_actor_attrs": {"focus_point": 1},
        },
    )


LINGERING_COMPOSITION_STATUS = LingeringCompositionStatus()

__all__ = [
    "LINGERING_COMPOSITION_DESCRIPTION",
    "LINGERING_COMPOSITION_PROMPT",
    "LingeringCompositionStatus",
    "LINGERING_COMPOSITION_STATUS",
]
