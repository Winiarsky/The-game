"""Physical pool capacity is independent from weighted ability unlocks."""
from dataclasses import replace

import pytest

from dnd_board_game.rules import pooled_mana as r
from dnd_board_game.scenarios.pooled_mana_catalog import hero_profile, load_catalog, pool_ability
from tests.unit.test_mana_charge import pool


@pytest.mark.parametrize('hero', tuple(load_catalog()['heroes']))
def test_three_trumps_unlock_ultimate_but_bonus_and_passives_count_physical_cards(hero):
    profile = hero_profile(hero)
    trump = profile['trump_color']
    state = pool(hero, (trump,) * 3)
    assert state.points(hero) == 6
    assert state.roll_bonus(hero) == 3
    assert not state.full(hero)
    assert r.start_turn(state, hero).draw_due
    for key, definition in load_catalog()['abilities'].items():
        if definition['hero'] == hero and definition['minimum'] == 6:
            pool_ability(key).validate(state.hand(hero), profile['values'])
    from dnd_board_game.combat.mana_charge import charge_effects
    effects = charge_effects(state, {hero: profile})
    assert next(e.value for e in effects if e.kind == 'charge_accuracy') == 3
    passive = profile['color_passives'][trump]
    if passive['kind'] == 'melee_damage':
        assert next(e.value for e in effects if e.kind == 'charge_melee_damage') == 3 * passive['value']


def test_sixth_card_stops_draw_and_seventh_is_rejected_even_with_stale_phase():
    state = pool('brakka', ('C', 'C', 'C', 'B', 'Z'))
    state = replace(state, deck=state.deck[:-2], offer=('N', 'F'), phase='choose', draw_due=True)
    state = r.take(state, 0)
    assert (state.points('brakka'), state.roll_bonus('brakka')) == (6, 6)
    assert not r.start_turn(state, 'brakka').draw_due
    with pytest.raises(ValueError):
        r.take(replace(state, phase='choose', draw_due=True), 0)
    # A stripped card moves to burned: the next turn must draw again.
    state = replace(state, pools=(('brakka', state.hand('brakka')[:-1]),), burned=('N',))
    assert r.start_turn(state, 'brakka').draw_due


def test_non_trump_cards_unlock_at_two_four_and_six_without_inflating_bonus():
    profile = hero_profile('brakka')
    for count, ability in [(2, 'hamstring_cut'), (4, 'powerful_strike'), (6, 'reaper')]:
        # Use Brakka's actual medium/ultimate and a pure threshold for the weak tier.
        from dnd_board_game.rules.pooled_mana_catalog import PoolAbility
        definition = PoolAbility('weak', 'brakka', 2, (), False, 1) if count == 2 else pool_ability(ability)
        hand = ('B', 'N', 'Z', 'F', 'B', 'N')[:count]
        definition.validate(hand, profile['values'])
        with pytest.raises(ValueError):
            definition.validate(hand[:-1], profile['values'])
        state = pool('brakka', hand)
        assert state.points('brakka') == state.roll_bonus('brakka') == count


def test_legacy_save_migrates_weights_without_changing_any_physical_zone():
    state = pool('brakka', ('C', 'C', 'B', 'B', 'Z', 'N', 'F'))
    payload = state.as_payload()
    payload.update(catalog_version=2, values=(('brakka', (7, 1, 3, 4, 4)),), phase='choose', draw_due=True)
    restored = r.PooledMana.from_payload(payload)
    assert restored.catalog_version == 3
    assert restored.point_values('brakka') == hero_profile('brakka')['values']
    for zone in ('deck', 'offer', 'pools', 'burned', 'expired', 'prisons', 'excluded'):
        assert getattr(restored, zone) == getattr(state, zone)
    assert restored.roll_bonus('brakka') == 6 and not restored.draw_due
    assert r.PooledMana.from_payload(restored.as_payload()) == restored
    reset = r.confirm_shuffle(r.drain(restored, 'test'))
    assert not reset.pools and reset.roll_bonus('brakka') == 0
    assert reset.values == restored.values


@pytest.mark.parametrize('players,remaining', [(3, 12), (4, 16), (5, 20), (6, 24)])
def test_full_party_capacity_leaves_expected_shared_supply(players, remaining):
    assert r.deck_copies(players) * 5 - players * 6 == remaining
