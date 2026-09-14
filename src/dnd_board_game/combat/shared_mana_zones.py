"""Persistent matrix checks, independent of UI, random generators and time."""
from __future__ import annotations
from dataclasses import dataclass, replace
from dnd_board_game.rules import ActiveEffect, EffectDuration, SavingThrowRequest, SavingThrowResult, apply_active_effect
from dnd_board_game.world import Coordinate
from .conditions import CombatCondition, apply_condition
from .session import CombatState
from .spells import resolve_actor_saving_throw
from .physical_mana import effect


def matrix_contains(zone: ActiveEffect, position: Coordinate) -> bool:
    if not zone.source or zone.source.id != 'nimra_sticky_matrix' or zone.anchor_position is None:
        return False
    before = (zone.value // 5 - 1) // 2
    after = zone.value // 5 - before - 1
    return position not in zone.excluded_positions and zone.anchor_position.col-before <= position.col <= zone.anchor_position.col+after and zone.anchor_position.row-before <= position.row <= zone.anchor_position.row+after


@dataclass(frozen=True, slots=True)
class MatrixResolution:
    state: CombatState
    effects: tuple[ActiveEffect, ...]
    saving_throw: SavingThrowResult | None = None


def resolve_matrix_save(state: CombatState, effects: tuple[ActiveEffect, ...], zone: ActiveEffect,
                        actor_id: str, natural_roll: int, natural_roll_2: int | None = None) -> MatrixResolution:
    marker_id = f'shared_matrix_used:{actor_id}:{zone.source_actor_id}'
    if state.shared_mana is None or any(e.id == marker_id for e in effects):
        return MatrixResolution(state, effects)
    target = next(a for a in state.actors if str(a.id) == actor_id)
    caster = next(a for a in state.actors if str(a.id) == zone.source_actor_id)
    save = resolve_actor_saving_throw(target, SavingThrowRequest('dexterity', caster.spell_save_dc, 'Lepka matryca'),
        natural_roll=natural_roll, natural_roll_2=natural_roll_2, condition_states=state.condition_states, combat_actors=state.actors, active_effects=effects)
    used = replace(effect(actor_id, 'shared_matrix_used', 'Matryca: test wykonany', 1, EffectDuration.UNTIL_TURN_START), id=marker_id, expiration_actor_id=actor_id)
    effects = apply_active_effect(effects, used).active_effects
    if not save.success:
        conditions = apply_condition(state.condition_states, target, CombatCondition.PRONE, source_actor_id=str(caster.id),
            source_label='Lepka matryca', duration=EffectDuration.UNTIL_TURN_START, expiration_actor_id=str(caster.id),
            source_spell_id='nimra_sticky_matrix', source_spell_level=0).condition_states
        state = replace(state, condition_states=conditions)
    return MatrixResolution(state, effects, save)
