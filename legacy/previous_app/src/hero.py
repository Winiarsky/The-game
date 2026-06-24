from dataclasses import dataclass, field
from typing import List, Optional

from GameObjects.interactions_mixin import BonusMixin, StatusMixin, ReactiveMixin
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources
from skills import Skill
from combat.reactions import OpportunityAttack
from combat.damage_utils import apply_damage_resistance
from combat.hp_engine import apply_damage as hp_apply_damage
from combat.hp_engine import current_hp as hp_current_hp
from combat.hp_engine import heal as hp_heal
from combat.hp_engine import get_temp_hp as hp_get_temp_hp
from damage_types import DamageType
from statuses import apply_shield_cantrip_absorb
from statuses import is_dead as status_is_dead
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
    max_hp: int = 20
    temp_hp: int = 0
    coin_pouch: dict[str, int] = field(default_factory=lambda: {"cp": 0, "sp": 0, "gp": 0, "pp": 0})
    track_ammo: bool = False

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
            apply_modifiers=True,
        )
        if getattr(self, "has_status", lambda _s: False)("deafened"):
            try:
                from statuses import mark_deafened_initiative_applied

                mark_deafened_initiative_applied(self)
            except Exception:
                pass
        self.initiative = resolution.total
        return resolution.total

    def apply_damage(
        self,
        amount: int,
        damage_type: str = DamageType.NORMAL.value,
        *,
        nonlethal: bool = False,
    ) -> tuple[int, bool]:
        """Zastosuj obrażenia na bohaterze (uwzględnia redukcje ze statusów)."""
        effective, _ = apply_damage_resistance(self, amount, damage_type)
        effective, _absorbed, _broken = apply_shield_cantrip_absorb(self, effective)
        info = hp_apply_damage(
            self,
            effective,
            damage_type,
            source=f"damage:{damage_type}",
            nonlethal=bool(nonlethal),
        )
        return int(getattr(self, "wounds", 0) or 0), bool(info.get("defeated", False))

    def heal(self, amount: int) -> int:
        """Wylecz bohatera (wounds-model, ograniczone przez efektywne max HP)."""
        hp_heal(self, amount, source="heal")
        return int(getattr(self, "wounds", 0) or 0)

    def is_dead(self) -> bool:
        return bool(status_is_dead(self))

    def current_hp(self) -> int:
        return max(0, int(hp_current_hp(self) or 0))

    def current_temp_hp(self) -> int:
        return max(0, int(hp_get_temp_hp(self) or 0))
