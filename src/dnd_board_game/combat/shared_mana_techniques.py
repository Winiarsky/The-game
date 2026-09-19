"""Movement and target constraints that belong to a paid weapon technique."""
from __future__ import annotations

from dnd_board_game.inventory.magic_items import effective_ability_modifier
from dataclasses import replace
from dnd_board_game.world import BoardState
from .session import CombatState
from .spells import grid_distance_feet
from dnd_board_game.rules import ActiveEffect, SavingThrowResult


def technique_board(board: BoardState, state: CombatState) -> BoardState:
    if state.shared_mana is None or state.shared_mana.pending_ability != 'unstoppable':
        return board
    return replace(board, terrain_by_tile={p: terrain for p, terrain in board.terrain_by_tile.items() if not terrain.is_difficult})


def validate_technique_target(state: CombatState, source_id: str, target_id: str) -> None:
    mana = state.shared_mana
    if mana is None or mana.pending_ability != source_id or not mana.attack_targets:
        return
    if source_id in {'unstoppable', 'blade_dance', 'anchoring_arrow'} and target_id in mana.attack_targets:
        raise ValueError('Ten atak techniki wymaga innego wroga.')
    if source_id == 'anchoring_arrow':
        first = next(a for a in state.actors if str(a.id) == mana.attack_targets[0])
        target = next(a for a in state.actors if str(a.id) == target_id)
        if grid_distance_feet(first.position, target.position) > 5:
            raise ValueError('Drugi cel Strzały kotwiczącej musi sąsiadować z pierwszym.')


def resolve_unstoppable_knockdown(state: CombatState, target_id: str, roll: int, roll_2: int, effects: tuple[ActiveEffect, ...] = ()) -> tuple[CombatState, SavingThrowResult]:
    from .session import current_actor
    from .conditions import apply_condition, CombatCondition
    from .spells import resolve_actor_saving_throw
    from dnd_board_game.rules import SavingThrowRequest, EffectDuration, ability_modifier
    owner = current_actor(state)
    target = next(a for a in state.actors if str(a.id) == target_id)
    save = resolve_actor_saving_throw(target, SavingThrowRequest('strength', 8 + owner.proficiency_bonus + effective_ability_modifier(owner, 'strength'), 'Niepowstrzymana'), natural_roll=roll, natural_roll_2=roll_2, active_effects=effects, condition_states=state.condition_states, combat_actors=state.actors)
    if not save.success:
        conditions = apply_condition(state.condition_states, target, CombatCondition.PRONE, source_actor_id=str(owner.id), source_label='Niepowstrzymana', duration=EffectDuration.UNTIL_TURN_START, expiration_actor_id=str(owner.id), source_spell_id='unstoppable', source_spell_level=0).condition_states
        state = replace(state, condition_states=conditions)
    return state, save
