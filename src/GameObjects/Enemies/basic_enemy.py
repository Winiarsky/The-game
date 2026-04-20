from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Optional

from GameObjects.interactions_mixin.bonus_mixin import BonusMixin
from GameObjects.interactions_mixin.magical_mixin import MagicalMixin
from GameObjects.interactions_mixin.status_mixin import StatusMixin
from GameObjects.interactions_mixin.watchful_mixin import WatchfulMixin
from GameObjects.interactions_mixin.reactive_mixin import ReactiveMixin
from GameObjects.Enemies.enemy_types import EnemyType
from combat.reactions import OpportunityAttack
from combat.damage_utils import apply_damage_resistance
from combat.hp_engine import apply_damage as hp_apply_damage
from combat.hp_engine import heal as hp_heal
from statuses import Status
from statuses import apply_shield_cantrip_absorb
from object_registry import assign_id
from damage_types import DamageType

logger = logging.getLogger(__name__)


@dataclass
class BasicEnemy(StatusMixin, BonusMixin, WatchfulMixin, ReactiveMixin, MagicalMixin):
    """Bazowa klasa przeciwnika do walki turowej."""

    name: str = "Enemy"
    hp: int = 10
    max_hp: int | None = None
    ac: int = 14
    ac_includes_armor_bonus: bool = True
    initiative_bonus: int = 0
    distance: int = 25
    base_speed_feet: int | None = None
    move_points: int | None = None
    attack_bonus: int = 0
    strength: int = 0
    dex_mod: int = 0
    fortitude_bonus: int = 0
    reflex_bonus: int = 0
    behavior_id: str | None = "basic_melee"
    reach: int = 1
    enemy_type: EnemyType | str = EnemyType.HUMAN
    watch_disturbed: int = 0  # 0 blokuje wejście w stealth w pokoju
    watch_disabled: bool = False
    perception_bonus: int = 4
    will_bonus: int = 0
    athletics_bonus: int = 0
    intimidation_bonus: int = 0
    stealth_bonus: int = 0
    traits: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    weapon_loadout: tuple[str, ...] = ()
    armor_loadout: tuple[str, ...] = ()
    inventory: list[object] = field(default_factory=list)
    equipped_weapon_item_ids: list[str] = field(default_factory=list)
    equipped_armor_item_id: str | None = None
    active_weapon: str | None = None
    weapon_attack_bonuses: dict[str, int] = field(default_factory=dict)
    weapon_damage_bonuses: dict[str, int] = field(default_factory=dict)
    special_actions: tuple[str, ...] = ()
    special_reactions: tuple[str, ...] = ()
    ai_profile: dict[str, object] = field(default_factory=dict)
    awareness_profile: dict[str, object] = field(default_factory=dict)
    ai_memory: dict[str, object] = field(default_factory=dict)
    auto_opportunity_attack: bool = True
    loot_items: list[object] = field(default_factory=list)
    loot_cp: int = 0
    coin_pouch: dict[str, int] = field(default_factory=dict)
    initiative: Optional[int] = None
    position: Optional[tuple[int, int]] = None
    statuses: list[Status] = field(default_factory=list)
    blocks_movement: bool = True
    object_id: str = field(init=False)

    def __post_init__(self):
        self.object_id = assign_id(self)
        if self.max_hp is None:
            try:
                self.max_hp = int(self.hp)
            except Exception:
                self.max_hp = 0
        if self.move_points is not None and (self.distance is None or self.distance == 25):
            try:
                self.distance = max(5, int(self.move_points) * 5)
            except Exception:
                self.distance = 25
        if self.base_speed_feet is None:
            try:
                self.base_speed_feet = max(5, int(self.distance or 25))
            except Exception:
                self.base_speed_feet = 25
        elif self.distance in (None, 25):
            try:
                self.distance = max(5, int(self.base_speed_feet))
            except Exception:
                self.distance = 25
        if self.auto_opportunity_attack and not self.reactions:
            try:
                self.reactions.append(OpportunityAttack())
            except Exception:
                pass
        try:
            from GameObjects.items.inventory import ensure_actor_inventory

            ensure_actor_inventory(self)
        except Exception:
            pass
        default_awareness = {
            "awareness_range_feet": 30,
            "move_trigger_threshold": 0.70,
            "interaction_trigger_threshold": 0.20,
            "spell_trigger_threshold": 0.40,
            "stealth_fail_trigger_threshold": 0.20,
        }
        merged_awareness = dict(default_awareness)
        if isinstance(self.awareness_profile, dict):
            merged_awareness.update(self.awareness_profile)
        self.awareness_profile = merged_awareness

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

    def current_hp(self) -> int:
        try:
            return int(self.hp)
        except Exception:
            return 0

    def hp_ratio(self) -> float:
        try:
            max_hp = max(1, int(self.max_hp or self.hp or 1))
            return max(0.0, min(1.0, float(self.current_hp()) / float(max_hp)))
        except Exception:
            return 0.0

    def is_dead(self) -> bool:
        return self.current_hp() <= 0

    def has_trait(self, trait: str) -> bool:
        needle = str(trait or "").strip().lower()
        if not needle:
            return False
        return needle in {str(item).strip().lower() for item in (self.traits or ())}

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
        if getattr(self, "has_status", lambda _s: False)("deafened"):
            roll -= 2
            try:
                from statuses import mark_deafened_initiative_applied

                mark_deafened_initiative_applied(self)
            except Exception:
                pass
        self.initiative = roll
        logger.info("%s rzuca inicjatywę: %s (bonus %s).", self.name, roll, self.initiative_bonus)
        return roll

    def apply_damage(
        self,
        amount: int,
        damage_type: str = DamageType.NORMAL.value,
        *,
        nonlethal: bool = False,
    ) -> tuple[int, bool]:
        """Odejmij HP i zwróć (aktualne_hp, czy_pokonany)."""
        effective, reduced = apply_damage_resistance(self, amount, damage_type)
        effective, _absorbed, _broken = apply_shield_cantrip_absorb(self, effective)
        info = hp_apply_damage(
            self,
            effective,
            damage_type,
            source=f"damage:{damage_type}",
            nonlethal=bool(nonlethal),
        )
        defeated = bool(info.get("defeated", False))
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

    def heal(self, amount: int) -> int:
        """Wylecz wroga (zwiększa HP, bez max HP)."""
        hp_heal(self, amount, source="heal")
        return self.hp

    def trigger_combat(self, game) -> None:
        """Wywołuje wejście w stan walki, gdy jesteśmy w turze bohaterów."""
        if getattr(self, "position", None) is None or int(getattr(self, "hp", 1) or 0) <= 0:
            logger.info("Pomijam trigger walki dla %s (brak pozycji lub HP <= 0).", self.name)
            return
        try:
            game.start_combat(trigger=self)
        except Exception as exc:
            logger.error("Nie udało się uruchomić walki: %s", exc)
