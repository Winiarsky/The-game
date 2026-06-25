from __future__ import annotations

import random
from dataclasses import dataclass

from dnd_board_game.actors import Actor
from dnd_board_game.rules import D20RollInput, D20RollResult, resolve_d20_roll
from dnd_board_game.world import BoardState

from .action_economy import ActionUse
from .attack_flow import AttackDeclaration, AttackResolution, AttackSource, legal_melee_targets, resolve_attack
from .damage import DamageComponentInput, DamageResult, DamageType, apply_damage, resolve_damage
from .session import CombatState, replace_actor, use_turn_action
from .targets import CombatTarget


@dataclass(frozen=True, slots=True)
class EnemyAutoAttackResult:
    state: CombatState
    enemy: Actor
    target: CombatTarget | None
    message: str
    attack_roll: D20RollResult | None = None
    attack_resolution: AttackResolution | None = None
    damage: DamageResult | None = None
    updated_target: Actor | None = None
    action_used: bool = False


def resolve_enemy_auto_attack(
    board: BoardState,
    state: CombatState,
    enemy: Actor,
    source: AttackSource,
    rng: random.Random,
) -> EnemyAutoAttackResult:
    action_result = use_turn_action(state)
    if not action_result.accepted:
        return EnemyAutoAttackResult(action_result.state, enemy, None, action_result.message, action_used=False)

    targets = legal_melee_targets(board, enemy, action_result.state.actors)
    if not targets:
        return EnemyAutoAttackResult(
            action_result.state,
            enemy,
            None,
            f"{enemy.name} nie ma legalnego celu ataku i kończy akcję.",
            action_used=True,
        )

    target = targets[0]
    attack_roll = resolve_d20_roll(D20RollInput(source.attack_roll_request, rng.randint(1, 20)))
    declaration = AttackDeclaration(attacker=enemy, target=target, source=source)
    resolution = resolve_attack(declaration, attack_roll, ActionUse.ACTION_AVAILABLE)
    updated_state = action_result.state
    damage: DamageResult | None = None
    updated_target: Actor | None = None

    if resolution.hit:
        damage_amount = rng.randint(1, 6) + 2
        damage = resolve_damage((DamageComponentInput(damage_amount, DamageType.SLASHING, source.name),))
        target_actor = _actor_for_target(action_result.state, target)
        updated_target = apply_damage(target_actor, damage)
        updated_state = replace_actor(action_result.state, updated_target)
        message = (
            f"{enemy.name} trafia {target.name}. Wynik ataku: {attack_roll.total}. "
            f"Obrażenia: {damage.total_applied} slashing."
        )
    else:
        message = f"{enemy.name} pudłuje przeciwko {target.name}. Wynik ataku: {attack_roll.total}."

    return EnemyAutoAttackResult(
        state=updated_state,
        enemy=enemy,
        target=target,
        message=message,
        attack_roll=attack_roll,
        attack_resolution=resolution,
        damage=damage,
        updated_target=updated_target,
        action_used=True,
    )


def _actor_for_target(state: CombatState, target: CombatTarget) -> Actor:
    for actor in state.actors:
        if str(actor.id) == target.id:
            return actor
    raise ValueError(f"Unknown target actor: {target.id}.")
