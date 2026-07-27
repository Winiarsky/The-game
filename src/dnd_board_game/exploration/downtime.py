"""Deterministic D&D 5e downtime crafting rules."""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import ceil

from dnd_board_game.actors import Actor, Faction
from dnd_board_game.inventory import (
    InventoryItem,
    add_inventory_item,
    currency_wallet_from_cp,
)


CRAFTING_PROGRESS_CP_PER_DAY = 500
WORKDAY_MINUTES = 8 * 60


@dataclass(frozen=True, slots=True)
class DowntimeCraftingRecipe:
    id: str
    label: str
    description: str
    zone_id: str
    workshop_label: str
    product: InventoryItem
    required_tool_id: str

    def __post_init__(self) -> None:
        for field_name, value in (
            ("id", self.id),
            ("label", self.label),
            ("zone_id", self.zone_id),
            ("workshop_label", self.workshop_label),
            ("required_tool_id", self.required_tool_id),
        ):
            if not value.strip():
                raise ValueError(f"Downtime crafting recipe {field_name} cannot be empty.")
        if self.product.value_cp <= 0:
            raise ValueError("Downtime crafting product must have a positive market value.")
        if not self.product.portable:
            raise ValueError("Downtime crafting product must be portable.")
        if self.product.magic_effects or self.product.requires_attunement:
            raise ValueError("Downtime crafting supports mundane products only.")

    @property
    def market_value_cp(self) -> int:
        return self.product.value_cp * self.product.quantity

    @property
    def material_cost_cp(self) -> int:
        return ceil(self.market_value_cp / 2)

    @property
    def work_days(self) -> int:
        return ceil(self.market_value_cp / CRAFTING_PROGRESS_CP_PER_DAY)

    @property
    def time_cost_minutes(self) -> int:
        return self.work_days * WORKDAY_MINUTES


@dataclass(frozen=True, slots=True)
class DowntimePolicy:
    crafting_recipes: tuple[DowntimeCraftingRecipe, ...] = ()

    def __post_init__(self) -> None:
        recipe_ids = tuple(recipe.id for recipe in self.crafting_recipes)
        if len(recipe_ids) != len(set(recipe_ids)):
            raise ValueError("Downtime crafting recipe ids must be unique.")

    def recipe_by_id(self, recipe_id: str) -> DowntimeCraftingRecipe:
        recipe = next(
            (candidate for candidate in self.crafting_recipes if candidate.id == recipe_id),
            None,
        )
        if recipe is None:
            raise ValueError(f"Unknown downtime crafting recipe: {recipe_id}.")
        return recipe


@dataclass(frozen=True, slots=True)
class DowntimeCraftingPlan:
    actor: Actor
    recipe: DowntimeCraftingRecipe
    material_cost_cp: int
    time_cost_minutes: int


@dataclass(frozen=True, slots=True)
class DowntimeCraftingResult:
    actor_before: Actor
    actor_after: Actor
    recipe: DowntimeCraftingRecipe
    material_cost_cp: int
    time_cost_minutes: int


def plan_downtime_crafting(
    *,
    actor: Actor,
    recipe: DowntimeCraftingRecipe,
    current_zone_id: str,
) -> DowntimeCraftingPlan:
    if actor.faction != Faction.ALLY:
        raise ValueError("Tylko członek drużyny może wykonywać rzemiosło w downtime.")
    if actor.is_defeated():
        raise ValueError(f"{actor.name} nie może pracować, gdy jest pokonany.")
    if current_zone_id != recipe.zone_id:
        raise ValueError(
            f"Ta receptura wymaga miejsca: {recipe.workshop_label}."
        )
    if recipe.required_tool_id not in actor.proficiencies.tools:
        raise ValueError(
            f"{actor.name} nie ma wymaganej biegłości: {recipe.required_tool_id}."
        )
    has_tool = any(
        item.available and item.tool_proficiency_id == recipe.required_tool_id
        for item in actor.inventory
    )
    if not has_tool:
        raise ValueError(
            f"{actor.name} nie ma wymaganych narzędzi: {recipe.required_tool_id}."
        )
    if actor.currency.total_cp < recipe.material_cost_cp:
        raise ValueError(
            f"{actor.name} nie ma dość monet na materiały "
            f"({recipe.material_cost_cp} cp)."
        )
    return DowntimeCraftingPlan(
        actor=actor,
        recipe=recipe,
        material_cost_cp=recipe.material_cost_cp,
        time_cost_minutes=recipe.time_cost_minutes,
    )


def complete_downtime_crafting(
    plan: DowntimeCraftingPlan,
) -> DowntimeCraftingResult:
    remaining_cp = plan.actor.currency.total_cp - plan.material_cost_cp
    actor_after = replace(
        plan.actor,
        currency=currency_wallet_from_cp(remaining_cp),
    )
    actor_after = add_inventory_item(actor_after, plan.recipe.product)
    return DowntimeCraftingResult(
        actor_before=plan.actor,
        actor_after=actor_after,
        recipe=plan.recipe,
        material_cost_cp=plan.material_cost_cp,
        time_cost_minutes=plan.time_cost_minutes,
    )
