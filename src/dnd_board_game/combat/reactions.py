from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass, replace
from enum import StrEnum


class ReactionKind(StrEnum):
    READY_ATTACK = "ready_attack"
    OPPORTUNITY_ATTACK = "opportunity_attack"
    DEFENSIVE_SPELL = "defensive_spell"
    SPELL_COUNTER = "spell_counter"


class ReactionStage(StrEnum):
    CHOICE = "choice"
    ATTACK_ROLL = "attack_roll"
    DAMAGE_ROLL = "damage_roll"
    ABILITY_CHECK = "ability_check"


@dataclass(frozen=True, slots=True)
class ReactionOption:
    """One ordered reaction that may interrupt an in-progress action."""

    id: str
    kind: ReactionKind
    reactor_actor_id: str
    target_actor_id: str
    trigger_event: str
    effect_id: str | None = None
    label: str = ""
    value: int = 0
    spell_level: int = 0
    cast_levels: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Reaction option id cannot be empty.")
        if not self.reactor_actor_id.strip():
            raise ValueError("Reaction reactor actor id cannot be empty.")
        if not self.target_actor_id.strip():
            raise ValueError("Reaction target actor id cannot be empty.")
        if not self.trigger_event.strip():
            raise ValueError("Reaction trigger event cannot be empty.")


@dataclass(frozen=True, slots=True)
class ReactionWindow:
    """Ordered reactions suspending one actor's unresolved action."""

    interrupted_actor_id: str
    trigger_event: str
    options: tuple[ReactionOption, ...]
    current_index: int = 0
    stage: ReactionStage = ReactionStage.CHOICE
    natural_roll: int | None = None
    natural_rolls: tuple[int, ...] = ()
    total: int | None = None
    hit: bool | None = None
    critical: bool = False
    dc: int | None = None
    modifier: int | None = None
    cast_level: int | None = None

    def __post_init__(self) -> None:
        if not self.interrupted_actor_id.strip():
            raise ValueError("Interrupted actor id cannot be empty.")
        if not self.trigger_event.strip():
            raise ValueError("Reaction window trigger event cannot be empty.")
        if not self.options:
            raise ValueError("Reaction window requires at least one option.")
        if len({option.id for option in self.options}) != len(self.options):
            raise ValueError("Reaction option ids must be unique within a window.")
        if not 0 <= self.current_index < len(self.options):
            raise ValueError("Reaction window current index is out of range.")

    @property
    def current_option(self) -> ReactionOption:
        return self.options[self.current_index]

    @property
    def remaining_options(self) -> tuple[ReactionOption, ...]:
        return self.options[self.current_index :]


def open_reaction_window(
    *,
    interrupted_actor_id: str,
    trigger_event: str,
    options: tuple[ReactionOption, ...],
) -> ReactionWindow | None:
    if not options:
        return None
    return ReactionWindow(
        interrupted_actor_id=interrupted_actor_id,
        trigger_event=trigger_event,
        options=options,
    )


def start_current_reaction(window: ReactionWindow) -> ReactionWindow:
    if window.stage != ReactionStage.CHOICE:
        raise ValueError("Current reaction is not waiting for a choice.")
    return replace(window, stage=ReactionStage.ATTACK_ROLL)


def record_current_reaction_attack(
    window: ReactionWindow,
    *,
    natural_roll: int,
    natural_rolls: tuple[int, ...],
    total: int,
    hit: bool,
    critical: bool,
) -> ReactionWindow:
    if window.stage != ReactionStage.ATTACK_ROLL:
        raise ValueError("Current reaction is not waiting for an attack roll.")
    return replace(
        window,
        stage=(
            ReactionStage.DAMAGE_ROLL
            if hit
            else ReactionStage.ATTACK_ROLL
        ),
        natural_roll=int(natural_roll),
        natural_rolls=tuple(int(roll) for roll in natural_rolls),
        total=int(total),
        hit=bool(hit),
        critical=bool(critical),
    )


def advance_reaction_window(
    window: ReactionWindow,
    *,
    available_reactor_ids: Collection[str] | None = None,
) -> ReactionWindow | None:
    """Complete the current option and select the next still-available reactor."""

    next_index = window.current_index + 1
    while next_index < len(window.options):
        option = window.options[next_index]
        if (
            available_reactor_ids is None
            or option.reactor_actor_id in available_reactor_ids
        ):
            return replace(
                window,
                current_index=next_index,
                stage=ReactionStage.CHOICE,
                natural_roll=None,
                natural_rolls=(),
                total=None,
                hit=None,
                critical=False,
                dc=None,
                modifier=None,
                cast_level=None,
            )
        next_index += 1
    return None
