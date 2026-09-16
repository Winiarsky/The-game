"""Adapt authored combat content for the explicitly selected physical-mana rules."""
from dataclasses import replace
from typing import TypeVar

from dnd_board_game.actors import Actor
from dnd_board_game.actors.resources import uses_physical_mana, uses_shared_mana
from dnd_board_game.rules import DiceExpression, RollModifier, RollModifierType, EffectDuration
from dnd_board_game.rules.physical_mana import mana_ability
from .action_economy import ActionEconomyCost
from .attack_flow import AttackSource
from .damage import DamageComponentSpec

T = TypeVar('T')


def _charge_instructions(actor: Actor, ability_id: str) -> str | None:
    if not any(f.feature_id == "pooled_mana_v01" for f in actor.features):
        return None
    from dnd_board_game.scenarios.pooled_mana_catalog import load_catalog, requirement_text, ability_description
    if ability_id not in load_catalog()["abilities"]:
        return None
    return requirement_text(ability_id, str(actor.id)) + " " + ability_description(str(actor.id), ability_id)


def adapt_action(actor: Actor, action: T) -> T:
    if not uses_physical_mana(actor):
        return action
    ability = mana_ability(str(actor.id), action.id)
    if ability is None:
        return action
    updates = {'action_cost': {'A': ActionEconomyCost.ACTION, 'D': ActionEconomyCost.BONUS_ACTION,
                              'R': ActionEconomyCost.REACTION, 'MOD': ActionEconomyCost.FREE}[ability.timing],
               'instructions': f'Wydaj: {ability.cost_label}. {ability.description}',
               'resource_pool_id': None}
    instructions = _charge_instructions(actor, action.id)
    if instructions is not None:
        updates['instructions'] = instructions
    if action.id in {'bless', 'divine_care_aura', 'healing_grace_aura', 'nimra_sticky_matrix',
                     'nimra_fog', 'nimra_web', 'nimra_stasis', 'spike_growth', 'hunters_mark', 'spiritual_weapon'}:
        updates['duration_rounds'] = 3
    if action.id == 'healing_grace_aura':
        updates['bonus_modifier_ability'] = None
    if action.id == 'nimra_sleep':
        updates['duration'] = 'next_turn_end'
    if action.id == 'shield':
        updates['value'] = 3
    if uses_shared_mana(actor):
        updates['duration_rounds'] = 0
        if action.id == 'nimra_web' and action.area is not None:
            updates['area'] = replace(action.area, length_feet=10, width_feet=10)
        if action.id == 'nimra_stasis':
            from .conditions import CombatCondition
            updates.update(condition=CombatCondition.STASIS, save_timing=None)
        if action.id == 'spiritual_weapon' and action.summon is not None:
            summon = action.summon
            updates['summon'] = replace(summon, duration_rounds=0) if hasattr(summon, 'duration_rounds') else summon
    return replace(action, **updates)


def adapt_attack(actor: Actor, source: AttackSource) -> AttackSource:
    if not uses_physical_mana(actor):
        return source
    ability = mana_ability(str(actor.id), source.id)
    if ability is None:
        return source
    source = replace(source, resource_pool_id=None, tabletop_riders=(_charge_instructions(actor, source.id) or ability.description,),
                     action_cost={'A': ActionEconomyCost.ACTION, 'D': ActionEconomyCost.BONUS_ACTION,
                                  'R': ActionEconomyCost.REACTION, 'MOD': ActionEconomyCost.FREE}[ability.timing])
    if source.id == 'anchoring_arrow':
        source = replace(source, on_hit_effect_duration=EffectDuration.UNTIL_TURN_START,
                         on_hit_effect_remaining_rounds=None)
    if source.id == 'double_shot' and not uses_shared_mana(actor):
        request = source.attack_roll_request
        if not any(m.stacking_key == 'mana_double_shot' for m in request.modifiers):
            source = replace(source, attack_roll_request=replace(request, modifiers=(*request.modifiers,
                RollModifier('Podwójny strzał', 2, RollModifierType.FEATURE, stacking_key='mana_double_shot'))))
    if uses_shared_mana(actor):
        from dnd_board_game.core.damage_types import DamageType
        formulas = {'guiding_bolt': (2, 6, 'radiant'), 'nimra_frost_pulse': (1, 8, 'cold'),
                    'nimra_mind_spike': (1, 6, 'psychic'), 'nimra_mind_break': (1, 6, 'psychic'),
                    'nimra_lightning_path': (4, 6, 'lightning'), 'shatter': (4, 8, 'thunder'),
                    'deafening_roar': (1, 6, 'thunder')}
        if source.id in formulas:
            count, sides, damage_type = formulas[source.id]
            component = DamageComponentSpec(source.id, DamageType(damage_type), dice=DiceExpression(count, sides), label=source.name)
            components = (component, *(c for c in source.damage_components if c.id == "shared_boost"))
            source = replace(source, damage_components=components, damage_hint=" + ".join(c.hint() for c in components), damage_die_sides=sides, damage_modifier=0)
        if source.id == 'sacred_flame' and source.area is not None:
            from .spells import SpellAreaTargetMode
            source = replace(source, area=replace(source.area, target_mode=SpellAreaTargetMode.ALL_CREATURES))
        if source.id == 'guiding_bolt':
            source = replace(source, range_feet=75)
        if source.id == 'nimra_mind_break':
            source = replace(source, area=None)
    return source


def powerful_strike_source(actor: Actor, source: AttackSource) -> AttackSource:
    component = DamageComponentSpec('mana_powerful_strike', source.damage_components[0].damage_type,
                                    dice=DiceExpression(1, 12), label='Potężne uderzenie')
    return adapt_attack(actor, replace(source, id='powerful_strike', name='Potężne uderzenie',
                        damage_components=(*source.damage_components, component),
                        damage_hint=f'{source.damage_hint} + 1k12'))
