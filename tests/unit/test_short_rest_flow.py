from dataclasses import replace

import pytest

from dnd_board_game.actors import ActorTrigger, TriggerEffectKind, TriggerEventType
from dnd_board_game.application import ShortRestFlowService
from dnd_board_game.exploration import ExplorationState, challenge_state_for
from dnd_board_game.scenarios import build_exploration_from_scenario, load_scenario
from dnd_board_game.rules import (
    ActiveEffect,
    EffectDuration,
    EffectSource,
    EffectSourceType,
)


def _loaded():
    return build_exploration_from_scenario(
        load_scenario("content/scenarios/abandoned_watchtower.json")
    )


def _state(exploration) -> ExplorationState:
    return ExplorationState(
        exploration.zones,
        exploration.points,
        exploration.party_position,
        challenges=exploration.challenges,
        resources=exploration.resources,
        inventory_resource_ids=exploration.initial_resource_ids,
    )


def test_short_rest_preview_and_completion_apply_time_policy_and_effects() -> None:
    exploration = _loaded()
    state = _state(exploration)
    gate = next(zone for zone in exploration.zones if zone.id == "gate")
    actors = tuple(
        replace(
            actor,
            hp=max(1, actor.hp - 5),
            resource_pools=tuple(replace(pool, current=0) for pool in actor.resource_pools),
        )
        if str(actor.id) == "hero"
        else actor
        for actor in exploration.actors
    )
    service = ShortRestFlowService()

    pending = service.start(state=state, zone=gate, encounter_pending=False)
    transition = service.complete(state=state, actors=actors, pending=pending)

    assert pending.policy.safety.value == "contested"
    assert transition.pending.completed is True
    assert transition.state.elapsed_minutes == 60
    assert transition.state.short_rest_counts == (("short_rest:gate", 1),)
    assert challenge_state_for(transition.state, "closed_gate").noise == 2
    assert transition.actors[0].hp == actors[0].hp
    assert transition.actors[0].resource_pools[0].current == 1
    assert transition.effects[0].effect_type == "add_noise"


def test_short_rest_hit_die_can_be_spent_after_completion() -> None:
    exploration = _loaded()
    wounded = tuple(
        replace(actor, hp=10) if str(actor.id) == "hero" else actor
        for actor in exploration.actors
    )
    service = ShortRestFlowService()

    transition = service.spend_hit_die(
        actors=wounded,
        actor_id="hero",
        die_sides=10,
        natural_roll=5,
    )

    hero = next(actor for actor in transition.actors if str(actor.id) == "hero")
    assert hero.hp == 16
    assert hero.hit_dice[0].remaining == 1


def test_short_rest_policy_limit_and_missing_policy_are_explicit() -> None:
    exploration = _loaded()
    gate = next(zone for zone in exploration.zones if zone.id == "gate")
    tower = next(zone for zone in exploration.zones if zone.id == "tower")
    state = replace(_state(exploration), short_rest_counts=(("short_rest:gate", 1),))
    service = ShortRestFlowService()

    with pytest.raises(ValueError, match="wykorzystała już"):
        service.start(state=state, zone=gate, encounter_pending=False)
    with pytest.raises(ValueError, match="nie ma warunków"):
        service.start(state=state, zone=tower, encounter_pending=False)


def test_short_rest_expires_only_effects_bound_to_short_rest() -> None:
    exploration = _loaded()
    state = _state(exploration)
    gate = next(zone for zone in exploration.zones if zone.id == "gate")
    service = ShortRestFlowService()
    short_effect = ActiveEffect(
        "short-effect",
        "hero",
        "short_bonus",
        "Krótka premia",
        "test",
        1,
        source=EffectSource(EffectSourceType.SYSTEM, "test", "Test"),
        duration=EffectDuration.UNTIL_SHORT_REST,
    )
    daily_effect = ActiveEffect(
        "daily-effect",
        "hero",
        "daily_bonus",
        "Premia dzienna",
        "test",
        1,
        source=EffectSource(EffectSourceType.SYSTEM, "test", "Test"),
        duration=EffectDuration.UNTIL_SCENARIO_END,
    )

    pending = service.start(state=state, zone=gate, encounter_pending=False)
    transition = service.complete(
        state=state,
        actors=exploration.actors,
        pending=pending,
        active_effects=(short_effect, daily_effect),
    )

    assert transition.expired_effects == (short_effect,)
    assert transition.active_effects == (daily_effect,)


def test_short_rest_completion_emits_actor_trigger_after_recovery() -> None:
    exploration = _loaded()
    state = _state(exploration)
    gate = next(zone for zone in exploration.zones if zone.id == "gate")
    trigger = ActorTrigger(
        id="rest_guard",
        label="Osłona po odpoczynku",
        event_type=TriggerEventType.SHORT_REST_COMPLETED,
        effect_kind=TriggerEffectKind.GRANT_TEMP_HP,
        value=3,
    )
    actors = tuple(
        replace(actor, triggers=(trigger,)) if str(actor.id) == "hero" else actor
        for actor in exploration.actors
    )

    transition = ShortRestFlowService().complete(
        state=state,
        actors=actors,
        pending=ShortRestFlowService().start(
            state=state,
            zone=gate,
            encounter_pending=False,
        ),
    )

    hero = next(actor for actor in transition.actors if str(actor.id) == "hero")
    assert hero.temp_hp == 3
    assert transition.trigger_activations[0].trigger.id == "rest_guard"
