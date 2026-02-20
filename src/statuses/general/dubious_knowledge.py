from __future__ import annotations

from statuses.base import Status
from statuses.check_effects import CheckEffect

DUBIOUS_KNOWLEDGE_DESCRIPTION = (
    "Gdy nie zdasz (ale nie krytycznie) Recall Knowledge, otrzymujesz prawdziwa i falszywa "
    "informacje, bez mozliwosci odroznienia. Uproszczenie: sukces z tagiem knowledge "
    "staje sie krytycznym sukcesem."
)


def DubiousKnowledgeStatus() -> Status:
    """Feat: Dubious Knowledge (opis do UI)."""
    return Status(
        id="dubious_knowledge",
        label="Dubious Knowledge",
        data={"ui_description": DUBIOUS_KNOWLEDGE_DESCRIPTION},
        check_effects=[
            CheckEffect(
                applies_to="source",
                tags_required=["knowledge"],
                promote=1,
                promote_on=["success"],
                prompt_notes=["Dubious Knowledge: sukces (knowledge) -> krytyczny sukces."],
            )
        ],
    )


DUBIOUS_KNOWLEDGE_STATUS = DubiousKnowledgeStatus()

__all__ = [
    "DubiousKnowledgeStatus",
    "DUBIOUS_KNOWLEDGE_STATUS",
    "DUBIOUS_KNOWLEDGE_DESCRIPTION",
]
