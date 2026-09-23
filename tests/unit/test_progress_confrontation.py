"""Finite progress, mutually exclusive post-roll boosts and persisted campaign costs."""
from dataclasses import replace
import json

import pytest

from dnd_board_game.application import reputation as campaign
from dnd_board_game.combat.scene import SceneFlags
from dnd_board_game.rules import progress_confrontation as rules
from dnd_board_game.rules.reputation import Reputation, change


def game(count=4, *, social=True):
    return rules.begin(rules.Confrontation(tuple(rules.Participant(str(i), f"Hero{i}", (
        rules.Approach("arguments", "Argumenty", "Opis", "Inteligencja", 0),
        rules.Approach("guarantee", "Gwarancja", "Opis", "Charyzma", 2, repeatable=False),
    )) for i in range(count)), social))


def rolled(value, **kwargs):
    return rules.roll(rules.choose(game(**kwargs), "arguments"), value)


@pytest.mark.parametrize("natural,delta,critical", [(1,-1,"failure"),(2,0,""),(13,0,""),(14,1,""),(20,2,"success")])
def test_one_check_alone_resolves_progress(natural,delta,critical):
    state,cost=rules.confirm(rolled(natural),20)
    assert state.stage=="after_action" and state.progress==delta and cost==0
    assert state.last_critical==critical
    with pytest.raises(ValueError):rules.confirm(state,20)


def test_exclusive_boost_selection_toggle_and_cost_only_at_confirmation():
    state=rolled(10)
    state=rules.select_boost(state,"plus_one",20)
    assert rules.preview(state)["total"]==11
    state=rules.select_boost(state,"plus_five",20)
    assert rules.preview(state)["total"]==15
    state=rules.select_boost(state,"plus_five",20)
    assert state.boost==""
    state=rules.select_boost(state,"plus_five",20)
    assert rules.cancel(state).boost==""
    confirmed,cost=rules.confirm(state,20)
    assert cost==3 and confirmed.progress==1
    with pytest.raises(ValueError):rules.confirm(state,2)


def test_extra_die_paid_before_roll_cannot_refund_or_stack_and_roundtrips():
    state=rules.select_boost(rolled(1),"extra_die",20)
    state,cost=rules.confirm(state,20)
    assert cost==5 and state.stage=="extra_check" and state.progress==0
    state=rules.Confrontation.from_data(json.loads(json.dumps(state.to_data())))
    assert state.paid==5
    with pytest.raises(ValueError):rules.cancel(state)
    with pytest.raises(ValueError):rules.select_boost(state,"plus_one",15)
    state=rules.roll(state,20)
    assert rules.preview(state)["natural"]==20
    with pytest.raises(ValueError):rules.cancel(state)
    state,cost=rules.confirm(state,15)
    assert cost==0 and state.progress==2 and not state.natural_one_seen


def test_lower_extra_roll_still_costs_five_and_preserves_original_natural():
    state=rules.select_boost(rolled(12),"extra_die",5)
    state,cost=rules.confirm(state,5)
    state=rules.roll(state,1)
    state,secondcost=rules.confirm(state,0)
    assert (cost,secondcost,state.last_roll,state.last_impact)==(5,0,12,0)


@pytest.mark.parametrize("natural,available",[(1,("extra_die",)),(20,()),(10,("plus_one","plus_five","extra_die"))])
def test_natural_criticals_and_affordability_gate_boosts(natural,available):
    assert rules.available_boosts(rolled(natural),20)==available
    assert rules.available_boosts(rolled(10),2)==("plus_one",)
    assert rules.available_boosts(rolled(10),0)==()


def test_physical_test_rejects_reputation_and_preserves_first_bonus_on_cancel():
    state=replace(game(social=False),first_test_bonus=2)
    state=rules.choose(state,"arguments")
    assert state.check_modifier==2
    state=rules.cancel(state)
    assert state.first_test_bonus==2
    state=rules.roll(rules.choose(state,"arguments"),12)
    assert not rules.available_boosts(state,20)
    with pytest.raises(ValueError):rules.select_boost(state,"plus_five",20)
    state,cost=rules.confirm(state,20)
    assert state.progress==1 and state.first_test_bonus==0 and cost==0


@pytest.mark.parametrize("count",[3,4,5,6])
def test_one_round_and_party_scaled_maximum(count):
    state=game(count)
    for i in range(count):
        assert state.actor.id==str(i)
        state=rules.pass_turn(state)
        if i<count-1:state=rules.advance(state)
    assert state.stage=="result" and state.outcome=="failure" and state.tier=="unchanged"
    assert state.maximum==count and len(state.choices)==count
    with pytest.raises(ValueError):rules.advance(state)
    state=replace(game(count),progress=count-1)
    state,_=rules.confirm(rules.roll(rules.choose(state,"arguments"),20),20)
    assert state.stage=="result" and state.progress==count and state.tier=="full"


def test_second_critical_failure_at_minus_one_ends_early():
    state,_=rules.confirm(rolled(1),20)
    assert state.stage=="after_action" and state.progress==-1
    state=rules.advance(state)
    state,_=rules.confirm(rules.roll(rules.choose(state,"arguments"),1),20)
    assert state.stage=="result" and state.progress==-1 and state.tier=="worsened"
    assert len(state.choices)==2


def test_exclusive_approach_consumed_after_resolution_repeatable_remains():
    state=rules.choose(game(),"guarantee")
    assert rules.cancel(state).choices==()
    state,_=rules.confirm(rules.roll(state,10),20)
    state=rules.advance(state)
    assert [a.id for a in rules.available_approaches(state)]==["arguments"]
    with pytest.raises(ValueError):rules.choose(state,"guarantee")


@pytest.mark.parametrize("value",[0,21,True,10.5,"10"])
def test_invalid_roll_is_rejected_without_advancing(value):
    state=rules.choose(game(),"arguments")
    with pytest.raises(ValueError):rules.roll(state,value)
    assert state.stage=="check"


def test_campaign_shared_balance_threshold_idempotency_and_serialization():
    flags=campaign.initialize(SceneFlags())
    assert campaign.read(flags).points==20
    flags=campaign.apply(flags,"cart",-3,minimum=20)
    assert campaign.read(flags).points==17
    assert campaign.apply(flags,"cart",-3,minimum=20)==flags
    with pytest.raises(ValueError):campaign.apply(flags,"another_cart",-3,minimum=20)
    flags=campaign.apply(flags,"mission",5)
    assert campaign.read(flags).points==22
    assert campaign.apply(flags,"mission",5)==flags
    with pytest.raises(ValueError):change(Reputation(),"huge",-21)
    with pytest.raises(ValueError):change(Reputation(),"bad",True)
