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

    def as_payload(self) -> dict[str, str]:
        return {
            "interaction_id": self.interaction_id,
            "role": self.role,
            "title": self.title,
            "body": self.body,
            "outcome": self.outcome,
        }
