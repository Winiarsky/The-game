import pytest

from dnd_board_game.rules import (
    ActiveEffect,
    AdditionalEffectExpiration,
    EffectDuration,
    EffectEvent,
    EffectEventType,
    EffectSource,
    EffectSourceType,
    EffectStackingPolicy,
    apply_active_effect,
    expire_active_effects,
)


def _effect(
    effect_id: str,
    *,
    actor_id: str = "hero",
    duration: EffectDuration = EffectDuration.UNTIL_SCENARIO_END,
    stacking: EffectStackingPolicy = EffectStackingPolicy.REPLACE,
    stacking_key: str = "test:buff",
) -> ActiveEffect:
    return ActiveEffect(
        id=effect_id,
        actor_id=actor_id,
        kind="test_bonus",
        label="Premia próbna",
        object_id="spell:test",
        value=2,
        source=EffectSource(EffectSourceType.SPELL, "test", "Czar próbny"),
        duration=duration,
        stacking=stacking,
        stacking_key=stacking_key,
    )


def test_active_effect_payload_exposes_source_duration_and_stacking() -> None:
    payload = _effect("effect-1").as_payload()

    assert payload["source"] == {
        "type": "spell",
        "id": "test",
        "label": "Czar próbny",
    }
    assert payload["duration"] == "until_scenario_end"
    assert payload["stacking"] == "replace"
    assert payload["expires"] == "znika po zakończeniu scenariusza"
    assert "źródło: Czar próbny" in str(payload["summary"])


def test_apply_effect_replaces_or_refreshes_shared_stacking_key() -> None:
    old = _effect("old")
    replacement = _effect("new")
    replaced = apply_active_effect((old,), replacement)

    assert replaced.active_effects == (replacement,)
    assert replaced.replaced_effects == (old,)
    assert replaced.refreshed is False

    refreshed_effect = _effect("fresh", stacking=EffectStackingPolicy.REFRESH)
    refreshed = apply_active_effect((replacement,), refreshed_effect)

    assert refreshed.active_effects == (refreshed_effect,)
    assert refreshed.replaced_effects == (replacement,)
    assert refreshed.refreshed is True


def test_stack_policy_keeps_distinct_effects_and_rejects_duplicate_ids() -> None:
    first = _effect("first", stacking=EffectStackingPolicy.STACK)
    second = _effect("second", stacking=EffectStackingPolicy.STACK)

    assert apply_active_effect((first,), second).active_effects == (first, second)
    with pytest.raises(ValueError, match="already exists"):
        apply_active_effect((first,), first)


def test_turn_and_attack_events_use_explicit_actor_and_target_contracts() -> None:
    turn_effect = _effect(
        "turn",
        actor_id="helper",
        duration=EffectDuration.UNTIL_TURN_START,
        stacking_key="turn",
    )
    attack_effect = ActiveEffect(
        id="attack",
        actor_id="hero",
        kind="attack_bonus",
        label="Pomoc",
        object_id="action:help",
        value=0,
        target_actor_id="goblin",
        source=EffectSource(EffectSourceType.ACTION, "help", "Pomoc"),
        duration=EffectDuration.UNTIL_NEXT_ATTACK,
        stacking_key="attack",
    )

    wrong_target = expire_active_effects(
        (turn_effect, attack_effect),
        EffectEvent(
            EffectEventType.ATTACK_RESOLVED,
            actor_id="hero",
            target_actor_id="orc",
        ),
    )
    assert wrong_target.expired_effects == ()

    missing_target = expire_active_effects(
        wrong_target.active_effects,
        EffectEvent(EffectEventType.ATTACK_RESOLVED, actor_id="hero"),
    )
    assert missing_target.expired_effects == ()

    attack = expire_active_effects(
        missing_target.active_effects,
        EffectEvent(
            EffectEventType.ATTACK_RESOLVED,
            actor_id="hero",
            target_actor_id="goblin",
        ),
    )
    assert attack.expired_effects == (attack_effect,)

    turn = expire_active_effects(
        attack.active_effects,
        EffectEvent(EffectEventType.TURN_START, actor_id="helper"),
    )
    assert turn.expired_effects == (turn_effect,)


def test_round_end_event_expires_round_bound_effect() -> None:
    effect = _effect(
        "round",
        duration=EffectDuration.UNTIL_ROUND_END,
        stacking_key="round",
    )

    result = expire_active_effects(
        (effect,),
        EffectEvent(EffectEventType.ROUND_ENDED),
    )

    assert result.expired_effects == (effect,)


def test_additional_expiration_supports_effect_with_two_end_conditions() -> None:
    effect = ActiveEffect(
        id="help",
        actor_id="ally",
        kind="attack_bonus",
        label="Pomoc",
        object_id="action:help",
        value=0,
        target_actor_id="goblin",
        source_actor_id="helper",
        source=EffectSource(EffectSourceType.ACTION, "help", "Pomoc"),
        duration=EffectDuration.UNTIL_NEXT_ATTACK,
        additional_expirations=(
            AdditionalEffectExpiration(
                EffectDuration.UNTIL_TURN_START,
                actor_id="helper",
            ),
        ),
    )

    result = expire_active_effects(
        (effect,),
        EffectEvent(EffectEventType.TURN_START, actor_id="helper"),
    )

    assert result.expired_effects == (effect,)


def test_rest_encounter_and_scenario_boundaries_expire_matching_effects() -> None:
    short = _effect("short", duration=EffectDuration.UNTIL_SHORT_REST, stacking_key="short")
    encounter = _effect(
        "encounter",
        duration=EffectDuration.UNTIL_ENCOUNTER_END,
        stacking_key="encounter",
    )
    scenario = _effect(
        "scenario",
        duration=EffectDuration.UNTIL_SCENARIO_END,
        stacking_key="scenario",
    )
    permanent = _effect(
        "permanent",
        duration=EffectDuration.PERMANENT,
        stacking_key="permanent",
    )

    after_short = expire_active_effects(
        (short, encounter, scenario, permanent),
        EffectEvent(EffectEventType.SHORT_REST_COMPLETED),
    )
    assert after_short.expired_effects == (short,)

    after_encounter = expire_active_effects(
        after_short.active_effects,
        EffectEvent(EffectEventType.ENCOUNTER_ENDED),
    )
    assert after_encounter.expired_effects == (encounter,)

    after_scenario = expire_active_effects(
        after_encounter.active_effects,
        EffectEvent(EffectEventType.SCENARIO_ENDED),
    )
    assert after_scenario.expired_effects == (scenario,)
    assert after_scenario.active_effects == (permanent,)


def test_long_rest_ends_every_non_permanent_effect() -> None:
    turn = _effect("turn", duration=EffectDuration.UNTIL_TURN_END, stacking_key="turn")
    concentration = _effect(
        "concentration",
        duration=EffectDuration.CONCENTRATION,
        stacking_key="concentration",
    )
    permanent = _effect(
        "permanent",
        duration=EffectDuration.PERMANENT,
        stacking_key="permanent",
    )

    result = expire_active_effects(
        (turn, concentration, permanent),
        EffectEvent(EffectEventType.LONG_REST_COMPLETED),
    )

    assert result.expired_effects == (turn, concentration)
    assert result.active_effects == (permanent,)
