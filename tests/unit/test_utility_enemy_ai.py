from dataclasses import replace
from random import Random

import pytest

from dnd_board_game.actors import ActorId, Faction
from dnd_board_game.application import CombatTurnFinalizationService
from dnd_board_game.combat import (
    CombatStatus,
    InitiativeEntry,
    InitiativeOrder,
    combat_winner,
    initialize_enemy_ai,
    plan_utility_enemy_turn,
    refresh_pack_morale,
    replace_actor,
    resolve_planned_enemy_turn,
    start_combat,
    SceneObject,
)
from dnd_board_game.combat.setup import SetupVisibility
from dnd_board_game.combat.utility_ai import _movement_plan_toward
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.scenarios import (
    build_encounter_from_scenario,
    encounter_for_party_size,
    load_scenario,
)
from dnd_board_game.world import BoardState, Coordinate


def _encounter(party_size: int = 1):
    encounter = build_encounter_from_scenario(
        load_scenario("content/scenarios/ostatni_transport_01_glodne_cienie.json")
    )
    return encounter_for_party_size(encounter, party_size)


def _state(enemy, hero):
    actors = (enemy, hero)
    request = D20RollRequest()
    order = InitiativeOrder(
        tuple(
            InitiativeEntry(
                actor,
                resolve_d20_roll(D20RollInput(request, 20 - index)),
                2,
                index,
            )
            for index, actor in enumerate(actors)
        )
    )
    return start_combat(actors, order)


def test_party_variant_filters_ai_roles_to_active_enemies() -> None:
    encounter = _encounter(1)

    assert encounter.enemy_ai_roles == (("hungry_shadow_solo", "skirmisher"),)


def test_solo_shadow_breaks_at_half_hp_once() -> None:
    encounter = _encounter(1)
    profile = encounter.enemy_ai_profile
    assert profile is not None
    enemy = next(actor for actor in encounter.actors if actor.faction == Faction.ENEMY)
    hero = next(actor for actor in encounter.actors if actor.faction == Faction.ALLY)
    enemy = replace(enemy, hp=enemy.max_hp // 2)
    state = initialize_enemy_ai(
        _state(enemy, hero),
        profile_id=profile.id,
        starting_morale=1,
    )

    first = refresh_pack_morale(state, profile, dict(encounter.enemy_ai_roles))
    second = refresh_pack_morale(first, profile, dict(encounter.enemy_ai_roles))

    assert first.enemy_ai.morale == 0
    assert first.enemy_ai.used_morale_events == ("half_skirmishers_defeated",)
    assert second.enemy_ai == first.enemy_ai


def test_broken_enemy_reaching_escape_leaves_board_and_grants_victory() -> None:
    encounter = _encounter(1)
    profile = encounter.enemy_ai_profile
    assert profile is not None
    source_enemy = next(actor for actor in encounter.actors if actor.faction == Faction.ENEMY)
    source_hero = next(actor for actor in encounter.actors if actor.faction == Faction.ALLY)
    enemy = replace(source_enemy, position=Coordinate(1, 1))
    hero = replace(source_hero, position=Coordinate(10, 10))
    state = initialize_enemy_ai(
        _state(enemy, hero),
        profile_id=profile.id,
        starting_morale=0,
        encounter_seed=13,
    )

    plan = plan_utility_enemy_turn(
        BoardState(),
        state,
        enemy,
        encounter.attack_sources_by_actor[source_enemy.id],
        profile=profile,
        role_id="skirmisher",
        actor_roles={str(enemy.id): "skirmisher"},
        escape_positions=(Coordinate(2, 1),),
    )

    assert plan.intent == "flee"
    assert plan.escaped is True
    assert plan.state.status == CombatStatus.ACTIVE
    result = resolve_planned_enemy_turn(
        BoardState(),
        plan,
        encounter.attack_sources_by_actor[source_enemy.id],
        Random(1),
        original_state=state,
    )
    committed = CombatTurnFinalizationService().commit_enemy_result(
        result=result,
        active_effects=(),
    )

    assert committed.state.status == CombatStatus.FINISHED
    assert combat_winner(committed.state) == Faction.ALLY
    assert committed.state.enemy_ai.outcomes[0].outcome == "escaped"
    escaped = next(actor for actor in committed.state.actors if actor.id == enemy.id)
    assert escaped.hp > 0
    assert escaped.faction == Faction.NEUTRAL


def test_defeated_enemy_is_recorded_as_dead_not_escaped() -> None:
    encounter = _encounter(1)
    profile = encounter.enemy_ai_profile
    assert profile is not None
    enemy = next(actor for actor in encounter.actors if actor.faction == Faction.ENEMY)
    hero = next(actor for actor in encounter.actors if actor.faction == Faction.ALLY)
    state = initialize_enemy_ai(
        _state(enemy, hero),
        profile_id=profile.id,
        starting_morale=1,
    )

    defeated = replace_actor(state, replace(enemy, hp=0))

    assert defeated.status == CombatStatus.FINISHED
    assert combat_winner(defeated) == Faction.ALLY
    assert [(item.actor_id, item.outcome) for item in defeated.enemy_ai.outcomes] == [
        (str(enemy.id), "dead")
    ]


def test_broken_enemy_without_escape_uses_cornered_fallback() -> None:
    encounter = _encounter(1)
    profile = encounter.enemy_ai_profile
    assert profile is not None
    enemy = next(actor for actor in encounter.actors if actor.faction == Faction.ENEMY)
    hero = next(actor for actor in encounter.actors if actor.faction == Faction.ALLY)
    state = initialize_enemy_ai(
        _state(enemy, hero),
        profile_id=profile.id,
        starting_morale=0,
    )

    plan = plan_utility_enemy_turn(
        encounter.board,
        state,
        enemy,
        encounter.attack_sources_by_actor[enemy.id],
        profile=profile,
        role_id="skirmisher",
        actor_roles=dict(encounter.enemy_ai_roles),
        escape_positions=(),
    )

    assert plan.intent == "cornered"
    assert plan.escaped is False


def test_same_seed_and_state_produce_same_utility_decision() -> None:
    encounter = _encounter(1)
    profile = encounter.enemy_ai_profile
    assert profile is not None
    enemy = next(actor for actor in encounter.actors if actor.faction == Faction.ENEMY)
    hero = next(actor for actor in encounter.actors if actor.faction == Faction.ALLY)
    state = initialize_enemy_ai(
        _state(enemy, hero),
        profile_id=profile.id,
        starting_morale=1,
        encounter_seed=91,
    )
    arguments = dict(
        profile=profile,
        role_id="skirmisher",
        actor_roles=dict(encounter.enemy_ai_roles),
        escape_positions=(Coordinate(8, 0),),
    )

    first = plan_utility_enemy_turn(
        encounter.board,
        state,
        enemy,
        encounter.attack_sources_by_actor[enemy.id],
        **arguments,
    )
    second = plan_utility_enemy_turn(
        encounter.board,
        state,
        enemy,
        encounter.attack_sources_by_actor[enemy.id],
        **arguments,
    )

    assert first.intent == second.intent
    assert first.utility_score == second.utility_score
    assert first.utility_breakdown == second.utility_breakdown
    assert first.movement_path == second.movement_path


def test_advancing_shadow_scores_real_progress_toward_distant_hero() -> None:
    encounter = _encounter(1)
    profile = encounter.enemy_ai_profile
    assert profile is not None
    source_enemy = next(actor for actor in encounter.actors if actor.faction == Faction.ENEMY)
    source_hero = next(actor for actor in encounter.actors if actor.faction == Faction.ALLY)
    enemy = replace(source_enemy, position=Coordinate(0, 0))
    hero = replace(source_hero, position=Coordinate(10, 0))
    state = initialize_enemy_ai(
        _state(enemy, hero),
        profile_id=profile.id,
        starting_morale=1,
        encounter_seed=9,
    )

    plan = plan_utility_enemy_turn(
        BoardState(),
        state,
        enemy,
        encounter.attack_sources_by_actor[source_enemy.id],
        profile=profile,
        role_id="skirmisher",
        actor_roles={str(enemy.id): "skirmisher"},
        escape_positions=(Coordinate(0, 10),),
    )

    assert plan.intent == "advance"
    assert plan.movement_path is not None
    assert plan.movement_path.destination != enemy.position
    assert dict(plan.utility_breakdown)["distance_progress"] > 0


def test_pack_pressure_moves_third_shadow_to_an_unsaturated_target() -> None:
    encounter = _encounter(1)
    profile = encounter.enemy_ai_profile
    assert profile is not None
    source_enemy = next(actor for actor in encounter.actors if actor.faction == Faction.ENEMY)
    source_hero = next(actor for actor in encounter.actors if actor.faction == Faction.ALLY)
    enemy = replace(source_enemy, position=Coordinate(1, 1))
    first_hero = replace(source_hero, id=ActorId("first_hero"), position=Coordinate(1, 2))
    second_hero = replace(source_hero, id=ActorId("second_hero"), position=Coordinate(2, 1))
    state = initialize_enemy_ai(
        _state(enemy, first_hero),
        profile_id=profile.id,
        starting_morale=1,
        encounter_seed=12,
    )
    state = replace(
        state,
        actors=(enemy, first_hero, second_hero),
        enemy_ai=replace(
            state.enemy_ai,
            previous_targets=(
                ("pack_a", str(first_hero.id)),
                ("pack_b", str(first_hero.id)),
            ),
        ),
    )

    plan = plan_utility_enemy_turn(
        BoardState(),
        state,
        enemy,
        encounter.attack_sources_by_actor[source_enemy.id],
        profile=profile,
        role_id="skirmisher",
        actor_roles={str(enemy.id): "skirmisher"},
        escape_positions=(Coordinate(0, 10),),
    )

    assert plan.target is not None
    assert plan.target.id == str(second_hero.id)


def test_obsolete_old_bell_and_its_morale_event_are_removed() -> None:
    encounter = _encounter(3)
    profile = encounter.enemy_ai_profile
    assert profile is not None
    assert all(item.id != "old_bell" for item in encounter.scene_objects)
    assert all(event.event_id != "old_bell_rung" for event in profile.morale_events)


@pytest.mark.parametrize("intent", ("guard", "regroup"))
def test_guard_and_regroup_can_attack_after_movement(intent: str) -> None:
    encounter = _encounter(1)
    source_enemy = next(actor for actor in encounter.actors if actor.faction == Faction.ENEMY)
    source_hero = next(actor for actor in encounter.actors if actor.faction == Faction.ALLY)
    enemy = replace(source_enemy, position=Coordinate(0, 0))
    hero = replace(source_hero, position=Coordinate(2, 0))
    state = _state(enemy, hero)

    plan = _movement_plan_toward(
        BoardState(),
        state,
        enemy,
        (Coordinate(1, 0),),
        intent=intent,
        dash=False,
        source=encounter.attack_sources_by_actor[source_enemy.id],
    )

    assert plan is not None
    assert plan.movement_path is not None
    assert plan.movement_path.destination == Coordinate(1, 0)
    assert plan.target is not None
    assert plan.target.id == str(hero.id)
    assert plan.action_used is False


def test_damaged_pack_prefers_reachable_passive_cover_over_guarding() -> None:
    encounter = _encounter(2)
    profile = encounter.enemy_ai_profile
    assert profile is not None
    source_enemy = next(
        actor for actor in encounter.actors if str(actor.id) == "hungry_shadow_leader"
    )
    source_hero = next(actor for actor in encounter.actors if actor.faction == Faction.ALLY)
    enemy = replace(source_enemy, position=Coordinate(0, 0), hp=source_enemy.max_hp - 1)
    hero = replace(source_hero, position=Coordinate(10, 0))
    state = initialize_enemy_ai(
        _state(enemy, hero),
        profile_id=profile.id,
        starting_morale=2,
        encounter_seed=31,
    )
    defensive_spot = SceneObject(
        "cover",
        "Zwalony pień",
        (Coordinate(4, 0),),
        "",
        visibility=SetupVisibility.HIDDEN,
        cover_bonus=2,
    )

    plan = plan_utility_enemy_turn(
        BoardState(),
        state,
        enemy,
        encounter.attack_sources_by_actor[source_enemy.id],
        profile=profile,
        role_id="leader",
        actor_roles={str(enemy.id): "leader"},
        escape_positions=(Coordinate(0, 10),),
        guard_positions=(Coordinate(1, 0),),
        scene_objects=(defensive_spot,),
    )

    assert plan.intent == "regroup"
    assert plan.movement_path is not None
    assert plan.movement_path.destination == Coordinate(4, 0)
    assert "szuka osłony" in plan.message


def test_desperate_enemy_flees_instead_of_returning_to_cover() -> None:
    encounter = _encounter(2)
    profile = encounter.enemy_ai_profile
    assert profile is not None
    source_enemy = next(
        actor for actor in encounter.actors if str(actor.id) == "hungry_shadow_s2"
    )
    source_hero = next(actor for actor in encounter.actors if actor.faction == Faction.ALLY)
    enemy = replace(
        source_enemy,
        position=Coordinate(3, 11),
        hp=max(1, source_enemy.max_hp // 4),
    )
    hero = replace(source_hero, position=Coordinate(10, 20))
    state = initialize_enemy_ai(
        _state(enemy, hero),
        profile_id=profile.id,
        starting_morale=2,
        encounter_seed=47,
    )
    defensive_spot = SceneObject(
        "cover",
        "Zwalony pień",
        (Coordinate(3, 16),),
        "",
        visibility=SetupVisibility.HIDDEN,
        cover_bonus=2,
    )

    plan = plan_utility_enemy_turn(
        BoardState(),
        state,
        enemy,
        encounter.attack_sources_by_actor[source_enemy.id],
        profile=profile,
        role_id="skirmisher",
        actor_roles={str(enemy.id): "skirmisher"},
        escape_positions=(Coordinate(0, 9),),
        scene_objects=(defensive_spot,),
    )

    assert plan.intent == "flee"


def test_low_morale_enemy_flees_instead_of_returning_to_cover() -> None:
    encounter = _encounter(2)
    profile = encounter.enemy_ai_profile
    assert profile is not None
    source_enemy = next(
        actor for actor in encounter.actors if str(actor.id) == "hungry_shadow_leader"
    )
    source_hero = next(actor for actor in encounter.actors if actor.faction == Faction.ALLY)
    enemy = replace(source_enemy, position=Coordinate(3, 11))
    hero = replace(source_hero, position=Coordinate(10, 20))
    state = initialize_enemy_ai(
        _state(enemy, hero),
        profile_id=profile.id,
        starting_morale=2,
        encounter_seed=53,
    )
    state = replace(state, enemy_ai=replace(state.enemy_ai, morale=1))
    defensive_spot = SceneObject(
        "cover",
        "Zwalony pień",
        (Coordinate(3, 16),),
        "",
        visibility=SetupVisibility.HIDDEN,
        cover_bonus=2,
    )

    plan = plan_utility_enemy_turn(
        BoardState(),
        state,
        enemy,
        encounter.attack_sources_by_actor[source_enemy.id],
        profile=profile,
        role_id="leader",
        actor_roles={str(enemy.id): "leader"},
        escape_positions=(Coordinate(0, 9),),
        scene_objects=(defensive_spot,),
    )

    assert plan.intent == "flee"
