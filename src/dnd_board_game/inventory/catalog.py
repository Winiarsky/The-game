"""Data-driven item definitions and concrete item instances."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re

from .magic_items import MagicItemEffect
from .weapons import WeaponCategory, WeaponProperty
from .adventuring_gear import (
    BundleEntry,
    CheckModifier,
    ContainerCapacity,
    GearCategory,
    LightSource,
    ObjectDurability,
    SpellcastingFocusKind,
)


def _validated_ids(values: tuple[str, ...], field: str) -> tuple[str, ...]:
    normalized = tuple(value.strip() for value in values)
    if any(not value for value in normalized):
        raise ValueError(f"{field} cannot contain empty ids.")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field} cannot contain duplicate ids.")
    return normalized


class ItemCollectionDestination(StrEnum):
    """Engine-owned destination used when a scene item is explicitly collected."""

    ACTOR_INVENTORY = "actor_inventory"
    PARTY_TREASURE = "party_treasure"
    SCENARIO_QUEST = "scenario_quest"


class ArmorCategory(StrEnum):
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"


class ItemChargeRecovery(StrEnum):
    NEVER = "never"
    SHORT_REST = "short_rest"
    LONG_REST = "long_rest"


def validate_charge_configuration(
    *,
    maximum: int | None,
    current: int | None,
    recovery: ItemChargeRecovery,
    recovery_dice: str | None,
    recovery_modifier: int,
) -> None:
    if maximum is None:
        if (
            current is not None
            or recovery != ItemChargeRecovery.NEVER
            or recovery_dice is not None
            or recovery_modifier != 0
        ):
            raise ValueError("Charge state requires charges_maximum.")
        return
    if maximum < 1:
        raise ValueError("charges_maximum must be positive.")
    if current is not None and not 0 <= current <= maximum:
        raise ValueError("charges_current must be between zero and charges_maximum.")
    if recovery_dice is not None:
        match = re.fullmatch(r"\s*(\d+)[dD](\d+)\s*", recovery_dice)
        if match is None or int(match.group(1)) < 1 or int(match.group(2)) < 2:
            raise ValueError("charges_recovery_dice must use positive NdM notation.")
        if recovery == ItemChargeRecovery.NEVER:
            raise ValueError("Random charge recovery requires a recovery period.")
    elif recovery_modifier != 0:
        raise ValueError("charges_recovery_modifier requires charges_recovery_dice.")


@dataclass(frozen=True, slots=True)
class ItemPropertyDefinition:
    id: str
    label: str
    description: str = ""

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Item property id cannot be empty.")
        if not self.label.strip():
            raise ValueError("Item property label cannot be empty.")


@dataclass(frozen=True, slots=True)
class ItemPropertyCatalog:
    schema_version: int
    properties: tuple[ItemPropertyDefinition, ...]

    def __post_init__(self) -> None:
        if self.schema_version < 1:
            raise ValueError("Item property catalog schema_version must be positive.")
        ids = tuple(item.id for item in self.properties)
        _validated_ids(ids, "Item property catalog")

    @property
    def known_ids(self) -> frozenset[str]:
        return frozenset(item.id for item in self.properties)

    def validate(self, properties: tuple[str, ...], field: str = "properties") -> None:
        normalized = _validated_ids(properties, field)
        unknown = set(normalized) - self.known_ids
        if unknown:
            raise ValueError(f"{field} contains unknown item properties: {', '.join(sorted(unknown))}.")


@dataclass(frozen=True, slots=True)
class ItemDefinition:
    id: str
    name: str
    kind: str
    description: str = ""
    properties: tuple[str, ...] = ()
    portable: bool = True
    default_weight_lb: float | None = None
    default_value_cp: int | None = None
    collection_destination: ItemCollectionDestination = ItemCollectionDestination.ACTOR_INVENTORY
    hands_required: int = 0
    light_weapon: bool = False
    versatile_damage_dice: str | None = None
    armor_class_bonus: int = 0
    armor_proficiency: str | None = None
    armor_category: ArmorCategory | None = None
    armor_base_ac: int | None = None
    armor_dexterity_cap: int | None = None
    armor_strength_requirement: int | None = None
    stealth_disadvantage: bool = False
    charges_maximum: int | None = None
    charges_current: int | None = None
    charges_recovery: ItemChargeRecovery = ItemChargeRecovery.NEVER
    charges_recovery_dice: str | None = None
    charges_recovery_modifier: int = 0
    requires_attunement: bool = False
    magic_effects: tuple[MagicItemEffect, ...] = ()
    weapon_category: WeaponCategory | None = None
    weapon_properties: tuple[WeaponProperty, ...] = ()
    ammunition_type: str | None = None
    gear_category: GearCategory | None = None
    stackable: bool = True
    tool_proficiency_id: str | None = None
    spellcasting_focus_kind: SpellcastingFocusKind | None = None
    container_capacity: ContainerCapacity | None = None
    light_source: LightSource | None = None
    check_modifiers: tuple[CheckModifier, ...] = ()
    durability: ObjectDurability | None = None
    bundle_contents: tuple[BundleEntry, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Item definition id cannot be empty.")
        if not self.name.strip():
            raise ValueError("Item definition name cannot be empty.")
        if not self.kind.strip():
            raise ValueError("Item definition kind cannot be empty.")
        _validated_ids(self.properties, f"Item definition {self.id}.properties")
        if self.default_weight_lb is not None and self.default_weight_lb < 0:
            raise ValueError("Item definition default_weight_lb cannot be negative.")
        if self.default_value_cp is not None and self.default_value_cp < 0:
            raise ValueError("Item definition default_value_cp cannot be negative.")
        if self.ammunition_type is not None and not self.ammunition_type.strip():
            raise ValueError("Item definition ammunition_type cannot be empty.")
        if self.tool_proficiency_id is not None and not self.tool_proficiency_id.strip():
            raise ValueError("Item definition tool_proficiency_id cannot be empty.")
        if self.gear_category == GearCategory.EQUIPMENT_PACK and not self.bundle_contents:
            raise ValueError("Equipment packs require bundle contents.")
        if self.bundle_contents and self.gear_category != GearCategory.EQUIPMENT_PACK:
            raise ValueError("Only equipment packs can define bundle contents.")
        if self.container_capacity is not None and self.gear_category != GearCategory.CONTAINER:
            raise ValueError("Container capacity requires gear_category=container.")
        modifier_ids = tuple(rule.id for rule in self.check_modifiers)
        if len(modifier_ids) != len(set(modifier_ids)):
            raise ValueError("Gear check modifier ids must be unique per item definition.")
        effect_ids = tuple(effect.id for effect in self.magic_effects)
        if len(effect_ids) != len(set(effect_ids)):
            raise ValueError("Magic item effect ids must be unique per item definition.")
        if self.weapon_category is None and self.weapon_properties:
            raise ValueError("Weapon properties require a weapon category.")
        if self.weapon_category is not None and self.kind != "weapon":
            raise ValueError("Only kind=weapon can define a weapon category.")
        if self.hands_required not in {0, 1, 2}:
            raise ValueError("Item definition hands_required must be 0, 1, or 2.")
        if self.versatile_damage_dice is not None and self.hands_required != 1:
            raise ValueError("Only one-handed equipment can define versatile damage.")
        if self.armor_class_bonus < 0:
            raise ValueError("Item definition armor_class_bonus cannot be negative.")
        if self.armor_category is None:
            if any(
                value is not None
                for value in (
                    self.armor_base_ac,
                    self.armor_dexterity_cap,
                    self.armor_strength_requirement,
                )
            ) or self.stealth_disadvantage:
                raise ValueError("Armor rules require an armor_category.")
        else:
            if self.kind != "armor":
                raise ValueError("Only kind=armor can define an armor_category.")
            if self.armor_base_ac is None or self.armor_base_ac < 1:
                raise ValueError("Body armor requires a positive armor_base_ac.")
            if self.armor_dexterity_cap is not None and self.armor_dexterity_cap < 0:
                raise ValueError("armor_dexterity_cap cannot be negative.")
            if (
                self.armor_strength_requirement is not None
                and self.armor_strength_requirement < 1
            ):
                raise ValueError("armor_strength_requirement must be positive.")
        validate_charge_configuration(
            maximum=self.charges_maximum,
            current=self.charges_current,
            recovery=self.charges_recovery,
            recovery_dice=self.charges_recovery_dice,
            recovery_modifier=self.charges_recovery_modifier,
        )


@dataclass(frozen=True, slots=True)
class ItemInstance:
    id: str
    definition: ItemDefinition
    quantity: int = 1
    condition: str = "normal"
    added_properties: tuple[str, ...] = ()
    removed_properties: tuple[str, ...] = ()
    owner_id: str | None = None
    visible: bool = True
    available: bool = True

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Item instance id cannot be empty.")
        if self.quantity < 0:
            raise ValueError("Item instance quantity cannot be negative.")
        if not self.condition.strip():
            raise ValueError("Item instance condition cannot be empty.")
        added = _validated_ids(self.added_properties, f"Item instance {self.id}.added_properties")
        removed = _validated_ids(self.removed_properties, f"Item instance {self.id}.removed_properties")
        overlap = set(added) & set(removed)
        if overlap:
            raise ValueError(
                f"Item instance {self.id} cannot add and remove the same properties: "
                f"{', '.join(sorted(overlap))}."
            )

    @property
    def definition_id(self) -> str:
        return self.definition.id

    @property
    def properties(self) -> frozenset[str]:
        return (frozenset(self.definition.properties) | frozenset(self.added_properties)) - frozenset(
            self.removed_properties
        )

    @property
    def usable(self) -> bool:
        return self.available and self.quantity > 0


__all__ = [
    "ItemDefinition",
    "ArmorCategory",
    "ItemChargeRecovery",
    "ItemCollectionDestination",
    "ItemInstance",
    "ItemPropertyCatalog",
    "ItemPropertyDefinition",
    "validate_charge_configuration",
]
