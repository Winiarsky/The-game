"""Shared action-source selection for authored exploration goals."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from dnd_board_game.actors import Actor
from dnd_board_game.combat import actor_spell_cast_validation
from dnd_board_game.exploration import ExplorationResource, ExplorationState
from dnd_board_game.rules import spellcasting_ability_for_spell


class ExplorationActionSourceKind(StrEnum):
    RESOURCE = "resource"
    ITEM = "item"
    TOOL = "tool"
    WEAPON = "weapon"
    SPELL = "spell"


@dataclass(frozen=True, slots=True)
class ExplorationActionSource:
    id: str
    reference_id: str
    label: str
    kind: ExplorationActionSourceKind
    tags: tuple[str, ...]
    target_tags: tuple[str, ...] = ()
    consequence_tags: tuple[str, ...] = ()
    owner_actor_id: str | None = None
    owner_name: str = ""
    modifier: int = 0
    spell_level: int = 0
    check_ability: str | None = None
    available: bool = True
    unavailable_reason: str = ""

    def matches(self, accepted_tags: tuple[str, ...]) -> bool:
        return bool(set(self.tags).intersection(accepted_tags))

    def as_payload(self, accepted_tags: tuple[str, ...]) -> dict[str, object]:
        return {
            "id": self.id,
            "reference_id": self.reference_id,
            "label": self.label,
            "kind": self.kind.value,
            "tags": list(self.tags),
            "matched_tags": [tag for tag in accepted_tags if tag in self.tags],
            "target_tags": list(self.target_tags),
            "consequence_tags": list(self.consequence_tags),
            "owner_actor_id": self.owner_actor_id,
            "owner_name": self.owner_name,
            "modifier": self.modifier,
            "spell_level": self.spell_level,
            "check_ability": self.check_ability,
            "available": self.available,
            "unavailable_reason": self.unavailable_reason,
        }


def action_sources_for_goal(
    state: ExplorationState,
    actors: tuple[Actor, ...],
    accepted_tags: tuple[str, ...],
) -> tuple[ExplorationActionSource, ...]:
    if not accepted_tags:
        return ()
    sources = (
        *_resource_sources(state),
        *_actor_item_sources(actors),
        *_actor_spell_sources(actors),
    )
    return tuple(
        sorted(
            (source for source in sources if source.matches(accepted_tags)),
            key=lambda source: (
                not source.available,
                source.kind.value,
                source.owner_name,
                source.label,
            ),
        )
    )


def selected_action_source(
    state: ExplorationState,
    actors: tuple[Actor, ...],
    accepted_tags: tuple[str, ...],
    source_id: str | None,
    *,
    lead_actor_id: str | None,
    required: bool,
) -> ExplorationActionSource | None:
    if source_id is None or not source_id.strip():
        if required:
            raise ValueError("Ten sposób wymaga wybrania czaru, przedmiotu albo narzędzia.")
        return None
    source = next(
        (
            candidate
            for candidate in action_sources_for_goal(state, actors, accepted_tags)
            if candidate.id == source_id
        ),
        None,
    )
    if source is None:
        raise ValueError("Wybrane źródło nie pasuje do tego celu albo nie istnieje.")
    if not source.available:
        raise ValueError(source.unavailable_reason or "Wybrane źródło nie jest dostępne.")
    if (
        source.owner_actor_id is not None
        and lead_actor_id is not None
        and source.owner_actor_id != lead_actor_id
    ):
        raise ValueError(
            f"{source.owner_name} posiada wybrane źródło i musi prowadzić tę próbę."
        )
    return source


def resource_for_action_source(
    state: ExplorationState,
    source: ExplorationActionSource | None,
) -> ExplorationResource | None:
    if source is None:
        return None
    if source.kind == ExplorationActionSourceKind.RESOURCE:
        return next(
            (resource for resource in state.resources if resource.id == source.reference_id),
            None,
        )
    if source.modifier == 0:
        return None
    return ExplorationResource(
        id=source.id,
        label=source.label,
        bonus_tags=source.tags,
        modifier=source.modifier,
        properties=(),
    )


def _resource_sources(state: ExplorationState) -> tuple[ExplorationActionSource, ...]:
    owned = set(state.inventory_resource_ids)
    return tuple(
        ExplorationActionSource(
            id=f"resource:{resource.id}",
            reference_id=resource.id,
            label=resource.label,
            kind=ExplorationActionSourceKind.RESOURCE,
            tags=tuple(dict.fromkeys((*resource.bonus_tags, *_property_tags(resource.properties)))),
            modifier=resource.modifier,
            available=resource.id in owned,
            unavailable_reason="Drużyna nie posiada już tego zasobu.",
        )
        for resource in state.resources
    )


def _actor_item_sources(actors: tuple[Actor, ...]) -> tuple[ExplorationActionSource, ...]:
    result: list[ExplorationActionSource] = []
    for actor in actors:
        if actor.faction.value != "ally":
            continue
        for item in actor.inventory:
            if item.quantity < 1:
                continue
            kind = (
                ExplorationActionSourceKind.WEAPON
                if item.kind == "weapon"
                else ExplorationActionSourceKind.TOOL
                if item.tool_proficiency_id is not None or item.kind == "tool"
                else ExplorationActionSourceKind.ITEM
            )
            tags = list(_property_tags(item.properties))
            if kind == ExplorationActionSourceKind.WEAPON:
                tags.extend(("damage", "damage_object", "break"))
            if item.tool_proficiency_id == "thieves_tools":
                tags.extend(("unlock", "lockpicking"))
            normalized_tags = tuple(dict.fromkeys(tags))
            result.append(
                ExplorationActionSource(
                    id=f"actor:{actor.id}:item:{item.id}",
                    reference_id=item.id,
                    label=item.name,
                    kind=kind,
                    tags=normalized_tags,
                    owner_actor_id=str(actor.id),
                    owner_name=actor.name,
                    modifier=2 if "climbing_aid" in normalized_tags else 0,
                    available=item.available,
                    unavailable_reason=f"{item.name} jest uszkodzony albo niedostępny.",
                )
            )
    return tuple(result)


def _actor_spell_sources(actors: tuple[Actor, ...]) -> tuple[ExplorationActionSource, ...]:
    result: list[ExplorationActionSource] = []
    for actor in actors:
        if actor.faction.value != "ally":
            continue
        for spell in actor.spells:
            if not spell.exploration_tags:
                continue
            validation = actor_spell_cast_validation(actor, spell.id)
            available = validation is not None and validation.valid
            reason = (
                ""
                if available
                else " ".join(validation.errors)
                if validation is not None
                else f"{actor.name} nie może teraz rzucić tego czaru."
            )
            result.append(
                ExplorationActionSource(
                    id=f"actor:{actor.id}:spell:{spell.id}",
                    reference_id=spell.id,
                    label=spell.name,
                    kind=ExplorationActionSourceKind.SPELL,
                    tags=spell.exploration_tags,
                    target_tags=spell.exploration_target_tags,
                    consequence_tags=spell.exploration_consequence_tags,
                    owner_actor_id=str(actor.id),
                    owner_name=actor.name,
                    spell_level=spell.level,
                    check_ability=spellcasting_ability_for_spell(actor, spell.id),
                    available=available,
                    unavailable_reason=reason,
                )
            )
    return tuple(result)


def _property_tags(properties: tuple[str, ...]) -> tuple[str, ...]:
    mapping = {
        "cutting": ("cut", "break"),
        "sharp": ("cut", "damage_object"),
        "prying": ("pry", "break"),
        "load_bearing": ("climbing_aid",),
        "binding": ("climbing_aid", "bind"),
        "flexible": ("bind",),
    }
    return tuple(
        dict.fromkeys(
            tag
            for prop in properties
            for tag in mapping.get(prop, ())
        )
    )


__all__ = [
    "ExplorationActionSource",
    "ExplorationActionSourceKind",
    "action_sources_for_goal",
    "resource_for_action_source",
    "selected_action_source",
]
