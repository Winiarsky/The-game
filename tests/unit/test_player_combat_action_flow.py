from dataclasses import replace
from random import Random

import pytest

from dnd_board_game.actors import AbilityScores, Actor, ActorId, DamageAffinityProfile, Faction
from dnd_board_game.application import PlayerCombatActionFlowService
from dnd_board_game.combat import (
    ActionUse,
    ActiveCombatEffect,
    AttackKind,
    AttackSource,
    AttackSourceType,
    CombatState,
    CombatCondition,
    ConditionState,
    HealingSource,
    HealingSourceType,
    HiddenState,
    DamageType,
    InitiativeEntry,
    InitiativeOrder,
    SceneObject,
    current_actor,
    start_combat,
)
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.world import BoardState, Coordinate


def _actor(actor_id: str, faction: Faction, position: Coordinate) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id.title(),
        ac=12,
        hp=10,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=faction,
        ability_scores=AbilityScores(dexterity=14),
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


def _source() -> AttackSource:
    return AttackSource(
        name="Miecz",
        source_type=AttackSourceType.WEAPON,
        range_feet=5,
        attack_roll_request=D20RollRequest(),
        damage_hint="1d8",
        damage_type="slashing",
        id="sword",
    )


def _dexterity_save_source() -> AttackSource:
    return AttackSource(
        name="Święty płomień",
        source_type=AttackSourceType.SPELL,
        range_feet=60,
        attack_roll_request=D20RollRequest(),
        damage_hint="1d8",
        damage_type="radiant",
        id="sacred_flame",
        attack_kind=AttackKind.RANGED,
        save_ability="dexterity",
        save_dc=9,
        save_damage_on_success="half",
    )


def test_source_selection_validates_active_hero_and_preserves_event_contract() -> None:
    service = PlayerCombatActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(1, 0))
    state = _state(hero, enemy)

    attack = service.select_attack_source(
        state=state,
        sources=(_source(),),
        source_id="sword",
    )
    healing = service.select_healing_source(
        state=state,
        sources=(
            HealingSource(
                id="heal",
                name="Leczenie ran",
                source_type=HealingSourceType.SPELL,
                range_feet=5,
            ),
        ),
        source_id="heal",
    )

    assert attack.actor_id == "hero"
    assert attack.event_type == "ui_combat_attack_source_selected"
    assert dict(attack.event_payload) == {"actor_id": "hero", "source_id": "sword"}
    assert healing.event_type == "ui_combat_healing_source_selected"

    with pytest.raises(ValueError, match="Nieznane źródło ataku"):
        service.select_attack_source(state=state, sources=(_source(),), source_id="missing")
    with pytest.raises(ValueError, match="To nie jest tura bohatera"):
        service.select_attack_source(
            state=_state(enemy, hero),
            sources=(_source(),),
            source_id="sword",
        )


def test_staged_attack_moves_from_target_preview_through_damage() -> None:
    service = PlayerCombatActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(1, 0))
    state = _state(hero, enemy)
    source = _source()
    penalty = ActiveCombatEffect(
        id="penalty",
        actor_id="hero",
        kind="grant_next_attack_penalty",
        label="Kara",
        object_id="test:penalty",
        value=-1,
    )

    selected = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        position=enemy.position,
        active_effects=(penalty,),
    )
    assert selected.pending is not None
    assert selected.pending.stage == "confirm_attack"

    confirmed = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        pending=selected.pending,
        active_effects=(penalty,),
        rng=Random(1),
    )
    assert confirmed.pending is not None
    assert confirmed.pending.stage == "attack_roll"

    rolled = service.submit_attack_roll(
        state=state,
        board=BoardState(),
        source=source,
        pending=confirmed.pending,
        active_effects=(penalty,),
        natural_roll=20,
    )
    assert rolled.pending is not None
    assert rolled.pending.stage == "damage_roll"
    assert rolled.pending.critical is True
    assert rolled.active_effects == ()
    assert rolled.state.turn_action.action_use == ActionUse.ACTION_USED

    damaged = service.submit_damage(
        state=rolled.state,
        source=source,
        pending=rolled.pending,
        active_effects=rolled.active_effects,
        damage=5,
    )
    updated_enemy = next(actor for actor in damaged.state.actors if actor.id == enemy.id)
    assert updated_enemy.hp == 5
    assert damaged.pending is None
    assert damaged.applied_damage is not None
    assert damaged.event_type == "ui_combat_player_damage_roll"


def test_single_target_dexterity_save_uses_scene_cover_bonus() -> None:
    service = PlayerCombatActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(4, 0))
    state = _state(hero, enemy)
    source = _dexterity_save_source()
    cover = SceneObject(
        id="cart",
        name="Wóz",
        positions=(Coordinate(2, 0),),
        interaction_label="",
        projectile_cover_bonus=2,
    )

    selected = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        position=enemy.position,
        active_effects=(),
        scene_objects=(cover,),
    )
    assert selected.pending is not None
    assert selected.pending.cover_bonus == 2

    confirmed = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        pending=selected.pending,
        active_effects=(),
        rng=Random(1),
        scene_objects=(cover,),
    )

    assert confirmed.pending is not None
    save = confirmed.pending.saving_throws[0]
    assert save.total == 9
    assert save.success is True
    assert any(
        modifier.label == "Połowa osłony" and modifier.value == 2
        for modifier in save.modifiers
    )


def test_missed_attack_spends_action_and_finishes_pending_flow() -> None:
    service = PlayerCombatActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(1, 0))
    state = _state(hero, enemy)
    pending = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=_source(),
        position=enemy.position,
        active_effects=(),
    ).pending
    assert pending is not None
    pending = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=_source(),
        pending=pending,
        active_effects=(),
        rng=Random(1),
    ).pending
    assert pending is not None

    transition = service.submit_attack_roll(
        state=state,
        board=BoardState(),
        source=_source(),
        pending=pending,
        active_effects=(),
        natural_roll=1,
    )

    assert transition.pending is None
    assert transition.state.turn_action.action_use == ActionUse.ACTION_USED
    assert "pudłuje" in transition.message_body
    assert dict(transition.event_payload)["hit"] is False


def test_direct_attack_compatibility_transition_applies_damage() -> None:
    service = PlayerCombatActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(1, 0))

    transition = service.resolve_direct_attack(
        state=_state(hero, enemy),
        board=BoardState(),
        source=_source(),
        target_id="enemy",
        active_effects=(),
        natural_roll=20,
        damage=4,
    )

    assert current_actor(transition.state).id == hero.id
    assert transition.state.turn_action.action_use == ActionUse.ACTION_USED
    assert next(actor for actor in transition.state.actors if actor.id == enemy.id).hp == 6
    assert transition.applied_damage is not None
    assert transition.event_type == "ui_combat_player_attack"


def test_extra_attack_actor_can_change_target_between_weapon_attacks() -> None:
    service = PlayerCombatActionFlowService()
    hero = replace(
        _actor("hero", Faction.ALLY, Coordinate(0, 0)),
        attacks_per_action=2,
    )
    first_enemy = _actor("enemy_1", Faction.ENEMY, Coordinate(1, 0))
    second_enemy = _actor("enemy_2", Faction.ENEMY, Coordinate(0, 1))
    state = _state(hero, first_enemy, second_enemy)

    first = service.resolve_direct_attack(
        state=state,
        board=BoardState(),
        source=_source(),
        target_id="enemy_1",
        active_effects=(),
        natural_roll=20,
        damage=1,
    )
    second = service.resolve_direct_attack(
        state=first.state,
        board=BoardState(),
        source=_source(),
        target_id="enemy_2",
        active_effects=(),
        natural_roll=20,
        damage=1,
    )

    assert first.state.turn_action.attacks_used == 1
    assert second.state.turn_action.attacks_used == 2
    assert next(actor for actor in second.state.actors if str(actor.id) == "enemy_1").hp == 9
    assert next(actor for actor in second.state.actors if str(actor.id) == "enemy_2").hp == 9


def test_direct_attack_applies_target_resistance_and_exposes_breakdown() -> None:
    service = PlayerCombatActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    enemy = replace(
        _actor("enemy", Faction.ENEMY, Coordinate(1, 0)),
        damage_affinities=DamageAffinityProfile(resistances=(DamageType.SLASHING,)),
    )

    transition = service.resolve_direct_attack(
        state=_state(hero, enemy),
        board=BoardState(),
        source=_source(),
        target_id="enemy",
        active_effects=(),
        natural_roll=20,
        damage=9,
    )

    assert next(actor for actor in transition.state.actors if actor.id == enemy.id).hp == 6
    assert transition.applied_damage is not None
    assert transition.applied_damage.damage.total_before_reduction == 9
    assert transition.applied_damage.damage.total_applied == 4
    payload = dict(transition.event_payload)["damage_result"]
    assert payload["damage_before_affinities"] == 9
    assert payload["damage_breakdown"]["components"][0]["adjustment"] == "resistance"
    assert "odporność" in transition.message_body


def test_ranged_attack_flow_applies_cover_ac_and_melee_disadvantage() -> None:
    service = PlayerCombatActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    target = _actor("target", Faction.ENEMY, Coordinate(4, 0))
    threat = _actor("threat", Faction.ENEMY, Coordinate(0, 1))
    state = _state(hero, target, threat)
    crossbow = AttackSource(
        name="Kusza",
        source_type=AttackSourceType.WEAPON,
        range_feet=80,
        attack_roll_request=D20RollRequest(),
        id="crossbow",
        attack_kind=AttackKind.RANGED,
    )
    cart = SceneObject(
        "cart",
        "Wóz",
        (Coordinate(2, 0),),
        "",
        projectile_cover_bonus=2,
    )

    selected = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=crossbow,
        position=target.position,
        active_effects=(),
        scene_objects=(cart,),
    )
    assert selected.pending is not None
    assert selected.pending.cover_bonus == 2
    assert selected.pending.cover_sources == ("Wóz",)
    assert selected.pending.ranged_threat_actor_ids == ("threat",)

    confirmed = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=crossbow,
        pending=selected.pending,
        active_effects=(),
        rng=Random(1),
        scene_objects=(cart,),
    )
    assert confirmed.pending is not None

    rolled = service.submit_attack_roll(
        state=state,
        board=BoardState(),
        source=crossbow,
        pending=confirmed.pending,
        active_effects=(),
        natural_roll=15,
        natural_roll_2=13,
        scene_objects=(cart,),
    )

    assert rolled.pending is None
    payload = dict(rolled.event_payload)
    assert payload["natural_rolls"] == [15, 13]
    assert payload["total"] == 13
    assert payload["hit"] is False


def test_melee_attack_flow_records_default_flanking_and_rolls_with_advantage() -> None:
    service = PlayerCombatActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 2))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(2, 2))
    ally = _actor("ally", Faction.ALLY, Coordinate(3, 2))
    state = _state(hero, enemy, ally)

    selected = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=_source(),
        position=enemy.position,
        active_effects=(),
    )
    assert selected.pending is not None
    assert selected.pending.flanking_ally_ids == ("ally",)
    confirmed = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=_source(),
        pending=selected.pending,
        active_effects=(),
        rng=Random(1),
    )
    assert confirmed.pending is not None

    rolled = service.submit_attack_roll(
        state=state,
        board=BoardState(),
        source=_source(),
        pending=confirmed.pending,
        active_effects=(),
        natural_roll=5,
        natural_roll_2=15,
    )

    payload = dict(rolled.event_payload)
    assert payload["natural_rolls"] == [5, 15]
    assert payload["total"] == 15


def test_attack_from_hidden_has_advantage_and_reveals_attacker() -> None:
    service = PlayerCombatActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(1, 0))
    state = replace(
        _state(hero, enemy),
        hidden_states=(HiddenState("hero", 18, ("enemy",)),),
    )

    selected = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=_source(),
        position=enemy.position,
        active_effects=(),
    )
    assert selected.pending is not None
    confirmed = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=_source(),
        pending=selected.pending,
        active_effects=(),
        rng=Random(1),
    )
    assert confirmed.pending is not None
    rolled = service.submit_attack_roll(
        state=state,
        board=BoardState(),
        source=_source(),
        pending=confirmed.pending,
        active_effects=(),
        natural_roll=5,
        natural_roll_2=15,
    )

    assert dict(rolled.event_payload)["natural_rolls"] == [5, 15]
    assert rolled.state.hidden_states == ()


def test_prone_attacker_rolls_with_disadvantage() -> None:
    service = PlayerCombatActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(1, 0))
    state = replace(
        _state(hero, enemy),
        condition_states=(ConditionState("hero", CombatCondition.PRONE),),
    )

    selected = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=_source(),
        position=enemy.position,
        active_effects=(),
    )
    assert selected.pending is not None
    confirmed = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=_source(),
        pending=selected.pending,
        active_effects=(),
        rng=Random(1),
    )
    assert confirmed.pending is not None
    rolled = service.submit_attack_roll(
        state=state,
        board=BoardState(),
        source=_source(),
        pending=confirmed.pending,
        active_effects=(),
        natural_roll=17,
        natural_roll_2=4,
    )

    assert dict(rolled.event_payload)["natural_rolls"] == [17, 4]
    assert dict(rolled.event_payload)["total"] == 4
