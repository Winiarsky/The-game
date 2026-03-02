from __future__ import annotations

from statuses.base import Status

LINGERING_COMPOSITION_DESCRIPTION = (
    "Lingering Composition: naucz sie focus spell 'Lingering Composition' "
    "(dopisanie do znanych czarow recznie)."
)

LINGERING_COMPOSITION_PROMPT = (
    "Lingering Composition: dopisz do listy znanych czarow focus spell "
    "'Lingering Composition'. Zwiekszasz Focus Pool o 1 (mechanicznie)."
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
