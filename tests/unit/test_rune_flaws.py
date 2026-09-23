"""Rune flaws share printed text, actual payment and saved actor normalization."""
from dataclasses import replace

import pytest

from dnd_board_game.actors import ActorId
from dnd_board_game.character_creation.runes import apply_rune_profile
from dnd_board_game.combat import current_actor, replace_actor
from dnd_board_game.combat.rune_flaws import rune_flaw_cost
from dnd_board_game.combat.runes import quote_runes, rune_requirements
from dnd_board_game.rules.shared_mana import SharedMana, pay_mana, finish_mana_action, sync_runes
from dnd_board_game.scenarios.rune_traits import rune_flaw
from dnd_board_game.scenarios.rune_catalog import rune_cards
from dnd_board_game.ui.training_arena import training_hero
from dnd_board_game.ui.exploration_app import _feature_grant_payload
from dnd_board_game.save.session_snapshot import _actor_payload, _actor_from_payload
from dnd_board_game.world import Coordinate
from tests.unit.test_rune_resources import state_with_hand


HEROES = ('garran', 'brakka', 'mira', 'dagna', 'lorian', 'nimra', 'erynd')


@pytest.mark.parametrize('hero', HEROES)
def test_features_prints_and_saved_rune_actors_use_current_rules(hero):
    from dnd_board_game.physical_cards.mana_print import build_print_hero
    actor = apply_rune_profile(training_hero(hero))
    flaw = rune_flaw(hero)
    features = [_feature_grant_payload(f, hero) for f in actor.features]
    displayed = next(f for f in features if f['id'].startswith('flaw_'))
    assert displayed['mechanics'] == flaw.body
    assert build_print_hero(hero, rune_profile=True).flaw == (flaw.name, flaw.body)
    assert not any(f.feature_id in {'mana_great_tuning', 'turn_undead'} for f in actor.features)
    cards = {c.id: c for c in rune_cards(hero)}
    for feature in actor.features:
        for action in feature.action_ids:
            if action in cards:
                assert _feature_grant_payload(feature, hero)['mechanics'] == cards[action].description
    stale = replace(actor, hp=max(1, actor.hp - 3), features=tuple(
        replace(f, description='spala starą kartę', source_ref='physical_mana:v02')
        if f.feature_id.startswith('flaw_') else f for f in actor.features))
    restored = _actor_from_payload(_actor_payload(stale))
    assert restored.hp == stale.hp and restored.inventory == stale.inventory
    assert restored.resource_pools == stale.resource_pools
    assert next(f.description for f in restored.features if f.feature_id.startswith('flaw_')) == flaw.body
    assert apply_rune_profile(restored) == restored


def hero_state(hero, cards=('Klepsydra', 'Klepsydra', 'Kielich', 'Klucz', 'Kotwica')):
    state = state_with_hand(cards)
    actor = apply_rune_profile(training_hero(hero))
    actor = replace(actor, position=Coordinate(0, 1))
    # Preserve a unique roster when Nimra replaces Garran.
    other = tuple(a for a in state.actors[1:] if str(a.id) != hero)
    actors = (actor, *other)
    order = replace(state.initiative_order, entries=(replace(state.initiative_order.entries[0], actor=actor),
        *tuple(e for e in state.initiative_order.entries[1:] if str(e.actor.id) != hero)))
    pool = state.shared_mana.runes
    hands = tuple((hero if h == 'garran' else 'dagna' if h == hero else h, rs) for h, rs in pool.hands)
    pool = replace(pool, heroes=tuple(h for h, _ in hands), hands=hands)
    return replace(state, actors=actors, initiative_order=order,
        shared_mana=replace(sync_runes(state.shared_mana, pool), turn_actor=hero))


def test_lorian_audience_range_consciousness_and_free_attacks():
    state = hero_state('lorian')
    actor = current_actor(state)
    ally = next(a for a in state.actors if str(a.id) == 'mira')
    state = replace(state, actors=(actor, replace(ally, position=Coordinate(2, 1))))
    assert rune_flaw_cost(state, actor, 'mana_inspiration').count == 0
    state = replace_actor(state, replace(ally, position=Coordinate(3, 1)))
    assert rune_requirements(state, actor, 'mana_inspiration', {})[-1] == '*'
    assert rune_flaw_cost(state, actor, 'cutting_words').count == 1
    assert quote_runes(state, actor, 'basic_attack:hand_crossbow', {}) == ()
    state = replace_actor(state, replace(ally, hp=0, position=Coordinate(1, 1)))
    assert rune_flaw_cost(state, actor, 'mana_inspiration').count == 1
    from dnd_board_game.combat.conditions import CombatCondition, ConditionState
    state = replace_actor(state, replace(ally, position=Coordinate(1, 1)))
    state = replace(state, condition_states=(ConditionState(str(ally.id), CombatCondition.UNCONSCIOUS),))
    assert rune_flaw_cost(state, actor, 'mana_inspiration').count == 1
    from dnd_board_game.rules.runes import new_runes, RESOURCE_RUNES
    state = replace(state, shared_mana=sync_runes(state.shared_mana, new_runes(('lorian',), RESOURCE_RUNES)))
    assert rune_flaw_cost(state, actor, 'mana_inspiration').count == 0


def test_dagna_only_offensive_powers_next_to_wounded_ally():
    state = hero_state('dagna')
    actor = current_actor(state)
    ally = next(a for a in state.actors if str(a.id) == 'mira')
    state = replace_actor(state, replace(ally, hp=9, max_hp=20))
    assert rune_flaw_cost(state, actor, 'guiding_bolt').count == 1
    assert rune_flaw_cost(state, actor, 'sacred_flame').count == 1
    assert rune_flaw_cost(state, actor, 'healing_word').count == 0
    assert rune_flaw_cost(state, actor, 'basic_attack:mace').count == 0
    state = replace_actor(state, replace(ally, hp=10, max_hp=20))
    assert rune_flaw_cost(state, actor, 'guiding_bolt').count == 0


def test_nimra_echo_payment_cap_reset_and_save():
    state = hero_state('nimra', ('Rozwidlenie', 'Rozwidlenie', 'Kielich', 'Klucz', 'Kotwica'))
    actor = current_actor(state)
    ability = 'nimra_frost_pulse'
    assert rune_flaw_cost(state, actor, ability).count == 0
    mana = state.shared_mana
    paid = pay_mana(mana, revision=mana.revision, actor_id='nimra', ability_id=ability, count=1,
                    rune_payment=('Rozwidlenie',))
    ready = finish_mana_action(paid, revision=paid.revision)
    state = replace(state, shared_mana=SharedMana.from_payload(ready.as_payload()))
    assert rune_flaw_cost(state, actor, ability).count == 1
    with pytest.raises(ValueError, match='Echa'):
        pay_mana(ready, revision=ready.revision, actor_id='nimra', ability_id=ability, count=1, rune_payment=('Rozwidlenie',))
    paid = pay_mana(ready, revision=ready.revision, actor_id='nimra', ability_id=ability,
        count=2, rune_payment=('Rozwidlenie', 'Klucz'), rune_surcharge=1)
    ready = finish_mana_action(paid, revision=paid.revision)
    state = replace(state, shared_mana=replace(ready, echo_count=99))
    assert rune_flaw_cost(state, actor, ability).count == 2
    assert rune_flaw_cost(state, actor, 'shield').count == 0
    # A different paid reaction starts its own series; previewing it did not.
    paid = pay_mana(ready, revision=ready.revision, actor_id='nimra', ability_id='shield',
        count=2, rune_payment=('Kielich', 'Kotwica'))
    assert paid.echo_spell == 'shield' and paid.echo_count == 1
    state = replace(state, shared_mana=paid)
    assert rune_flaw_cost(state, actor, ability).count == 0


def test_erynd_only_powers_with_threatened_targets():
    state = hero_state('erynd')
    state = replace(state, actors=tuple(a for a in state.actors if str(a.id) != 'nimra'))
    actor = current_actor(state)
    enemy = next(a for a in state.actors if a.faction != actor.faction)
    ally = next(a for a in state.actors if str(a.id) == 'mira')
    state = replace_actor(state, replace(ally, position=Coordinate(enemy.position.col, enemy.position.row+1)))
    assert rune_flaw_cost(state, actor, 'double_shot', (enemy,)).count == 1
    assert rune_flaw_cost(state, actor, 'arrow_rain', (enemy,)).count == 1
    assert rune_flaw_cost(state, actor, 'basic_attack:longbow', (enemy,)).count == 0
    assert rune_flaw_cost(state, actor, 'aim', (enemy,)).count == 0
    state = replace_actor(state, replace(ally, hp=0))
    assert rune_flaw_cost(state, actor, 'double_shot', (enemy,)).count == 0


def test_legacy_mana_actor_is_not_migrated_to_runes():
    from dnd_board_game.character_creation.physical_mana import apply_physical_mana_profile
    actor = apply_physical_mana_profile(training_hero('lorian'))
    assert _actor_from_payload(_actor_payload(actor)) == actor


def test_nimra_has_only_card_boosts_and_no_legacy_echo_markers():
    from dnd_board_game.combat.nimra_features import arcane_echo_effects
    actor = apply_rune_profile(training_hero('nimra'))
    assert any(f.feature_id == 'nimra_catalogue' for f in actor.features)
    assert not any(f.feature_id in {'nimra_sculpt_field', 'nimra_distant_spell', 'nimra_overcharged_spell',
        'nimra_forced_weave', 'nimra_energy_transmutation'} for f in actor.features)
    assert arcane_echo_effects(actor, spell_id='nimra_frost_pulse', metamagic_ids=(), round_number=2) == ()


def test_tabletop_biography_and_echo_match_the_rune_profile():
    # Exercise the public presentation entrypoint with a minimal real actor payload.
    from dnd_board_game.ui.exploration_app import _exploration_actor_payload
    actor = apply_rune_profile(training_hero('nimra'))
    payload = _exploration_actor_payload(actor)
    combat = {'actors': [payload], 'current_actor': payload,
              'shared_mana': {'rune_view': {}, 'echo_spell': 'nimra_frost_pulse', 'echo_count': 2}}
    from dnd_board_game.ui.tabletop_combat import tabletop_combat_payload
    shown = tabletop_combat_payload(combat)['actors'][0]
    assert shown['biography']['flaw'] == rune_flaw('nimra').body
    effects = shown['details']
    assert any(e['id'] == 'rune_echo' and '+2' in e['body'] for e in effects)
