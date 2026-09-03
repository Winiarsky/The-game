from dataclasses import replace

from dnd_board_game.actors import ActorResourcePool, Faction, RecoveryPeriod
from dnd_board_game.application import SpellDebuffFlowService
from dnd_board_game.combat import (
    ActionUse,
    CombatCondition,
    ConditionSaveTiming,
    InitiativeEntry,
    InitiativeOrder,
    current_actor,
    pending_condition_saves,
    resolve_condition_save,
    start_combat,
)
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.scenarios import build_encounter_from_scenario, load_scenario


class FixedRng:
    def __init__(self, value: int) -> None:
        self.value = value

    def randint(self, _minimum: int, _maximum: int) -> int:
        return self.value


class SequenceRng:
    def __init__(self, *values: int) -> None:
        self.values = list(values)

    def randint(self, _minimum: int, _maximum: int) -> int:
        return self.values.pop(0)


def _fixture(action_id: str):
    encounter = build_encounter_from_scenario(
        load_scenario("content/scenarios/gate_skirmish.json")
    )
    cleric = next(actor for actor in encounter.actors if str(actor.id) == "cleric")
    enemy = next(actor for actor in encounter.actors if actor.faction == Faction.ENEMY)
    roll = resolve_d20_roll(D20RollInput(D20RollRequest(), 15))
    state = start_combat(
        (cleric, enemy),
        InitiativeOrder(
            (
                InitiativeEntry(cleric, roll, 1, 0),
                InitiativeEntry(enemy, roll, 1, 1),
            )
        ),
    )
    action = next(
        action
        for action in encounter.combat_actions_by_actor[cleric.id]
        if action.id == action_id
    )
    return encounter, cleric, enemy, action, state


def test_failed_initial_save_applies_condition_and_spends_cast():
    encounter, cleric, enemy, action, state = _fixture("weakening_miasma")
    service = SpellDebuffFlowService()
    slot_before = next(
        slot.remaining for slot in cleric.spell_slots if slot.level == 1
    )
    prepared = service.prepare(
        board=encounter.board,
        state=state,
        action=action,
        cast_level=1,
    )
    assert prepared.pending is not None

    confirmed = service.confirm(
        board=encounter.board,
        state=state,
        action=action,
        pending=prepared.pending,
        target_id=str(enemy.id),
        rng=FixedRng(1),
    )

    condition = confirmed.state.condition_states[0]
    assert condition.actor_id == str(enemy.id)
    assert condition.condition == CombatCondition.POISONED
    assert condition.save_ability == "constitution"
    assert condition.save_dc == 13
    assert condition.save_timing == ConditionSaveTiming.TURN_END
    assert condition.source_spell_id == "weakening_miasma"
    assert condition.source_spell_level == 1
    assert confirmed.state.turn_action.action_use == ActionUse.ACTION_USED
    caster_after = current_actor(confirmed.state)
    assert next(
        slot.remaining for slot in caster_after.spell_slots if slot.level == 1
    ) == slot_before - 1


def test_successful_initial_save_prevents_debuff_but_spends_action():
    encounter, _cleric, enemy, action, state = _fixture("binding_frost")
    service = SpellDebuffFlowService()
    prepared = service.prepare(
        board=encounter.board,
        state=state,
        action=action,
        cast_level=1,
    )
    assert prepared.pending is not None

    confirmed = service.confirm(
        board=encounter.board,
        state=state,
        action=action,
        pending=prepared.pending,
        target_id=str(enemy.id),
        rng=FixedRng(20),
    )

    assert confirmed.state.condition_states == ()
    assert confirmed.state.turn_action.action_use == ActionUse.ACTION_USED


def test_repeated_turn_end_save_removes_applied_debuff():
    encounter, _cleric, enemy, action, state = _fixture("weakening_miasma")
    service = SpellDebuffFlowService()
    prepared = service.prepare(
        board=encounter.board,
        state=state,
        action=action,
        cast_level=1,
    )
    assert prepared.pending is not None
    confirmed = service.confirm(
        board=encounter.board,
        state=state,
        action=action,
        pending=prepared.pending,
        target_id=str(enemy.id),
        rng=FixedRng(1),
    )
    saves = pending_condition_saves(
        confirmed.state.condition_states,
        str(enemy.id),
        ConditionSaveTiming.TURN_END,
    )

    resolution = resolve_condition_save(
        confirmed.state.condition_states,
        enemy,
        saves[0],
        natural_roll=20,
        combat_actors=confirmed.state.actors,
    )

    assert resolution.removed
    assert resolution.condition_states == ()


def test_forced_weave_uses_disadvantage_and_spends_metamagic_on_commit() -> None:
    encounter, caster, enemy, action, state = _fixture("weakening_miasma")
    pool = ActorResourcePool(
        "metamagic_points",
        "Punkty Metamagii",
        4,
        4,
        RecoveryPeriod.LONG_REST,
    )
    caster = replace(caster, resource_pools=(pool,))
    state = replace(
        state,
        actors=tuple(caster if str(actor.id) == str(caster.id) else actor for actor in state.actors),
    )
    action = replace(
        action,
        metamagic_ids=("nimra_forced_weave",),
        resource_pool_id="metamagic_points",
        resource_cost=2,
    )
    service = SpellDebuffFlowService()
    prepared = service.prepare(
        board=encounter.board,
        state=state,
        action=action,
        cast_level=1,
    )
    assert prepared.pending is not None

    rng = SequenceRng(20, 1)
    confirmed = service.confirm(
        board=encounter.board,
        state=state,
        action=action,
        pending=prepared.pending,
        target_id=str(enemy.id),
        rng=rng,
    )

    save = dict(confirmed.event_payload)["save"]
    assert save["natural_roll"] == 1
    assert rng.values == []
    caster_after = current_actor(confirmed.state)
    assert caster_after.resource_pools[0].current == 2
