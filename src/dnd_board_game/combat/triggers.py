from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace

from dnd_board_game.actors import Actor, ActorTrigger, TriggerEffectKind
from dnd_board_game.rules import EffectEvent

from .session import CombatState, replace_actor


@dataclass(frozen=True, slots=True)
class TriggerActivation:
    owner_actor_id: str
    trigger: ActorTrigger
    previous_temp_hp: int
    current_temp_hp: int

    @property
    def changed(self) -> bool:
        return self.previous_temp_hp != self.current_temp_hp


@dataclass(frozen=True, slots=True)
class TriggerResolution:
    state: CombatState
    activations: tuple[TriggerActivation, ...]


@dataclass(frozen=True, slots=True)
class ActorTriggerResolution:
    actors: tuple[Actor, ...]
    activations: tuple[TriggerActivation, ...]


def resolve_combat_triggers(
    state: CombatState,
    event: EffectEvent,
) -> TriggerResolution:
    updated_state = state
    activations: list[TriggerActivation] = []
    for owner, trigger in matching_actor_triggers(state, event):
        current_owner = next(
            actor for actor in updated_state.actors if actor.id == owner.id
        )
        if trigger.effect_kind == TriggerEffectKind.GRANT_TEMP_HP:
            updated_owner = replace(
                current_owner,
                temp_hp=max(current_owner.temp_hp, trigger.value),
            )
        else:
            raise ValueError(f"Unsupported trigger effect: {trigger.effect_kind}.")
        updated_state = replace_actor(updated_state, updated_owner)
        activations.append(
            TriggerActivation(
                str(owner.id),
                trigger,
                current_owner.temp_hp,
                updated_owner.temp_hp,
            )
        )
    return TriggerResolution(updated_state, tuple(activations))


def resolve_combat_trigger_events(
    state: CombatState,
    events: Iterable[EffectEvent],
) -> TriggerResolution:
    """Resolve an ordered event batch against the state produced by the prior event."""

    updated_state = state
    activations: list[TriggerActivation] = []
    for event in events:
        resolution = resolve_combat_triggers(updated_state, event)
        updated_state = resolution.state
        activations.extend(resolution.activations)
    return TriggerResolution(updated_state, tuple(activations))


def resolve_actor_trigger_events(
    actors: Sequence[Actor],
    events: Iterable[EffectEvent],
) -> ActorTriggerResolution:
    """Resolve triggers outside combat, for example after a completed rest."""

    updated_actors = tuple(actors)
    activations: list[TriggerActivation] = []
    for event in events:
        if event.actor_id is None:
            continue
        for index, actor in enumerate(updated_actors):
            if str(actor.id) != event.actor_id or actor.is_defeated():
                continue
            updated_actor = actor
            for trigger in actor.triggers:
                if trigger.event_type.value != event.event_type.value:
                    continue
                previous_temp_hp = updated_actor.temp_hp
                if trigger.effect_kind == TriggerEffectKind.GRANT_TEMP_HP:
                    updated_actor = replace(
                        updated_actor,
                        temp_hp=max(updated_actor.temp_hp, trigger.value),
                    )
                else:
                    raise ValueError(f"Unsupported trigger effect: {trigger.effect_kind}.")
                activations.append(
                    TriggerActivation(
                        str(actor.id),
                        trigger,
                        previous_temp_hp,
                        updated_actor.temp_hp,
                    )
                )
            if updated_actor != actor:
                updated_actors = (
                    *updated_actors[:index],
                    updated_actor,
                    *updated_actors[index + 1 :],
                )
            break
    return ActorTriggerResolution(updated_actors, tuple(activations))


def matching_actor_triggers(
    state: CombatState,
    event: EffectEvent,
) -> tuple[tuple[Actor, ActorTrigger], ...]:
    if event.actor_id is None:
        return ()
    return tuple(
        (actor, trigger)
        for actor in state.actors
        if str(actor.id) == event.actor_id and not actor.is_defeated()
        for trigger in actor.triggers
        if trigger.event_type.value == event.event_type.value
    )
