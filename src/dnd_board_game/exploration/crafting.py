"""Deterministic property-based crafting for exploration scenes."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .crafting_sources import CraftingSource, CraftingSourceKind, CraftingSourceRegistry
from .models import (
    CraftingComponentDisposition,
    CraftingComponentUse,
    ExplorationState,
    TemporaryItem,
    TemporaryItemScope,
)


class CraftingValidationError(ValueError):
    """Raised when a crafting draft is not grounded in available components."""


@dataclass(frozen=True, slots=True)
class CraftingPropertyRequirement:
    properties: tuple[str, ...]
    minimum_quantity: int = 1

    def __post_init__(self) -> None:
        if not self.properties:
            raise ValueError("Crafting property requirement needs at least one property.")
        if len(self.properties) != len(set(self.properties)):
            raise ValueError("Crafting property requirement cannot contain duplicate properties.")
        if self.minimum_quantity < 1:
            raise ValueError("Crafting property requirement minimum_quantity must be positive.")


@dataclass(frozen=True, slots=True)
class CraftingPurpose:
    id: str
    label: str
    requirements: tuple[CraftingPropertyRequirement, ...]
    bonus_tags: tuple[str, ...]
    modifier: int
    uses: int
    time_cost_minutes: int
    risk: str = ""

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.label.strip():
            raise ValueError("Crafting purpose id and label cannot be empty.")
        if not self.requirements:
            raise ValueError("Crafting purpose needs at least one requirement.")
        if not self.bonus_tags:
            raise ValueError("Crafting purpose needs at least one bonus tag.")
        if not -2 <= self.modifier <= 2:
            raise ValueError("Crafting purpose modifier must be between -2 and 2.")
        if self.uses < 1:
            raise ValueError("Crafting purpose uses must be positive.")
        if self.time_cost_minutes < 0:
            raise ValueError("Crafting purpose time_cost_minutes cannot be negative.")


@dataclass(frozen=True, slots=True)
class CraftingPolicy:
    schema_version: int = 1
    purposes: tuple[CraftingPurpose, ...] = ()
    max_active_items: int = 3
    property_ids: tuple[str, ...] = ()
    property_labels: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError("Unsupported crafting policy schema version.")
        ids = tuple(purpose.id for purpose in self.purposes)
        if len(ids) != len(set(ids)):
            raise ValueError("Crafting policy cannot contain duplicate purpose ids.")
        if len(self.property_ids) != len(set(self.property_ids)):
            raise ValueError("Crafting policy cannot contain duplicate property ids.")
        if any(not property_id.strip() for property_id in self.property_ids):
            raise ValueError("Crafting policy property ids cannot be empty.")
        label_ids = tuple(property_id for property_id, _label in self.property_labels)
        if len(label_ids) != len(set(label_ids)):
            raise ValueError("Crafting policy property labels cannot contain duplicate ids.")
        if any(not property_id.strip() or not label.strip() for property_id, label in self.property_labels):
            raise ValueError("Crafting policy property labels cannot be empty.")
        if set(label_ids) - set(self.property_ids):
            raise ValueError("Crafting policy labels must reference known property ids.")
        if self.max_active_items < 1:
            raise ValueError("Crafting policy max_active_items must be positive.")

    def purpose_by_id(self, purpose_id: str) -> CraftingPurpose | None:
        return next((purpose for purpose in self.purposes if purpose.id == purpose_id), None)

    def property_label(self, property_id: str) -> str:
        return dict(self.property_labels).get(property_id, property_id)


@dataclass(frozen=True, slots=True)
class CraftingComponentSelection:
    source_id: str
    quantity: int = 1

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("Crafting component selection source_id cannot be empty.")
        if self.quantity < 1:
            raise ValueError("Crafting component selection quantity must be positive.")


@dataclass(frozen=True, slots=True)
class CraftingDraft:
    label: str
    description: str
    purpose_id: str
    components: tuple[CraftingComponentSelection, ...]
    scope: TemporaryItemScope = TemporaryItemScope.SCENE
    auto_select_missing_components: bool = False

    def __post_init__(self) -> None:
        if not self.label.strip() or not self.description.strip() or not self.purpose_id.strip():
            raise ValueError("Crafting draft label, description and purpose_id cannot be empty.")
        if not self.components and not self.auto_select_missing_components:
            raise ValueError("Crafting draft needs at least one component.")
        ids = tuple(component.source_id for component in self.components)
        if len(ids) != len(set(ids)):
            raise ValueError("Crafting draft cannot select the same source more than once.")


@dataclass(frozen=True, slots=True)
class CraftingPlan:
    draft: CraftingDraft
    purpose: CraftingPurpose
    component_uses: tuple[CraftingComponentUse, ...]


def validate_crafting_draft(
    state: ExplorationState,
    draft: CraftingDraft,
    registry: CraftingSourceRegistry,
    policy: CraftingPolicy,
) -> CraftingPlan:
    active_items = tuple(
        item
        for item in state.temporary_items
        if item.purpose_id is not None and not item.dismantled
    )
    if len(active_items) >= policy.max_active_items:
        raise CraftingValidationError("Osiągnięto limit aktywnych konstrukcji tymczasowych.")
    purpose = policy.purpose_by_id(draft.purpose_id)
    if purpose is None:
        raise CraftingValidationError(f"Nieznany cel konstrukcji: {draft.purpose_id}.")

    resolved_components = draft.components
    if draft.auto_select_missing_components:
        resolved_components = _complete_component_selection(draft.components, registry, purpose)

    selected: list[tuple[CraftingSource, CraftingComponentSelection]] = []
    for selection in resolved_components:
        source = registry.source_by_id(selection.source_id)
        if source is None:
            raise CraftingValidationError(f"Nieznane źródło komponentu: {selection.source_id}.")
        if not source.usable:
            raise CraftingValidationError(f"Komponent {source.label} nie jest obecnie dostępny.")
        if selection.quantity > source.quantity:
            raise CraftingValidationError(
                f"Brakuje komponentu {source.label}: dostępne {source.quantity}, wymagane {selection.quantity}."
            )
        if (
            source.kind == CraftingSourceKind.SCENE_FIXTURE
            and not source.portable
            and not source.detachable
        ):
            raise CraftingValidationError(
                f"Element {source.label} jest trwale związany ze sceną i nie może zostać użyty jako komponent."
            )
        selected.append((source, selection))

    for requirement in purpose.requirements:
        matching_quantity = sum(
            selection.quantity
            for source, selection in selected
            if set(requirement.properties).issubset(source.properties)
        )
        if matching_quantity < requirement.minimum_quantity:
            properties = ", ".join(requirement.properties)
            raise CraftingValidationError(
                f"Konstrukcja wymaga komponentów [{properties}] w ilości "
                f"{requirement.minimum_quantity}; zapewniono {matching_quantity}."
            )

    component_uses = tuple(
        CraftingComponentUse(
            source_id=source.id,
            quantity=selection.quantity,
            disposition=_component_disposition(source),
        )
        for source, selection in selected
    )
    resolved_draft = replace(draft, components=resolved_components)
    return CraftingPlan(draft=resolved_draft, purpose=purpose, component_uses=component_uses)


def craft_temporary_item(
    state: ExplorationState,
    draft: CraftingDraft,
    registry: CraftingSourceRegistry,
    policy: CraftingPolicy,
) -> tuple[ExplorationState, TemporaryItem]:
    plan = validate_crafting_draft(state, draft, registry, policy)
    item = TemporaryItem(
        id=_next_crafted_item_id(state),
        template_id=None,
        label=plan.draft.label,
        description=plan.draft.description,
        bonus_tags=plan.purpose.bonus_tags,
        modifier=plan.purpose.modifier,
        advantage=False,
        uses_remaining=plan.purpose.uses,
        created_in_zone_id=state.party_position.zone_id,
        source_materials=tuple(component.source_id for component in plan.draft.components),
        risk=plan.purpose.risk,
        purpose_id=plan.purpose.id,
        component_uses=plan.component_uses,
        scope=draft.scope,
        time_cost_minutes=plan.purpose.time_cost_minutes,
    )
    return (
        replace(
            state,
            temporary_items=(*state.temporary_items, item),
            elapsed_minutes=state.elapsed_minutes + plan.purpose.time_cost_minutes,
        ),
        item,
    )


def dismantle_crafted_item(
    state: ExplorationState,
    item_id: str,
) -> tuple[ExplorationState, TemporaryItem]:
    items = list(state.temporary_items)
    for index, item in enumerate(items):
        if item.id != item_id:
            continue
        if item.purpose_id is None:
            raise CraftingValidationError("Przedmiot ze starego szablonu nie obsługuje rozmontowania.")
        if item.dismantled:
            raise CraftingValidationError("Konstrukcja została już rozmontowana.")
        dismantled = replace(item, dismantled=True, uses_remaining=0)
        items[index] = dismantled
        return replace(state, temporary_items=tuple(items)), dismantled
    raise CraftingValidationError(f"Nieznana konstrukcja tymczasowa: {item_id}.")


def _component_disposition(source: CraftingSource) -> CraftingComponentDisposition:
    if source.kind == CraftingSourceKind.SCENE_ITEM:
        return CraftingComponentDisposition.CONSUMED
    if source.kind == CraftingSourceKind.EXPLORATION_RESOURCE and source.consumed_on_use:
        return CraftingComponentDisposition.CONSUMED
    return CraftingComponentDisposition.RESERVED


def _complete_component_selection(
    initial: tuple[CraftingComponentSelection, ...],
    registry: CraftingSourceRegistry,
    purpose: CraftingPurpose,
) -> tuple[CraftingComponentSelection, ...]:
    quantities = {selection.source_id: selection.quantity for selection in initial}
    sources = {source.id: source for source in registry.available_sources}

    for selection in initial:
        source = registry.source_by_id(selection.source_id)
        if source is None:
            raise CraftingValidationError(f"Nieznane źródło komponentu: {selection.source_id}.")
        if not source.usable:
            raise CraftingValidationError(f"Komponent {source.label} nie jest obecnie dostępny.")
        if selection.quantity > source.quantity:
            raise CraftingValidationError(
                f"Brakuje komponentu {source.label}: dostępne {source.quantity}, wymagane {selection.quantity}."
            )

    for requirement in purpose.requirements:
        matching_quantity = sum(
            quantity
            for source_id, quantity in quantities.items()
            if source_id in sources
            and set(requirement.properties).issubset(sources[source_id].properties)
        )
        while matching_quantity < requirement.minimum_quantity:
            candidates = tuple(
                source
                for source in registry.available_sources
                if set(requirement.properties).issubset(source.properties)
                and quantities.get(source.id, 0) < source.quantity
                and not (
                    source.kind == CraftingSourceKind.SCENE_FIXTURE
                    and not source.portable
                    and not source.detachable
                )
            )
            if not candidates:
                properties = ", ".join(requirement.properties)
                raise CraftingValidationError(
                    f"Konstrukcja wymaga komponentów [{properties}] w ilości "
                    f"{requirement.minimum_quantity}; zapewniono {matching_quantity}."
                )
            selected = min(candidates, key=_automatic_component_priority)
            quantities[selected.id] = quantities.get(selected.id, 0) + 1
            matching_quantity += 1

    ordered_ids = tuple(selection.source_id for selection in initial)
    completed_ids = (*ordered_ids, *(source_id for source_id in quantities if source_id not in ordered_ids))
    return tuple(
        CraftingComponentSelection(source_id=source_id, quantity=quantities[source_id])
        for source_id in completed_ids
    )


def _automatic_component_priority(source: CraftingSource) -> tuple[int, int, str]:
    kind_priority = {
        CraftingSourceKind.SCENE_ITEM: 0,
        CraftingSourceKind.EXPLORATION_RESOURCE: 1,
        CraftingSourceKind.ACTOR_INVENTORY: 2,
        CraftingSourceKind.SCENE_FIXTURE: 3,
        CraftingSourceKind.TEMPORARY_ITEM: 4,
    }
    detachment_priority = 1 if source.detachable and not source.portable else 0
    return kind_priority[source.kind], detachment_priority, source.id


def _next_crafted_item_id(state: ExplorationState) -> str:
    existing = {item.id for item in state.temporary_items}
    index = 1
    while f"temporary:crafted:{index}" in existing:
        index += 1
    return f"temporary:crafted:{index}"


__all__ = [
    "CraftingComponentSelection",
    "CraftingDraft",
    "CraftingPlan",
    "CraftingPolicy",
    "CraftingPropertyRequirement",
    "CraftingPurpose",
    "CraftingValidationError",
    "craft_temporary_item",
    "dismantle_crafted_item",
    "validate_crafting_draft",
]
