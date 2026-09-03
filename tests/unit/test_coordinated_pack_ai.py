from dataclasses import replace
from random import Random

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.application import CombatTurnFinalizationService, EnemyTurnFlowService
from dnd_board_game.combat import (
    CombatCondition,
    ConditionState,
    DamageComponentInput,
    DamageType,
    EnemyAutoTurnResult,
    InitiativeEntry,
    InitiativeOrder,
    apply_damage_result,
    initialize_enemy_ai,
    plan_coordinated_pack_turn,
    replace_actor,
    resolve_damage,
    start_combat,
)
from dnd_board_game.rules import D20RollInput, D20RollRequest, EffectDuration, resolve_d20_roll
from dnd_board_game.scenarios import build_encounter_from_scenario, encounter_for_party_size, load_scenario
from dnd_board_game.world import BLOCKING_TERRAIN, BoardState, Coordinate


SCENARIO = "content/scenarios/ostatni_transport_01_glodne_cienie.json"


def _actor(actor_id: str, faction: Faction, position: Coordinate, *, hp: int = 20) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id,
        ac=12,
        hp=hp,
        max_hp=20,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=faction,
        ability_scores=AbilityScores(),
    )


def _state(*actors: Actor):
    request = D20RollRequest()
    order = InitiativeOrder(
        tuple(
            InitiativeEntry(actor, resolve_d20_roll(D20RollInput(request, 20 - index)), 0, index)
            for index, actor in enumerate(actors)
        )
    )
    return initialize_enemy_ai(
        start_combat(tuple(actors), order),
        profile_id="hungry_shadow_pack",
        starting_morale=4,
        encounter_seed=19,
    )


def _sources():
    encounter = encounter_for_party_size(
        build_encounter_from_scenario(load_scenario(SCENARIO)), 4
    )
    leader = next(actor for actor in encounter.actors if str(actor.id) == "hungry_shadow_leader")
    follower = next(actor for actor in encounter.actors if str(actor.id) == "hungry_shadow_s1")
    return (
        encounter.attack_source_options_by_actor[leader.id],
        encounter.attack_source_options_by_actor[follower.id][0],
    )


def test_leader_uses_life_drain_in_melee_and_cannot_heal_follower() -> None:
    leader_sources, _ = _sources()
    leader = _actor("leader", Faction.ENEMY, Coordinate(5, 5), hp=12)
    follower = _actor("follower", Faction.ENEMY, Coordinate(8, 8), hp=4)
    hero = _actor("hero", Faction.ALLY, Coordinate(6, 5))
    state = replace(
        _state(leader, follower, hero),
        condition_states=(
            ConditionState(
                "follower",
                CombatCondition.BLEEDING,
                source_actor_id="mira",
                duration=EffectDuration.PERMANENT,
            ),
        ),
    )

    plan = plan_coordinated_pack_turn(
        BoardState(),
        state,
        leader,
        leader_sources,
        role_id="leader",
        actor_roles={"leader": "leader", "follower": "skirmisher"},
    )

    assert plan.source_id == "hungry_shadow_leader_life_drain"
    assert plan.target is not None and plan.target.id == "hero"
    assert plan.life_drain is True
    assert plan.pack_heal_target_id is None


def test_leader_ranged_target_prefers_pack_support_and_queues_wounded_follower() -> None:
    leader_sources, _ = _sources()
    leader = _actor("leader", Faction.ENEMY, Coordinate(1, 1))
    follower = _actor("follower", Faction.ENEMY, Coordinate(9, 2), hp=6)
    supported = _actor("supported", Faction.ALLY, Coordinate(9, 1))
    nearer = _actor("nearer", Faction.ALLY, Coordinate(3, 3))
    state = _state(leader, follower, supported, nearer)

    plan = plan_coordinated_pack_turn(
        BoardState(),
        state,
        leader,
        leader_sources,
        role_id="leader",
        actor_roles={"leader": "leader", "follower": "skirmisher"},
    )

    assert plan.source_id == "hungry_shadow_leader_spirit_bolt"
    assert plan.target is not None and plan.target.id == "supported"
    assert plan.movement_path is None
    assert plan.pack_heal_target_id == "follower"


def test_leader_moves_only_to_range_edge_and_movement_disables_pack_heal() -> None:
    leader_sources, _ = _sources()
    leader = _actor("leader", Faction.ENEMY, Coordinate(1, 1))
    follower = _actor("follower", Faction.ENEMY, Coordinate(2, 2), hp=5)
    hero = _actor("hero", Faction.ALLY, Coordinate(15, 1))
    state = _state(leader, follower, hero)

    plan = plan_coordinated_pack_turn(
        BoardState(),
        state,
        leader,
        leader_sources,
        role_id="leader",
        actor_roles={"leader": "leader", "follower": "skirmisher"},
    )

    assert plan.target is not None and plan.target.id == "hero"
    assert plan.movement_path is not None
    assert plan.movement_path.cost_feet == 10
    assert max(
        abs(plan.moved_enemy.position.col - hero.position.col),
        abs(plan.moved_enemy.position.row - hero.position.row),
    ) == 12
    assert plan.pack_heal_target_id is None


def test_follower_focuses_supported_target_and_excludes_itself_from_bonus() -> None:
    _, source = _sources()
    attacker = _actor("attacker", Faction.ENEMY, Coordinate(4, 5))
    supporter = _actor("supporter", Faction.ENEMY, Coordinate(6, 5))
    leader = _actor("leader", Faction.ENEMY, Coordinate(1, 1))
    supported = _actor("supported", Faction.ALLY, Coordinate(5, 5))
    nearer = _actor("nearer", Faction.ALLY, Coordinate(4, 6))
    state = _state(attacker, supporter, leader, supported, nearer)

    plan = plan_coordinated_pack_turn(
        BoardState(),
        state,
        attacker,
        (source,),
        role_id="skirmisher",
        actor_roles={"leader": "leader", "attacker": "skirmisher", "supporter": "flanker"},
    )

    assert plan.target is not None and plan.target.id == "supported"
    assert plan.pack_attack_bonus == 1


def test_pack_bonus_changes_both_attack_roll_and_damage_source() -> None:
    _, source = _sources()
    attacker = _actor("attacker", Faction.ENEMY, Coordinate(4, 5))
    supporter = _actor("supporter", Faction.ENEMY, Coordinate(6, 5))
    leader = _actor("leader", Faction.ENEMY, Coordinate(1, 1))
    hero = _actor("hero", Faction.ALLY, Coordinate(5, 5))
    state = _state(attacker, supporter, leader, hero)
    roles = {"leader": "leader", "attacker": "skirmisher", "supporter": "flanker"}
    plan = plan_coordinated_pack_turn(
        BoardState(), state, attacker, (source,), role_id="skirmisher", actor_roles=roles
    )

    result = EnemyTurnFlowService().resolve(
        state=state,
        intent=plan,
        board=BoardState(),
        attack_sources_by_actor={attacker.id: source},
        attack_source_options_by_actor={attacker.id: (source,)},
        active_effects=(),
        rng=Random(2),
    ).result

    assert result.source is not None
    assert sum(mod.value for mod in result.source.attack_roll_request.modifiers) == 6
    assert result.source.damage_components[0].formula() == "1d4 + 3"


def test_leader_flees_when_last_follower_is_down_and_marks_escape() -> None:
    leader_sources, _ = _sources()
    leader = _actor("leader", Faction.ENEMY, Coordinate(5, 5))
    dead_follower = _actor("follower", Faction.ENEMY, Coordinate(6, 5), hp=0)
    hero = _actor("hero", Faction.ALLY, Coordinate(10, 10))
    state = _state(leader, dead_follower, hero)

    plan = plan_coordinated_pack_turn(
        BoardState(),
        state,
        leader,
        leader_sources,
        role_id="leader",
        actor_roles={"leader": "leader", "follower": "skirmisher"},
        escape_positions=(Coordinate(0, 5),),
    )

    assert plan.intent == "flee"
    assert plan.escaped is True
    assert plan.escape_target == Coordinate(0, 5)
    assert plan.movement_path is not None and plan.movement_path.destination == Coordinate(0, 5)
    assert "coordinated_pack_retreat:followers_lost" in plan.state.enemy_ai.used_morale_events


def test_followers_flee_after_leader_is_defeated() -> None:
    _, source = _sources()
    follower = _actor("follower", Faction.ENEMY, Coordinate(5, 5))
    dead_leader = _actor("leader", Faction.ENEMY, Coordinate(6, 5), hp=0)
    hero = _actor("hero", Faction.ALLY, Coordinate(10, 10))
    state = _state(follower, dead_leader, hero)

    plan = plan_coordinated_pack_turn(
        BoardState(),
        state,
        follower,
        (source,),
        role_id="skirmisher",
        actor_roles={"leader": "leader", "follower": "skirmisher"},
        escape_positions=(Coordinate(0, 5),),
    )

    assert plan.intent == "flee"
    assert plan.escaped is True
    assert "coordinated_pack_retreat:leader_lost" in plan.state.enemy_ai.used_morale_events


def test_unreachable_escape_becomes_cornered_without_zero_progress_loop() -> None:
    leader_sources, _ = _sources()
    leader = _actor("leader", Faction.ENEMY, Coordinate(1, 1))
    dead_follower = _actor("follower", Faction.ENEMY, Coordinate(6, 5), hp=0)
    hero = _actor("hero", Faction.ALLY, Coordinate(10, 10))
    state = _state(leader, dead_follower, hero)
    blocked = BoardState(
        terrain_by_tile={
            Coordinate(col, row): BLOCKING_TERRAIN
            for col in range(3)
            for row in range(3)
            if Coordinate(col, row) != leader.position
        }
    )

    plan = plan_coordinated_pack_turn(
        blocked,
        state,
        leader,
        leader_sources,
        role_id="leader",
        actor_roles={"leader": "leader", "follower": "skirmisher"},
        escape_positions=(Coordinate(19, 19),),
    )

    assert plan.intent == "cornered"
    assert plan.movement_path is None
    assert plan.action_used is True


def test_deferred_healing_caps_follower_and_is_skipped_if_leader_died() -> None:
    leader = _actor("leader", Faction.ENEMY, Coordinate(1, 1), hp=10)
    follower = _actor("follower", Faction.ENEMY, Coordinate(2, 1), hp=18)
    hero = _actor("hero", Faction.ALLY, Coordinate(5, 5))
    state = _state(leader, follower, hero)
    result = EnemyAutoTurnResult(
        state,
        leader,
        None,
        "atak",
        action_used=True,
        pack_heal_target_id="follower",
        pack_heal_amount=8,
    )

    committed = CombatTurnFinalizationService().commit_enemy_result(result=result, active_effects=())
    healed = next(actor for actor in committed.state.actors if actor.id == follower.id)
    assert healed.hp == 20
    assert not any(
        condition.actor_id == "follower"
        and condition.condition == CombatCondition.BLEEDING
        for condition in committed.state.condition_states
    )

    dead_state = replace_actor(state, replace(leader, hp=0))
    skipped = CombatTurnFinalizationService().commit_enemy_result(
        result=replace(result, state=dead_state), active_effects=()
    )
    untouched = next(actor for actor in skipped.state.actors if actor.id == follower.id)
    assert untouched.hp == 18


def test_life_drain_heals_half_applied_damage_rounded_down() -> None:
    leader = _actor("leader", Faction.ENEMY, Coordinate(1, 1), hp=10)
    hero = _actor("hero", Faction.ALLY, Coordinate(2, 1))
    state = _state(leader, hero)
    applied = apply_damage_result(
        hero,
        resolve_damage((DamageComponentInput(5, DamageType.NECROTIC, "test"),)),
    )
    damaged_state = replace_actor(state, applied.actor_after)
    result = EnemyAutoTurnResult(
        damaged_state,
        leader,
        None,
        "trafienie",
        applied_damage=applied,
        life_drain=True,
    )

    committed = CombatTurnFinalizationService().commit_enemy_result(result=result, active_effects=())
    healed_leader = next(actor for actor in committed.state.actors if actor.id == leader.id)
    assert healed_leader.hp == 12
