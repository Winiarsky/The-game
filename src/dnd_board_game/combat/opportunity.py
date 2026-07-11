from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from dnd_board_game.actors import Actor, ActorId, Faction
from dnd_board_game.world import Coordinate

from .attack_flow import AttackSource
from .scene_interactions import ActiveCombatEffect
from .session import CombatState, reaction_available_for


@dataclass(frozen=True, slots=True)
class OpportunityAttackThreat:
    attacker: Actor
    target: Actor
    origin: Coordinate
    destination: Coordinate


def opportunity_attackers_for_movement(
    state: CombatState,
    mover: Actor,
    origin: Coordinate,
    destination: Coordinate,
    attack_sources_by_actor: Mapping[ActorId, AttackSource],
    active_effects: tuple[ActiveCombatEffect, ...] = (),
) -> tuple[OpportunityAttackThreat, ...]:
    if mover.is_defeated() or _has_disengage_effect(active_effects, mover):
        return ()
    threats: list[OpportunityAttackThreat] = []
    for attacker in state.actors:
        if attacker.id == mover.id or attacker.faction in {mover.faction, Faction.NEUTRAL}:
            continue
        if attacker.is_defeated() or not reaction_available_for(state, attacker):
            continue
        source = attack_sources_by_actor.get(attacker.id)
        if source is None or source.range_feet > 10:
            continue
        reach_tiles = source.range_feet // 5
        if _in_melee_reach(attacker.position, origin, reach_tiles) and not _in_melee_reach(
            attacker.position,
            destination,
            reach_tiles,
        ):
            threats.append(OpportunityAttackThreat(attacker, mover, origin, destination))
    return tuple(sorted(threats, key=lambda threat: (threat.attacker.position.col, threat.attacker.position.row, str(threat.attacker.id))))


def _has_disengage_effect(active_effects: tuple[ActiveCombatEffect, ...], actor: Actor) -> bool:
    return any(effect.actor_id == str(actor.id) and effect.kind == "disengage_until_turn_end" for effect in active_effects)


def _in_melee_reach(attacker_position: Coordinate, target_position: Coordinate, reach_tiles: int) -> bool:
    distance = max(abs(attacker_position.col - target_position.col), abs(attacker_position.row - target_position.row))
    return 0 < distance <= reach_tiles
