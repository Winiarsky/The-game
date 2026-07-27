"""Content-neutral D&D 5e spell definitions and casting validation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, Sequence


class SpellSchool(StrEnum):
    ABJURATION = "abjuration"
    CONJURATION = "conjuration"
    DIVINATION = "divination"
    ENCHANTMENT = "enchantment"
    EVOCATION = "evocation"
    ILLUSION = "illusion"
    NECROMANCY = "necromancy"
    TRANSMUTATION = "transmutation"


class SpellCastingTime(StrEnum):
    ACTION = "action"
    BONUS_ACTION = "bonus_action"
    REACTION = "reaction"
    MINUTE = "minute"
    TEN_MINUTES = "ten_minutes"
    HOUR = "hour"


class SpellRangeKind(StrEnum):
    SELF = "self"
    TOUCH = "touch"
    DISTANCE = "distance"
    SIGHT = "sight"
    UNLIMITED = "unlimited"


class SpellDurationKind(StrEnum):
    INSTANTANEOUS = "instantaneous"
    ROUND = "round"
    MINUTE = "minute"
    TEN_MINUTES = "ten_minutes"
    HOUR = "hour"
    EIGHT_HOURS = "eight_hours"
    TWENTY_FOUR_HOURS = "twenty_four_hours"
    UNTIL_DISPELLED = "until_dispelled"


class SpellAccessKind(StrEnum):
    PREPARED = "prepared"
    KNOWN = "known"
    SPELLBOOK = "spellbook"


class SpellExplorationEffectKind(StrEnum):
    SET_FLAG = "set_flag"


@dataclass(frozen=True, slots=True)
class SpellExplorationEffect:
    kind: SpellExplorationEffectKind
    flag_key: str
    flag_value: bool | int | str = True

    def __post_init__(self) -> None:
        if not self.flag_key.strip():
            raise ValueError("Spell exploration effect requires a flag key.")


@dataclass(frozen=True, slots=True)
class SpellMaterial:
    item_id: str
    label: str
    minimum_value_cp: int = 0
    consumed: bool = False
    quantity: int = 1

    def __post_init__(self) -> None:
        if not self.item_id.strip() or not self.label.strip():
            raise ValueError("Spell material requires a non-empty item id and label.")
        if self.minimum_value_cp < 0:
            raise ValueError("Spell material value cannot be negative.")
        if self.quantity < 1:
            raise ValueError("Spell material quantity must be positive.")

    @property
    def can_be_replaced_by_focus(self) -> bool:
        return self.minimum_value_cp == 0 and not self.consumed


@dataclass(frozen=True, slots=True)
class SpellComponents:
    verbal: bool = False
    somatic: bool = False
    materials: tuple[SpellMaterial, ...] = ()

    def __post_init__(self) -> None:
        if not (self.verbal or self.somatic or self.materials):
            raise ValueError("A spell must require at least one component.")
        ids = tuple(material.item_id for material in self.materials)
        if len(ids) != len(set(ids)):
            raise ValueError("Spell material item ids must be unique.")


@dataclass(frozen=True, slots=True)
class SpellRange:
    kind: SpellRangeKind
    feet: int = 0

    def __post_init__(self) -> None:
        if self.kind == SpellRangeKind.DISTANCE:
            if self.feet <= 0 or self.feet % 5:
                raise ValueError("A distance spell range must be a positive multiple of 5 feet.")
        elif self.feet != 0:
            raise ValueError("Only a distance spell range can define feet.")


@dataclass(frozen=True, slots=True)
class SpellDuration:
    kind: SpellDurationKind
    amount: int = 1

    def __post_init__(self) -> None:
        if self.kind in {SpellDurationKind.INSTANTANEOUS, SpellDurationKind.UNTIL_DISPELLED}:
            if self.amount != 1:
                raise ValueError("Instantaneous and until-dispelled durations do not use an amount.")
        elif self.amount < 1:
            raise ValueError("Spell duration amount must be positive.")


def spell_duration_minutes(duration: SpellDuration) -> int | None:
    multipliers = {
        SpellDurationKind.ROUND: 0,
        SpellDurationKind.MINUTE: 1,
        SpellDurationKind.TEN_MINUTES: 10,
        SpellDurationKind.HOUR: 60,
        SpellDurationKind.EIGHT_HOURS: 8 * 60,
        SpellDurationKind.TWENTY_FOUR_HOURS: 24 * 60,
    }
    if duration.kind == SpellDurationKind.INSTANTANEOUS:
        return 0
    if duration.kind == SpellDurationKind.UNTIL_DISPELLED:
        return None
    return duration.amount * multipliers[duration.kind]


def spell_target_count(
    *,
    base_targets: int,
    spell_level: int,
    cast_level: int,
    targets_per_slot_level: int = 0,
) -> int:
    if base_targets < 1:
        raise ValueError("A targeted spell must allow at least one base target.")
    if spell_level < 0:
        raise ValueError("Spell level cannot be negative.")
    if cast_level < spell_level:
        raise ValueError("Cast level cannot be lower than spell level.")
    if targets_per_slot_level < 0:
        raise ValueError("Target scaling cannot be negative.")
    return base_targets + (cast_level - spell_level) * targets_per_slot_level


def cantrip_damage_dice_count(
    *,
    base_dice: int,
    actor_level: int,
    dice_per_tier: int = 1,
) -> int:
    """Return a cantrip's damage dice at the 5e character-level breakpoints."""
    if base_dice < 1:
        raise ValueError("A damaging cantrip must have at least one base die.")
    if not 1 <= actor_level <= 20:
        raise ValueError("Actor level must be between 1 and 20.")
    if dice_per_tier < 0:
        raise ValueError("Cantrip damage scaling cannot be negative.")
    tiers = sum(actor_level >= threshold for threshold in (5, 11, 17))
    return base_dice + tiers * dice_per_tier


@dataclass(frozen=True, slots=True)
class SpellScaling:
    damage_dice_per_slot_level: int = 0
    healing_dice_per_slot_level: int = 0
    targets_per_slot_level: int = 0
    cantrip_damage_dice_per_tier: int = 0

    def __post_init__(self) -> None:
        values = (
            self.damage_dice_per_slot_level,
            self.healing_dice_per_slot_level,
            self.targets_per_slot_level,
            self.cantrip_damage_dice_per_tier,
        )
        if any(value < 0 for value in values):
            raise ValueError("Spell scaling values cannot be negative.")
        if not any(values):
            raise ValueError("Spell scaling must increase at least one effect value.")


@dataclass(frozen=True, slots=True)
class SpellDefinition:
    id: str
    name: str
    level: int
    school: SpellSchool
    casting_time: SpellCastingTime
    range: SpellRange
    components: SpellComponents
    duration: SpellDuration
    concentration: bool = False
    ritual: bool = False
    effect_kind: str = ""
    scaling: SpellScaling | None = None
    exploration_effect: SpellExplorationEffect | None = None

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.name.strip():
            raise ValueError("Spell definition requires a non-empty id and name.")
        if not 0 <= self.level <= 9:
            raise ValueError("Spell level must be between 0 and 9.")
        if self.concentration and self.duration.kind == SpellDurationKind.INSTANTANEOUS:
            raise ValueError("An instantaneous spell cannot require concentration.")
        if self.ritual and self.level == 0:
            raise ValueError("A cantrip cannot be cast as a ritual.")
        if not self.effect_kind.strip():
            raise ValueError("Spell definition requires an effect kind.")
        if self.scaling is not None:
            if self.level == 0 and any(
                (
                    self.scaling.damage_dice_per_slot_level,
                    self.scaling.healing_dice_per_slot_level,
                    self.scaling.targets_per_slot_level,
                )
            ):
                raise ValueError("A cantrip cannot scale from spell-slot level.")
            if self.level > 0 and self.scaling.cantrip_damage_dice_per_tier:
                raise ValueError("Only a cantrip can use cantrip damage scaling.")
        if self.effect_kind == "exploration" and self.exploration_effect is None:
            raise ValueError("An exploration spell requires an exploration effect.")
        if self.effect_kind != "exploration" and self.exploration_effect is not None:
            raise ValueError("Only an exploration spell can define an exploration effect.")


@dataclass(frozen=True, slots=True)
class SpellAccessProfile:
    kind: SpellAccessKind
    spell_ids: tuple[str, ...]
    allowed_focus_kinds: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.spell_ids or any(not value.strip() for value in self.spell_ids):
            raise ValueError("Spell access profile requires non-empty spell ids.")
        if len(self.spell_ids) != len(set(self.spell_ids)):
            raise ValueError("Spell access spell ids must be unique.")
        if len(self.allowed_focus_kinds) != len(set(self.allowed_focus_kinds)):
            raise ValueError("Allowed spellcasting focus kinds must be unique.")


class SpellSlotLike(Protocol):
    level: int
    remaining: int


class SpellItemLike(Protocol):
    id: str
    source_ref: str | None
    quantity: int
    equipped: bool
    broken: bool
    value_cp: int
    held_in: tuple[object, ...]
    spellcasting_focus_kind: object | None


@dataclass(frozen=True, slots=True)
class SpellMaterialUse:
    item_id: str
    quantity: int
    consumed: bool


@dataclass(frozen=True, slots=True)
class SpellCastValidation:
    valid: bool
    cast_level: int
    available_cast_levels: tuple[int, ...]
    focus_item_id: str | None = None
    material_uses: tuple[SpellMaterialUse, ...] = ()
    errors: tuple[str, ...] = ()


def available_spell_slot_levels(
    slots: Sequence[SpellSlotLike],
    spell_level: int,
) -> tuple[int, ...]:
    if spell_level == 0:
        return (0,)
    return tuple(
        sorted(
            {
                slot.level
                for slot in slots
                if slot.level >= spell_level and slot.remaining > 0
            }
        )
    )


def spell_is_accessible(
    spell: SpellDefinition,
    profiles: Sequence[SpellAccessProfile],
    *,
    prepared_spell_ids: Sequence[str] = (),
    always_prepared_spell_ids: Sequence[str] = (),
) -> bool:
    if spell.level == 0:
        return any(spell.id in profile.spell_ids for profile in profiles)
    prepared = set(prepared_spell_ids) | set(always_prepared_spell_ids)
    for profile in profiles:
        if spell.id not in profile.spell_ids:
            continue
        if profile.kind == SpellAccessKind.KNOWN:
            return True
        if profile.kind in {SpellAccessKind.PREPARED, SpellAccessKind.SPELLBOOK}:
            return spell.id in prepared
    return False


def validate_spell_cast(
    spell: SpellDefinition,
    *,
    slots: Sequence[SpellSlotLike],
    inventory: Sequence[SpellItemLike] = (),
    cast_level: int | None = None,
    allowed_focus_kinds: Sequence[str] = (),
    has_free_hand: bool = True,
    ritual: bool = False,
) -> SpellCastValidation:
    if ritual and not spell.ritual:
        return SpellCastValidation(
            valid=False,
            cast_level=spell.level,
            available_cast_levels=(),
            errors=(f"Czar {spell.name} nie ma znacznika rytuału.",),
        )
    levels = () if ritual else available_spell_slot_levels(slots, spell.level)
    selected_level = (
        (levels[0] if levels else spell.level)
        if cast_level is None
        else int(cast_level)
    )
    errors: list[str] = []
    if not ritual and selected_level not in levels:
        errors.append(
            f"Czar {spell.name} nie może zostać rzucony na poziomie {selected_level}; "
            f"dostępne poziomy: {', '.join(map(str, levels)) or 'brak'}."
        )

    focus = _usable_focus(inventory, allowed_focus_kinds)
    material_uses: list[SpellMaterialUse] = []
    for material in spell.components.materials:
        item = _material_item(inventory, material)
        if item is not None:
            material_uses.append(
                SpellMaterialUse(
                    item_id=item.id,
                    quantity=material.quantity,
                    consumed=material.consumed,
                )
            )
        elif material.can_be_replaced_by_focus and focus is not None:
            continue
        else:
            errors.append(f"Brak komponentu materialnego: {material.label}.")

    material_hand_available = bool(material_uses or focus is not None)
    if spell.components.somatic and not has_free_hand:
        if not (spell.components.materials and material_hand_available):
            errors.append("Brak wolnej dłoni do wykonania komponentu somatycznego.")

    return SpellCastValidation(
        valid=not errors,
        cast_level=selected_level,
        available_cast_levels=levels,
        focus_item_id=focus.id if focus is not None else None,
        material_uses=tuple(material_uses),
        errors=tuple(errors),
    )


def _usable_focus(
    inventory: Sequence[SpellItemLike],
    allowed_focus_kinds: Sequence[str],
) -> SpellItemLike | None:
    allowed = set(allowed_focus_kinds)
    for item in inventory:
        kind = item.spellcasting_focus_kind
        kind_value = getattr(kind, "value", kind)
        if (
            item.quantity > 0
            and item.equipped
            and not item.broken
            and kind_value in allowed
        ):
            return item
    return None


def _material_item(
    inventory: Sequence[SpellItemLike],
    material: SpellMaterial,
) -> SpellItemLike | None:
    for item in inventory:
        if (
            (item.id == material.item_id or item.source_ref == material.item_id)
            and item.quantity >= material.quantity
            and not item.broken
            and item.value_cp >= material.minimum_value_cp
        ):
            return item
    return None
