"""Apply declared boosts to combat sources without mutating authored content."""
from __future__ import annotations

from dataclasses import replace
from typing import Mapping, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from dnd_board_game.scenarios.loader import ScenarioCombatActionDefinition

from dnd_board_game.actors import Actor
from dnd_board_game.rules import DiceExpression, ActiveEffect
from dnd_board_game.rules.shared_mana import SharedMana
from .attack_flow import AttackSource
from .damage import DamageComponentSpec
from .healing import HealingSource


def lightning_chain(caster: Actor, first: Actor, actors: Sequence[Actor]) -> tuple[str, ...]:
    """Two automatic jumps; an already struck actor cannot be selected again."""
    from .nimra_features import select_lightning_jump_target
    used = {str(first.id)}
    current = first
    targets = []
    for _ in range(2):
        jump = select_lightning_jump_target(caster, current, tuple(a for a in actors if str(a.id) not in used))
        if jump is None:
            break
        used.add(jump.target_id)
        targets.append(jump.target_id)
        current = next(a for a in actors if str(a.id) == jump.target_id)
    return tuple(targets)


def boost_counts(mana: SharedMana | None, source_id: str) -> Mapping[str, int]:
    return dict(mana.pending_boosts) if mana and mana.pending_ability == source_id else {}


def boost_attack(source: AttackSource, mana: SharedMana | None) -> AttackSource:
    if mana is None:
        return source
    boosts = boost_counts(mana, source.id)
    count = boosts.get('damage', 0)
    if source.id == 'blade_mistress' and not any(c.id == 'rune_blade_mistress' for c in source.damage_components):
        count += 1
    if count and source.damage_components:
        component_id = 'mana_double_shot' if source.id == 'double_shot' else 'shared_boost'
        components = tuple(c for c in source.damage_components if c.id != component_id)
        extra = DamageComponentSpec(component_id, components[0].damage_type,
            dice=DiceExpression(count, 12 if source.id == 'powerful_strike' else 6), label='Podbicie' if source.id != 'blade_mistress' else 'Mistrzyni ostrzy i podbicie')
        source = replace(source, damage_components=(*components, extra), damage_hint=' + '.join(c.hint() for c in (*components, extra)))
    if source.id == 'nimra_force_wave':
        source = replace(source, failed_save_push_feet=5 * (1 + boosts.get('push', 0)))
    if source.id == 'entangling_shot' and source.area:
        side = 15 + 5 * boosts.get('area', 0)
        source = replace(source, area=replace(source.area, length_feet=side, width_feet=side))
    return source


def boost_healing(actor: Actor, source: HealingSource, mana: SharedMana | None) -> HealingSource:
    if mana is None or str(actor.id) != 'dagna' or source.id != 'healing_word':
        return source
    from .action_economy import ActionEconomyCost
    count = boost_counts(mana, source.id).get('heal', 0)
    hint = '1k4' + (f' + {count}k6' if count else '') + ' + 7'
    return replace(source, healing_hint=hint, healing_modifier=7, healing_dice_count=1,
                   action_cost=ActionEconomyCost.ACTION, resource_pool_id=None,
                   upcast_healing_dice_per_level=0, healing_modifier_per_cast_level=0)


def additional_weapon_sources(actor: Actor, sources: tuple[AttackSource, ...], effects: tuple[ActiveEffect, ...], mana: SharedMana | None) -> tuple[AttackSource, ...]:
    """Reuse equipped weapons and the normal attack resolver for new techniques."""
    if mana is None:
        return sources
    from .attack_flow import AttackSourceType, AttackKind
    from dnd_board_game.rules.shared_mana_catalog import shared_ability
    available = {'brakka': ('reaper', 'unstoppable'), 'mira': ('shadow_verdict', 'blade_dance'), 'garran': ('counterattack_command',) if mana.command_step == 1 else ()}.get(str(actor.id), ())
    if str(actor.id) == 'brakka' and not any(e.kind == 'rage' and e.actor_id == str(actor.id) for e in effects):
        return sources
    if str(actor.id) == 'erynd':
        bow = next((s for s in sources if s.source_type == AttackSourceType.WEAPON and s.proficiency_id == 'longbow'), None)
        if bow is not None:
            from .spells import SpellArea, SpellAreaShape, SpellAreaTargetMode
            extra = DamageComponentSpec('arrow_rain_extra', bow.damage_components[0].damage_type, dice=DiceExpression(1, 6), label='Deszcz strzał')
            area = SpellArea(SpellAreaShape.CUBE, length_feet=15, width_feet=15, target_mode=SpellAreaTargetMode.ENEMIES)
            volley = replace(bow, id='arrow_rain', name='Deszcz strzał', area=area, damage_components=(*bow.damage_components, extra), damage_hint=bow.damage_hint + ' + 1k6')
            sources = (*sources, volley)
    base = next((s for s in sources if s.source_type == AttackSourceType.WEAPON and s.attack_kind == AttackKind.MELEE and shared_ability(str(actor.id), s.id) is None), None)
    if mana.command_step == 2 and str(actor.id) == mana.command_ally:
        available = ("counterattack_command",)
    if 'counterattack_command' in available:
        base = next((s for s in sources if s.source_type == AttackSourceType.WEAPON
            and shared_ability(str(actor.id), s.id) is None
            and (s.source_item_id is None or any(item.equipped and item.available
                and (item.id == s.source_item_id or item.source_ref == s.source_item_id) for item in actor.inventory))), None)
    if base is None:
        return sources
    extra = []
    for key in available:
        ability = shared_ability("garran" if key == "counterattack_command" else str(actor.id), key)
        source = replace(base, id=key, name=f'{ability.name} · {base.name}' if key == 'counterattack_command' else ability.name, resource_pool_id=None, tabletop_riders=(ability.description,))
        if key == 'shadow_verdict' and source.damage_components:
            component = DamageComponentSpec('shadow_verdict', source.damage_components[0].damage_type, dice=DiceExpression(5, 6), label='Wyrok z cienia')
            source = replace(source, damage_components=(*source.damage_components, component), damage_hint=source.damage_hint + ' + 5k6')
        extra.append(source)
    return (*sources, *extra)


def boost_action(action: ScenarioCombatActionDefinition, mana: SharedMana | None) -> ScenarioCombatActionDefinition:
    if mana is None:
        return action
    boosts = boost_counts(mana, action.id)
    if action.id == 'nimra_web' and action.area is not None:
        side = 10 + 5 * boosts.get('area', 0)
        return replace(action, area=replace(action.area, length_feet=side, width_feet=side))
    if action.id == 'divine_care_aura':
        return replace(action, aura_radius_feet=10 if boosts.get('radius', 0) else 5, value=2)
    return action
