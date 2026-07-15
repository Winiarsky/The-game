from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InteractionConversationEntry:
    """A persisted message belonging to one exploration interaction instance."""

    interaction_id: str
    role: str
    title: str
    body: str
    outcome: str = ""
    grounded_fact_ids: tuple[str, ...] = ()
    hint_level: int = 0

    def __post_init__(self) -> None:
        if self.role not in {"player", "gm"}:
            raise ValueError(f"Unknown conversation role: {self.role}.")
        if len(self.grounded_fact_ids) != len(set(self.grounded_fact_ids)):
            raise ValueError("Conversation fact ids cannot contain duplicates.")
        if not 0 <= self.hint_level <= 3:
            raise ValueError("Conversation hint level must be between 0 and 3.")

    def as_payload(self) -> dict[str, object]:
        return {
            "interaction_id": self.interaction_id,
            "role": self.role,
            "title": self.title,
            "body": self.body,
            "outcome": self.outcome,
            "grounded_fact_ids": list(self.grounded_fact_ids),
            "hint_level": self.hint_level,
        }
