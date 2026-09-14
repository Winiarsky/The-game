from dataclasses import replace

import pytest

from dnd_board_game.rules.exploration_mana import (
    ManaAttempt, choose_color, declare_draw, stand, request_reroll, next_value,
)
from dnd_board_game.rules.exploration_mana_catalog import METHODS, profile_values
from dnd_board_game.application.exploration_mana_flow import check_request, resolve_attempt, method_modifiers
from dnd_board_game.ui.training_arena import training_hero
from dnd_board_game.scenarios.exploration_mana import content, lessons_for, scene_for, scene_by_id


def build(method='intimidation', obstacle='none'):
    return ManaAttempt('one', 'irena', method, profile_values('balanced'), obstacle)


def select(attempt, colors):
    for color in colors:
        if attempt.phase == 'decision':
            attempt = declare_draw(attempt)
        attempt = choose_color(attempt, color)
    return attempt


def test_declare_before_offer_and_exact_success():
    a = select(build(), 'C')
    with pytest.raises(ValueError):
        choose_color(a, 'B')
    a = declare_draw(a)
    with pytest.raises(ValueError):
        stand(a)
    a = select(a, 'CC')
    assert a.total == 21 and a.success and a.phase == 'result'
    with pytest.raises(ValueError):
        declare_draw(a)


def test_bust_uses_two_dice_lower_result_no_negative_modifier():
    a = select(build(), 'CCNF')
    assert a.total == 23 and a.busted and a.bonus == 0
    actor = training_hero('brakka')
    request = check_request(actor, a)
    assert request.mode.value == 'disadvantage'
    assert sum(m.value for m in request.modifiers) == 5
    with pytest.raises(ValueError):
        resolve_attempt(actor, a, 16, (20,))
    result = resolve_attempt(actor, a, 16, (20, 2))
    assert result.roll_total == 7 and not result.success
    assert resolve_attempt(actor, a, 16, (19, 12)).success


def test_constitution_intimidation_counts_training_not_save_or_charisma():
    a = stand(select(build('intimidation', 'after_red'), 'CBNZ'))
    assert a.total == 19 and a.amounts == (7, 4, 5, 3)
    result = resolve_attempt(training_hero('brakka'), a, 16, (7,))
    assert result.roll_total == 16 and result.success


def test_repeat_and_after_red_are_local_not_retroactive():
    a = select(build(obstacle='repeat'), 'CCB')
    assert a.amounts == (7, 9, 2) and a.total == 18
    assert next_value(a, 'B') == 4 and next_value(a, 'C') == 7
    a = select(build(obstacle='after_red'), 'CBN')
    assert a.amounts == (7, 4, 5)


def test_four_forces_normal_stand_but_exact_and_bust_take_precedence():
    a = select(build(obstacle='four'), 'BZFB')
    assert a.total == 11 and a.phase == 'roll' and not a.busted and a.bonus == 1
    assert select(build(obstacle='four'), 'CCNF').busted
    assert select(build(obstacle='four'), 'CCNB').success


def test_lorian_rerolls_whole_disadvantaged_check_once():
    a = select(build('inspiration'), 'CCNF')
    actor = training_hero('lorian')
    a = resolve_attempt(actor, a, 16, (20, 1), improvisation_available=True)
    assert a.phase == 'reroll_choice' and not a.success
    a = request_reroll(a)
    a = resolve_attempt(actor, a, 16, (19, 2), improvisation_available=True)
    assert a.phase == 'result' and a.reroll_used and not a.success
    with pytest.raises(ValueError):
        request_reroll(a)


@pytest.mark.parametrize('method', METHODS, ids=lambda m:m.id)
def test_every_method_uses_declared_actor_and_ability(method):
    actor = training_hero(method.hero_id)
    mods = method_modifiers(actor, method)
    assert mods[0].value == (getattr(actor.ability_scores, method.ability)-10)//2
    assert sum(m.label == 'Praktyka terenowa' for m in mods) == int(method.id == 'survey')
    assert sum(m.label == 'Obycie i targowanie' for m in mods) == int(method.id == 'inspiration')
    with pytest.raises(ValueError):
        method_modifiers(training_hero('mira' if method.hero_id != 'mira' else 'dagna'), method)


def test_round_trip_preserves_locked_profile_and_pending_roll():
    for a in (build(), select(build(), 'CN'), stand(select(build(), 'CN')), select(build(), 'CCNF')):
        assert ManaAttempt.from_data(a.to_data()) == a
    with pytest.raises(ValueError):
        ManaAttempt.from_data({**build().to_data(), 'version': 9})


def test_deck_end_and_known_sixth_copy():
    with pytest.raises(ValueError):
        stand(build(), empty_deck=True)
    a = declare_draw(select(build(), 'B'))
    assert stand(a, empty_deck=True).phase == 'roll'
    a = replace(build(), values=(1,1,1,1,1))
    a = declare_draw(select(a, 'BBBBB'))
    with pytest.raises(ValueError):
        choose_color(a, 'B')


def test_all_prepared_lessons_reach_their_authored_outcome():
    scenes, lessons = content()
    assert all(len(s.options) >= 3 for s in scenes)
    for lesson in lessons:
        if lesson.open_after_preparation:
            continue  # Branching condition lessons have their own transition tests.
        if not lesson.choices:
            continue
        method = 'inspiration' if lesson.kind == 'npc' else 'survey'
        a = replace(build(method, lesson.obstacle), values=profile_values(lesson.profile))
        a = select(a, lesson.choices)
        if lesson.finish in {'stand','reroll'}:
            a = stand(a)
        if lesson.finish == 'exact':
            assert a.success
        elif lesson.finish == 'bust':
            assert a.busted
        else:
            assert a.phase == 'roll'
