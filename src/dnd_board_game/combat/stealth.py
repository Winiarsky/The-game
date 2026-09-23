from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Mapping, Sequence

from dnd_board_game.actors import (
    Actor,
    Faction,
    actor_has_feature,
    creature_size_rank,
    passive_skill_score,
)
from dnd_board_game.world import BoardState, bresenham_line, line_of_sight_clear
from dnd_board_game.rules import ActiveEffect
from .smoke import smoke_contains

if TYPE_CHECKING:
    from .scene import SceneObject


@dataclass(frozen=True, slots=True)
class HiddenState:
    actor_id: str
    stealth_total: int
    hidden_from_actor_ids: tuple[str, ...]
    observer_perception_totals: tuple[tuple[str, int], ...] = ()


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
    active_effects: Sequence[ActiveEffect] = (),
) -> HideEligibility:
    if smoke_contains(actor.position, active_effects):
        return HideEligibility(True)
    if actor_has_feature(actor, "mira_shadow_stealth"):
        blockers = tuple(
            str(observer.id)
            for observer in actors
            if _hostile(actor, observer)
            and not observer.is_defeated()
            and _adjacent(actor, observer)
        )
        return HideEligibility(not blockers, blockers)
    blockers = tuple(
        str(observer.id)
        for observer in actors
        if _hostile(actor, observer)
        and not observer.is_defeated()
        and _sees_clearly(board, observer, actor, actors, scene_objects)
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
    observer_perception_totals: Mapping[str, int] | None = None,
) -> HideResolution:
    opponents = tuple(
        observer
        for observer in actors
        if _hostile(actor, observer) and not observer.is_defeated()
    )
    adjustments = passive_perception_adjustments or {}
    perception_totals = observer_perception_totals or {}
    automatic = set(automatically_hidden_from_actor_ids)
    hidden_from = tuple(
        str(observer.id)
        for observer in opponents
        if (
            str(observer.id) in automatic
            or stealth_total
            > (
                perception_totals.get(
                    str(observer.id),
                    passive_skill_score(observer, "perception")
                    + (2 if actor_has_feature(observer, "scouts_vigilance") else 0)
                    + adjustments.get(str(observer.id), 0),
                )
            )
        )
    )
    detected_by = tuple(
        str(observer.id) for observer in opponents if str(observer.id) not in hidden_from
    )
    remaining = tuple(state for state in hidden_states if state.actor_id != str(actor.id))
    recorded_totals = tuple(
        (str(observer.id), perception_totals[str(observer.id)])
        for observer in opponents
        if str(observer.id) in perception_totals
    )
    state = (
        HiddenState(str(actor.id), stealth_total, hidden_from, recorded_totals)
        if hidden_from
        else None
    )
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
            updated.append(
                HiddenState(
                    state.actor_id,
                    state.stealth_total,
                    remaining,
                    state.observer_perception_totals,
                )
            )
    return SearchResolution(tuple(updated), tuple(found))


def is_hidden_from(hidden_states: Sequence[HiddenState], actor_id: str, observer_id: str) -> bool:
    return any(
        state.actor_id == actor_id and observer_id in state.hidden_from_actor_ids
        for state in hidden_states
    )


def reveal_actor(hidden_states: Sequence[HiddenState], actor_id: str) -> tuple[HiddenState, ...]:
    return tuple(state for state in hidden_states if state.actor_id != actor_id)


def reveal_all_to_observer(
    hidden_states: Sequence[HiddenState],
    observer_id: str,
) -> tuple[HiddenState, ...]:
    """Remove one observer from every per-observer hidden relationship."""

    updated: list[HiddenState] = []
    for state in hidden_states:
        remaining = tuple(
            candidate
            for candidate in state.hidden_from_actor_ids
            if candidate != observer_id
        )
        if remaining:
            updated.append(
                HiddenState(
                    state.actor_id,
                    state.stealth_total,
                    remaining,
                    state.observer_perception_totals,
                )
            )
    return tuple(updated)


def hidden_state_for(hidden_states: Sequence[HiddenState], actor_id: str) -> HiddenState | None:
    return next((state for state in hidden_states if state.actor_id == actor_id), None)


def reveal_to_observer(
    hidden_states: Sequence[HiddenState],
    actor_id: str,
    observer_id: str,
) -> tuple[HiddenState, ...]:
    """Reveal one hidden actor to one observer without ending stealth mode."""

    updated: list[HiddenState] = []
    for state in hidden_states:
        if state.actor_id != actor_id:
            updated.append(state)
            continue
        remaining = tuple(
            candidate
            for candidate in state.hidden_from_actor_ids
            if candidate != observer_id
        )
        if remaining:
            updated.append(
                HiddenState(
                    state.actor_id,
                    state.stealth_total,
                    remaining,
                    state.observer_perception_totals,
                )
            )
    return tuple(updated)


def actors_visible_for_pathfinding(
    actors: Sequence[Actor],
    hidden_states: Sequence[HiddenState],
    observer_id: str,
) -> tuple[Actor, ...]:
    """Occupied tiles known to an observer; hidden actors are not AI obstacles."""

    return tuple(
        actor
        for actor in actors
        if str(actor.id) == observer_id
        or not is_hidden_from(hidden_states, str(actor.id), observer_id)
    )


def refresh_hidden_after_movement(
    board: BoardState,
    moved_actor: Actor,
    actors: Sequence[Actor],
    hidden_states: Sequence[HiddenState],
    scene_objects: Sequence[SceneObject] = (),
    active_effects: Sequence[ActiveEffect] = (),
) -> HiddenMovementResolution:
    current = hidden_state_for(hidden_states, str(moved_actor.id))
    if current is None:
        return HiddenMovementResolution(tuple(hidden_states), ())
    if actor_has_feature(moved_actor, "mira_shadow_stealth") or smoke_contains(moved_actor.position, active_effects):
        # Mira's roll establishes per-observer knowledge. Ordinary movement does
        # not leak her location; attacks, Search and path collisions reveal her.
        return HiddenMovementResolution(tuple(hidden_states), ())
    observers = {str(actor.id): actor for actor in actors}
    revealed = tuple(
        observer_id
        for observer_id in current.hidden_from_actor_ids
        if observer_id in observers
        and _sees_clearly(
            board,
            observers[observer_id],
            moved_actor,
            tuple(observers.values()),
            scene_objects,
        )
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
            HiddenState(
                current.actor_id,
                current.stealth_total,
                remaining_observers,
                current.observer_perception_totals,
            ),
        )
    return HiddenMovementResolution(remaining_states, revealed)


def _adjacent(first: Actor, second: Actor) -> bool:
    return max(
        abs(first.position.col - second.position.col),
        abs(first.position.row - second.position.row),
    ) <= 1


def _sees_clearly(
    board: BoardState,
    observer: Actor,
    actor: Actor,
    actors: Sequence[Actor],
    scene_objects: Sequence[SceneObject],
) -> bool:
    if not line_of_sight_clear(board, observer.position, actor.position):
        return False
    intermediate = frozenset(bresenham_line(observer.position, actor.position)[1:-1])
    if actor_has_feature(actor, "naturally_stealthy") and any(
        other.id not in {observer.id, actor.id}
        and not other.is_defeated()
        and other.position in intermediate
        and creature_size_rank(other.size) > creature_size_rank(actor.size)
        for other in actors
    ):
        return False
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
