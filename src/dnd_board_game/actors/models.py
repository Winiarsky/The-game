from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, NewType

from .damage_affinities import DamageAffinityProfile
from .auras import ActorAura
from .features import FeatureGrant, validate_unique_feature_grants
from .triggers import ActorTrigger
from .proficiency_profile import ProficiencyProfile
from .size import CreatureSize
from .senses import ActorSenseProfile
from dnd_board_game.inventory.economy import CurrencyWallet
from dnd_board_game.inventory.adventuring_gear import ActiveLight

if TYPE_CHECKING:
    from dnd_board_game.actors.resources import ActorResourcePool, HitDicePool
    from dnd_board_game.actors.spell_preparation import SpellPreparationProfile
    from dnd_board_game.combat.spells import SpellSlotState
    from dnd_board_game.inventory import InventoryItem
    from dnd_board_game.rules import SpellAccessProfile, SpellDefinition
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
class WildShapeState:
    form_id: str
    form_name: str
    original_ac: int
    original_hp: int
    original_max_hp: int
    original_speed_feet: int
    original_ability_scores: AbilityScores
    original_size: CreatureSize
    original_senses: ActorSenseProfile
    original_damage_affinities: DamageAffinityProfile
    original_creature_type: str
    remaining_minutes: int

    def __post_init__(self) -> None:
        if not self.form_id.strip() or not self.form_name.strip():
            raise ValueError("Wild Shape form id and name cannot be empty.")
        if self.original_hp < 0 or self.original_max_hp < 1:
            raise ValueError("Wild Shape original hit points are invalid.")
        if self.remaining_minutes < 1:
            raise ValueError("Wild Shape duration must be positive.")


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
    active_light: ActiveLight | None = None
    senses: ActorSenseProfile = field(default_factory=ActorSenseProfile)
    currency: CurrencyWallet = field(default_factory=CurrencyWallet)
    spell_ids: tuple[str, ...] = ()
    spell_preparation: SpellPreparationProfile | None = None
    spells: tuple[SpellDefinition, ...] = ()
    spell_access: tuple[SpellAccessProfile, ...] = ()
    hit_dice: tuple[HitDicePool, ...] = ()
    resource_pools: tuple[ActorResourcePool, ...] = ()
    level: int = 1
    experience_points: int = 0
    exhaustion_level: int = 0
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
    features: tuple[FeatureGrant, ...] = ()
    portrait: str = ""
    creature_type: str = "humanoid"
    wild_shape: WildShapeState | None = None

    def __post_init__(self) -> None:
        if self.creature_type not in {
            "aberration", "beast", "celestial", "construct", "dragon",
            "elemental", "fey", "fiend", "giant", "humanoid",
            "monstrosity", "ooze", "plant", "undead",
        }:
            raise ValueError("Actor creature type is unknown.")
        if self.max_hp <= 0:
            object.__setattr__(self, "max_hp", max(0, self.hp))
        if not 1 <= self.level <= 20:
            raise ValueError("Actor level must be between 1 and 20.")
        if self.experience_points < 0:
            raise ValueError("Actor experience_points cannot be negative.")
        if not 0 <= self.exhaustion_level <= 6:
            raise ValueError("Actor exhaustion_level must be between 0 and 6.")
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
        validate_unique_feature_grants(self.features)

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
