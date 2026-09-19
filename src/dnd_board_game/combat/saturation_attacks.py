"""Persistent color damage on direct and reaction attacks, including saved rolls."""
from __future__ import annotations
from dataclasses import replace
from dnd_board_game.actors import Actor
from dnd_board_game.rules import ActiveEffect, EffectDuration
from dnd_board_game.rules.charge_rolls import uses_charge
from .attack_flow import AttackSource
from .session import CombatState


def saturation_damage_source(state: CombatState, attacker: Actor, target: Actor,
                             source: AttackSource) -> AttackSource:
    if not uses_charge(attacker):
        return source
    from .class_features import plan_sneak_attack
    from .erynd_features import first_blood_damage
    if not any(c.id == 'sneak_attack' for c in source.damage_components):
        source = plan_sneak_attack(state=state, active_effects=(), attacker=attacker,
            target=target, source=source, roll_mode=source.attack_roll_request.mode).source
    if source.damage_components and not any(c.id == 'first_blood' for c in source.damage_components):
        bonus = first_blood_damage(attacker, target, source.damage_components[0].damage_type)
        if bonus is not None:
            source = replace(source, damage_components=(*source.damage_components, bonus))
    return source


def snapshot_reaction_bonuses(effects: tuple[ActiveEffect, ...], attacker: Actor,
                             target: Actor, source: AttackSource) -> tuple[ActiveEffect, ...]:
    """Keep the hit's dice after attacking reveals a hidden character."""
    if not uses_charge(attacker):
        return effects
    kept = tuple(e for e in effects if not (e.actor_id == str(attacker.id) and e.kind == 'saturation_reaction_damage'))
    return kept + tuple(ActiveEffect(
        id=f'saturation-reaction:{attacker.id}:{c.id}', actor_id=str(attacker.id),
        target_actor_id=str(target.id), kind='saturation_reaction_damage',
        object_id=c.id, label=f'Premia rozstrzyganego trafienia: {c.label}', value=c.dice.count,
        duration=EffectDuration.UNTIL_TURN_START, expiration_actor_id=str(attacker.id))
        for c in source.damage_components if c.id in {'sneak_attack','first_blood'} and c.dice)


def reaction_damage_source(source: AttackSource, attacker: Actor, target: Actor,
                           effects: tuple[ActiveEffect, ...]) -> AttackSource:
    from .damage import DamageComponentSpec
    from dnd_board_game.rules import DiceExpression
    if not uses_charge(attacker) or not source.damage_components:
        return source
    bonuses = tuple(DamageComponentSpec(e.object_id, source.damage_components[0].damage_type,
        DiceExpression(e.value, 6), label='Atak z ukrycia / flanki' if e.object_id=='sneak_attack' else 'Pierwsza krew')
        for e in effects if e.kind == 'saturation_reaction_damage' and e.actor_id == str(attacker.id)
        and e.target_actor_id == str(target.id) and not any(c.id==e.object_id for c in source.damage_components))
    return replace(source, damage_components=(*source.damage_components,*bonuses))
