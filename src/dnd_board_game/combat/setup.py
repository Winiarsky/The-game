from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Iterable

from dnd_board_game.actors import Actor, Faction
from dnd_board_game.hardware import LedColor, LedFeedback, LedFrame, LedRole
from dnd_board_game.world import Coordinate


class SetupVisibility(StrEnum):
    VISIBLE = "visible"
    HIDDEN = "hidden"
    CONDITIONAL = "conditional"


class EnvironmentSetupType(StrEnum):
    OBSTACLE = "obstacle"
    DIFFICULT_TERRAIN = "difficult_terrain"
    BLOCKING_TERRAIN = "blocking_terrain"
    COVER = "cover"
    INTERACTABLE = "interactable"
    NPC = "npc"
    CONTAINER = "container"
    MARKER = "marker"
    CUSTOM = "custom"


class SetupStepKind(StrEnum):
    ACTORS = "actors"
    ENEMIES = "enemies"
    ENVIRONMENT = "environment"


@dataclass(frozen=True, slots=True)
class ActorSetupEntry:
    actor: Actor
    role: str
    position: Coordinate | None = None
    visibility: SetupVisibility = SetupVisibility.VISIBLE


@dataclass(frozen=True, slots=True)
class EnvironmentSetupEntry:
    id: str
    name: str
    setup_type: EnvironmentSetupType
    positions: tuple[Coordinate, ...] = field(default_factory=tuple)
    visibility: SetupVisibility = SetupVisibility.VISIBLE
    description: str = ""


@dataclass(frozen=True, slots=True)
class EncounterSetup:
    name: str
    actors: tuple[ActorSetupEntry, ...] = field(default_factory=tuple)
    environment: tuple[EnvironmentSetupEntry, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class SetupStep:
    kind: SetupStepKind
    label: str
    positions: tuple[Coordinate, ...]
    color: tuple[int, int, int]
    message: str
    visibility: SetupVisibility = SetupVisibility.VISIBLE


SETUP_COLORS: dict[str, tuple[int, int, int]] = {
    "heroes": LedColor.PLAYER_START_ZONE,
    "enemies": LedColor.ENEMY,
    "blocking": LedColor.BLOCKING_TERRAIN,
    "difficult": LedColor.DIFFICULT_TERRAIN,
    "interactive": LedColor.INTERACTIVE_OBJECT,
    "marker": LedColor.MARKER,
}


def build_setup_steps(setup: EncounterSetup) -> tuple[SetupStep, ...]:
    steps: list[SetupStep] = [
        SetupStep(
            kind=SetupStepKind.ENVIRONMENT,
            label="Start walki",
            positions=(),
            color=SETUP_COLORS["marker"],
            message=(
                f"Rozpoczyna się walka: {setup.name}. "
                "Najpierw przygotujcie planszę i ustawcie figurki oraz jawne elementy otoczenia."
            ),
        )
    ]

    hero_entries = _visible_actor_entries(
        entry for entry in setup.actors if entry.actor.faction == Faction.ALLY
    )
    enemy_entries = _visible_actor_entries(
        entry for entry in setup.actors if entry.actor.faction != Faction.ALLY
    )
    if hero_entries:
        steps.append(_actor_step(SetupStepKind.ACTORS, "bohaterów", hero_entries, SETUP_COLORS["heroes"]))
    if enemy_entries:
        steps.append(_actor_step(SetupStepKind.ENEMIES, "jawnych przeciwników i NPC", enemy_entries, SETUP_COLORS["enemies"]))

    grouped_environment: dict[EnvironmentSetupType, list[EnvironmentSetupEntry]] = defaultdict(list)
    for entry in setup.environment:
        if entry.visibility != SetupVisibility.VISIBLE:
            continue
        grouped_environment[entry.setup_type].append(entry)

    for setup_type in sorted(grouped_environment, key=lambda item: item.value):
        entries = grouped_environment[setup_type]
        positions = tuple(_unique_positions(position for entry in entries for position in entry.positions))
        names = ", ".join(entry.name for entry in entries)
        label = _environment_label(setup_type)
        steps.append(
            SetupStep(
                kind=SetupStepKind.ENVIRONMENT,
                label=label,
                positions=positions,
                color=_environment_color(setup_type),
                message=f"Ustaw {label}: {names}{_positions_text(positions)}.",
            )
        )

    return tuple(steps)


def setup_led_feedback(step: SetupStep) -> LedFeedback:
    if step.visibility != SetupVisibility.VISIBLE or not step.positions:
        return LedFeedback()
    return LedFeedback((LedFrame(step.positions, step.color, _led_role_for_step(step)),))


def build_setup_instructions(setup: EncounterSetup) -> tuple[str, ...]:
    return tuple(step.message for step in build_setup_steps(setup))


def _visible_actor_entries(entries: Iterable[ActorSetupEntry]) -> tuple[ActorSetupEntry, ...]:
    return tuple(entry for entry in entries if entry.visibility == SetupVisibility.VISIBLE)


def _actor_step(kind: SetupStepKind, label: str, entries: tuple[ActorSetupEntry, ...], color: tuple[int, int, int]) -> SetupStep:
    positions = tuple(_unique_positions(entry.position for entry in entries if entry.position is not None))
    actor_names = ", ".join(entry.actor.name for entry in entries)
    return SetupStep(
        kind=kind,
        label=label,
        positions=positions,
        color=color,
        message=f"Ustaw {label}: {actor_names}{_positions_text(positions)}.",
    )


def _positions_text(positions: tuple[Coordinate, ...]) -> str:
    if not positions:
        return ""
    return " na polach: " + ", ".join(f"({position.col},{position.row})" for position in positions)


def _unique_positions(positions: Iterable[Coordinate | None]) -> tuple[Coordinate, ...]:
    result: list[Coordinate] = []
    seen: set[Coordinate] = set()
    for position in positions:
        if position is None or position in seen:
            continue
        seen.add(position)
        result.append(position)
    return tuple(sorted(result))


def _environment_label(setup_type: EnvironmentSetupType) -> str:
    labels = {
        EnvironmentSetupType.OBSTACLE: "przeszkody",
        EnvironmentSetupType.DIFFICULT_TERRAIN: "trudny teren",
        EnvironmentSetupType.BLOCKING_TERRAIN: "blokady",
        EnvironmentSetupType.COVER: "osłony",
        EnvironmentSetupType.INTERACTABLE: "obiekty interaktywne",
        EnvironmentSetupType.NPC: "NPC",
        EnvironmentSetupType.CONTAINER: "skrzynie i pojemniki",
        EnvironmentSetupType.MARKER: "markery",
        EnvironmentSetupType.CUSTOM: "elementy otoczenia",
    }
    return labels[setup_type]


def _environment_color(setup_type: EnvironmentSetupType) -> tuple[int, int, int]:
    if setup_type in {EnvironmentSetupType.OBSTACLE, EnvironmentSetupType.BLOCKING_TERRAIN, EnvironmentSetupType.COVER}:
        return SETUP_COLORS["blocking"]
    if setup_type == EnvironmentSetupType.DIFFICULT_TERRAIN:
        return SETUP_COLORS["difficult"]
    if setup_type in {EnvironmentSetupType.INTERACTABLE, EnvironmentSetupType.NPC, EnvironmentSetupType.CONTAINER}:
        return SETUP_COLORS["interactive"]
    return SETUP_COLORS["marker"]


def _led_role_for_step(step: SetupStep) -> LedRole:
    if step.kind == SetupStepKind.ACTORS:
        return LedRole.ALLY
    if step.kind == SetupStepKind.ENEMIES:
        return LedRole.ENEMY
    if step.color == SETUP_COLORS["difficult"]:
        return LedRole.DIFFICULT_TERRAIN
    if step.color == SETUP_COLORS["blocking"]:
        return LedRole.BLOCKING_TERRAIN
    return LedRole.DESTINATION
