"""Live mission command/board boundary and save/load: no physical mana in conversations."""
from dataclasses import replace

import pytest

from dnd_board_game.application import reputation
from dnd_board_game.hardware.board_panel import panel_position
from dnd_board_game.ui import confrontation as adapter, mission_zero as mission
from dnd_board_game.ui.exploration_mana_board import select_position, scan_target
from tests.unit.test_mission_zero import session, stage, send


def command(s,action,**extra):
    return adapter.command(s,dict(action=action,revision=adapter.read_store(s)["revision"],**extra))


def start(s,scene="nessa"):
    stage(s,"brief" if scene=="nessa" else "road")
    send(s,"negotiate" if scene=="nessa" else "cart")
    command(s,"acknowledge")


def attempt(s,natural=10):
    p=adapter.payload(s)
    choice=next(c for c in p["board_choices"] if c["action"]=="approach")
    select_position(s,panel_position(choice["slot"]))
    command(s,"roll",rolls=[natural])


def test_new_mission_uses_immediate_check_and_three_reputation_runes(tmp_path):
    s=session(tmp_path);start(s)
    p=adapter.payload(s)
    assert p["engine"]=="progress_v1" and p["mana"]=={} and p["progress"]==0
    assert p["approaches"][0]["slot"]==5
    attempt(s)
    p=adapter.payload(s)
    assert p["phase"]=="summary"
    assert [(c["slot"],c["extra"]["option"]) for c in p["board_choices"] if c["action"]=="reputation"]==[(5,"plus_one"),(6,"plus_five"),(7,"extra_die")]
    assert all(panel_position(i) in scan_target(s).positions for i in (5,6,7,28,29))
    revision=p["revision"]
    select_position(s,panel_position(6))
    assert reputation.read(s.state.flags).points==20
    select_position(s,panel_position(28))
    assert reputation.read(s.state.flags).points==17
    with pytest.raises(ValueError):adapter.command(s,dict(action="confirm",revision=revision))
    assert reputation.read(s.state.flags).points==17


def test_paid_extra_die_survives_actual_snapshot_and_never_refunds(tmp_path):
    s=session(tmp_path);start(s);attempt(s,1)
    command(s,"reputation",option="extra_die");command(s,"confirm")
    assert reputation.read(s.state.flags).points==15
    assert s.snapshot_path.exists()
    s._load_snapshot_from_path(s.snapshot_path)
    assert adapter.payload(s)["phase"]=="extra_check"
    assert adapter.payload(s)["reputation"]["paid"]==5
    with pytest.raises(ValueError):command(s,"cancel")
    with pytest.raises(ValueError):command(s,"leave")
    command(s,"roll",rolls=[20]);command(s,"confirm")
    assert reputation.read(s.state.flags).points==15
    assert adapter.payload(s)["progress"]==2


def test_physical_cart_has_no_reputation_bonus_and_exchange_can_cancel(tmp_path):
    s=session(tmp_path);start(s,"cart")
    command(s,"cart_preview")
    assert adapter.payload(s)["phase"]=="cart_preview"
    command(s,"cart_cancel")
    assert reputation.read(s.state.flags).points==20
    attempt(s,10)
    assert not any(c["action"]=="reputation" for c in adapter.payload(s)["board_choices"])
    with pytest.raises(ValueError):command(s,"reputation",option="plus_five")
    command(s,"confirm");command(s,"advance")
    command(s,"cart_preview");command(s,"cart_exchange")
    assert reputation.read(s.state.flags).points==17
    assert mission.read(s)["fatigue"]==0 and not adapter.active(s)
    assert "cart_exchanged" in mission.read(s)["flags"]


def test_cart_preview_in_mission_checks_live_threshold_before_charge(tmp_path):
    s=session(tmp_path);stage(s,"road")
    send(s,"cart_coerce")
    assert mission.read(s)["stage"]=="cart_exchange_preview"
    assert reputation.read(s.state.flags).points==20
    send(s,"cart_exchange_cancel")
    assert mission.read(s)["stage"]=="road"
    send(s,"cart_coerce")
    s.state=replace(s.state,flags=reputation.apply(s.state.flags,"spent",-1))
    with pytest.raises(ValueError):send(s,"cart_exchange_confirm")
    assert reputation.read(s.state.flags).points==19
    send(s,"cart_exchange_cancel")
    assert not any(c["action"]=="cart_coerce" for c in mission.payload(s)["choices"])


def test_three_hero_round_ends_with_no_new_draw_and_reward_once(tmp_path):
    s=session(tmp_path);start(s)
    for index in range(3):
        attempt(s,14 if index==0 else 2);command(s,"confirm")
        if index<2:command(s,"advance")
    assert adapter.payload(s)["phase"]=="result"
    # Exact chosen abilities vary; at least the first roll succeeds at ST 14.
    assert adapter.payload(s)["outcome"]=="compromise"
    command(s,"next")
    assert sum(i.id=="mission_weak_potion" for i in s.state.party_loot.items)==1
    with pytest.raises(ValueError):command(s,"next")
    stage(s,"summary");send(s,"finish")
    assert reputation.read(s.state.flags).points==25
    send(s,"finish")
    assert reputation.read(s.state.flags).points==25
    s._load_snapshot_from_path(s.snapshot_path)
    assert reputation.read(s.state.flags).points==25


def test_worsened_cart_adds_one_fatigue_round_and_preserves_morality(tmp_path):
    s=session(tmp_path);start(s,"cart")
    attempt(s,1);command(s,"confirm");command(s,"advance")
    attempt(s,1);command(s,"confirm")
    assert adapter.payload(s)["tier"]=="worsened"
    command(s,"next");send(s,"roll",roll=4)
    assert mission.read(s)["fatigue"]==5
