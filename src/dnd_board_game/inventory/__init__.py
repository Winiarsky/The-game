"""Items, equipment, and inventory rules."""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import isfinite
from typing import TYPE_CHECKING

from .catalog import (
    ArmorCategory,
    ItemChargeRecovery,
    ItemCollectionDestination,
    ItemDefinition,
    ItemInstance,
    ItemPropertyCatalog,
    ItemPropertyDefinition,
    validate_charge_configuration,
)
from .magic_items import (
    MagicItemEffect,
    MagicItemEffectContribution,
    MagicItemEffectKind,
    active_magic_item_effects,
    magic_item_effect_total,
    magic_item_roll_modifiers,
)
from .weapons import WeaponCategory, WeaponProperty, WeaponSpecialRule
from .adventuring_gear import (
    ActiveLight,
    BundleEntry,
    CheckModifier,
    CheckModifierMode,
    ContainerCapacity,
    GearCategory,
    LightShape,
    LightSource,
    LightUseResult,
    ObjectDurability,
    SpellcastingFocusKind,
    advance_active_light,
    advance_actor_light,
    can_store_in_container,
    expand_equipment_pack,
    gear_check_modifier,
    ignite_light_source,
    set_light_hood,
    unpack_equipment_pack,
)
from .armor import (
    ArmorUseResult,
    armor_doff_time_minutes,
    armor_don_time_minutes,
    armor_speed_penalty_feet,
    armor_skill_roll_request,
    body_armor_class,
    doff_armor,
    don_armor,
    effective_armor_class,
    effective_speed_feet,
    equipped_armor_class_bonus,
    equipped_body_armor,
    has_stealth_disadvantage,
)
from .attunement import (
    MAX_ATTUNED_ITEMS,
    ItemAttunementAction,
    ItemAttunementChoice,
    ItemAttunementResult,
    apply_item_attunement,
    attuned_item_count,
    item_power_available,
    validate_attunement_limit,
)
from .ammunition import (
    AmmunitionUse,
    ammunition_quantity,
    consume_ammunition,
    has_ammunition,
)
from .charges import (
    ItemChargeRecoveryBatch,
    ItemChargeRecoveryResult,
    ItemChargeSpendResult,
    consume_item_use,
    has_item_use,
    recover_item_charges,
)
from .economy import (
    CurrencyWallet,
    carried_weight_lb,
    carrying_capacity_lb,
    carrying_payload,
    currency_weight_lb,
    currency_wallet_from_cp,
    inventory_weight_lb,
    remaining_capacity_lb,
)
from .trade import (
    MerchantState,
    TradeResult,
    buy_from_merchant,
    merchant_buy_unit_price_cp,
    merchant_item,
    merchant_sell_unit_price_cp,
    sell_to_merchant,
)
from .loot import (
    LootBundle,
    LootBundleTransferResult,
    LootTransferResult,
    loot_bundle_from_actor,
    transfer_actor_loot,
    transfer_all_actor_loot,
    transfer_all_loot,
    transfer_loot,
)
from .hands import (
    HAND_SLOTS,
    HandEquipPlan,
    HandLoadout,
    HandSlot,
    free_hand_count,
    hand_loadout,
    hand_loadout_payload,
    hands_required,
    normalize_hand_equipment,
    plan_hand_equip,
)

if TYPE_CHECKING:
    from dnd_board_game.actors import Actor


@dataclass(frozen=True, slots=True)
class InventoryItem:
    id: str
    name: str
    kind: str
    quantity: int = 1
    equipped: bool = True
    source_ref: str | None = None
    broken: bool = False
    description: str = ""
    properties: tuple[str, ...] = ()
    portable: bool = True
    hands_required: int = 0
    held_in: tuple[HandSlot, ...] = ()
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
    attuned: bool = False
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
    value_cp: int = 0
    weight_lb: float = 0.0

    def __post_init__(self) -> None:
        if self.hands_required not in {0, 1, 2}:
            raise ValueError("hands_required must be 0, 1, or 2.")
        if len(self.held_in) != len(set(self.held_in)):
            raise ValueError("held_in cannot contain duplicate hand slots.")
        if any(slot not in HAND_SLOTS for slot in self.held_in):
            raise ValueError("held_in contains an unknown hand slot.")
        if self.held_in and not self.equipped:
            raise ValueError("An unequipped item cannot occupy a hand slot.")
        if self.armor_class_bonus < 0:
            raise ValueError("armor_class_bonus cannot be negative.")
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
        if self.charges_maximum is not None and self.charges_current is None:
            object.__setattr__(self, "charges_current", self.charges_maximum)
        validate_charge_configuration(
            maximum=self.charges_maximum,
            current=self.charges_current,
            recovery=self.charges_recovery,
            recovery_dice=self.charges_recovery_dice,
            recovery_modifier=self.charges_recovery_modifier,
        )
        if self.charges_maximum is not None and self.quantity != 1:
            raise ValueError("Charge-bearing inventory items cannot be stacked.")
        if self.attuned and not self.requires_attunement:
            raise ValueError("Only an item requiring attunement can be attuned.")
        if self.requires_attunement and self.quantity != 1:
            raise ValueError("Items requiring attunement cannot be stacked.")
        effect_ids = tuple(effect.id for effect in self.magic_effects)
        if len(effect_ids) != len(set(effect_ids)):
            raise ValueError("Magic item effect ids must be unique per item.")
        if self.magic_effects and self.quantity != 1:
            raise ValueError("Items with magic effects cannot be stacked.")
        if self.weapon_category is None and self.weapon_properties:
            raise ValueError("Weapon properties require a weapon category.")
        if self.weapon_category is not None and self.kind != "weapon":
            raise ValueError("Only kind=weapon can define a weapon category.")
        if len(self.weapon_properties) != len(set(self.weapon_properties)):
            raise ValueError("Weapon properties cannot contain duplicates.")
        if self.ammunition_type is not None and not self.ammunition_type.strip():
            raise ValueError("ammunition_type cannot be empty.")
        if self.tool_proficiency_id is not None and not self.tool_proficiency_id.strip():
            raise ValueError("tool_proficiency_id cannot be empty.")
        if not self.stackable and self.quantity > 1:
            raise ValueError("Non-stackable inventory items cannot have quantity above one.")
        if self.gear_category == GearCategory.EQUIPMENT_PACK and not self.bundle_contents:
            raise ValueError("Equipment packs require bundle contents.")
        if self.bundle_contents and self.gear_category != GearCategory.EQUIPMENT_PACK:
            raise ValueError("Only equipment packs can define bundle contents.")
        if self.container_capacity is not None and self.gear_category != GearCategory.CONTAINER:
            raise ValueError("Container capacity requires gear_category=container.")
        modifier_ids = tuple(rule.id for rule in self.check_modifiers)
        if len(modifier_ids) != len(set(modifier_ids)):
            raise ValueError("Gear check modifier ids must be unique per item.")
        if self.value_cp < 0:
            raise ValueError("value_cp cannot be negative.")
        if not isfinite(self.weight_lb) or self.weight_lb < 0:
            raise ValueError("weight_lb must be finite and non-negative.")

    @property
    def available(self) -> bool:
        return self.quantity > 0 and not self.broken


def inventory_item_payload(item: InventoryItem) -> dict[str, object]:
    return {
        "id": item.id,
        "name": item.name,
        "kind": item.kind,
        "quantity": item.quantity,
        "equipped": item.equipped,
        "source_ref": item.source_ref,
        "broken": item.broken,
        "description": item.description,
        "properties": list(item.properties),
        "portable": item.portable,
        "hands_required": hands_required(item),
        "held_in": [slot.value for slot in item.held_in],
        "light_weapon": item.light_weapon,
        "versatile_damage_dice": item.versatile_damage_dice,
        "armor_class_bonus": item.armor_class_bonus,
        "armor_proficiency": item.armor_proficiency,
        "armor_category": item.armor_category.value if item.armor_category is not None else None,
        "armor_base_ac": item.armor_base_ac,
        "armor_dexterity_cap": item.armor_dexterity_cap,
        "armor_strength_requirement": item.armor_strength_requirement,
        "stealth_disadvantage": item.stealth_disadvantage,
        "charges_maximum": item.charges_maximum,
        "charges_current": item.charges_current,
        "charges_recovery": item.charges_recovery.value,
        "charges_recovery_dice": item.charges_recovery_dice,
        "charges_recovery_modifier": item.charges_recovery_modifier,
        "requires_attunement": item.requires_attunement,
        "attuned": item.attuned,
        "magic_effects": [
            {
                "id": effect.id,
                "kind": effect.kind.value,
                "value": effect.value,
                "requires_equipped": effect.requires_equipped,
            }
            for effect in item.magic_effects
        ],
        "weapon_category": (
            item.weapon_category.value if item.weapon_category is not None else None
        ),
        "weapon_properties": [value.value for value in item.weapon_properties],
        "ammunition_type": item.ammunition_type,
        "gear_category": item.gear_category.value if item.gear_category is not None else None,
        "stackable": item.stackable,
        "tool_proficiency_id": item.tool_proficiency_id,
        "spellcasting_focus_kind": (
            item.spellcasting_focus_kind.value
            if item.spellcasting_focus_kind is not None
            else None
        ),
        "container_capacity": (
            {
                "maximum_weight_lb": item.container_capacity.maximum_weight_lb,
                "volume_cubic_feet": item.container_capacity.volume_cubic_feet,
                "liquid_pints": item.container_capacity.liquid_pints,
                "ammunition_type": item.container_capacity.ammunition_type,
                "ammunition_count": item.container_capacity.ammunition_count,
                "sheet_count": item.container_capacity.sheet_count,
            }
            if item.container_capacity is not None
            else None
        ),
        "light_source": (
            {
                "bright_distance_feet": item.light_source.bright_distance_feet,
                "dim_additional_feet": item.light_source.dim_additional_feet,
                "duration_minutes": item.light_source.duration_minutes,
                "shape": item.light_source.shape.value,
                "fuel_item_id": item.light_source.fuel_item_id,
                "hooded_dim_distance_feet": item.light_source.hooded_dim_distance_feet,
            }
            if item.light_source is not None
            else None
        ),
        "check_modifiers": [
            {
                "id": rule.id,
                "label": rule.label,
                "context": rule.context,
                "mode": rule.mode.value,
                "value": rule.value,
                "ability": rule.ability,
                "skill": rule.skill,
            }
            for rule in item.check_modifiers
        ],
        "durability": (
            {
                "hit_points": item.durability.hit_points,
                "break_strength_dc": item.durability.break_strength_dc,
                "escape_dexterity_dc": item.durability.escape_dexterity_dc,
                "pick_lock_dc": item.durability.pick_lock_dc,
            }
            if item.durability is not None
            else None
        ),
        "bundle_contents": [
            {"item_id": entry.item_id, "quantity": entry.quantity}
            for entry in item.bundle_contents
        ],
        "value_cp": item.value_cp,
        "total_value_cp": item.value_cp * item.quantity,
        "weight_lb": item.weight_lb,
        "total_weight_lb": item.weight_lb * item.quantity,
        "available": item.available,
    }


def inventory_item_by_id(actor: Actor, item_id: str) -> InventoryItem | None:
    return next((item for item in actor.inventory if item.id == item_id), None)


def has_inventory_quantity(actor: Actor, item_id: str, quantity: int = 1) -> bool:
    item = inventory_item_by_id(actor, item_id)
    return item is not None and item.quantity >= quantity and not item.broken


def consume_inventory_item(actor: Actor, item_id: str, quantity: int = 1) -> Actor:
    if quantity <= 0:
        raise ValueError("Consumed inventory quantity must be positive.")
    items = list(actor.inventory)
    for index, item in enumerate(items):
        if item.id != item_id:
            continue
        if item.quantity < quantity:
            raise ValueError(f"Not enough inventory quantity for item: {item_id}.")
        items[index] = replace(item, quantity=item.quantity - quantity)
        return replace(actor, inventory=tuple(items))
    raise ValueError(f"Actor does not have inventory item: {item_id}.")


def add_inventory_item(actor: Actor, item: InventoryItem) -> Actor:
    """Add an item instance or merge another quantity of the same instance."""

    if item.quantity <= 0:
        raise ValueError("Added inventory quantity must be positive.")
    items = list(actor.inventory)
    for index, current in enumerate(items):
        if current.id != item.id:
            continue
        if (
            current.name,
            current.kind,
            current.source_ref,
            current.properties,
            current.portable,
            current.hands_required,
            current.light_weapon,
            current.versatile_damage_dice,
            current.armor_class_bonus,
            current.armor_proficiency,
            current.armor_category,
            current.armor_base_ac,
            current.armor_dexterity_cap,
            current.armor_strength_requirement,
            current.stealth_disadvantage,
            current.charges_maximum,
            current.charges_current,
            current.charges_recovery,
            current.charges_recovery_dice,
            current.charges_recovery_modifier,
            current.requires_attunement,
            current.magic_effects,
            current.weapon_category,
            current.weapon_properties,
            current.attuned,
            current.ammunition_type,
            current.gear_category,
            current.stackable,
            current.tool_proficiency_id,
            current.spellcasting_focus_kind,
            current.container_capacity,
            current.light_source,
            current.check_modifiers,
            current.durability,
            current.bundle_contents,
            current.value_cp,
            current.weight_lb,
        ) != (
            item.name,
            item.kind,
            item.source_ref,
            item.properties,
            item.portable,
            item.hands_required,
            item.light_weapon,
            item.versatile_damage_dice,
            item.armor_class_bonus,
            item.armor_proficiency,
            item.armor_category,
            item.armor_base_ac,
            item.armor_dexterity_cap,
            item.armor_strength_requirement,
            item.stealth_disadvantage,
            item.charges_maximum,
            item.charges_current,
            item.charges_recovery,
            item.charges_recovery_dice,
            item.charges_recovery_modifier,
            item.requires_attunement,
            item.magic_effects,
            item.weapon_category,
            item.weapon_properties,
            item.attuned,
            item.ammunition_type,
            item.gear_category,
            item.stackable,
            item.tool_proficiency_id,
            item.spellcasting_focus_kind,
            item.container_capacity,
            item.light_source,
            item.check_modifiers,
            item.durability,
            item.bundle_contents,
            item.value_cp,
            item.weight_lb,
        ):
            raise ValueError(f"Inventory item id collision: {item.id}.")
        items[index] = replace(current, quantity=current.quantity + item.quantity)
        return replace(actor, inventory=tuple(items))
    return replace(actor, inventory=(*actor.inventory, item))


def break_inventory_item(actor: Actor, item_id: str) -> Actor:
    items = list(actor.inventory)
    for index, item in enumerate(items):
        if item.id != item_id:
            continue
        items[index] = replace(item, broken=True)
        return replace(actor, inventory=tuple(items))
    raise ValueError(f"Actor does not have inventory item: {item_id}.")


__all__ = [
    "ActiveLight",
    "BundleEntry",
    "CheckModifier",
    "CheckModifierMode",
    "ContainerCapacity",
    "GearCategory",
    "LightShape",
    "LightSource",
    "LightUseResult",
    "ObjectDurability",
    "SpellcastingFocusKind",
    "MAX_ATTUNED_ITEMS",
    "ItemDefinition",
    "ArmorCategory",
    "ItemAttunementAction",
    "ItemAttunementChoice",
    "ItemAttunementResult",
    "ItemCollectionDestination",
    "ItemChargeRecovery",
    "ItemInstance",
    "ItemChargeRecoveryBatch",
    "ItemChargeRecoveryResult",
    "ItemChargeSpendResult",
    "ItemPropertyCatalog",
    "ItemPropertyDefinition",
    "InventoryItem",
    "MagicItemEffect",
    "MagicItemEffectContribution",
    "MagicItemEffectKind",
    "WeaponCategory",
    "WeaponProperty",
    "WeaponSpecialRule",
    "AmmunitionUse",
    "ArmorUseResult",
    "MerchantState",
    "CurrencyWallet",
    "LootBundle",
    "LootBundleTransferResult",
    "LootTransferResult",
    "HAND_SLOTS",
    "HandEquipPlan",
    "HandLoadout",
    "HandSlot",
    "add_inventory_item",
    "active_magic_item_effects",
    "apply_item_attunement",
    "attuned_item_count",
    "armor_doff_time_minutes",
    "armor_don_time_minutes",
    "armor_speed_penalty_feet",
    "armor_skill_roll_request",
    "ammunition_quantity",
    "break_inventory_item",
    "body_armor_class",
    "consume_inventory_item",
    "consume_item_use",
    "consume_ammunition",
    "carried_weight_lb",
    "carrying_capacity_lb",
    "carrying_payload",
    "currency_weight_lb",
    "currency_wallet_from_cp",
    "doff_armor",
    "don_armor",
    "effective_armor_class",
    "effective_speed_feet",
    "equipped_armor_class_bonus",
    "equipped_body_armor",
    "has_inventory_quantity",
    "has_item_use",
    "has_stealth_disadvantage",
    "has_ammunition",
    "inventory_item_by_id",
    "inventory_item_payload",
    "inventory_weight_lb",
    "item_power_available",
    "magic_item_effect_total",
    "magic_item_roll_modifiers",
    "validate_attunement_limit",
    "loot_bundle_from_actor",
    "TradeResult",
    "buy_from_merchant",
    "merchant_buy_unit_price_cp",
    "merchant_item",
    "merchant_sell_unit_price_cp",
    "sell_to_merchant",
    "free_hand_count",
    "hand_loadout",
    "hand_loadout_payload",
    "hands_required",
    "normalize_hand_equipment",
    "plan_hand_equip",
    "remaining_capacity_lb",
    "recover_item_charges",
    "transfer_all_actor_loot",
    "transfer_all_loot",
    "transfer_actor_loot",
    "advance_active_light",
    "advance_actor_light",
    "can_store_in_container",
    "expand_equipment_pack",
    "gear_check_modifier",
    "ignite_light_source",
    "set_light_hood",
    "unpack_equipment_pack",
    "transfer_loot",
]
