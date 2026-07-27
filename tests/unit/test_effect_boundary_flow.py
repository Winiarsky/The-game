from dnd_board_game.application import (
    expire_exploration_conditions,
    reconcile_conditions_after_encounter,
)
from dnd_board_game.combat import (
    CombatCondition,
    ConditionSaveTiming,
    ConditionState,
)
from dnd_board_game.exploration import ExplorationState, PartyPosition
from dnd_board_game.rules import EffectDuration, EffectEvent, EffectEventType


def test_encounter_boundary_expires_local_condition_and_preserves_scenario_condition() -> None:
    local = ConditionState(
        "hero",
        CombatCondition.RESTRAINED,
        duration=EffectDuration.UNTIL_ENCOUNTER_END,
    )
    persistent = ConditionState(
        "hero",
        CombatCondition.POISONED,
        duration=EffectDuration.UNTIL_SHORT_REST,
    )

    transition = reconcile_conditions_after_encounter(
        exploration_conditions=(persistent,),
        combat_conditions=(local, persistent),
        exploration_actor_ids=frozenset({"hero"}),
        encounter_actor_ids=frozenset({"hero", "goblin"}),
    )

    assert transition.condition_states == (persistent,)
    assert transition.expired_conditions == (local,)


def test_encounter_boundary_discards_grapple_from_actor_left_in_encounter() -> None:
    grappled = ConditionState(
        "hero",
        CombatCondition.GRAPPLED,
        source_actor_id="goblin",
    )

    transition = reconcile_conditions_after_encounter(
        exploration_conditions=(),
        combat_conditions=(grappled,),
        exploration_actor_ids=frozenset({"hero"}),
        encounter_actor_ids=frozenset({"hero", "goblin"}),
    )

    assert transition.condition_states == ()
    assert transition.expired_conditions == (grappled,)


def test_scenario_boundary_expires_nonpermanent_condition_even_with_repeat_save() -> None:
    poisoned = ConditionState(
        "hero",
        CombatCondition.POISONED,
        duration=EffectDuration.UNTIL_SCENARIO_END,
        save_ability="constitution",
        save_dc=12,
        save_timing=ConditionSaveTiming.TURN_END,
    )
    permanent = ConditionState(
        "hero",
        CombatCondition.PRONE,
        duration=EffectDuration.PERMANENT,
    )
    state = ExplorationState(
        (),
        (),
        PartyPosition("gate"),
        condition_states=(poisoned, permanent),
    )

    updated, transition = expire_exploration_conditions(
        state,
        EffectEvent(EffectEventType.SCENARIO_ENDED),
    )

    assert updated.condition_states == (permanent,)
    assert transition.expired_conditions == (poisoned,)
