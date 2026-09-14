"""Guided lessons use real payment/action boundaries and retain board contracts."""
from dataclasses import replace
from pathlib import Path

import pytest

from dnd_board_game.application.recruitment_arena import HERO_ORDER
from dnd_board_game.application.training_walkthrough import steps
from dnd_board_game.actors import Faction
from dnd_board_game.combat import current_actor, replace_actor
from dnd_board_game.ui import training_walkthrough as guided
from dnd_board_game.ui.training_tutorial import acknowledge, notice_id
from dnd_board_game.ui.routes import create_app
from dnd_board_game.ui.exploration_app import ExplorationUiSession
from tests.unit.test_recruitment_arena import arena
from tests.unit.test_shared_mana_runtime import send


def prepared(tmp_path: Path, hero: str = 'garran', index: int = 0) -> ExplorationUiSession:
    s = arena(tmp_path)
    guided.launch(s, hero, index)
    assert guided.flag(s, 'phase') == 'introduction'
    acknowledge(s, notice_id(s))
    for _ in range(30):
        if s.encounter_setup_flow.completed:
            break
        s.confirm_encounter_setup_step()
    assert s.encounter_setup_flow.completed
    assert notice_id(s)
    return s


def test_first_lesson_is_real_second_wind_with_board_confirmation(tmp_path: Path) -> None:
    s = prepared(tmp_path)
    assert current_actor(s.combat_state).id == 'garran'
    hero = current_actor(s.combat_state)
    assert hero.hp < hero.max_hp
    state = s.state_payload()
    assert state['board_selection']['legal_positions'] == [[19, 1]]
    assert state['training_arena']['tutorial']['current']['id'] == 'second_wind'
    acknowledge(s, notice_id(s))
    menu = s._combat_turn_action_options()
    assert menu and all(o.action_id == 'second_wind' or o.source_id == 'second_wind' for o in menu)
    s.use_combat_class_feature('second_wind', natural_roll=5)
    assert guided.flag(s, 'phase') == 'exercise'
    send(s, 'pay')
    assert current_actor(s.combat_state).hp > hero.hp
    assert guided.flag(s, 'phase') == 'success'
    old_token = notice_id(s)
    acknowledge(s, old_token)
    assert guided.current_step(s).id == 'shield_bash'
    assert s.combat_state is None
    assert not any('Nessa' in step.label for step in s.encounter_setup_flow.steps)
    with pytest.raises(ValueError):
        acknowledge(s, old_token)


def test_defensive_stance_rune_preview_then_blue_payment_and_next_lesson(tmp_path: Path) -> None:
    from dnd_board_game.hardware.led_palette import LedColor
    from tests.unit.test_initiative_panel import Board

    index = next(i for i, step in enumerate(steps('garran')) if step.id == 'defensive_stance')
    s = prepared(tmp_path, index=index)
    acknowledge(s, notice_id(s))
    board = Board()
    s.attach_board_connection(board, backend='simulator')
    client = create_app(s).test_client()

    def scan(position: tuple[int, int]) -> dict[str, object]:
        board.selected = position
        response = client.post('/api/board/scan', json={
            'revision': s._board_selection_payload()['revision'], 'automatic': True,
        })
        assert response.status_code == 200, response.json
        return response.json

    before = s.combat_state
    for _ in range(3):
        state = scan((19, 20))
        assert 'Naciśnij niebieskie ✓' in state['training_arena']['tutorial']['current']['instruction']
        assert state['combat']['turn_action_menu']['stage'] == 'preview'
        assert board.leds[(19, 1)] == LedColor.PANEL_ACCEPT
        assert s.combat_state == before
        assert s.shared_mana_declaration is None
    event = scan((19, 1))
    assert event['panel_event'] == {'slot': 28, 'context': None}
    # The browser dispatches ordinary preview confirmation to this endpoint.
    response = client.post('/api/combat/turn-actions/confirm', json={})
    assert response.status_code == 200, response.json
    assert 'Odłóż pokazany koszt' in response.json['training_arena']['tutorial']['current']['instruction']
    assert s.shared_mana_declaration.stage == 'payment'
    assert guided.flag(s, 'phase') == 'exercise'
    state = scan((19, 1))
    assert state['training_arena']['tutorial']['phase'] == 'success'
    assert s.shared_mana_declaration is None
    scan((19, 1))
    assert guided.flag(s, 'phase') == 'introduction'
    assert guided.current_step(s).id == steps('garran')[index + 1].id


@pytest.mark.parametrize('hero', HERO_ORDER)
def test_all_abilities_and_each_boost_have_ordered_steps(hero: str) -> None:
    from dnd_board_game.ui.training_tutorial import abilities
    course = steps(hero)
    assert len({s.id for s in course}) == len(course)
    assert {s.ability.id for s in course} == {a.id for a in abilities(hero)}
    for a in abilities(hero):
        variants = [s for s in course if s.ability.id == a.id]
        assert variants[0].boosts == {}
        assert [s.boost_id for s in variants[1:]] == [b.id for b in a.boosts]
        for step in variants:
            assert len(a.payment(step.boosts)) <= 5


def test_final_is_normal_duel_and_does_not_count_before_victory(tmp_path: Path) -> None:
    s = prepared(tmp_path, 'garran', len(steps('garran')))
    assert s.combat_state is None
    encounter = s.encounter_setup_flow.encounter
    assert len(encounter.actors) == 2
    dummy = next(a for a in encounter.actors if a.faction == Faction.ENEMY)
    assert (dummy.hp, dummy.ac) == (30, 13)
    source = encounter.attack_sources_by_actor[dummy.id]
    assert sum(m.value for m in source.attack_roll_request.modifiers) == 3
    assert source.damage_components[0].dice.count == 1
    assert source.damage_components[0].dice.sides == 6
    assert not encounter.objectives
    assert not any(o.id == 'recruitment_nessa' for o in encounter.scene_objects)
    acknowledge(s, notice_id(s))
    assert guided.flag(s, 'phase') == 'final'
    assert s.encounter_initiative_flow.current_prompt is not None
    assert 'garran' not in s.state_payload()['training_arena']['completed']


@pytest.mark.parametrize('hero', HERO_ORDER)
def test_each_lesson_has_available_required_action(tmp_path: Path, hero: str) -> None:
    for index, step in enumerate(steps(hero)):
        s = prepared(tmp_path / str(index), hero, index)
        assert len({a.position for a in s.combat_state.actors}) == len(s.combat_state.actors), step.id
        assert not any(e.id == 'recruitment_nessa' for e in s._active_encounter().environment)
        acknowledge(s, notice_id(s))
        if step.ability.timing == 'R':
            assert s.pending_enemy_turn_intent or s.pending_enemy_turn_result or s.pending_reaction_window, step.id
            continue
        menu = s._combat_turn_action_options()
        assert menu, step.id
        reasons = [s._combat_turn_option_unavailable_reason(o) for o in menu]
        assert any(reason is None for reason in reasons), (step.id, reasons)


def test_boost_is_required_before_payment_and_not_awarded_for_cancel(tmp_path: Path) -> None:
    index = next(i for i, step in enumerate(steps('garran')) if step.id == 'shield_bash:damage')
    s = prepared(tmp_path, 'garran', index)
    acknowledge(s, notice_id(s))
    assert guided.payment_error(s, 'shield_bash', {})
    assert guided.payment_error(s, 'shield_bash', {'damage': 2})
    assert guided.payment_error(s, 'defensive_stance', {})
    assert not guided.payment_error(s, 'shield_bash', {'damage': 1})
    guided.record_ability(s, 'shield_bash', 'garran')
    assert guided.flag(s, 'phase') == 'exercise'


@pytest.mark.parametrize('hero,ability', [('garran','garran_guard_companion'), ('brakka','hard_as_rock'),
    ('mira','instinctive_dodge'), ('lorian','cutting_words'), ('nimra','shield')])
def test_reaction_situation_really_offers_required_reaction(tmp_path: Path, hero: str, ability: str) -> None:
    index = next(i for i, step in enumerate(steps(hero)) if step.ability.id == ability)
    s = prepared(tmp_path, hero, index)
    acknowledge(s, notice_id(s))
    if ability not in {'garran_guard_companion', 'instinctive_dodge'}:
        s._commit_pending_enemy_turn()
    option = s.pending_reaction_window.current_option.effect_id if s.pending_reaction_window and s.pending_reaction_window.current_option else ''
    declaration = s.shared_mana_declaration.ability_id if s.shared_mana_declaration else ''
    assert ability in (option, declaration, s.pending_physical_feature_action_id), (ability, option, declaration, s.board_message)
    if ability == 'hard_as_rock':
        s._resolve_hard_as_rock_reaction(4)
    elif ability == 'cutting_words':
        s.resolve_cutting_words_reaction(die_roll=4)
    elif ability == 'shield':
        s.cast_defensive_spell_reaction()
    elif ability == 'instinctive_dodge':
        s.use_instinctive_dodge_reaction()
    send(s, 'pay')
    assert guided.flag(s, 'phase') == 'success'
    assert notice_id(s) == ''
    if s.pending_enemy_turn_result:
        s._commit_pending_enemy_turn()
    if s.pending_enemy_turn_ack_result:
        s.confirm_enemy_turn_result()
    assert notice_id(s)
    assert s.state_payload()['board_selection']['legal_positions'] == [[19, 1]]


def test_progress_and_briefing_survive_save_and_leave(tmp_path: Path) -> None:
    s = prepared(tmp_path)
    original = notice_id(s)
    s.save_snapshot()
    s.load_snapshot()
    assert notice_id(s) == original
    assert s.state_payload()['board_selection']['legal_positions'] == [[19, 1]]
    acknowledge(s, original)
    s.use_combat_class_feature('second_wind', natural_roll=6)
    send(s, 'pay')
    guided.leave(s)
    assert s.state_payload()['training_arena']['can_start']
    guided.start(s, 'garran')
    assert guided.current_step(s).id == 'shield_bash'


@pytest.mark.parametrize('won', [True, False])
def test_duel_result_returns_to_roster_and_only_victory_completes(tmp_path: Path, won: bool) -> None:
    s = prepared(tmp_path, 'garran', len(steps('garran')))
    acknowledge(s, notice_id(s))
    s.submit_encounter_initiative_roll(20)
    assert s.combat_state.shared_mana.market == 5
    assert s.combat_state.shared_mana.deck == 20
    victim = next(a for a in s.combat_state.actors if (a.faction == Faction.ENEMY) == won)
    s.combat_state = replace_actor(s.combat_state, replace(victim, hp=0))
    state = s.state_payload()
    assert state['training_arena']['tutorial']['notice']['phase'] == 'final_result'
    acknowledge(s, notice_id(s))
    state = s.state_payload()
    assert state['training_arena']['can_start']
    assert ('garran' in state['training_arena']['completed']) == won


@pytest.mark.parametrize('boosted,hit', [(False, False), (False, True), (True, True)])
def test_shield_lesson_requires_real_push_and_correct_boost(tmp_path: Path, boosted: bool, hit: bool) -> None:
    from dnd_board_game.ui.shield_bash import submit_shield_bash, confirm_shield_bash
    index = next(i for i, step in enumerate(steps('garran')) if step.id == ('shield_bash:damage' if boosted else 'shield_bash'))
    s = prepared(tmp_path, 'garran', index)
    acknowledge(s, notice_id(s))
    enemy = s._actor_by_string_id('recruitment_dummy')
    s.start_combat_class_feature_targeting('shield_bash')
    s._handle_board_position(enemy.position)
    s.confirm_combat_class_feature_targeting()
    if boosted:
        market = s.combat_state.shared_mana.market
        with pytest.raises(ValueError, match='podbicia'):
            send(s, 'pay')
        assert s.combat_state.shared_mana.market == market
        send(s, 'boost', boost_id='damage', count=1)
    send(s, 'pay')
    assert guided.flag(s, 'phase') == 'exercise'
    s.encounter_rng.seed(1)
    submit_shield_bash(s, {'attacker_roll': 20 if hit else 1})
    if hit:
        submit_shield_bash(s, {'damage_roll': 12 if boosted else 6})
    confirm_shield_bash(s)
    assert guided.flag(s, 'phase') == ('success' if hit else 'retry')
    if hit:
        assert s._actor_by_string_id('recruitment_dummy').position != enemy.position
    else:
        token = notice_id(s)
        acknowledge(s, token)
        assert guided.current_step(s).id == 'shield_bash'
        assert guided.flag(s, 'phase') == 'introduction'


def test_http_start_defaults_to_guided_mode_and_rejects_early_action(tmp_path: Path) -> None:
    s = arena(tmp_path)
    client = create_app(s).test_client()
    response = client.post('/api/training/start', json={'hero_id': 'garran'})
    assert response.status_code == 200
    assert response.json['training_arena']['mode'] == 'walkthrough'
    assert response.json['training_arena']['tutorial']['notice']['phase'] == 'introduction'
    acknowledge(s, notice_id(s))
    while not s.encounter_setup_flow.completed:
        s.confirm_encounter_setup_step()
    with pytest.raises(ValueError, match='objaśnienie'):
        s.use_combat_class_feature('second_wind', natural_roll=6)
    assert s.state_payload()['training_arena']['tutorial']['notice']


def test_lorian_solo_shared_mana_does_not_use_legacy_audience_lock(tmp_path: Path) -> None:
    from dnd_board_game.combat.lorian_features import require_lorian_audience
    from dnd_board_game.ui.training_arena import training_hero
    hero = training_hero('lorian')
    for action in ('optical_scope', 'mocking_shot', 'entangling_shot', 'cutting_words'):
        require_lorian_audience(hero, (hero,), action)


def test_saved_final_briefing_rebuilds_figurine_setup(tmp_path: Path) -> None:
    s = prepared(tmp_path, 'mira', len(steps('mira')))
    s.save_snapshot()
    s.load_snapshot()
    assert s.encounter_setup_flow is not None
    assert not s.encounter_setup_flow.completed
    assert guided.current_step(s) is None
    assert guided.flag(s, 'phase') == 'setup'


def test_victory_on_last_mana_card_does_not_require_another_turn(tmp_path: Path) -> None:
    from dnd_board_game.rules.shared_mana import SharedMana, ManaPhase
    s = prepared(tmp_path, 'garran', len(steps('garran')))
    acknowledge(s, notice_id(s))
    s.submit_encounter_initiative_roll(20)
    dummy = s._actor_by_string_id('recruitment_dummy')
    s.combat_state = replace_actor(s.combat_state, replace(dummy, hp=0))
    s.combat_state = replace(s.combat_state, shared_mana=SharedMana(deck=0, market=0, discard=25, phase=ManaPhase.REFRESH))
    state = s.state_payload()
    token = state['training_arena']['tutorial']['notice']['id']
    assert s.state_payload()['training_arena']['tutorial']['notice']['id'] == token
    acknowledge(s, token)
    assert s.state_payload()['training_arena']['completed'] == ['garran']
