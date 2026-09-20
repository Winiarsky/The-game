from dataclasses import replace

import pytest

from tests.unit.test_hero_rules_consistency import heroes
from tests.unit.test_physical_mana import session_for
from dnd_board_game.ui.shared_mana import command, payload
from dnd_board_game.ui.pooled_mana import scan_target, select_position
from dnd_board_game.hardware.board_panel import panel_position


def send(s, action, **data):
    return command(s, dict(command=action, revision=s.combat_state.shared_mana.revision, **data))


def prepare(s, first="C", second="B"):
    send(s, "pool_shuffle")
    send(s, "pool_color", color=first)
    send(s, "pool_color", color=second)
    send(s, "pool_take", index=0)


def test_setup_pick_free_stance_preserves_pool_and_runs_real_effect(heroes, tmp_path):
    s = session_for(heroes["garran"], tmp_path, pooled=True)
    assert s.combat_state.shared_mana.pooled.phase == "setup"
    prepare(s, "B", "C")
    s.use_combat_class_feature("defensive_stance")
    result = send(s, "pay")
    assert s.combat_state.shared_mana.pooled.hand("garran") == ("B",)
    assert any(e.kind == "garran_defensive_stance_ac" and e.duration.value == "until_deck_refresh" for e in s.active_combat_effects)


def test_charge_healing_retains_pool_and_burns_deck(heroes, tmp_path):
    s = session_for(heroes["garran"], tmp_path, pooled=True)
    prepare(s, "B", "C")
    s.use_combat_class_feature("second_wind", natural_roll=5)
    assert not payload(s)["declaration"]["error"]
    send(s, "pay")
    assert s.combat_state.shared_mana.pooled.hand("garran") == ("B",)
    assert s.combat_state.shared_mana.pooled.phase == "burn"
    send(s, "pool_color", color="Z")
    assert s.combat_state.shared_mana.pooled.burned == ("Z",)


def test_board_runes_drive_full_draw_and_old_revision_rejected(heroes, tmp_path):
    s = session_for(heroes["brakka"], tmp_path, pooled=True)
    old = s.combat_state.shared_mana.revision
    select_position(s, panel_position(28))
    assert panel_position(6) in scan_target(s).positions
    select_position(s, panel_position(6))
    select_position(s, panel_position(7))
    select_position(s, panel_position(24))
    assert s.combat_state.shared_mana.pooled.hand("brakka") == ("C",)
    with pytest.raises(ValueError):
        command(s, dict(command="pool_take", index=0, revision=old))


def test_lorian_tunes_after_free_activation(heroes, tmp_path):
    s = session_for(heroes["lorian"], tmp_path, pooled=True)
    prepare(s)
    s.use_combat_class_feature("mana_tuning")
    send(s, "pay")
    assert s.shared_mana_declaration.stage == "cards"
    with pytest.raises(ValueError):
        send(s, "cards_done")
    send(s, "pool_color", color="N")
    send(s, "pool_color", color="Z")
    send(s, "pool_bard_done")
    assert s.combat_state.shared_mana.pooled.deck[:2] == ("N", "Z")
    assert s.shared_mana_declaration is None


@pytest.mark.parametrize("phase", ["choose", "ready", "burn", "drain"])
def test_real_snapshot_preserves_card_zones_and_pending_draw(heroes, tmp_path, phase):
    from dnd_board_game.rules.pooled_mana import attack_mana, drain
    from dnd_board_game.rules.shared_mana import sync_pool
    s = session_for(heroes["garran"], tmp_path, pooled=True)
    send(s, "pool_shuffle")
    send(s, "pool_color", color="C")
    send(s, "pool_color", color="B")
    if phase != "choose":
        send(s, "pool_take", index=0)
    mana = s.combat_state.shared_mana
    if phase == "burn":
        mana = sync_pool(mana, attack_mana(mana.pooled, "deck", 2))
    elif phase == "drain":
        mana = sync_pool(mana, drain(mana.pooled, "Test odtworzenia kompletu"))
    s.combat_state = replace(s.combat_state, shared_mana=mana)
    before = mana.pooled
    s.save_snapshot()
    s.load_snapshot()
    assert s.combat_state.shared_mana.pooled == before


def test_spiritual_weapon_activation_is_free_and_cannot_spend_boosts(heroes, tmp_path):
    from dnd_board_game.scenarios.pooled_mana_catalog import pool_ability
    definition = pool_ability("spiritual_weapon_activation", "dagna")
    assert definition.free
    assert pool_ability("spiritual_weapon", "dagna").minimum > 0



def test_dagna_healing_requires_actual_charge_before_payment(heroes, tmp_path):
    from dnd_board_game.combat import current_actor
    from dnd_board_game.rules.shared_mana import sync_pool
    from dnd_board_game.world import Coordinate
    s = session_for(heroes['dagna'], tmp_path, pooled=True)
    prepare(s)
    actor = current_actor(s.combat_state)
    ally = replace(heroes['garran'], id='ally', hp=5, position=Coordinate(actor.position.col, actor.position.row + 1))
    mana = s.combat_state.shared_mana
    # Three white cards unlock the ultimate, independent of its target.
    pool = replace(mana.pooled, deck=(None,) * 21, pools=(('dagna', ('B', 'B', 'B')),))
    s.combat_state = replace(s.combat_state, actors=(*s.combat_state.actors, ally), shared_mana=sync_pool(mana, pool))
    s.use_combat_class_feature('preserve_life', allocations=(('ally', 5),))
    assert not payload(s)['declaration']['error']
    send(s, 'pay')
    assert s._actor_by_string_id('ally').hp == 10
    assert s.combat_state.shared_mana.pooled.hand('dagna') == ('B', 'B', 'B')


def test_action_menu_shows_card_points_and_base_threshold_after_spending(heroes, tmp_path):
    from dnd_board_game.ui.combat_menu_mana import menu_mana_payload
    s = session_for(heroes['garran'], tmp_path, pooled=True)
    prepare(s, 'B', 'C')
    option = next(o for o in s._combat_turn_action_options() if (o.action_id or o.source_id) == 'second_wind')
    note = menu_mana_payload(option, s.combat_state, s.active_combat_effects)['mana_cost_note']
    assert 'Ładunek: 2/6' in note and 'Ładunek co najmniej 2/6' in note
    s.use_combat_class_feature('second_wind')
    send(s, 'pay')
    note = menu_mana_payload(option, s.combat_state, s.active_combat_effects)['mana_cost_note']
    assert 'Ładunek: 2/6' in note
