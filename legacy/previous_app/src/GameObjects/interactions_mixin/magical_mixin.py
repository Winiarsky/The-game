from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass
class MagicalMixin:
    """Mixin dla obiektów nasyconych magią (opis + tag)."""

    magical: bool = False
    magical_description: str = ""
    tags: list[str] = field(default_factory=list)

    def magic_tags(self) -> list[str]:
        tags = list(self.tags or [])
        if self.magical and "magical" not in tags:
            tags.append("magical")
        return tags

    def has_tag(self, tag: str) -> bool:
        return tag in set(self.magic_tags())

    def add_tags(self, tags: Iterable[str]) -> None:
        for tag in tags:
            if tag and tag not in self.tags:
                self.tags.append(tag)
