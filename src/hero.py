from dataclasses import dataclass, field
from typing import List, Optional

from GameObjects.interactions_mixin import BonusMixin, StatusMixin, ReactiveMixin
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources
from skills import Skill
from combat.reactions import OpportunityAttack
from combat.damage_utils import apply_damage_resistance
from damage_types import DamageType
from object_registry import assign_id

# to do make hero scrpt, 
@dataclass
class Hero(StatusMixin, BonusMixin, ReactiveMixin):
    object_id: str = field(init=False)
    position: Optional[tuple[int, int]] = None
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    neighbors: List[tuple[int, int]] = field(default_factory=list)
    initiative: Optional[int] = None
    wounds: int = 0
    level: int = 1

    def __post_init__(self):
        self.object_id = assign_id(self)
        if self.position is not None:
            self.position_x, self.position_y = self.position
        if not self.reactions:
            self.reactions.append(OpportunityAttack())

    def __repr__(self):
        return f"position: {self.position}"

    def __hash__(self):
        return hash(self.object_id)
    
    def __eq__(self, other):
        if not isinstance(other, Hero):
            return False
        return self.object_id == other.object_id

    def set_position(self, position: Optional[tuple[int, int]]):
        self.position = position
        if position is None:
            self.position_x = None
            self.position_y = None
        else:
            self.position_x, self.position_y = position

    def make_move(self, action: str, connection):
        pass

    def _get_neighbors(self):
        pass

    def _light_tiles(self, connection):
        pass

    def roll_for_initiative(self) -> int:
        """Test inicjatywy: Perception z tagiem initiative (uwzględnia premie/kary)."""
        resolution = resolve_skill_check_with_sources(
            skill_id=Skill.PERCEPTION.value,
            dc=0,
            actor=self,
            tags=["initiative"],
            game=None,
            apply_modifiers=False,
        )
        self.initiative = resolution.total
        return resolution.total

    def apply_damage(self, amount: int, damage_type: str = DamageType.NORMAL.value) -> tuple[int, bool]:
        """Zastosuj obrażenia na bohaterze (uwzględnia redukcje ze statusów)."""
        effective, _ = apply_damage_resistance(self, amount, damage_type)
        try:
            self.wounds += effective  # type: ignore[attr-defined]
        except Exception:
            self.wounds = getattr(self, "wounds", 0) + effective  # type: ignore[attr-defined]
        return self.wounds, False
