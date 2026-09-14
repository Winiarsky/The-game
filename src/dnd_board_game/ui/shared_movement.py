"""Apply terrain effects to additional and forced movement, without opportunity attacks."""
from __future__ import annotations
from typing import TYPE_CHECKING
from dnd_board_game.world import Coordinate, PathResult, bresenham_line, find_path
from dnd_board_game.combat.magic_movement import legal_teleport_positions
from dnd_board_game.rules import EffectEvent, EffectEventType

if TYPE_CHECKING:
    from .exploration_app import ExplorationUiSession


def nimble_positions(session: ExplorationUiSession) -> tuple[Coordinate, ...]:
    from dnd_board_game.combat.session import current_actor
    state = session.combat_state
    actor = current_actor(state)
    encounter = session._active_encounter()
    candidates = legal_teleport_positions(encounter.board, state, actor, distance_feet=5, scene_objects=encounter.scene_objects)
    return tuple(p for p in candidates if (path := find_path(encounter.board, actor, state.actors, p)).valid and path.cost_feet <= 5)


def apply_extra_movement(session: ExplorationUiSession, actor_id: str, origin: Coordinate, destination: Coordinate) -> None:
    if origin == destination:
        return
    positions = bresenham_line(origin, destination)
    path = PathResult(origin, destination, positions, 5*(len(positions)-1), True)
    session._apply_spike_growth_movement_damage(actor_id, path)
    session._apply_moonbeam_entry_damage(actor_id, path)
    session._apply_web_entry_save(actor_id, path)
    session._apply_zone_of_truth_entry_save(actor_id, path)
    session._apply_combat_trigger_events((EffectEvent(EffectEventType.ACTOR_MOVED, actor_id=actor_id, position=destination),))
