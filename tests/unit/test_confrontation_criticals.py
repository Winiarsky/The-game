"""Natural extremes resolve once, preserve passives and pay physical costs."""
from dataclasses import replace
import json

import pytest

from dnd_board_game.rules import confrontation as r
from tests.unit.test_confrontation import charged, settle
from tests.unit.test_distinct_exploration_passives import scene


@pytest.mark.parametrize('die', [4, 6, 8, 10, 12])
def test_twenty_beats_any_dc_and_resolves_maximum_without_second_roll(die: int) -> None:
    state = scene('nimra', ('F', 'F'), aids=(('nimra', 1),))
    actor = replace(state.actor, dc=50, die=die, test_modifier=-30, impact_modifier=2)
    state = replace(state, participants=(actor, *state.participants[1:]))
    result = r.roll_check(r.declare(state, 2), 20)
    assert result.last_total < actor.dc
    assert result.last_critical == 'success' and result.last_action_success
    assert result.last_impact == die + 2 + 2
    assert result.resistance == state.resistance - result.last_impact
    assert result.stage == 'after_action' and result.mana.pending_count == 1
    assert not result.aids
    assert 'rzuć na wpływ' not in result.last
    loaded = r.Confrontation.from_data(json.loads(json.dumps(result.to_data())))
    assert loaded == result
    with pytest.raises(ValueError):
        r.roll_impact(loaded, die)
    with pytest.raises(ValueError):
        r.roll_check(loaded, 20)
    assert r.advance(settle(loaded)).last_critical == ''


def test_one_fails_despite_bonuses_consumes_aid_and_preserves_garran_rally() -> None:
    state = scene('garran', ('F',), aids=(('garran', 30),))
    result = r.roll_check(r.declare(state, 1), 1)
    assert result.last_total >= result.actor.dc
    assert result.last_critical == 'failure' and not result.last_action_success
    assert result.resistance == state.resistance and result.last_impact == 0
    assert dict(result.aids) == {'dagna': 1, 'erynd': 1}
    assert result.cost == result.mana.pending_count == 2
    first = r.report_color(result, result.mana.deck[0])
    assert first.last_critical == 'failure' and first.mana.pending_count == 1
    loaded = r.Confrontation.from_data(json.loads(json.dumps(first.to_data())))
    paid = settle(loaded)
    assert len(paid.mana.burned) == len(state.mana.burned) + 2
    assert paid.mana.hand('garran') == ('F',)


def test_critical_surcharge_is_applied_after_dagnas_cost_reduction() -> None:
    state = scene('dagna', ('N',))
    result = r.roll_check(r.declare(state, 0), 1)
    assert result.last_critical == 'failure'
    assert result.cost == result.mana.pending_count == 1
    assert r.roll_check(r.declare(state, 0), 2).cost == 0


def test_failure_keeps_brakkas_impact_and_self_aid() -> None:
    result = r.roll_check(r.declare(scene('brakka', ('B', 'Z')), 0), 1)
    assert result.last_impact == 1 and result.resistance == 59
    assert dict(result.aids) == {'brakka': 2}
    assert result.cost == 2


@pytest.mark.parametrize('hero,hand,impact', [('mira', ('Z', 'Z'), 8), ('nimra', ('C',), 9)])
def test_maximum_and_exact_total_passives_apply_to_critical_success(
    hero: str, hand: tuple[str, ...], impact: int,
) -> None:
    state = scene(hero, hand)
    state = replace(state, participants=(replace(state.actor, dc=20), *state.participants[1:]))
    assert r.roll_check(r.declare(state, 0), 20).last_impact == impact


def test_critical_success_keeps_erynds_aid() -> None:
    result = r.roll_check(r.declare(scene('erynd', ('N',)), 0), 20)
    assert dict(result.aids) == {'garran': 1}


def test_winning_critical_waits_for_dagnas_recovery_and_cost_after_reload() -> None:
    state = charged(scene('dagna', ('Z',), resistance=1), {'dagna': ('Z',)}, deck_size=0)
    result = r.roll_check(r.declare(state, 0), 20)
    assert result.stage == 'recovery' and not result.outcome and result.resistance == 0
    loaded = r.Confrontation.from_data(json.loads(json.dumps(result.to_data())))
    result = settle(loaded)
    assert result.outcome == 'success' and result.last_critical == 'success'


@pytest.mark.parametrize('natural,expected', [(1, 'failure'), (20, 'success')])
def test_last_card_drain_preserves_critical_result(natural: int, expected: str) -> None:
    state = charged(scene('garran', (), resistance=1), {}, deck_size=1)
    result = settle(r.roll_check(r.declare(state, 0), natural))
    assert result.outcome == expected
    assert result.last_critical == expected


@pytest.mark.parametrize('natural,modifier,stage', [(2, 18, 'impact'), (19, -18, 'after_action')])
def test_only_natural_extremes_are_critical(natural: int, modifier: int, stage: str) -> None:
    state = scene('garran', ())
    state = replace(state, participants=(replace(state.actor, test_modifier=modifier), *state.participants[1:]))
    result = r.roll_check(r.declare(state, 0), natural)
    assert result.stage == stage and result.last_critical == ''
    assert result.cost == 1


def test_old_pending_impact_is_not_reinterpreted_as_new_critical() -> None:
    state = r.roll_check(r.declare(scene('garran', ()), 0), 19)
    data = state.to_data()
    data.pop('last_critical')
    data['last_roll'] = 20
    loaded = r.Confrontation.from_data(data)
    assert loaded.stage == 'impact' and loaded.last_critical == ''
    assert r.roll_impact(loaded, 2).last_impact == 2
