"""Deterministic actions introduced by the shared-market hero catalogue."""
from __future__ import annotations

from dnd_board_game.inventory.magic_items import effective_ability_modifier

from dataclasses import dataclass, replace
from typing import Sequence, TYPE_CHECKING

from dnd_board_game.actors import Actor
from dnd_board_game.rules import ActiveEffect, AdditionalEffectExpiration, EffectDuration, EffectEvent, EffectEventType, EffectSource, EffectSourceType, apply_active_effect, expire_active_effects, ability_modifier
from dnd_board_game.rules.shared_mana_catalog import shared_ability
from .action_economy import ActionEconomyCost
from .auras import strongest_aura_members
from .session import CombatState, current_actor, replace_actor, use_action_economy_cost
from .spells import grid_distance_feet

if TYPE_CHECKING:
    from dnd_board_game.rules.shared_mana import SharedMana
    from dnd_board_game.scenarios.loader import ScenarioCombatActionDefinition

SIMPLE_ACTIONS = frozenset({'iron_bastion', 'victory_hymn', 'feint', 'caring_gesture'})
SERIES_ACTIONS = {'reaper': 3, 'unstoppable': 2, 'blade_dance': 2}
AURA_ABILITIES = (('garran_shield_wall', 'garran_shield_wall_source'), ('iron_bastion', 'iron_bastion'),
    ('bless', 'bless_aura_source'), ('divine_care_aura', 'divine_care_aura_source'),
    ('healing_grace_aura', 'healing_grace_aura_source'), ('victory_hymn', 'victory_hymn'))


@dataclass(frozen=True)
class SupportAuraPreview:
    source: Actor
    radius_feet: int
    affected_actor_ids: tuple[str, ...]
    source_kind: str = ''
    square_range: bool = False


def support_aura_preview(actors: Sequence[Actor], effects: tuple[ActiveEffect, ...],
                        ability_id: str, source_id: str, *, active_only: bool = False,
                        action: ScenarioCombatActionDefinition | None = None,
                        mana: SharedMana | None = None) -> SupportAuraPreview | None:
    """Project current or prospective membership without applying an ability."""
    kind = dict(AURA_ABILITIES).get(ability_id)
    if kind is None:
        return None
    owner = next((a for a in actors if str(a.id) == source_id), None)
    if owner is None or owner.is_unconscious() or owner.is_defeated():
        return None
    from .garran_features import synchronize_garran_effects
    shield = ability_id == 'garran_shield_wall'
    source = next((e for e in effects if e.kind == kind and (e.source_actor_id or e.actor_id) == source_id), None) if active_only else None
    if source is None and active_only:
        return None
    if source is None:
        from .shared_mana_sources import boost_action
        if ability_id in {'bless', 'divine_care_aura', 'healing_grace_aura'}:
            if action is None or action.effect_kind != kind:
                return None
            radius = boost_action(action, mana).aura_radius_feet
        else:
            radius = 30 if ability_id == 'victory_hymn' else 5 if shield else 10
        source = ActiveEffect(id='aura_preview', actor_id=source_id, source_actor_id=source_id,
            kind=kind, label='Podgląd aury', object_id=ability_id,
            value=2 if shield else effective_ability_modifier(owner, 'strength') if ability_id == 'iron_bastion' else 1,
            radius_feet=radius)
    if source.radius_feet <= 0:
        return None
    if ability_id == 'victory_hymn':
        from .session import hymn_affects
        members = tuple(str(a.id) for a in actors if hymn_affects(owner, a))
    elif ability_id in {'bless', 'divine_care_aura', 'healing_grace_aura'}:
        from .auras import active_spell_auras
        members = active_spell_auras(actors, (source,))[0].affected_actor_ids
    else:
        synchronize = synchronize_garran_effects if shield else synchronize_bastion
        member_kind = 'garran_shield_wall_member' if shield else 'iron_bastion_member'
        members = tuple(e.actor_id for e in synchronize(actors, (source,)) if e.kind == member_kind)
    return SupportAuraPreview(owner, source.radius_feet, members, kind, ability_id == 'victory_hymn')


def resolve_simple_action(state: CombatState, effects: tuple[ActiveEffect, ...], ability_id: str,
                          *, target_id: str = '', roll: int | None = None) -> tuple[CombatState, tuple[ActiveEffect, ...]]:
    actor = current_actor(state)
    ability = shared_ability(str(actor.id), ability_id)
    if state.shared_mana is None or ability is None or ability_id not in SIMPLE_ACTIONS:
        raise ValueError('Nieznana zdolność wspólnej many.')
    target = actor
    if ability_id in {'feint', 'caring_gesture'}:
        target = next((a for a in state.actors if str(a.id) == target_id), None)
        friendly = ability_id == 'caring_gesture'
        if target is None or target.id == actor.id or target.is_dead() or (target.faction == actor.faction) != friendly or grid_distance_feet(actor.position, target.position) > 5:
            raise ValueError('Wybierz sąsiadującego sojusznika.' if friendly else 'Wybierz sąsiadującego wroga.')
        if ability_id == 'caring_gesture' and (type(roll) is not int or not 1 <= roll <= 4):
            raise ValueError('Opiekuńczy gest wymaga naturalnego k4 (1–4).')
    spent = use_action_economy_cost(state, ActionEconomyCost.ACTION if ability.timing == 'A' else ActionEconomyCost.BONUS_ACTION)
    if not spent.accepted:
        raise ValueError(spent.message)
    updated = spent.state
    extra = ()
    if ability_id == 'victory_hymn':
        effects = expire_active_effects(effects, EffectEvent(EffectEventType.CONCENTRATION_ENDED, actor_id=str(actor.id))).active_effects
        extra = (AdditionalEffectExpiration(EffectDuration.CONCENTRATION, actor_id=str(actor.id)),)
    value = effective_ability_modifier(actor, 'strength') if ability_id == 'iron_bastion' else 1
    kind = ability_id
    if ability_id == 'caring_gesture':
        value = max(0, roll + ability_modifier(actor.ability_scores.wisdom))
        kind = 'temporary_hit_points'
        if target.temp_hp >= value:
            return updated, effects
        effects = tuple(e for e in effects if not (e.actor_id == str(target.id) and e.kind == "temporary_hit_points"))
        updated = replace_actor(updated, replace(target, temp_hp=value))
    effect = ActiveEffect(id=f'{ability_id}:{actor.id}:{target.id}', actor_id=str(target.id),
        kind=kind, label=ability.name, object_id=f'class_feature:{ability_id}', value=value,
        source_actor_id=str(actor.id), target_actor_id=str(target.id),
        source=EffectSource(EffectSourceType.ACTION, ability_id, ability.name),
        duration=EffectDuration.UNTIL_DECK_REFRESH if ability.duration == 'O' else EffectDuration.UNTIL_TURN_START,
        expiration_actor_id=str(actor.id), additional_expirations=extra,
        radius_feet=30 if ability_id == 'victory_hymn' else 10 if ability_id == 'iron_bastion' else 0)
    return updated, apply_active_effect(effects, effect).active_effects


def synchronize_bastion(actors: Sequence[Actor], effects: tuple[ActiveEffect, ...]) -> tuple[ActiveEffect, ...]:
    retained = tuple(e for e in effects if e.kind != 'iron_bastion_member')
    members: list[ActiveEffect] = []
    for source in retained:
        if source.kind != 'iron_bastion':
            continue
        owner = next((a for a in actors if str(a.id) == source.source_actor_id), None)
        if owner is None or owner.is_unconscious() or owner.is_defeated():
            continue
        for target in actors:
            if target.faction == owner.faction and not target.is_dead() and grid_distance_feet(owner.position, target.position) <= 10:
                members.append(replace(source, id=f'iron_bastion_member:{target.id}', actor_id=str(target.id), kind='iron_bastion_member'))
    return (*retained, *strongest_aura_members(members))


def blocks_forced_movement(actor: Actor, effects: Sequence[ActiveEffect]) -> bool:
    return any(e.actor_id == str(actor.id) and e.kind == 'iron_bastion_member' for e in effects)


def state_blocks_forced_movement(state: CombatState, target: Actor) -> bool:
    if state.shared_mana is None:
        return False
    return any(str(a.id) in state.shared_mana.bastion_sources and a.faction == target.faction
               and not a.is_unconscious() and not a.is_defeated()
               and grid_distance_feet(a.position, target.position) <= 10 for a in state.actors)


def resolve_boost_support(state: CombatState, effects: tuple[ActiveEffect, ...], ability_id: str,
                          caster_id: str, target_id: str, roll: int | None = None) -> tuple[CombatState, tuple[ActiveEffect, ...]]:
    caster = next(a for a in state.actors if str(a.id) == caster_id)
    target = next((a for a in state.actors if str(a.id) == target_id), None)
    ward = ability_id == 'garran_shield_wall'
    if target is None or target.faction != caster.faction or target.is_dead() or (ward and target.id == caster.id) or grid_distance_feet(caster.position, target.position) > (5 if ward else 15):
        raise ValueError('Wybierz sojusznika w zasięgu zdolności.')
    if ward:
        if target.temp_hp >= 5:
            return state, effects
        effects = tuple(e for e in effects if not (e.actor_id == str(target.id) and e.kind == "temporary_hit_points"))
        state = replace_actor(state, replace(target, temp_hp=5))
        marker = ActiveEffect(id=f'shared_ward:{caster.id}:{target.id}', actor_id=str(target.id), kind='temporary_hit_points', label='Osłona tarczą: 5 tymczasowych PW',
            object_id='class_feature:garran_shield_wall', value=5, source_actor_id=caster_id, duration=EffectDuration.UNTIL_TURN_START, expiration_actor_id=caster_id)
        return state, apply_active_effect(effects, marker).active_effects
    if ability_id != 'garran_rally' or type(roll) is not int or not 1 <= roll <= 6:
        raise ValueError('Podaj naturalny wynik k6 leczenia Mowy dowódcy.')
    from .healing import HealingSource, HealingSourceType, apply_healing_result
    source = HealingSource('garran_rally', 'Mowa dowódcy: leczenie', HealingSourceType.CUSTOM, 15)
    applied = apply_healing_result(target, source, roll, condition_states=state.condition_states)
    return replace_actor(state, applied.actor_after), effects
