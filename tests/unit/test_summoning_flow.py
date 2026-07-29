from dataclasses import replace

from dnd_board_game.actors import Faction
from dnd_board_game.application import (
    SummoningFlowService,
    remove_orphaned_summons,
)
from dnd_board_game.combat import (
    DamageType,
    InitiativeEntry,
    InitiativeOrder,
    current_actor,
    replace_actor,
    start_combat,
    summon_attack_source,
)
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.scenarios import build_encounter_from_scenario, load_scenario


def _fixture():
    encounter = build_encounter_from_scenario(
        load_scenario("content/scenarios/gate_skirmish.json")
    )
    cleric = next(actor for actor in encounter.actors if str(actor.id) == "cleric")
    enemy = next(actor for actor in encounter.actors if actor.faction == Faction.ENEMY)
    roll = resolve_d20_roll(D20RollInput(D20RollRequest(), 15))
    order = InitiativeOrder(
        (
            InitiativeEntry(cleric, roll, 1, 0),
            InitiativeEntry(enemy, roll, 1, 1),
        )
    )
    state = start_combat((cleric, enemy), order)
    action = next(
        action
        for action in encounter.combat_actions_by_actor[cleric.id]
        if action.id == "call_guardian_spirit"
    )
    return encounter, cleric, enemy, action, state


def test_summon_joins_initiative_after_owner_and_uses_data_driven_attack():
    encounter, cleric, _enemy, action, state = _fixture()
    service = SummoningFlowService()
    slot_before = next(
        slot.remaining for slot in cleric.spell_slots if slot.level == 1
    )

    prepared = service.prepare(
        board=encounter.board,
        state=state,
        active_effects=(),
        action=action,
        cast_level=1,
    )
    assert prepared.pending is not None
    assert cleric.position not in prepared.pending.legal_positions
    position = prepared.pending.legal_positions[0]

    confirmed = service.confirm(
        board=encounter.board,
        state=state,
        active_effects=(),
        action=action,
        pending=prepared.pending,
        position=position,
    )

    summon = confirmed.state.summoned_creatures[0]
    entries = confirmed.state.initiative_order.entries
    assert entries[0].actor.id == cleric.id
    assert entries[1].actor.id == summon.actor_id
    assert entries[1].roll == entries[0].roll
    summoned_actor = next(
        actor for actor in confirmed.state.actors if actor.id == summon.actor_id
    )
    assert summoned_actor.position == position
    assert summoned_actor.faction == Faction.ALLY
    assert summon_attack_source(summon.definition).damage_fixed == 5
    cleric_after = current_actor(confirmed.state)
    assert next(
        slot.remaining
        for slot in cleric_after.spell_slots
        if slot.level == 1
    ) == slot_before - 1
    assert confirmed.active_effects[0].kind == "concentration_summon"


def test_spiritual_weapon_attack_uses_owner_spell_attack_and_damage_modifier():
    encounter, cleric, _enemy, action, _state = _fixture()
    spiritual_definition = replace(
        action.summon,
        id="spiritual_weapon",
        name="Duchowa broń",
        attack_name="Cios duchowej broni",
        attack_damage_type=DamageType.FORCE,
    )
    cleric = replace(cleric, spell_save_dc=15, proficiency_bonus=2)

    source = summon_attack_source(spiritual_definition, cleric)

    assert sum(
        modifier.value
        for modifier in source.attack_roll_request.modifiers
    ) == 7
    assert source.damage_fixed is None
    assert source.damage_die_sides == 8
    assert source.damage_modifier == 5
    assert source.damage_hint == "1d8 + 5"
    assert source.damage_type == "force"


def test_lost_concentration_removes_summon_and_its_initiative_entry():
    encounter, _cleric, _enemy, action, state = _fixture()
    service = SummoningFlowService()
    prepared = service.prepare(
        board=encounter.board,
        state=state,
        active_effects=(),
        action=action,
        cast_level=1,
    )
    assert prepared.pending is not None
    confirmed = service.confirm(
        board=encounter.board,
        state=state,
        active_effects=(),
        action=action,
        pending=prepared.pending,
        position=prepared.pending.legal_positions[0],
    )

    updated_state, effects, removed = remove_orphaned_summons(
        confirmed.state,
        (),
    )

    assert len(removed) == 1
    assert effects == ()
    assert updated_state.summoned_creatures == ()
    assert all(
        entry.actor.id != removed[0].actor_id
        for entry in updated_state.initiative_order.entries
    )
    assert all(actor.id != removed[0].actor_id for actor in updated_state.actors)


def test_defeated_summon_disappears_and_ends_its_concentration_effect():
    encounter, _cleric, _enemy, action, state = _fixture()
    service = SummoningFlowService()
    prepared = service.prepare(
        board=encounter.board,
        state=state,
        active_effects=(),
        action=action,
        cast_level=1,
    )
    assert prepared.pending is not None
    confirmed = service.confirm(
        board=encounter.board,
        state=state,
        active_effects=(),
        action=action,
        pending=prepared.pending,
        position=prepared.pending.legal_positions[0],
    )
    summoned = confirmed.state.summoned_creatures[0]
    actor = next(
        actor for actor in confirmed.state.actors if actor.id == summoned.actor_id
    )
    defeated_state = replace_actor(confirmed.state, replace(actor, hp=0))

    updated_state, effects, removed = remove_orphaned_summons(
        defeated_state,
        confirmed.active_effects,
    )

    assert removed == (summoned,)
    assert effects == ()
    assert updated_state.summoned_creatures == ()
