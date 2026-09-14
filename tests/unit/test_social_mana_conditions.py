"""Decision conditions, terminal results, and compatibility with old attempts."""
from dataclasses import replace

import pytest

from dnd_board_game.rules.exploration_mana import (
    ManaAttempt, answer_bargain, choose_color, declare_draw, set_favor, stand, request_reroll,
)
from dnd_board_game.rules.exploration_mana_conditions import ManaCondition
from dnd_board_game.rules.exploration_mana_catalog import profile_values
from dnd_board_game.application.exploration_mana_flow import resolve_attempt
from dnd_board_game.application.exploration_mana_outcomes import resolve_outcome
from dnd_board_game.scenarios.exploration_mana import scene_by_id
from dnd_board_game.ui.training_arena import training_hero


def attempt(kind, **params):
    return ManaAttempt('trial', 'scene', 'inspiration', profile_values('balanced'), condition=ManaCondition(kind, **params))


def pick(a, colors):
    for color in colors:
        if a.phase == 'decision':
            a = declare_draw(a)
        a = choose_color(a, color)
    return a


def test_offer_is_once_and_acceptance_is_distinct_result():
    a = pick(attempt('compromise'), 'NCF')
    assert a.total == 16 and a.phase == 'bargain'
    for command in (declare_draw, stand):
        with pytest.raises(ValueError): command(a)
    accepted = answer_bargain(a, accept=True)
    assert accepted.outcome_kind == 'compromise' and accepted.success is None and not accepted.rolls
    declined = answer_bargain(a, accept=False)
    assert stand(declined).phase == 'roll'
    # A second landing in the interval does not renew the offer.
    declined = replace(declined, values=(7, 1, 3, 4, 5))
    assert pick(declined, 'B').phase == 'decision'
    with pytest.raises(ValueError): answer_bargain(declined, accept=True)


def test_jumping_past_offer_and_terminal_priority():
    assert pick(attempt('compromise'), 'CCF').total == 18
    assert pick(attempt('compromise'), 'CCF').phase == 'decision'
    assert pick(attempt('compromise'), 'CCC').outcome_kind == 'success'
    assert pick(attempt('compromise'), 'CCNF').busted
    a = replace(attempt('compromise'), obstacle='four')
    assert pick(a, 'NFBF').phase == 'roll'


@pytest.mark.parametrize('kind,color,colors,variant', [
    ('sensitive_topic', 'C', 'CCC', 'sensitive_success'),
    ('sensitive_topic', 'C', 'NNNFB', 'success'),
    ('color_goal', 'N', 'NNFC', 'goal_success'),
    ('color_goal', 'N', 'CCC', 'success'),
])
def test_exact_result_uses_chosen_cards(kind, color, colors, variant):
    a = pick(attempt(kind, color=color), colors)
    scene = scene_by_id('irena_'+kind)
    result = resolve_outcome(a, next(o for o in scene.options if o.method_id == a.method_id))
    assert a.total == 21 and result['variant'] == variant


def test_goal_survives_bust_and_failed_first_lorian_roll():
    a = pick(attempt('color_goal', color='N'), 'NNCC')
    assert a.busted and a.goal_met
    a = resolve_attempt(training_hero('lorian'), a, 16, (20, 1), improvisation_available=True)
    assert a.phase == 'reroll_choice'
    with pytest.raises(ValueError): resolve_outcome(a, scene_by_id('irena_color_goal').options[4])
    a = resolve_attempt(training_hero('lorian'), request_reroll(a), 16, (20, 19))
    assert resolve_outcome(a, scene_by_id('irena_color_goal').options[4])['variant'] == 'goal_success'


def test_favor_is_optional_once_and_preserves_color_after_exact():
    a = pick(attempt('favor'), 'NNNN')
    a = declare_draw(a)
    armed = set_favor(a, armed=True)
    assert set_favor(armed, armed=False) == replace(a, revision=a.revision+2)
    final = choose_color(armed, 'C')
    assert final.total == 21 and final.colors[-1] == 'C' and final.amounts[-1] == 1
    assert final.favor_status == 'used'
    with pytest.raises(ValueError): set_favor(final, armed=True)
    busted = pick(attempt('favor'), 'CCNF')
    with pytest.raises(ValueError): set_favor(busted, armed=True)


def test_roundtrip_and_v1_no_retroactive_condition():
    a = pick(attempt('compromise'), 'NCF')
    assert ManaAttempt.from_data(a.to_data()) == a
    legacy = ManaAttempt('old','irena','authority',profile_values('balanced')).to_data()
    for key in ('condition','proposal_status','sensitive_used','favor_status'): legacy.pop(key)
    legacy['version'] = 1
    migrated = ManaAttempt.from_data(legacy)
    assert migrated.condition.kind == 'none' and migrated.to_data()['version'] == 2
    with pytest.raises(ValueError): ManaAttempt.from_data({**legacy,'version':3})
