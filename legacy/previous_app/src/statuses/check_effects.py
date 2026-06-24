from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional, Sequence

from bonuses import BonusEffect


@dataclass(frozen=True)
class CheckEffect:
    """Reguła modyfikująca test umiejętności."""

    applies_to: str  # "source" lub "target"
    skills: Optional[Sequence[str]] = None          # lista identyfikatorów skilli
    tags_required: Optional[Sequence[str]] = None   # tagi które muszą wystąpić w teście
    bonus_effects: Sequence[BonusEffect] = field(default_factory=tuple)
    promote: int = 0    # +1 podnosi sukces o 1 stopień
    demote: int = 0     # -1 obniża sukces o 1 stopień
    promote_on: Optional[Sequence[str]] = None  # ogranicz do wybranych wyników (np. tylko success)
    demote_on: Optional[Sequence[str]] = None   # jw.
    prompt_notes: Sequence[str] = field(default_factory=tuple)

    def matches(self, skill_id: str, tags: Iterable[str]) -> bool:
        tags_set = set(tags)
        if self.skills and skill_id not in self.skills:
            return False
        if self.tags_required:
            if not set(self.tags_required).issubset(tags_set):
                return False
        return True
