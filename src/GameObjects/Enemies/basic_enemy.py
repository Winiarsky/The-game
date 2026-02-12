from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Optional

from GameObjects.interactions_mixin.bonus_mixin import BonusMixin
from GameObjects.interactions_mixin.status_mixin import StatusMixin
from GameObjects.interactions_mixin.watchful_mixin import WatchfulMixin
from GameObjects.interactions_mixin.reactive_mixin import ReactiveMixin
from combat.reactions import OpportunityAttack
from combat.damage_utils import apply_damage_resistance
from statuses import Status
from object_registry import assign_id
from damage_types import DamageType

logger = logging.getLogger(__name__)


@dataclass
class BasicEnemy(StatusMixin, BonusMixin, WatchfulMixin, ReactiveMixin):
    """Bazowa klasa przeciwnika do walki turowej."""

    name: str = "Enemy"
    hp: int = 10
    ac: int = 14
    initiative_bonus: int = 0
    move_points: int = 3
    attack_bonus: int = 0
    strength: int = 0
    behavior_id: str | None = "basic_melee"
    reach: int = 1
    watch_disturbed: int = 0  # 0 blokuje wejście w stealth w pokoju
    watch_disabled: bool = False
    perception_bonus: int = 4
    initiative: Optional[int] = None
    position: Optional[tuple[int, int]] = None
    statuses: list[Status] = field(default_factory=list)
    blocks_movement: bool = True
    object_id: str = field(init=False)

    def __post_init__(self):
        self.object_id = assign_id(self)
        if not self.reactions:
            try:
                self.reactions.append(OpportunityAttack())
            except Exception:
                pass

    def __hash__(self):
        return hash(self.object_id)

    def __eq__(self, other):
        if not isinstance(other, BasicEnemy):
            return False
        return self.object_id == other.object_id

    def __repr__(self):
        return f"{self.name}(hp={self.hp}, ac={self.ac}, init={self.initiative})"

    def set_position(self, position: Optional[tuple[int, int]]) -> None:
        self.position = position

    def on_spot(self, hero, game) -> Optional[str]:
        """Po wykryciu bohatera przeciwnik wywołuje walkę."""
        try:
            state = getattr(game, "state", None)
            in_combat = getattr(state, "__class__", None).__name__ == "Combat"
            if not in_combat:
                self.trigger_combat(game)
            return f"{self.name} zauważa bohatera i szykuje się do walki."
        except Exception as exc:
            logger.error("Nie udało się uruchomić walki po wykryciu: %s", exc)
            return f"{self.name} dostrzega ruch, ale coś poszło nie tak."

    def roll_initiative(self) -> int:
        """Losowy rzut inicjatywy dla wrogów."""
        roll = random.randint(1, 20) + self.initiative_bonus
        self.initiative = roll
        logger.info("%s rzuca inicjatywę: %s (bonus %s).", self.name, roll, self.initiative_bonus)
        return roll

    def apply_damage(self, amount: int, damage_type: str = DamageType.NORMAL.value) -> tuple[int, bool]:
        """Odejmij HP i zwróć (aktualne_hp, czy_pokonany)."""
        effective, reduced = apply_damage_resistance(self, amount, damage_type)
        self.hp -= effective
        defeated = self.hp <= 0
        reduction_note = f" (zredukowano o {reduced})" if reduced else ""
        logger.info(
            "%s otrzymuje %s obrażeń %s%s (HP: %s).",
            self.name,
            effective,
            damage_type,
            reduction_note,
            self.hp,
        )
        return self.hp, defeated

    def trigger_combat(self, game) -> None:
        """Wywołuje wejście w stan walki, gdy jesteśmy w turze bohaterów."""
        try:
            game.start_combat(trigger=self)
        except Exception as exc:
            logger.error("Nie udało się uruchomić walki: %s", exc)
