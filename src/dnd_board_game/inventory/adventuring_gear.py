"""Typed rules shared by mundane adventuring gear definitions."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from math import isfinite
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dnd_board_game.actors import Actor

    from . import InventoryItem


class GearCategory(StrEnum):
    ADVENTURING_GEAR = "adventuring_gear"
    CONTAINER = "container"
    CONSUMABLE = "consumable"
    CLOTHING = "clothing"
    ARCANE_FOCUS = "arcane_focus"
    DRUIDIC_FOCUS = "druidic_focus"
    HOLY_SYMBOL = "holy_symbol"
    SPELLCASTING_GEAR = "spellcasting_gear"
    ARTISANS_TOOL = "artisans_tool"
    GAMING_SET = "gaming_set"
    MUSICAL_INSTRUMENT = "musical_instrument"
    TOOL = "tool"
    EQUIPMENT_PACK = "equipment_pack"


class SpellcastingFocusKind(StrEnum):
    ARCANE = "arcane"
    DRUIDIC = "druidic"
    HOLY_SYMBOL = "holy_symbol"
    COMPONENT_POUCH = "component_pouch"
    MUSICAL_INSTRUMENT = "musical_instrument"


class LightShape(StrEnum):
    RADIUS = "radius"
    CONE = "cone"


class CheckModifierMode(StrEnum):
    ADVANTAGE = "advantage"
    FLAT_BONUS = "flat_bonus"
    MULTIPLIER = "multiplier"


@dataclass(frozen=True, slots=True)
class ContainerCapacity:
    maximum_weight_lb: float | None = None
    volume_cubic_feet: float | None = None
    liquid_pints: float | None = None
    ammunition_type: str | None = None
    ammunition_count: int | None = None
    sheet_count: int | None = None

    def __post_init__(self) -> None:
        numeric = (
            self.maximum_weight_lb,
            self.volume_cubic_feet,
            self.liquid_pints,
        )
        if any(value is not None and (not isfinite(value) or value <= 0) for value in numeric):
            raise ValueError("Container numeric capacities must be finite and positive.")
        if self.ammunition_count is not None and self.ammunition_count < 1:
            raise ValueError("Container ammunition_count must be positive.")
        if self.ammunition_count is not None and not self.ammunition_type:
            raise ValueError("Container ammunition_count requires ammunition_type.")
        if self.sheet_count is not None and self.sheet_count < 1:
            raise ValueError("Container sheet_count must be positive.")
        if not any(
            value is not None
            for value in (
                *numeric,
                self.ammunition_count,
                self.sheet_count,
            )
        ):
            raise ValueError("Container capacity must define at least one limit.")


@dataclass(frozen=True, slots=True)
class LightSource:
    bright_distance_feet: int
    dim_additional_feet: int
    duration_minutes: int
    shape: LightShape = LightShape.RADIUS
    fuel_item_id: str | None = None
    hooded_dim_distance_feet: int | None = None

    def __post_init__(self) -> None:
        if self.bright_distance_feet < 0 or self.bright_distance_feet % 5:
            raise ValueError("Light bright distance must be a non-negative multiple of 5 feet.")
        if self.dim_additional_feet < 0 or self.dim_additional_feet % 5:
            raise ValueError("Light dim distance must be a non-negative multiple of 5 feet.")
        if self.duration_minutes < 1:
            raise ValueError("Light duration must be positive.")
        if self.hooded_dim_distance_feet is not None and (
            self.hooded_dim_distance_feet < 0
            or self.hooded_dim_distance_feet % 5
        ):
            raise ValueError("Hooded dim distance must be a non-negative multiple of 5 feet.")


@dataclass(frozen=True, slots=True)
class CheckModifier:
    id: str
    label: str
    context: str
    mode: CheckModifierMode
    value: int = 0
    ability: str | None = None
    skill: str | None = None

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.label.strip() or not self.context.strip():
            raise ValueError("Gear check modifiers require id, label, and context.")
        if self.mode == CheckModifierMode.ADVANTAGE and self.value != 0:
            raise ValueError("Advantage modifiers cannot define a flat value.")
        if self.mode == CheckModifierMode.FLAT_BONUS and self.value == 0:
            raise ValueError("Flat gear modifiers require a non-zero value.")
        if self.mode == CheckModifierMode.MULTIPLIER and self.value < 2:
            raise ValueError("Gear multipliers must be at least two.")


@dataclass(frozen=True, slots=True)
class ObjectDurability:
    hit_points: int | None = None
    break_strength_dc: int | None = None
    escape_dexterity_dc: int | None = None
    pick_lock_dc: int | None = None

    def __post_init__(self) -> None:
        values = (
            self.hit_points,
            self.break_strength_dc,
            self.escape_dexterity_dc,
            self.pick_lock_dc,
        )
        if not any(value is not None for value in values):
            raise ValueError("Object durability must define at least one rule.")
        if any(value is not None and value < 1 for value in values):
            raise ValueError("Object durability values must be positive.")


@dataclass(frozen=True, slots=True)
class BundleEntry:
    item_id: str
    quantity: int = 1

    def __post_init__(self) -> None:
        if not self.item_id.strip() or self.quantity < 1:
            raise ValueError("Bundle entries require an item id and positive quantity.")


@dataclass(frozen=True, slots=True)
class ActiveLight:
    source_item_id: str
    source_name: str
    bright_distance_feet: int
    dim_additional_feet: int
    remaining_minutes: int
    shape: LightShape
    hooded_dim_distance_feet: int | None = None
    hood_lowered: bool = False

    @property
    def current_bright_distance_feet(self) -> int:
        return 0 if self.hood_lowered else self.bright_distance_feet

    @property
    def current_dim_additional_feet(self) -> int:
        if self.hood_lowered:
            return int(self.hooded_dim_distance_feet or 0)
        return self.dim_additional_feet


@dataclass(frozen=True, slots=True)
class LightUseResult:
    actor: Actor
    active_light: ActiveLight
    consumed_item_id: str | None
    consumed_fuel_item_id: str | None


def can_store_in_container(
    capacity: ContainerCapacity,
    *,
    weight_lb: float = 0,
    liquid_pints: float = 0,
    ammunition_type: str | None = None,
    ammunition_count: int = 0,
    sheet_count: int = 0,
) -> bool:
    """Validate a proposed aggregate load against every declared capacity."""

    if min(weight_lb, liquid_pints, ammunition_count, sheet_count) < 0:
        raise ValueError("Container load values cannot be negative.")
    if capacity.maximum_weight_lb is not None and weight_lb > capacity.maximum_weight_lb:
        return False
    if capacity.liquid_pints is not None and liquid_pints > capacity.liquid_pints:
        return False
    if capacity.ammunition_count is not None:
        if ammunition_type != capacity.ammunition_type:
            return ammunition_count == 0
        if ammunition_count > capacity.ammunition_count:
            return False
    if capacity.sheet_count is not None and sheet_count > capacity.sheet_count:
        return False
    return True


def gear_check_modifier(
    item: InventoryItem,
    *,
    context: str,
    ability: str | None = None,
    skill: str | None = None,
) -> CheckModifier | None:
    """Return the first available rule matching an authored check context."""

    if not item.available:
        return None
    return next(
        (
            rule
            for rule in item.check_modifiers
            if rule.context == context
            and (rule.ability is None or rule.ability == ability)
            and (rule.skill is None or rule.skill == skill)
        ),
        None,
    )


def ignite_light_source(actor: Actor, item_id: str) -> LightUseResult:
    """Consume a candle/torch or lamp fuel and create deterministic light state."""

    from . import consume_inventory_item, inventory_item_by_id

    item = inventory_item_by_id(actor, item_id)
    if item is None or not item.available or item.light_source is None:
        raise ValueError("Wybrany przedmiot nie jest dostępnym źródłem światła.")
    updated = actor
    consumed_item_id: str | None = None
    consumed_fuel_item_id: str | None = None
    if item.light_source.fuel_item_id is None:
        updated = consume_inventory_item(updated, item.id)
        consumed_item_id = item.id
    else:
        fuel = inventory_item_by_id(updated, item.light_source.fuel_item_id)
        if fuel is None or not fuel.available:
            raise ValueError(
                f"{item.name} wymaga paliwa: {item.light_source.fuel_item_id}."
            )
        updated = consume_inventory_item(updated, fuel.id)
        consumed_fuel_item_id = fuel.id
    light = item.light_source
    return LightUseResult(
        actor=replace(
            updated,
            active_light=ActiveLight(
            source_item_id=item.id,
            source_name=item.name,
            bright_distance_feet=light.bright_distance_feet,
            dim_additional_feet=light.dim_additional_feet,
            remaining_minutes=light.duration_minutes,
            shape=light.shape,
            hooded_dim_distance_feet=light.hooded_dim_distance_feet,
            ),
        ),
        active_light=ActiveLight(
            source_item_id=item.id,
            source_name=item.name,
            bright_distance_feet=light.bright_distance_feet,
            dim_additional_feet=light.dim_additional_feet,
            remaining_minutes=light.duration_minutes,
            shape=light.shape,
            hooded_dim_distance_feet=light.hooded_dim_distance_feet,
        ),
        consumed_item_id=consumed_item_id,
        consumed_fuel_item_id=consumed_fuel_item_id,
    )


def advance_active_light(light: ActiveLight, minutes: int) -> ActiveLight | None:
    if minutes < 0:
        raise ValueError("Elapsed light time cannot be negative.")
    remaining = light.remaining_minutes - minutes
    return replace(light, remaining_minutes=remaining) if remaining > 0 else None


def advance_actor_light(actor: Actor, minutes: int) -> Actor:
    if actor.active_light is None:
        return actor
    return replace(actor, active_light=advance_active_light(actor.active_light, minutes))


def set_light_hood(light: ActiveLight, lowered: bool) -> ActiveLight:
    if light.hooded_dim_distance_feet is None:
        raise ValueError("To źródło światła nie ma regulowanej osłony.")
    return replace(light, hood_lowered=lowered)


def expand_equipment_pack(
    pack: InventoryItem,
    catalog: dict[str, InventoryItem],
) -> tuple[InventoryItem, ...]:
    """Expand a purchased pack into ordinary inventory stacks."""

    if not pack.bundle_contents:
        raise ValueError("Wybrany przedmiot nie jest pakietem wyposażenia.")
    expanded: list[InventoryItem] = []
    for entry in pack.bundle_contents:
        template = catalog.get(entry.item_id)
        if template is None:
            raise ValueError(f"Pakiet odwołuje się do nieznanego przedmiotu: {entry.item_id}.")
        expanded.append(
            replace(
                template,
                quantity=entry.quantity,
                equipped=False,
                held_in=(),
            )
        )
    return tuple(expanded)


def unpack_equipment_pack(
    actor: Actor,
    pack_item_id: str,
    catalog: dict[str, InventoryItem],
) -> Actor:
    """Consume one pack and atomically add each authored content stack."""

    from . import add_inventory_item, consume_inventory_item, inventory_item_by_id

    pack = inventory_item_by_id(actor, pack_item_id)
    if pack is None or not pack.available:
        raise ValueError("Aktor nie ma dostępnego pakietu wyposażenia.")
    expanded = expand_equipment_pack(pack, catalog)
    updated = consume_inventory_item(actor, pack.id)
    for item in expanded:
        updated = add_inventory_item(updated, item)
    return updated


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
    "advance_active_light",
    "advance_actor_light",
    "can_store_in_container",
    "expand_equipment_pack",
    "gear_check_modifier",
    "ignite_light_source",
    "set_light_hood",
    "unpack_equipment_pack",
]
