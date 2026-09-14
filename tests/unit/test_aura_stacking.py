"""Overlapping auras select one complete variant without destroying sources."""
from dataclasses import replace
from random import Random

import pytest

from dnd_board_game.actors import Actor, Faction
from dnd_board_game.combat import AttackSource, AttackSourceType, attack_source_with_combat_effects
from dnd_board_game.combat.auras import resolve_healing_grace_bonus, synchronize_spell_aura_effects
from dnd_board_game.combat.garran_features import synchronize_garran_effects
from dnd_board_game.combat.shared_mana_features import synchronize_bastion
from dnd_board_game.combat.targets import combat_armor_class
from dnd_board_game.rules import ActiveEffect, D20RollRequest, EffectDuration, EffectEvent, EffectEventType, expire_active_effects
from dnd_board_game.world import Coordinate
from tests.unit.test_combat_auras import _actor


def source(kind: str, owner: str, value: int, *, modifier: int = 0, radius: int = 10) -> ActiveEffect:
    return ActiveEffect(
        id=f'{kind}:{owner}', actor_id=owner, source_actor_id=owner,
        kind=kind, label=kind, value=value, modifier=modifier,
        object_id='shared_combat_action:divine_care_aura' if kind == 'divine_care_aura_source' else kind,
        radius_feet=radius, duration=EffectDuration.CONCENTRATION,
    )


def synchronize(actors: tuple[Actor, ...], effects: tuple[ActiveEffect, ...]) -> tuple[ActiveEffect, ...]:
    return synchronize_bastion(actors, synchronize_garran_effects(actors, synchronize_spell_aura_effects(actors, effects)))


@pytest.mark.parametrize('kind,member_kind,sign', [
    ('garran_shield_wall_source', 'garran_shield_wall_member', 1),
    ('iron_bastion', 'iron_bastion_member', 1),
    ('bless_aura_source', 'bless_roll_bonus', 1),
    ('divine_care_aura_source', 'divine_care_aura_penalty', -1),
])
@pytest.mark.parametrize('loss', ['movement', 'defeat', 'concentration'])
def test_strongest_aura_wins_and_weaker_resumes(kind: str, member_kind: str, sign: int, loss: str) -> None:
    weak = _actor('weak', Coordinate(0, 0))
    strong = _actor('strong', Coordinate(1, 0))
    target = _actor('target', Coordinate(1, 1), Faction.ENEMY if sign < 0 else Faction.ALLY)
    actors = (weak, strong, target)
    sources = (source(kind, 'weak', 2), source(kind, 'strong', 4))
    for ordered in (sources, sources[::-1]):
        effects = synchronize(actors, ordered)
        members = [e for e in effects if e.kind == member_kind and e.actor_id == 'target']
        assert len(members) == 1
        assert members[0].value == 4 * sign
        assert members[0].source_actor_id == 'strong'
        assert all(e in effects for e in sources)
        assert synchronize(actors, effects) == effects
        if 'shield' in kind or kind == 'iron_bastion':
            assert combat_armor_class(target, effects) == target.ac + 4

        remaining = actors
        if loss == 'movement':
            remaining = (weak, replace(strong, position=Coordinate(10, 10)), target)
        elif loss == 'defeat':
            remaining = (weak, replace(strong, hp=0), target)
        else:
            effects = expire_active_effects(effects, EffectEvent(
                EffectEventType.CONCENTRATION_ENDED, actor_id='strong')).active_effects
        updated = synchronize(remaining, effects)
        members = [e for e in updated if e.kind == member_kind and e.actor_id == 'target']
        assert len(members) == 1
        assert members[0].value == 2 * sign
        assert members[0].source_actor_id == 'weak'


def test_different_auras_from_one_owner_combine_but_repeated_shield_does_not() -> None:
    owner = _actor('garran', Coordinate(0, 0))
    other = _actor('other', Coordinate(0, 1))
    target = _actor('target', Coordinate(1, 0))
    effects = synchronize((owner, other, target), (
        source('garran_shield_wall_source', 'garran', 2),
        source('garran_shield_wall_source', 'other', 2),
        source('iron_bastion', 'garran', 1),
    ))
    assert combat_armor_class(target, effects) == target.ac + 3
    assert len([e for e in effects if e.actor_id == 'target' and e.kind.endswith('_member')]) == 2


@pytest.mark.parametrize('wide_attack,boosted_attack,expected_attack,expected_damage', [
    (2, 2, -2, 2), (2, 3, -3, 2), (3, 2, -3, 4),
])
def test_divine_care_chooses_whole_variant_and_radius_only_controls_coverage(
    wide_attack: int, boosted_attack: int, expected_attack: int, expected_damage: int,
) -> None:
    wide = _actor('wide', Coordinate(0, 0))
    boosted = _actor('boosted', Coordinate(1, 0))
    target = _actor('enemy', Coordinate(2, 0), Faction.ENEMY)
    sources = (
        source('divine_care_aura_source', 'wide', wide_attack, radius=10),
        source('divine_care_aura_source', 'boosted', boosted_attack, modifier=-2, radius=5),
    )
    weapon = AttackSource(name='Atak', source_type=AttackSourceType.WEAPON,
        range_feet=5, attack_roll_request=D20RollRequest(), damage_modifier=4)
    for ordered in (sources, sources[::-1]):
        effects = synchronize((wide, boosted, target), ordered)
        attack = attack_source_with_combat_effects(target, weapon, effects)
        assert [m.value for m in attack.attack_roll_request.modifiers] == [expected_attack]
        assert attack.damage_modifier == expected_damage
        far_target = replace(target, position=Coordinate(0, 2))
        effects = synchronize((wide, boosted, far_target), effects)
        attack = attack_source_with_combat_effects(far_target, weapon, effects)
        assert [m.value for m in attack.attack_roll_request.modifiers] == [-wide_attack]
        assert attack.damage_modifier == 4


def test_healing_grace_uses_only_strongest_available_source_then_falls_back() -> None:
    weak = _actor('weak', Coordinate(0, 0))
    strong = _actor('strong', Coordinate(1, 0))
    target = _actor('target', Coordinate(1, 1))
    sources = (
        replace(source('healing_grace_aura_source', 'weak', 3), die_sides=8, modifier=1),
        replace(source('healing_grace_aura_source', 'strong', 1), die_sides=8, modifier=4),
    )
    for ordered in (sources, sources[::-1]):
        first = resolve_healing_grace_bonus((weak, strong, target), ordered, target, rng=Random(7))
        assert first.source_actor_id == 'strong'
        assert first.bonus == first.die_roll + 4
        assert sources[0] in first.active_effects  # Unused aura retains every charge.
        second = resolve_healing_grace_bonus((weak, strong, target), first.active_effects, target, rng=Random(7))
        assert second.source_actor_id == 'weak'
        assert second.bonus == second.die_roll + 1


def test_overlapping_hymns_still_grant_only_one_extra_bonus_action() -> None:
    from dnd_board_game.combat.session import shared_bonus_action_limit
    from dnd_board_game.rules.shared_mana import SharedMana
    from tests.unit.test_garran_features import _state

    first = _actor('first', Coordinate(0, 0))
    second = _actor('second', Coordinate(1, 0))
    target = _actor('target', Coordinate(2, 0))
    state = replace(_state(first, second, target), shared_mana=SharedMana(hymn_sources=('first', 'second')))
    assert shared_bonus_action_limit(state, target) == 2
    state = replace(state, actors=(replace(first, hp=0), second, target))
    assert shared_bonus_action_limit(state, target) == 2
    state = replace(state, actors=(replace(first, hp=0), replace(second, position=Coordinate(20, 20)), target))
    assert shared_bonus_action_limit(state, target) == 1
