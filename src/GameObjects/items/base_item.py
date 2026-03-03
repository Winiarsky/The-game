from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4


def _new_instance_id() -> str:
    return f"item-{uuid4().hex[:10]}"


@dataclass
class BaseItem:
    item_id: str
    name: str
    category: str
    description: str = ""
    traits: tuple[str, ...] = ()
    instance_id: str = field(default_factory=_new_instance_id)

    def ui_description(self) -> str:
        traits = ", ".join(self.traits) if self.traits else "brak"
        if self.description:
            return f"{self.description}\nTraits: {traits}"
        return f"Traits: {traits}"


__all__ = [
    "BaseItem",
]
