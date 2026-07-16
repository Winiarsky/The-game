from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, NewType

from .damage_affinities import DamageAffinityProfile
from .auras import ActorAura
from .triggers import ActorTrigger
from .proficiency_profile import ProficiencyProfile
from .size import CreatureSize

if TYPE_CHECKING:
    from dnd_board_game.actors.resources import ActorResourcePool, HitDicePool
    from dnd_board_game.actors.spell_preparation import SpellPreparationProfile
    from dnd_board_game.combat.spells import SpellSlotState
    from dnd_board_game.inventory import InventoryItem
    from dnd_board_game.world.coordinates import Coordinate


ActorId = NewType("ActorId", str)


class Faction(StrEnum):
    ALLY = "ally"
    ENEMY = "enemy"
    NEUTRAL = "neutral"


@dataclass(frozen=True, slots=True)
class AbilityScores:
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10


@dataclass(frozen=True, slots=True)
class DeathSaveState:
    successes: int = 0
    failures: int = 0
    stable: bool = False
    dead: bool = False

    def __post_init__(self) -> None:
        if not 0 <= self.successes <= 3 or not 0 <= self.failures <= 3:
            raise ValueError("Death save successes and failures must be between 0 and 3.")
        if self.stable and self.dead:
            raise ValueError("An actor cannot be both stable and dead.")


@dataclass(frozen=True, slots=True)
class Actor:
    id: ActorId
    name: str
    ac: int
    hp: int
    temp_hp: int
    speed_feet: int
    position: Coordinate
    faction: Faction
    max_hp: int = 0
    ability_scores: AbilityScores = field(default_factory=AbilityScores)
    spell_slots: tuple[SpellSlotState, ...] = ()
    spell_save_dc: int = 0
    inventory: tuple[InventoryItem, ...] = ()
    spell_ids: tuple[str, ...] = ()
    spell_preparation: SpellPreparationProfile | None = None
    hit_dice: tuple[HitDicePool, ...] = ()
    resource_pools: tuple[ActorResourcePool, ...] = ()
    proficiency_bonus: int = 2
    proficiencies: ProficiencyProfile = field(default_factory=ProficiencyProfile)
    uses_death_saves: bool = False
    death_saves: DeathSaveState = field(default_factory=DeathSaveState)
    size: CreatureSize = CreatureSize.MEDIUM
    damage_affinities: DamageAffinityProfile = field(default_factory=DamageAffinityProfile)
    attacks_per_action: int = 1
    condition_immunities: tuple[str, ...] = ()
    auras: tuple[ActorAura, ...] = ()
    triggers: tuple[ActorTrigger, ...] = ()

    def __post_init__(self) -> None:
        if self.max_hp <= 0:
            object.__setattr__(self, "max_hp", max(0, self.hp))
        if self.proficiency_bonus < 0:
            raise ValueError("Proficiency bonus cannot be negative.")
        if self.attacks_per_action < 1:
            raise ValueError("Attacks per action must be at least 1.")
        if any(not condition.strip() for condition in self.condition_immunities):
            raise ValueError("Condition immunity ids cannot be empty.")
        if len(self.condition_immunities) != len(set(self.condition_immunities)):
            raise ValueError("Condition immunity ids cannot contain duplicates.")
        aura_ids = tuple(aura.id for aura in self.auras)
        if len(aura_ids) != len(set(aura_ids)):
            raise ValueError("Actor aura ids cannot contain duplicates.")
        trigger_ids = tuple(trigger.id for trigger in self.triggers)
        if len(trigger_ids) != len(set(trigger_ids)):
            raise ValueError("Actor trigger ids cannot contain duplicates.")

    @property
    def skill_proficiencies(self) -> tuple[str, ...]:
        return self.proficiencies.skills

    @property
    def skill_expertise(self) -> tuple[str, ...]:
        return self.proficiencies.expertise

    def is_defeated(self) -> bool:
        return self.hp <= 0

    def is_dead(self) -> bool:
        return self.death_saves.dead or (self.hp <= 0 and not self.uses_death_saves)

    def is_unconscious(self) -> bool:
        return self.uses_death_saves and self.hp <= 0 and not self.death_saves.dead

    def needs_death_save(self) -> bool:
        return self.is_unconscious() and not self.death_saves.stable

    def can_take_combat_turn(self) -> bool:
        return self.hp > 0 or self.needs_death_save()


def is_ally_or_neutral(mover: Actor, other: Actor) -> bool:
    if other.faction == Faction.NEUTRAL:
        return True
    if mover.faction == Faction.NEUTRAL:
        return other.faction == Faction.NEUTRAL
    return mover.faction == other.faction
