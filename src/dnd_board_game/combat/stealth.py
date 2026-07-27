from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Mapping, Sequence

from dnd_board_game.actors import Actor, Faction, passive_skill_score
from dnd_board_game.world import BoardState, bresenham_line, line_of_sight_clear

if TYPE_CHECKING:
    from .scene import SceneObject


@dataclass(frozen=True, slots=True)
class HiddenState:
    actor_id: str
    stealth_total: int
    hidden_from_actor_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HideEligibility:
    allowed: bool
    blocking_observer_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class HideResolution:
    hidden_states: tuple[HiddenState, ...]
    hidden_state: HiddenState | None
    detected_by_actor_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SearchResolution:
    hidden_states: tuple[HiddenState, ...]
    found_actor_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HiddenMovementResolution:
    hidden_states: tuple[HiddenState, ...]
    revealed_to_actor_ids: tuple[str, ...]


def hide_eligibility(
    board: BoardState,
    actor: Actor,
    actors: Sequence[Actor],
    scene_objects: Sequence[SceneObject] = (),
) -> HideEligibility:
    blockers = tuple(
        str(observer.id)
        for observer in actors
        if _hostile(actor, observer)
        and not observer.is_defeated()
        and _sees_clearly(board, observer, actor, scene_objects)
    )
    return HideEligibility(not blockers, blockers)


def resolve_hide(
    hidden_states: Sequence[HiddenState],
    actor: Actor,
    actors: Sequence[Actor],
    stealth_total: int,
    *,
    passive_perception_adjustments: Mapping[str, int] | None = None,
    automatically_hidden_from_actor_ids: Sequence[str] = (),
) -> HideResolution:
    opponents = tuple(
        observer
        for observer in actors
        if _hostile(actor, observer) and not observer.is_defeated()
    )
    adjustments = passive_perception_adjustments or {}
    automatic = set(automatically_hidden_from_actor_ids)
    hidden_from = tuple(
        str(observer.id)
        for observer in opponents
        if (
            str(observer.id) in automatic
            or stealth_total
            > (
                passive_skill_score(observer, "perception")
                + adjustments.get(str(observer.id), 0)
            )
        )
    )
    detected_by = tuple(
        str(observer.id) for observer in opponents if str(observer.id) not in hidden_from
    )
    remaining = tuple(state for state in hidden_states if state.actor_id != str(actor.id))
    state = HiddenState(str(actor.id), stealth_total, hidden_from) if hidden_from else None
    return HideResolution(
        (*remaining, state) if state is not None else remaining,
        state,
        detected_by,
    )


def resolve_search(
    hidden_states: Sequence[HiddenState],
    searcher: Actor,
    perception_total: int,
) -> SearchResolution:
    found: list[str] = []
    updated: list[HiddenState] = []
    searcher_id = str(searcher.id)
    for state in hidden_states:
        if searcher_id not in state.hidden_from_actor_ids or perception_total < state.stealth_total:
            updated.append(state)
            continue
        found.append(state.actor_id)
        remaining = tuple(actor_id for actor_id in state.hidden_from_actor_ids if actor_id != searcher_id)
        if remaining:
            updated.append(HiddenState(state.actor_id, state.stealth_total, remaining))
    return SearchResolution(tuple(updated), tuple(found))


def is_hidden_from(hidden_states: Sequence[HiddenState], actor_id: str, observer_id: str) -> bool:
    return any(
        state.actor_id == actor_id and observer_id in state.hidden_from_actor_ids
        for state in hidden_states
    )


def reveal_actor(hidden_states: Sequence[HiddenState], actor_id: str) -> tuple[HiddenState, ...]:
    return tuple(state for state in hidden_states if state.actor_id != actor_id)


def hidden_state_for(hidden_states: Sequence[HiddenState], actor_id: str) -> HiddenState | None:
    return next((state for state in hidden_states if state.actor_id == actor_id), None)


def refresh_hidden_after_movement(
    board: BoardState,
    moved_actor: Actor,
    actors: Sequence[Actor],
    hidden_states: Sequence[HiddenState],
    scene_objects: Sequence[SceneObject] = (),
) -> HiddenMovementResolution:
    current = hidden_state_for(hidden_states, str(moved_actor.id))
    if current is None:
        return HiddenMovementResolution(tuple(hidden_states), ())
    observers = {str(actor.id): actor for actor in actors}
    revealed = tuple(
        observer_id
        for observer_id in current.hidden_from_actor_ids
        if observer_id in observers
        and _sees_clearly(board, observers[observer_id], moved_actor, scene_objects)
    )
    remaining_observers = tuple(
        observer_id
        for observer_id in current.hidden_from_actor_ids
        if observer_id not in revealed
    )
    remaining_states = tuple(
        state for state in hidden_states if state.actor_id != str(moved_actor.id)
    )
    if remaining_observers:
        remaining_states = (
            *remaining_states,
            HiddenState(current.actor_id, current.stealth_total, remaining_observers),
        )
    return HiddenMovementResolution(remaining_states, revealed)


def _sees_clearly(
    board: BoardState,
    observer: Actor,
    actor: Actor,
    scene_objects: Sequence[SceneObject],
) -> bool:
    if not line_of_sight_clear(board, observer.position, actor.position):
        return False
    intermediate = frozenset(bresenham_line(observer.position, actor.position)[1:-1])
    strongest_cover = max(
        (
            scene_object.projectile_cover_bonus
            for scene_object in scene_objects
            if intermediate.intersection(scene_object.positions)
        ),
        default=0,
    )
    # 2014 leaves the exact circumstances to the DM. For deterministic board play,
    # three-quarters cover counts as not being seen clearly; half cover does not.
    return strongest_cover < 5


def _hostile(first: Actor, second: Actor) -> bool:
    return {first.faction, second.faction} == {Faction.ALLY, Faction.ENEMY}
