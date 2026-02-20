from __future__ import annotations

from statuses.base import Status

ALCHEMIST_RESEARCH_FIELD_PROMPT = (
    "Research Field (Alchemist)\n"
    "Wybierz pole badań: Bomber, Chirurgeon lub Mutagenist.\n"
    "Twoje pole badań dodaje formuły do księgi: są to twoje signature items.\n"
    "Gdy wytwarzasz signature items w Advanced Alchemy, tworzysz 3 sztuki zamiast 2.\n"
    "Przy awansie poziomu możesz zamienić jeden signature item na inny z listy pola.\n"
)


def AlchemistResearchFieldStatus() -> Status:
    """Bonusowy status: wybór Research Field dla alchemika."""
    return Status(
        id="alchemist_research_field",
        label="Research Field",
        data={
            "ui_prompt": ALCHEMIST_RESEARCH_FIELD_PROMPT,
            "ui_choice_kind": "alchemist_research_field",
            "research_field_choices": ["bomber", "chirurgeon", "mutagenist"],
        },
    )


ALCHEMIST_RESEARCH_FIELD_STATUS = AlchemistResearchFieldStatus()

__all__ = [
    "ALCHEMIST_RESEARCH_FIELD_PROMPT",
    "AlchemistResearchFieldStatus",
    "ALCHEMIST_RESEARCH_FIELD_STATUS",
]
