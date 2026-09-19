"""Color-unlocked hero features, derived from charge rather than permanent grants."""
from __future__ import annotations

from dataclasses import replace
from typing import Mapping, Sequence

from .models import Actor
from .features import FeatureGrant, FeatureSourceKind
from dnd_board_game.rules.charge_rolls import uses_charge
from dnd_board_game.rules import ability_modifier
from dnd_board_game.core.damage_types import DamageType

SOURCE = 'mana_saturation:color'
MIGRATION = 'mana_passives_v1'
FEATURE_LABELS = {
    'iron_line': 'Żelazna linia',
    'fighting_style_defense': 'Styl walki: Obrona',
    'improved_critical': 'Ulepszony krytyk',
    'unarmored_defense_constitution': 'Obrona bez pancerza',
    'savage_attacks': 'Dzikie ataki',
    'relentless_endurance': 'Nieustępliwość',
    'mira_shadow_killer': 'Atak z cienia',
    'mana_shadow_strike': 'Atak z cienia',
    'mana_flanking_strike': 'Atak z flanki',
    'mira_ranged_evasion': 'Ruchomy cel',
    'lucky': 'Szczęście',
    'mana_nimble_hands': 'Zwinne dłonie',
    'field_medic_step': 'Krok ratowniczki',
    'dwarven_resilience': 'Odporność na truciznę',
    'fey_ancestry': 'Nieugięty umysł',
    'gnome_cunning': 'Magiczna przezorność',
    'fighting_style_archery': 'Łucznictwo',
    'first_blood': 'Pierwsza krew',
    'scouts_vigilance': 'Czujność zwiadowcy',
}
RETIRED = frozenset({*FEATURE_LABELS, 'darkvision', 'dwarven_speed',
    'dwarven_toughness', 'disciple_of_life', 'social_grace_bargaining',
    'improvisation', 'arcane_recovery', 'erynd_expertise', 'expertise',
    'mana_behind_shield', 'mana_momentum', 'mana_reservoir', 'mana_alchemy',
    'mana_read_currents', 'crossbowman', 'jack_of_all_trades', 'skill_versatility',
    'halfling_nimbleness', 'brave', 'stonecunning', 'artificers_lore',
    'trance', 'human_versatility', 'wanderer', 'rustic_hospitality',
    'elf_weapon_training'})


def normalize_mana_passives(actor: Actor) -> Actor:
    """Remove permanent/expired passives; migrate baked racial stats exactly once.

    Equipment, spent resource uses, actions, class access and the flaw stay intact.
    Mira's hide and Nimra's spell catalogue are action permissions, not bonuses.
    """
    if not uses_charge(actor):
        return actor
    ids = {f.feature_id for f in actor.features}
    maximum = actor.max_hp
    if MIGRATION not in ids and 'dwarven_toughness' in ids:
        maximum = max(1, maximum - actor.level)
    features = tuple(f for f in actor.features
                     if f.feature_id not in RETIRED | {MIGRATION} and f.source_ref != SOURCE)
    features += (FeatureGrant(MIGRATION, 'Pasywy odblokowywane maną',
        FeatureSourceKind.SCENARIO, 'mana_saturation:v1'),)
    # These bonuses were baked into the original character builder.
    base_ac = (10 + ability_modifier(actor.ability_scores.dexterity)
               if str(actor.id) == 'brakka' else actor.ac)
    affinities = actor.damage_affinities
    if str(actor.id) == 'dagna':
        affinities = replace(affinities, resistances=tuple(
            r for r in affinities.resistances if r != DamageType.POISON))
    from .resources import RecoveryPeriod
    pools = tuple(replace(p, recovery=RecoveryPeriod.NEVER,
                          label='Nieustępliwość — użycie do draina')
                  if p.id == 'relentless_endurance_uses' else p for p in actor.resource_pools)
    return replace(actor, features=features, ac=base_ac, max_hp=maximum,
        hp=min(actor.hp, maximum), damage_affinities=affinities,
        resource_pools=pools,
        senses=replace(actor.senses, darkvision_feet=0))


def apply_color_features(actor: Actor, cards: Sequence[str],
                         passives: Mapping[str, Mapping[str, object]]) -> Actor:
    """Rebuild native feature hooks from present colors, without stacking copies."""
    actor = normalize_mana_passives(actor)
    if not uses_charge(actor):
        return actor
    features = list(actor.features)
    added: set[str] = set()
    for color in dict.fromkeys(cards):
        passive = passives[color]
        for feature_id in passive.get('features', ()):
            if feature_id not in added:
                features.append(FeatureGrant(feature_id, FEATURE_LABELS[feature_id],
                    FeatureSourceKind.SCENARIO, SOURCE, str(passive['label'])))
                added.add(feature_id)
    ac = actor.ac
    if 'unarmored_defense_constitution' in added:
        ac = 10 + ability_modifier(actor.ability_scores.dexterity) + ability_modifier(actor.ability_scores.constitution)
    affinities = actor.damage_affinities
    if 'dwarven_resilience' in added and DamageType.POISON not in affinities.resistances:
        affinities = replace(affinities, resistances=(*affinities.resistances, DamageType.POISON))
    return replace(actor, features=tuple(features), ac=ac, damage_affinities=affinities)


def reset_mana_passives(actor: Actor) -> Actor:
    """Start a new deck cycle; losing/reacquiring a color alone never refills uses."""
    actor = normalize_mana_passives(actor)
    if not uses_charge(actor):
        return actor
    from .resources import RecoveryPeriod
    return replace(actor, resource_pools=tuple(
        replace(p, current=p.maximum, recovery=RecoveryPeriod.NEVER,
                label='Nieustępliwość — użycie do draina')
        if p.id == 'relentless_endurance_uses' else p for p in actor.resource_pools))


def color_passive_status(actor: Actor, passive: Mapping[str, object]) -> str:
    """Readable state shared by the character panel and native status effects."""
    if 'relentless_endurance' in passive.get('features', ()):
        from .resources import can_spend_actor_resource
        return ('Gotowe — uratuje przed 0 PW' if can_spend_actor_resource(actor, 'relentless_endurance_uses')
                else 'Zużyte — odnowi mana drain')
    if str(passive['kind']).startswith('heal'):
        return 'Leczenie przy każdym doborze tego koloru'
    return 'Aktywne'
