import pytest

from tests.unit.test_training_walkthrough import prepared
from tests.unit.test_shared_mana_runtime import send
from dnd_board_game.ui.training_tutorial import acknowledge, notice_id
from dnd_board_game.ui import training_walkthrough as guided
from dnd_board_game.application.training_walkthrough import steps
from dnd_board_game.application.recruitment_arena import HERO_ORDER
from dnd_board_game.ui.pooled_mana_training import prepared_hand
from dnd_board_game.scenarios.pooled_mana_catalog import hero_profile, pool_ability
from dnd_board_game.rules.pooled_mana import deck_copies


def activate(tmp_path, hero, lesson):
    index = next(i for i, step in enumerate(steps(hero)) if step.id == lesson)
    s = prepared(tmp_path, hero, index)
    acknowledge(s, notice_id(s))
    send(s, "pool_shuffle")
    pool = s.combat_state.shared_mana.pooled
    while pool.phase == "reveal":
        send(s, "pool_color", color=pool.deck[0] or next(c for c in ('C', 'B', 'Z', 'F', 'N') if sum(card == c for card in (*pool.deck, *pool.offer, *pool.burned, *(card for _, hand in pool.pools for card in hand))) < pool.copies))
        pool = s.combat_state.shared_mana.pooled
    return s


@pytest.mark.parametrize("hero", HERO_ORDER)
def test_every_hero_has_valid_prepared_pool_for_every_ability_and_boost(hero):
    for step in steps(hero):
        if step.ability.category == "tutorial":
            continue
        hand = prepared_hand(hero, step.ability.id, step.boost_id, deck_copies(1))
        pool_ability(step.ability.id, hero).validate(hand, hero_profile(hero)["values"])
        assert not pool_ability(step.ability.id, hero).required


@pytest.mark.parametrize("lesson", ["pool_draw", "pool_burn", "pool_prison", "pool_drain"])
def test_foundations_perform_real_operations_and_complete(tmp_path, lesson):
    s = activate(tmp_path, "garran", lesson)
    send(s, "pool_take", index=0)
    if lesson != "pool_draw":
        send(s, "pool_lesson_attack")
    if lesson == "pool_prison":
        assert s.combat_state.shared_mana.pooled.prisons
        send(s, "pool_lesson_release")
    if lesson == "pool_drain":
        assert s.combat_state.shared_mana.pooled.phase == "drain"
        send(s, "pool_shuffle")
        assert not s.combat_state.shared_mana.pooled.burned
    assert guided.flag(s, "phase") == "success"


def test_prepared_second_wind_can_be_paid_and_really_heals(tmp_path):
    s = activate(tmp_path, "garran", "second_wind")
    before = next(a.hp for a in s.combat_state.actors if a.id == "garran")
    s.use_combat_class_feature("second_wind", natural_roll=5)
    send(s, "pay")
    assert next(a.hp for a in s.combat_state.actors if a.id == "garran") > before
    assert guided.flag(s, "phase") == "exercise"
    send(s, "pool_color", color="Z")
    assert guided.flag(s, "phase") == "success"


@pytest.mark.parametrize("hero", HERO_ORDER)
def test_free_weapon_attack_completes_saving_lesson_and_keeps_pool(tmp_path, hero):
    from dnd_board_game.combat import current_actor
    s = activate(tmp_path, hero, "pool_hold")
    send(s, "pool_take", index=0)
    hand = s.combat_state.shared_mana.pooled.hand(hero)
    source = s._panel_basic_attack_source_id(current_actor(s.combat_state))
    assert source
    s.select_combat_attack_source(source)
    enemy = s._actor_by_string_id("recruitment_dummy")
    s.select_player_attack_target_at_position(enemy.position)
    s.confirm_player_attack_target()
    s.submit_player_attack_roll(natural_roll=1, natural_roll_2=1, natural_rerolls=(1,) if hero == "mira" else ())
    assert s.shared_mana_declaration is None
    assert s.combat_state.shared_mana.pooled.hand(hero) == hand
    assert guided.flag(s, "phase") == "success"


@pytest.mark.parametrize("hero", HERO_ORDER)
@pytest.mark.parametrize("lesson", ["pool_charge", "pool_expire"])
def test_charge_and_expiry_lessons_use_runes_and_finish(tmp_path, hero, lesson):
    s = activate(tmp_path, hero, lesson)
    send(s, "pool_take", index=0)
    send(s, "pool_lesson_attack")
    if lesson == "pool_expire":
        assert s.combat_state.shared_mana.pooled.phase == "expire"
        send(s, "pool_color", color="Z")
    else:
        assert s.combat_state.shared_mana.pooled.points(hero) >= 21
        assert not s.combat_state.shared_mana.pooled.draw_due
    assert guided.flag(s, "phase") == "success"
