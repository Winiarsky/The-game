from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from dnd_board_game.world import Coordinate


class CombatMenuCategory(StrEnum):
    FIELD = "field"
    ATTACK = "attack"
    MANEUVER = "maneuver"
    MAGIC = "magic"
    ITEM = "item"
    SUPPORT = "support"
    EQUIPMENT = "equipment"
    BASIC = "basic"
    TURN = "turn"


class CombatMenuAction(StrEnum):
    MOVE = "move"
    ATTACK = "attack"
    EQUIP_AND_ATTACK = "equip_and_attack"
    TWO_WEAPON_ATTACK = "two_weapon_attack"
    AREA_SPELL = "area_spell"
    HEAL = "heal"
    INTERACT = "interact"
    APPROACH_AND_INTERACT = "approach_and_interact"
    PICK_UP = "pick_up"
    APPROACH_AND_PICK_UP = "approach_and_pick_up"
    LOOT = "loot"
    LOOT_ITEM = "loot_item"
    LOOT_CURRENCY = "loot_currency"
    EQUIP_WEAPON = "equip_weapon"
    STOW_WEAPON = "stow_weapon"
    DROP_WEAPON = "drop_weapon"
    DON_SHIELD = "don_shield"
    DOFF_SHIELD = "doff_shield"
    SELECT_ATTACK_SOURCE = "select_attack_source"
    SELECT_HEALING_SOURCE = "select_healing_source"
    COMBAT_ACTION = "combat_action"
    CLASS_FEATURE = "class_feature"
    TARGETED_ITEM_ACTION = "targeted_item_action"
    DASH = "dash"
    DODGE = "dodge"
    DISENGAGE = "disengage"
    HELP = "help"
    READY = "ready"
    HIDE = "hide"
    SEARCH = "search"
    ESCAPE_NET = "escape_net"
    SHOVE = "shove"
    GRAPPLE = "grapple"
    DROP_PRONE = "drop_prone"
    STAND_UP = "stand_up"
    END_TURN = "end_turn"


@dataclass(frozen=True, slots=True)
class CombatMenuOption:
    id: str
    label: str
    description: str
    category: CombatMenuCategory
    action: CombatMenuAction
    position: Coordinate | None = None
    source_id: str | None = None
    action_id: str | None = None
    cast_level: int | None = None
    destination: Coordinate | None = None
    movement_cost_feet: int = 0
    dropped_weapon_id: str | None = None
    item_id: str | None = None
    target_actor_id: str | None = None
    loot_bundle_id: str | None = None
    loot_quantity_max: int | None = None
    loot_unit_weight_lb: float | None = None
    recipient_remaining_capacity_lb: float | None = None
    currency_denomination: str | None = None
    shove_mode: str | None = None
    grapple_mode: str | None = None
    provider: str = ""

    def as_payload(self) -> dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "category": self.category.value,
            "action": self.action.value,
            "position": [self.position.col, self.position.row] if self.position is not None else None,
            "source_id": self.source_id,
            "action_id": self.action_id,
            "cast_level": self.cast_level,
            "destination": [self.destination.col, self.destination.row] if self.destination is not None else None,
            "movement_cost_feet": self.movement_cost_feet,
            "dropped_weapon_id": self.dropped_weapon_id,
            "item_id": self.item_id,
            "target_actor_id": self.target_actor_id,
            "loot_bundle_id": self.loot_bundle_id,
            "loot_quantity_max": self.loot_quantity_max,
            "loot_unit_weight_lb": self.loot_unit_weight_lb,
            "recipient_remaining_capacity_lb": self.recipient_remaining_capacity_lb,
            "currency_denomination": self.currency_denomination,
            "shove_mode": self.shove_mode,
            "grapple_mode": self.grapple_mode,
            "provider": self.provider,
        }


_CATEGORY_ORDER = {
    CombatMenuCategory.FIELD: 0,
    CombatMenuCategory.ATTACK: 1,
    CombatMenuCategory.MANEUVER: 2,
    CombatMenuCategory.MAGIC: 3,
    CombatMenuCategory.ITEM: 4,
    CombatMenuCategory.SUPPORT: 5,
    CombatMenuCategory.EQUIPMENT: 6,
    CombatMenuCategory.BASIC: 7,
    CombatMenuCategory.TURN: 8,
}


@dataclass(frozen=True, slots=True)
class ContextualActionCatalog:
    """Stable, grouped collection assembled by independent action providers."""

    options: tuple[CombatMenuOption, ...]

    @classmethod
    def collect(cls, *groups: tuple[CombatMenuOption, ...]) -> ContextualActionCatalog:
        indexed = [option for group in groups for option in group]
        ids = [option.id for option in indexed]
        if len(ids) != len(set(ids)):
            raise ValueError("Contextual action ids must be unique.")
        ordered = tuple(
            option
            for _index, option in sorted(
                enumerate(indexed),
                key=lambda entry: (_CATEGORY_ORDER[entry[1].category], entry[0]),
            )
        )
        return cls(ordered)


@dataclass(frozen=True, slots=True)
class CombatContextMenu:
    actor_id: str
    position: Coordinate
    title: str
    options: tuple[CombatMenuOption, ...]
    selected_index: int = 0
    is_self_menu: bool = False
    notice: str = ""

    @property
    def selected_option(self) -> CombatMenuOption:
        if not self.options:
            raise ValueError("Menu walki nie ma dostępnych opcji.")
        return self.options[self.selected_index % len(self.options)]

    def move_selection(self, delta: int) -> CombatContextMenu:
        if not self.options:
            return self
        return replace(self, selected_index=(self.selected_index + delta) % len(self.options))

    def select(self, option_id: str) -> CombatContextMenu:
        index = next((index for index, option in enumerate(self.options) if option.id == option_id), None)
        if index is None:
            raise ValueError("Wybrana opcja nie należy do aktywnego menu walki.")
        return replace(self, selected_index=index)

    def as_payload(self) -> dict[str, object]:
        return {
            "actor_id": self.actor_id,
            "position": [self.position.col, self.position.row],
            "title": self.title,
            "is_self_menu": self.is_self_menu,
            "notice": self.notice,
            "selected_index": self.selected_index,
            "selected_option_id": self.selected_option.id if self.options else None,
            "options": [option.as_payload() for option in self.options],
        }
