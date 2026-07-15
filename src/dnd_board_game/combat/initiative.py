from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable, Mapping

from dnd_board_game.actors import Actor, Faction
from dnd_board_game.hardware import DEFAULT_COLORS, LedFeedback, LedFrame, LedRole
from dnd_board_game.rules import (
    D20RollInput,
    D20RollRequest,
    D20RollResult,
    RollModifier,
    RollModifierType,
    RollMode,
    dexterity_modifier,
    resolve_d20_roll,
    roll_instruction,
)


@dataclass(frozen=True, slots=True)
class InitiativePrompt:
    actor: Actor
    message: str
    request: D20RollRequest
    source: str
    dexterity_modifier: int


@dataclass(frozen=True, slots=True)
class InitiativeEntry:
    actor: Actor
    roll: D20RollResult
    dexterity_modifier: int
    stable_order: int


@dataclass(frozen=True, slots=True)
class InitiativeOrder:
    entries: tuple[InitiativeEntry, ...]
    current_index: int = 0
    round_number: int = 1

    @property
    def current_entry(self) -> InitiativeEntry:
        if not self.entries:
            raise ValueError("Initiative order is empty.")
        return self.entries[self.current_index]

    @property
    def current_actor(self) -> Actor:
        return self.current_entry.actor

    def advance_turn(self, *, skip_defeated: bool = True) -> InitiativeOrder:
        if not self.entries:
            raise ValueError("Initiative order is empty.")
        index = self.current_index
        round_number = self.round_number
        for _ in self.entries:
            index += 1
            if index >= len(self.entries):
                index = 0
                round_number += 1
            if not skip_defeated or not self.entries[index].actor.is_defeated():
                return InitiativeOrder(self.entries, index, round_number)
        return InitiativeOrder(self.entries, self.current_index, self.round_number)


def build_player_initiative_prompts(
    actors: Iterable[Actor],
    roll_modes_by_actor_id: Mapping[str, RollMode] | None = None,
) -> tuple[InitiativePrompt, ...]:
    roll_modes = roll_modes_by_actor_id or {}
    prompts: list[InitiativePrompt] = []
    for actor in actors:
        if actor.faction != Faction.ALLY or actor.is_defeated():
            continue
        modifier = dexterity_modifier(actor)
        request = _initiative_request(modifier, roll_modes.get(str(actor.id), RollMode.NORMAL))
        instruction = roll_instruction(request)
        prompts.append(
            InitiativePrompt(
                actor=actor,
                message=f"Test inicjatywy: {actor.name}. {instruction.message}",
                request=request,
                source="player",
                dexterity_modifier=modifier,
            )
        )
    return tuple(prompts)


def build_enemy_initiative_prompt(
    actor: Actor,
    mode: RollMode = RollMode.NORMAL,
) -> InitiativePrompt:
    modifier = dexterity_modifier(actor)
    request = _initiative_request(modifier, mode)
    return InitiativePrompt(
        actor=actor,
        message=f"Inicjatywa przeciwnika {actor.name} zostanie rzucona automatycznie.",
        request=request,
        source="auto",
        dexterity_modifier=modifier,
    )


def roll_enemy_initiative(
    actor: Actor,
    rng: random.Random,
    mode: RollMode = RollMode.NORMAL,
) -> InitiativeEntry:
    prompt = build_enemy_initiative_prompt(actor, mode)
    natural_roll = rng.randint(1, 20)
    natural_roll_2 = rng.randint(1, 20) if mode != RollMode.NORMAL else None
    roll = resolve_d20_roll(D20RollInput(prompt.request, natural_roll, natural_roll_2))
    return InitiativeEntry(actor=actor, roll=roll, dexterity_modifier=prompt.dexterity_modifier, stable_order=0)


def build_initiative_order(entries: Iterable[InitiativeEntry]) -> InitiativeOrder:
    sorted_entries = sorted(
        tuple(entries),
        key=lambda entry: (-entry.roll.total, -entry.dexterity_modifier, entry.stable_order),
    )
    if not sorted_entries:
        raise ValueError("Cannot build initiative order without entries.")
    return InitiativeOrder(entries=tuple(sorted_entries))


def initiative_prompt_led_feedback(prompt: InitiativePrompt) -> LedFeedback:
    return LedFeedback(
        (
            LedFrame(
                (prompt.actor.position,),
                DEFAULT_COLORS[LedRole.ACTIVE_ACTOR],
                LedRole.ACTIVE_ACTOR,
            ),
        )
    )


def active_actor_led_feedback(order: InitiativeOrder) -> LedFeedback:
    return LedFeedback(
        (
            LedFrame(
                (order.current_actor.position,),
                DEFAULT_COLORS[LedRole.ACTIVE_ACTOR],
                LedRole.ACTIVE_ACTOR,
            ),
        )
    )


def _initiative_request(dex_modifier: int, mode: RollMode = RollMode.NORMAL) -> D20RollRequest:
    return D20RollRequest(
        modifiers=(
            RollModifier(
                "Modyfikator ze Zręczności",
                dex_modifier,
                RollModifierType.ABILITY,
                stacking_key="initiative_dexterity",
            ),
        ),
        mode=mode,
    )
