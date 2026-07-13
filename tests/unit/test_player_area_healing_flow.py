from random import Random

import pytest

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.application import PlayerAreaHealingFlowService
from dnd_board_game.combat import (
    ActionUse,
    AttackSource,
    AttackSourceType,
    CombatState,
    HealingSource,
    HealingSourceType,
    InitiativeEntry,
    InitiativeOrder,
    SpellArea,
    SpellAreaShape,
    current_actor,
    start_combat,
)
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.world import BoardState, Coordinate


def _actor(
    actor_id: str,
    faction: Faction,
    position: Coordinate,
    *,
    hp: int = 10,
    max_hp: int = 10,
    spell_save_dc: int = 13,
) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id.title(),
        ac=12,
        hp=hp,
        max_hp=max_hp,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=faction,
        ability_scores=AbilityScores(dexterity=14),
        spell_save_dc=spell_save_dc,
    )


def _state(*actors: Actor) -> CombatState:
    order = InitiativeOrder(
        tuple(
            InitiativeEntry(
                actor,
                resolve_d20_roll(D20RollInput(D20RollRequest(), 20 - index)),
                2,
                index,
            )
            for index, actor in enumerate(actors)
        )
    )
    return start_combat(tuple(actors), order)


def _healing_source() -> HealingSource:
    return HealingSource(
        id="healing_word",
        name="Healing Word",
        source_type=HealingSourceType.SPELL,
        range_feet=30,
        healing_hint="1d4",
    )


def _line_spell() -> AttackSource:
    return AttackSource(
        name="Promień",
        source_type=AttackSourceType.SPELL,
        range_feet=30,
        attack_roll_request=D20RollRequest(),
        damage_hint="2d6",
        damage_type="radiant",
        id="radiant_line",
        area=SpellArea(SpellAreaShape.LINE, length_feet=15),
        save_ability="dexterity",
        save_dc=1,
        save_damage_on_success="half",
    )


def test_healing_flow_selects_wounded_ally_and_applies_effective_healing() -> None:
    service = PlayerAreaHealingFlowService()
    healer = _actor("healer", Faction.ALLY, Coordinate(0, 0))
    ally = _actor("ally", Faction.ALLY, Coordinate(1, 0), hp=4)
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(3, 0))
    state = _state(healer, ally, enemy)

    selected = service.select_healing_target(
        state=state,
        board=BoardState(),
        source=_healing_source(),
        position=ally.position,
    )
    assert selected.pending is not None
    assert selected.pending.target_id == "ally"
    assert selected.event_type == "ui_combat_player_healing_target_selected"

    healed = service.submit_healing(
        state=state,
        source=_healing_source(),
        pending=selected.pending,
        healing=8,
    )

    updated_ally = next(actor for actor in healed.state.actors if actor.id == ally.id)
    assert updated_ally.hp == 10
    assert healed.state.turn_action.action_use == ActionUse.ACTION_USED
    assert healed.pending is None
    assert dict(healed.event_payload)["effective_healing"] == 6


def test_healing_flow_rejects_a_full_health_target() -> None:
    service = PlayerAreaHealingFlowService()
    healer = _actor("healer", Faction.ALLY, Coordinate(0, 0))
    ally = _actor("ally", Faction.ALLY, Coordinate(1, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(3, 0))

    with pytest.raises(ValueError, match="legalnym celem leczenia"):
        service.select_healing_target(
            state=_state(healer, ally, enemy),
            board=BoardState(),
            source=_healing_source(),
            position=ally.position,
        )


def test_area_spell_flow_previews_confirms_and_applies_save_adjusted_damage() -> None:
    service = PlayerAreaHealingFlowService()
    caster = _actor("caster", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(2, 0))
    state = _state(caster, enemy)
    source = _line_spell()

    selected = service.select_area_spell(
        state=state,
        board=BoardState(),
        source=source,
        position=Coordinate(1, 0),
    )
    assert selected.pending is not None
    assert selected.pending.target_ids == ("enemy",)
    assert Coordinate(2, 0) in selected.pending.area_positions

    confirmed = service.confirm_area_spell(
        state=state,
        source=source,
        pending=selected.pending,
        rng=Random(1),
    )
    assert confirmed.pending is not None
    assert confirmed.pending.stage == "damage_roll"
    assert confirmed.pending.saving_throws[0].success is True
    assert confirmed.state.turn_action.action_use == ActionUse.ACTION_USED

    damaged = service.submit_area_damage(
        state=confirmed.state,
        source=source,
        pending=confirmed.pending,
        damage=5,
    )

    updated_enemy = next(actor for actor in damaged.state.actors if actor.id == enemy.id)
    assert updated_enemy.hp == 8
    assert damaged.pending is None
    assert len(damaged.applied_damages) == 1
    assert dict(damaged.event_payload)["base_damage"] == 5


def test_cancel_transitions_leave_combat_state_unchanged() -> None:
    service = PlayerAreaHealingFlowService()
    caster = _actor("caster", Faction.ALLY, Coordinate(0, 0))
    ally = _actor("ally", Faction.ALLY, Coordinate(0, 1), hp=5)
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(2, 0))
    state = _state(caster, ally, enemy)
    healing = service.select_healing_target(
        state=state,
        board=BoardState(),
        source=_healing_source(),
        position=ally.position,
    )
    area = service.select_area_spell(
        state=state,
        board=BoardState(),
        source=_line_spell(),
        position=Coordinate(1, 0),
    )
    assert healing.pending is not None
    assert area.pending is not None

    cancelled_healing = service.cancel_healing(state=state, pending=healing.pending)
    cancelled_area = service.cancel_area_spell(state=state, pending=area.pending)

    assert cancelled_healing.state is state
    assert cancelled_healing.pending is None
    assert cancelled_area.state is state
    assert cancelled_area.pending is None
    assert current_actor(cancelled_area.state).id == caster.id
