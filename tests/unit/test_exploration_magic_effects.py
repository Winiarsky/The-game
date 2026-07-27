from dnd_board_game.combat import scene_flag
from dnd_board_game.exploration import (
    ExplorationState,
    PartyPosition,
    ScenarioClockEvent,
    ScenarioClockPolicy,
    TimedMagicEffect,
    advance_exploration_time,
    apply_timed_magic_effect,
)


def _state(*, elapsed_minutes: int = 10) -> ExplorationState:
    return ExplorationState(
        (),
        (),
        PartyPosition("test"),
        elapsed_minutes=elapsed_minutes,
    )


def _effect(
    *,
    effect_id: str = "spell:hero:comprehend_languages",
    started_at_minute: int = 10,
    expires_at_minute: int | None = 70,
) -> TimedMagicEffect:
    return TimedMagicEffect(
        id=effect_id,
        actor_id="hero",
        spell_id="comprehend_languages",
        label="Rozumienie języków",
        flag_key="comprehend_languages_active",
        flag_value=True,
        started_at_minute=started_at_minute,
        expires_at_minute=expires_at_minute,
    )


def test_timed_magic_effect_expires_at_its_deadline() -> None:
    state = apply_timed_magic_effect(_state(), _effect())

    before_deadline = advance_exploration_time(state, 59)
    assert before_deadline.state.elapsed_minutes == 69
    assert before_deadline.expired_effects == ()
    assert scene_flag(
        before_deadline.state.flags,
        "comprehend_languages_active",
    ) is True

    at_deadline = advance_exploration_time(before_deadline.state, 1)
    assert at_deadline.state.elapsed_minutes == 70
    assert at_deadline.expired_effects == (_effect(),)
    assert at_deadline.state.magic_effects == ()
    assert scene_flag(
        at_deadline.state.flags,
        "comprehend_languages_active",
    ) is False


def test_reapplying_same_magic_flag_replaces_and_refreshes_effect() -> None:
    original = apply_timed_magic_effect(_state(), _effect())
    refreshed = _effect(
        effect_id="spell:cleric:comprehend_languages",
        started_at_minute=20,
        expires_at_minute=80,
    )

    state = apply_timed_magic_effect(
        advance_exploration_time(original, 10).state,
        refreshed,
    )

    assert state.magic_effects == (refreshed,)
    assert advance_exploration_time(state, 50).state.magic_effects == (refreshed,)


def test_until_dispelled_magic_effect_survives_time_advance() -> None:
    effect = _effect(expires_at_minute=None)
    state = apply_timed_magic_effect(_state(), effect)

    advanced = advance_exploration_time(state, 24 * 60)

    assert advanced.expired_effects == ()
    assert advanced.state.magic_effects == (effect,)
    assert scene_flag(
        advanced.state.flags,
        "comprehend_languages_active",
    ) is True


def test_scenario_clock_triggers_due_effects_once_in_authored_order() -> None:
    events = (
        ScenarioClockEvent(
            id="dusk",
            at_minute=20,
            label="Zmierzch",
            narration="Zapada zmierzch.",
            effects=(
                {
                    "type": "set_flag",
                    "parameters": {"key": "dusk_arrival", "value": True},
                },
            ),
        ),
        ScenarioClockEvent(
            id="alert",
            at_minute=30,
            label="Alarm",
            narration="Wrogowie kończą przygotowania.",
            effects=(
                {
                    "type": "set_flag",
                    "parameters": {"key": "defenders_alerted", "value": True},
                },
            ),
        ),
    )
    state = ExplorationState(
        (),
        (),
        PartyPosition("test"),
        clock_policy=ScenarioClockPolicy(start_hour=17, events=events),
    )

    before_threshold = advance_exploration_time(state, 19)
    assert before_threshold.triggered_clock_events == ()

    first = advance_exploration_time(before_threshold.state, 1)
    assert first.triggered_clock_events == (events[0],)
    assert scene_flag(first.state.flags, "dusk_arrival", False) is True
    assert scene_flag(first.state.flags, events[0].marker_flag, False) is True

    second = advance_exploration_time(first.state, 10)
    assert second.triggered_clock_events == (events[1],)
    assert scene_flag(second.state.flags, "defenders_alerted", False) is True

    repeated = advance_exploration_time(second.state, 60)
    assert repeated.triggered_clock_events == ()
