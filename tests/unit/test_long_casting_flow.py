from dnd_board_game.actors import Faction
from dnd_board_game.application import LongCastingFlowService
from dnd_board_game.combat import (
    InitiativeEntry,
    InitiativeOrder,
    current_actor,
    casting_time_actions,
    finish_turn,
    long_cast_for_actor,
    start_combat,
)
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.rules import SpellCastingTime
from dnd_board_game.scenarios import build_encounter_from_scenario, load_scenario


def _fixture():
    encounter = build_encounter_from_scenario(
        load_scenario("content/scenarios/gate_skirmish.json")
    )
    cleric = next(actor for actor in encounter.actors if str(actor.id) == "cleric")
    enemy = next(actor for actor in encounter.actors if actor.faction == Faction.ENEMY)
    request = D20RollRequest()
    order = InitiativeOrder(
        (
            InitiativeEntry(
                cleric,
                resolve_d20_roll(D20RollInput(request, 20)),
                1,
                0,
            ),
            InitiativeEntry(
                enemy,
                resolve_d20_roll(D20RollInput(request, 10)),
                1,
                1,
            ),
        )
    )
    state = start_combat((cleric, enemy), order)
    action = next(
        action
        for action in encounter.combat_actions_by_actor[cleric.id]
        if action.id == "warding_rite"
    )
    return cleric, action, state


def _advance_to_next_caster_turn(state, caster_id):
    state = finish_turn(state)
    while current_actor(state).id != caster_id:
        state = finish_turn(state)
    return state


def test_long_casting_time_converts_minutes_and_hours_to_six_second_rounds():
    assert casting_time_actions(SpellCastingTime.MINUTE) == 10
    assert casting_time_actions(SpellCastingTime.TEN_MINUTES) == 100
    assert casting_time_actions(SpellCastingTime.HOUR) == 600


def test_long_cast_spends_one_action_per_turn_and_slot_only_on_completion():
    cleric, action, state = _fixture()
    service = LongCastingFlowService()
    slot_before = next(
        slot.remaining for slot in cleric.spell_slots if slot.level == 1
    )

    transition = service.start(
        state=state,
        active_effects=(),
        action=action,
        cast_level=1,
    )

    assert transition.cast is not None
    assert transition.cast.completed_actions == 1
    assert transition.cast.required_actions == 10
    assert next(
        slot.remaining
        for slot in current_actor(transition.state).spell_slots
        if slot.level == 1
    ) == slot_before
    assert transition.active_effects[0].kind == "concentration_long_cast"

    for expected_progress in range(2, 11):
        state = _advance_to_next_caster_turn(
            transition.state,
            cleric.id,
        )
        transition = service.continue_cast(
            state=state,
            active_effects=transition.active_effects,
            action=action,
        )
        if expected_progress < 10:
            assert transition.cast is not None
            assert transition.cast.completed_actions == expected_progress

    completed_cleric = current_actor(transition.state)
    assert transition.completed
    assert transition.cast is None
    assert completed_cleric.temp_hp == 5
    assert next(
        slot.remaining
        for slot in completed_cleric.spell_slots
        if slot.level == 1
    ) == slot_before - 1
    assert transition.state.long_casts == ()
    assert transition.active_effects == ()


def test_interrupted_long_cast_does_not_consume_spell_slot():
    cleric, action, state = _fixture()
    service = LongCastingFlowService()
    started = service.start(
        state=state,
        active_effects=(),
        action=action,
        cast_level=1,
    )
    slot_after_start = next(
        slot.remaining
        for slot in current_actor(started.state).spell_slots
        if slot.level == 1
    )

    interrupted = service.interrupt(
        state=started.state,
        active_effects=started.active_effects,
        caster_id=str(cleric.id),
        reason="utrata koncentracji",
    )

    assert interrupted.interrupted
    assert long_cast_for_actor(interrupted.state.long_casts, cleric.id) is None
    assert next(
        slot.remaining
        for slot in current_actor(interrupted.state).spell_slots
        if slot.level == 1
    ) == slot_after_start
    assert interrupted.active_effects == ()
