from dataclasses import replace

from dnd_board_game.actors import ActorId, Faction
from dnd_board_game.application import SpellDispelFlowService
from dnd_board_game.combat import (
    ActionUse,
    CombatCondition,
    ConditionSaveTiming,
    InitiativeEntry,
    InitiativeOrder,
    SummonedCreatureState,
    add_summoned_creature,
    apply_condition,
    current_actor,
    start_combat,
    summon_actor,
)
from dnd_board_game.rules import (
    ActiveEffect,
    D20RollInput,
    D20RollRequest,
    EffectDuration,
    EffectSource,
    EffectSourceType,
    resolve_d20_roll,
)
from dnd_board_game.scenarios import build_encounter_from_scenario, load_scenario
from dnd_board_game.world import Coordinate


def _fixture():
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
        if action.id == "unravel_magic"
    )
    return encounter, cleric, enemy, action, state


def _magical_condition(state, enemy, *, spell_level: int):
    applied = apply_condition(
        state.condition_states,
        enemy,
        CombatCondition.POISONED,
        source_actor_id="enemy_caster",
        source_label="Wroga miazma",
        duration=EffectDuration.PERMANENT,
        save_ability="constitution",
        save_dc=13,
        save_timing=ConditionSaveTiming.TURN_END,
        source_spell_id="enemy_miasma",
        source_spell_level=spell_level,
    )
    return replace(state, condition_states=applied.condition_states)


def test_dispel_automatically_removes_equal_or_lower_level_spell_condition():
    encounter, cleric, enemy, action, state = _fixture()
    state = _magical_condition(state, enemy, spell_level=1)
    service = SpellDispelFlowService()
    prepared = service.prepare(
        board=encounter.board,
        state=state,
        active_effects=(),
        action=action,
        cast_level=1,
    )
    assert prepared.pending is not None
    slot_before = next(
        slot.remaining for slot in cleric.spell_slots if slot.level == 1
    )

    resolved = service.confirm_target(
        board=encounter.board,
        state=state,
        active_effects=(),
        action=action,
        pending=prepared.pending,
        target_id=str(enemy.id),
    )

    assert resolved.pending is None
    assert resolved.state.condition_states == ()
    assert resolved.state.turn_action.action_use == ActionUse.ACTION_USED
    caster_after = current_actor(resolved.state)
    assert next(
        slot.remaining for slot in caster_after.spell_slots if slot.level == 1
    ) == slot_before - 1


def test_higher_level_spell_requires_and_can_pass_ability_check():
    encounter, _cleric, enemy, action, state = _fixture()
    state = _magical_condition(state, enemy, spell_level=3)
    service = SpellDispelFlowService()
    prepared = service.prepare(
        board=encounter.board,
        state=state,
        active_effects=(),
        action=action,
        cast_level=1,
    )
    assert prepared.pending is not None
    confirmed = service.confirm_target(
        board=encounter.board,
        state=state,
        active_effects=(),
        action=action,
        pending=prepared.pending,
        target_id=str(enemy.id),
    )

    assert confirmed.pending is not None
    assert confirmed.pending.stage == "ability_check"
    assert confirmed.pending.current_check is not None
    assert confirmed.pending.current_check.dc == 13

    resolved = service.resolve_check(
        state=confirmed.state,
        active_effects=confirmed.active_effects,
        action=action,
        pending=confirmed.pending,
        natural_roll=20,
    )

    assert resolved.pending is None
    assert resolved.state.condition_states == ()


def test_failed_higher_level_check_leaves_spell_effect():
    encounter, _cleric, enemy, action, state = _fixture()
    effect = ActiveEffect(
        id="enemy_spell:ward",
        actor_id=str(enemy.id),
        kind="spell_ac_bonus",
        label="Wroga osłona",
        object_id="spell:enemy_ward",
        value=2,
        source_actor_id="enemy_caster",
        target_actor_id=str(enemy.id),
        source=EffectSource(
            EffectSourceType.SPELL,
            "enemy_ward",
            "Wroga osłona",
        ),
        duration=EffectDuration.CONCENTRATION,
        spell_level=4,
    )
    service = SpellDispelFlowService()
    prepared = service.prepare(
        board=encounter.board,
        state=state,
        active_effects=(effect,),
        action=action,
        cast_level=1,
    )
    assert prepared.pending is not None
    confirmed = service.confirm_target(
        board=encounter.board,
        state=state,
        active_effects=(effect,),
        action=action,
        pending=prepared.pending,
        target_id=str(enemy.id),
    )
    assert confirmed.pending is not None

    resolved = service.resolve_check(
        state=confirmed.state,
        active_effects=confirmed.active_effects,
        action=action,
        pending=confirmed.pending,
        natural_roll=1,
    )

    assert resolved.pending is None
    assert resolved.active_effects == (effect,)


def test_dispelling_summon_effect_removes_dynamic_actor():
    encounter, _cleric, enemy, action, state = _fixture()
    owner_action = next(
        candidate
        for actions in encounter.combat_actions_by_actor.values()
        for candidate in actions
        if candidate.id == "call_guardian_spirit"
    )
    assert owner_action.summon is not None
    summon_id = ActorId("summon:enemy:spirit:1")
    concentration_effect_id = "concentration_summon:enemy:spirit"
    summon_state = SummonedCreatureState(
        actor_id=summon_id,
        owner_actor_id=enemy.id,
        spell_id="enemy_summon",
        definition=owner_action.summon,
        concentration_effect_id=concentration_effect_id,
    )
    summoned_actor = summon_actor(
        owner_action.summon,
        actor_id=summon_id,
        owner=enemy,
        position=Coordinate(enemy.position.col + 1, enemy.position.row),
    )
    state = add_summoned_creature(state, summon_state, summoned_actor)
    effect = ActiveEffect(
        id=concentration_effect_id,
        actor_id=str(enemy.id),
        kind="concentration_summon",
        label="Wrogie przywołanie",
        object_id="spell:enemy_summon",
        value=0,
        source_actor_id=str(enemy.id),
        target_actor_id=str(summon_id),
        source=EffectSource(
            EffectSourceType.SPELL,
            "enemy_summon",
            "Wrogie przywołanie",
        ),
        duration=EffectDuration.CONCENTRATION,
        spell_level=1,
    )
    service = SpellDispelFlowService()
    prepared = service.prepare(
        board=encounter.board,
        state=state,
        active_effects=(effect,),
        action=action,
        cast_level=1,
    )
    assert prepared.pending is not None

    resolved = service.confirm_target(
        board=encounter.board,
        state=state,
        active_effects=(effect,),
        action=action,
        pending=prepared.pending,
        target_id=str(summon_id),
    )

    assert resolved.pending is None
    assert resolved.active_effects == ()
    assert resolved.state.summoned_creatures == ()
    assert all(actor.id != summon_id for actor in resolved.state.actors)
    assert resolved.removed_actor_ids == (str(summon_id),)
