from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable, Mapping

from dnd_board_game.actors import Actor, Faction, actor_has_feature
from dnd_board_game.hardware import DEFAULT_COLORS, LedFeedback, LedFrame, LedRole
from dnd_board_game.rules import (
    D20RollInput,
    D20RollKind,
    D20RollRequest,
    D20RollResult,
    RollModifier,
    RollModifierType,
    RollMode,
    apply_actor_d20_traits,
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

    def advance_turn(
        self,
        *,
        skip_defeated: bool = True,
        skip_actor_ids: frozenset[str] = frozenset(),
    ) -> InitiativeOrder:
        if not self.entries:
            raise ValueError("Initiative order is empty.")
        index = self.current_index
        round_number = self.round_number
        for _ in self.entries:
            index += 1
            if index >= len(self.entries):
                index = 0
                round_number += 1
            if str(self.entries[index].actor.id) in skip_actor_ids:
                continue
            if not skip_defeated or self.entries[index].actor.can_take_combat_turn():
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
        modifier = dexterity_modifier(actor) + (
            2 if actor_has_feature(actor, "scouts_vigilance") else 0
        )
        request = apply_actor_d20_traits(
            actor,
            _initiative_request(
                modifier,
                roll_modes.get(str(actor.id), RollMode.NORMAL),
            ),
            D20RollKind.ABILITY_CHECK,
        )
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
    modifier = dexterity_modifier(actor) + (
        2 if actor_has_feature(actor, "scouts_vigilance") else 0
    )
    request = apply_actor_d20_traits(
        actor,
        _initiative_request(modifier, mode),
        D20RollKind.ABILITY_CHECK,
    )
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
    original = (
        (natural_roll,)
        if natural_roll_2 is None
        else (natural_roll, natural_roll_2)
    )
    rerolls = (
        tuple(rng.randint(1, 20) for value in original if value == 1)
        if prompt.request.reroll_natural_ones
        else ()
    )
    roll = resolve_d20_roll(
        D20RollInput(prompt.request, natural_roll, natural_roll_2, rerolls)
    )
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
                "Inicjatywa (Zręczność i cechy)",
                dex_modifier,
                RollModifierType.ABILITY,
                stacking_key="initiative_dexterity",
            ),
        ),
        mode=mode,
    )
