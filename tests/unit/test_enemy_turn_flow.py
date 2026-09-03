from random import Random

import pytest

from dataclasses import replace

from dnd_board_game.actors import (
    AbilityScores,
    Actor,
    ActorId,
    CreatureSize,
    DamageAffinityProfile,
    Faction,
    FeatureGrant,
    FeatureSourceKind,
)
from dnd_board_game.application import EnemyTurnFlowService, EnemyTurnTransitionKind
from dnd_board_game.combat import (
    ActiveCombatEffect,
    AttackKind,
    AttackSource,
    AttackSourceType,
    CombatState,
    CombatCondition,
    InitiativeEntry,
    InitiativeOrder,
    DamageType,
    HiddenState,
    start_combat,
    has_condition,
)
from dnd_board_game.rules import (
    D20RollInput,
    D20RollRequest,
    RollModifier,
    RollModifierType,
    resolve_d20_roll,
)
from dnd_board_game.world import BLOCKING_TERRAIN, BoardState, Coordinate


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
    return start_combat(tuple(actors), order)


def _source() -> AttackSource:
    return AttackSource(
        "Miecz",
        AttackSourceType.WEAPON,
        5,
        D20RollRequest(),
        damage_fixed=1,
    )


def _stage_command(variant: str, target_id: str = "enemy") -> ActiveCombatEffect:
    return ActiveCombatEffect(
        id=f"stage-command:{variant}:{target_id}",
        actor_id=target_id,
        kind=f"stage_command:{variant}",
        label=f"Rozkaz sceniczny: {variant}",
        object_id="combat_action:stage_command",
        value=0,
        source_actor_id="lorian",
    )


def test_plan_validates_enemy_turn_and_preserves_intent_event() -> None:
    service = EnemyTurnFlowService()
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(0, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 0))

    transition = service.plan(
        state=_state(enemy, hero),
        board=BoardState(),
        attack_sources_by_actor={enemy.id: _source()},
    )

    assert transition.enemy_id == "enemy"
    assert transition.intent.target is not None
    assert transition.event_type == "ui_combat_enemy_turn_intent"
    assert dict(transition.event_payload)["target_id"] == "hero"

    with pytest.raises(ValueError, match="To nie jest tura przeciwnika"):
        service.plan(
            state=_state(hero, enemy),
            board=BoardState(),
            attack_sources_by_actor={enemy.id: _source()},
        )


@pytest.mark.parametrize(
    ("variant", "enemy_col", "expected_col"),
    [("approach", 8, 5), ("retreat", 3, 6)],
)
def test_stage_command_forces_at_most_fifteen_feet_then_enemy_still_acts(
    variant: str,
    enemy_col: int,
    expected_col: int,
) -> None:
    service = EnemyTurnFlowService()
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(enemy_col, 0))
    lorian = _actor("lorian", Faction.ALLY, Coordinate(0, 0))
    ranged = replace(
        _source(),
        id="bow",
        range_feet=60,
        attack_kind=AttackKind.RANGED,
    )

    transition = service.plan(
        state=_state(enemy, lorian),
        board=BoardState(),
        attack_sources_by_actor={enemy.id: ranged},
        active_effects=(_stage_command(variant),),
    )

    assert transition.intent.enemy.position == Coordinate(expected_col, 0)
    assert transition.intent.movement_path is not None
    assert transition.intent.movement_path.cost_feet == 15
    assert transition.intent.target is not None
    assert transition.intent.target.id == "lorian"
    assert "Rozkaz sceniczny" in transition.board_message


def test_stage_command_silence_uses_weapon_instead_of_spell() -> None:
    service = EnemyTurnFlowService()
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(0, 0))
    lorian = _actor("lorian", Faction.ALLY, Coordinate(1, 0))
    spell = replace(_source(), id="spell", source_type=AttackSourceType.SPELL)
    weapon = replace(_source(), id="weapon")

    transition = service.plan(
        state=_state(enemy, lorian),
        board=BoardState(),
        attack_sources_by_actor={enemy.id: spell},
        attack_source_options_by_actor={enemy.id: (spell, weapon)},
        active_effects=(_stage_command("silence"),),
    )

    assert transition.intent.source_id in {"", "weapon"}
    assert transition.intent.target is not None
    resolved = service.resolve(
        state=_state(enemy, lorian),
        intent=transition.intent,
        board=BoardState(),
        attack_sources_by_actor={enemy.id: spell},
        attack_source_options_by_actor={enemy.id: (spell, weapon)},
        active_effects=(_stage_command("silence"),),
        rng=Random(1),
    )
    assert resolved.result.source is not None
    assert resolved.result.source.id == "weapon"


def test_stage_command_silence_without_nonverbal_attack_finishes_without_loop() -> None:
    service = EnemyTurnFlowService()
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(0, 0))
    lorian = _actor("lorian", Faction.ALLY, Coordinate(1, 0))
    spell = replace(_source(), id="spell", source_type=AttackSourceType.SPELL)

    transition = service.plan(
        state=_state(enemy, lorian),
        board=BoardState(),
        attack_sources_by_actor={enemy.id: spell},
        active_effects=(_stage_command("silence"),),
    )

    assert transition.intent.target is None
    assert transition.intent.action_used is True
    assert transition.intent.intent == "stage_command_silence"


def test_provoking_shot_prefers_lorian_only_when_he_is_a_legal_target() -> None:
    service = EnemyTurnFlowService()
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(0, 0))
    nearest = _actor("nearest", Faction.ALLY, Coordinate(1, 0))
    lorian = _actor("lorian", Faction.ALLY, Coordinate(2, 0))
    ranged = replace(
        _source(),
        id="bow",
        range_feet=15,
        attack_kind=AttackKind.RANGED,
    )
    provoked = ActiveCombatEffect(
        id="provoked:enemy",
        actor_id="enemy",
        kind="lorian_provoked",
        label="Prowokujący ostrzał",
        object_id="class_feature:provoking_shot",
        value=2,
        source_actor_id="lorian",
    )

    transition = service.plan(
        state=_state(enemy, nearest, lorian),
        board=BoardState(),
        attack_sources_by_actor={enemy.id: ranged},
        active_effects=(provoked,),
    )

    assert transition.intent.target is not None
    assert transition.intent.target.id == "lorian"


def test_enemy_path_collision_reveals_only_that_observer_and_requires_replan() -> None:
    service = EnemyTurnFlowService()
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(0, 0))
    mira = replace(
        _actor("mira", Faction.ALLY, Coordinate(1, 0)),
        features=(
            FeatureGrant(
                "mira_shadow_stealth",
                "Mistrzyni ukrycia",
                FeatureSourceKind.SCENARIO,
                "boardgame_archetype:mira",
            ),
        ),
    )
    visible_hero = _actor("hero", Faction.ALLY, Coordinate(4, 0))
    state = replace(
        _state(enemy, mira, visible_hero),
        hidden_states=(HiddenState("mira", 18, ("enemy",)),),
    )
    sources = {enemy.id: _source()}

    intent = service.plan(
        state=state,
        board=BoardState(),
        attack_sources_by_actor=sources,
    )
    transition = service.resolve(
        state=state,
        intent=intent.intent,
        board=BoardState(),
        attack_sources_by_actor=sources,
        active_effects=(),
        rng=Random(1),
    )

    assert transition.kind == EnemyTurnTransitionKind.MOVEMENT
    assert transition.message_title == "Przypadkowe wykrycie"
    assert transition.result.accidentally_detected_actor_id == "mira"
    assert transition.result.movement_path.destination == enemy.position
    assert transition.result.state.hidden_states == ()
    assert "skradanie automatycznie się kończy" in transition.message_body


def test_adjacent_enemy_result_is_classified_as_attack_confirmation() -> None:
    service = EnemyTurnFlowService()
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(0, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 0))
    state = _state(enemy, hero)
    sources = {enemy.id: _source()}
    intent = service.plan(state=state, board=BoardState(), attack_sources_by_actor=sources)

    transition = service.resolve(
        state=state,
        intent=intent.intent,
        board=BoardState(),
        attack_sources_by_actor=sources,
        active_effects=(),
        rng=Random(1),
    )

    assert transition.kind == EnemyTurnTransitionKind.ATTACK
    assert transition.result.target is not None
    assert transition.result.target.id == "hero"
    assert transition.message_title == "Atak przeciwnika"


def test_pack_leap_requests_save_after_charge_and_prones_on_failure() -> None:
    service = EnemyTurnFlowService()
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(0, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(3, 0))
    pack_ally = _actor("pack_ally", Faction.ENEMY, Coordinate(3, 1))
    source = replace(
        _source(),
        attack_roll_request=D20RollRequest(
            modifiers=(RollModifier("pewne trafienie", 20, RollModifierType.CUSTOM),)
        ),
        conditional_on_hit_save_ability="strength",
        conditional_on_hit_save_dc=12,
        conditional_on_hit_save_condition="prone",
        conditional_on_hit_minimum_movement_feet=10,
        conditional_on_hit_requires_adjacent_ally=True,
    )
    state = _state(enemy, hero, pack_ally)
    sources = {enemy.id: source}
    intent = service.plan(state=state, board=BoardState(), attack_sources_by_actor=sources)

    transition = service.resolve(
        state=state,
        intent=intent.intent,
        board=BoardState(),
        attack_sources_by_actor=sources,
        active_effects=(),
        rng=Random(3),
    )

    assert transition.result.saving_throw_request is not None
    assert transition.result.saving_throw_request.dc == 12
    saved = service.resolve_player_saving_throw(
        result=transition.result,
        natural_roll=1,
    )
    assert has_condition(saved.result.state.condition_states, "hero", CombatCondition.PRONE)


def test_large_enemy_attack_opens_giant_killer_reaction_for_adjacent_ranger() -> None:
    service = EnemyTurnFlowService()
    enemy = replace(
        _actor("enemy", Faction.ENEMY, Coordinate(0, 0)),
        size=CreatureSize.LARGE,
    )
    ranger = replace(
        _actor("ranger", Faction.ALLY, Coordinate(1, 0)),
        features=(
            FeatureGrant(
                "giant_killer",
                "Giant Killer",
                FeatureSourceKind.SUBCLASS,
                "hunter",
            ),
        ),
    )
    state = _state(enemy, ranger)
    sources = {enemy.id: _source(), ranger.id: _source()}
    intent = service.plan(
        state=state,
        board=BoardState(),
        attack_sources_by_actor=sources,
    )

    transition = service.resolve(
        state=state,
        intent=intent.intent,
        board=BoardState(),
        attack_sources_by_actor=sources,
        active_effects=(),
        rng=Random(2),
    )

    assert transition.kind == EnemyTurnTransitionKind.REACTION
    assert transition.reaction_window is not None
    option = transition.reaction_window.current_option
    assert option.kind.value == "ready_attack"
    assert option.effect_id == "giant_killer"
    assert option.trigger_event == "giant_killer"


def test_enemy_multiattack_uses_next_data_driven_source() -> None:
    service = EnemyTurnFlowService()
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(0, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 0))
    first_source = replace(_source(), name="Pierwszy", id="first")
    second_source = replace(_source(), name="Drugi", id="second")
    sources = {enemy.id: first_source}
    sequence = {enemy.id: (first_source, second_source)}
    state = _state(enemy, hero)

    first_intent = service.plan(
        state=state,
        board=BoardState(),
        attack_sources_by_actor=sources,
        multiattack_sources_by_actor=sequence,
    )
    first = service.resolve(
        state=state,
        intent=first_intent.intent,
        board=BoardState(),
        attack_sources_by_actor=sources,
        multiattack_sources_by_actor=sequence,
        active_effects=(),
        rng=Random(1),
    )
    second_intent = service.plan(
        state=first.result.state,
        board=BoardState(),
        attack_sources_by_actor=sources,
        multiattack_sources_by_actor=sequence,
    )
    second = service.resolve(
        state=first.result.state,
        intent=second_intent.intent,
        board=BoardState(),
        attack_sources_by_actor=sources,
        multiattack_sources_by_actor=sequence,
        active_effects=(),
        rng=Random(2),
    )

    assert first.result.source is not None and first.result.source.id == "first"
    assert first.result.state.turn_action.attacks_used == 1
    assert second.result.source is not None and second.result.source.id == "second"
    assert second.result.state.turn_action.attacks_used == 2


def test_enemy_save_flow_applies_manual_roll_then_damage_affinity() -> None:
    service = EnemyTurnFlowService()
    enemy = _actor("guardian", Faction.ENEMY, Coordinate(0, 0))
    hero = replace(
        _actor("hero", Faction.ALLY, Coordinate(1, 0)),
        damage_affinities=DamageAffinityProfile(resistances=(DamageType.SLASHING,)),
    )
    state = _state(enemy, hero)
    source = replace(
        _source(),
        name="Kamienny podmuch",
        damage_fixed=8,
        damage_type="slashing",
        save_ability="dexterity",
        save_dc=12,
        save_damage_on_success="half",
    )
    sources = {enemy.id: source}
    intent = service.plan(state=state, board=BoardState(), attack_sources_by_actor=sources)
    pending = service.resolve(
        state=state,
        intent=intent.intent,
        board=BoardState(),
        attack_sources_by_actor=sources,
        active_effects=(),
        rng=Random(1),
    )

    resolved = service.resolve_player_saving_throw(
        result=pending.result,
        natural_roll=10,
    )

    assert pending.result.saving_throw_request is not None
    assert pending.message_title == "Efekt przeciwnika"
    assert resolved.saving_throw.success is True  # 10 + DEX 2 = ST 12
    assert resolved.result.damage is not None
    assert resolved.result.damage.total_before_reduction == 4  # save halves first
    assert resolved.result.damage.total_applied == 2  # resistance halves again
    assert resolved.result.updated_target is not None
    assert resolved.result.updated_target.hp == 8


def test_enemy_save_flow_accepts_bardic_inspiration_modifier() -> None:
    service = EnemyTurnFlowService()
    enemy = _actor("guardian", Faction.ENEMY, Coordinate(0, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 0))
    state = _state(enemy, hero)
    source = replace(
        _source(),
        damage_fixed=8,
        save_ability="dexterity",
        save_dc=15,
        save_damage_on_success="half",
    )
    sources = {enemy.id: source}
    intent = service.plan(
        state=state,
        board=BoardState(),
        attack_sources_by_actor=sources,
    )
    pending = service.resolve(
        state=state,
        intent=intent.intent,
        board=BoardState(),
        attack_sources_by_actor=sources,
        active_effects=(),
        rng=Random(1),
    )

    resolved = service.resolve_player_saving_throw(
        result=pending.result,
        natural_roll=10,
        additional_modifiers=(
            RollModifier(
                "Bardic Inspiration k6",
                3,
                RollModifierType.FEATURE,
                stacking_key="bardic_inspiration",
            ),
        ),
    )

    assert resolved.saving_throw.success is True
    assert resolved.saving_throw.total == 15


def test_enemy_approach_is_classified_as_movement_confirmation() -> None:
    service = EnemyTurnFlowService()
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(0, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(8, 0))
    state = _state(enemy, hero)
    sources = {enemy.id: _source()}
    intent = service.plan(state=state, board=BoardState(), attack_sources_by_actor=sources)

    transition = service.resolve(
        state=state,
        intent=intent.intent,
        board=BoardState(),
        attack_sources_by_actor=sources,
        active_effects=(),
        rng=Random(2),
    )

    assert transition.kind == EnemyTurnTransitionKind.MOVEMENT
    assert transition.result.movement_path is not None
    assert transition.message_title == "Ruch przeciwnika"


def test_ready_enemy_moves_trigger_uses_real_ai_movement_path() -> None:
    service = EnemyTurnFlowService()
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(0, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(4, 0))
    state = _state(enemy, hero)
    sources = {enemy.id: _source(), hero.id: _source()}
    ready = ActiveCombatEffect(
        id="ready:hero",
        actor_id="hero",
        kind="ready_attack",
        label="Ready",
        object_id="combat_action:ready:enemy_moves",
        value=0,
    )
    intent = service.plan(state=state, board=BoardState(), attack_sources_by_actor=sources)

    transition = service.resolve(
        state=state,
        intent=intent.intent,
        board=BoardState(),
        attack_sources_by_actor=sources,
        active_effects=(ready,),
        rng=Random(3),
    )

    assert transition.kind == EnemyTurnTransitionKind.REACTION
    assert transition.result.movement_path is not None
    assert transition.result.movement_path.origin != transition.result.movement_path.destination
    assert transition.reaction_window is not None
    assert transition.reaction_window.current_option.kind.value == "ready_attack"
    assert transition.ready_trigger is not None
    assert transition.ready_trigger.readied_actor_id == "hero"
    assert transition.ready_trigger.trigger == "enemy_moves"


def test_leaving_blocked_adjacent_hero_reach_prompts_opportunity_attack() -> None:
    service = EnemyTurnFlowService()
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(1, 0))
    nearby_hero = _actor("nearby", Faction.ALLY, Coordinate(0, 0))
    distant_hero = _actor("distant", Faction.ALLY, Coordinate(6, 0))
    state = _state(enemy, nearby_hero, distant_hero)
    board = BoardState()
    board.add_wall(nearby_hero.position, enemy.position)
    board.set_terrain(Coordinate(0, 1), BLOCKING_TERRAIN)
    board.set_terrain(Coordinate(1, 1), BLOCKING_TERRAIN)
    sources = {
        enemy.id: _source(),
        nearby_hero.id: _source(),
        distant_hero.id: _source(),
    }
    intent = service.plan(state=state, board=board, attack_sources_by_actor=sources)

    transition = service.resolve(
        state=state,
        intent=intent.intent,
        board=board,
        attack_sources_by_actor=sources,
        active_effects=(),
        rng=Random(4),
    )

    assert transition.kind == EnemyTurnTransitionKind.REACTION
    assert transition.reaction_window is not None
    assert transition.reaction_window.current_option.kind.value == "opportunity_attack"
    assert transition.threat_actor_ids == ("nearby",)
    assert transition.event_type == "ui_combat_enemy_opportunity_pending"


def test_enemy_movement_collects_ready_and_opportunity_into_one_ordered_window() -> None:
    service = EnemyTurnFlowService()
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(1, 0))
    nearby_hero = _actor("nearby", Faction.ALLY, Coordinate(0, 0))
    ranged_hero = _actor("ranged", Faction.ALLY, Coordinate(6, 0))
    state = _state(enemy, nearby_hero, ranged_hero)
    board = BoardState()
    board.add_wall(nearby_hero.position, enemy.position)
    board.set_terrain(Coordinate(0, 1), BLOCKING_TERRAIN)
    board.set_terrain(Coordinate(1, 1), BLOCKING_TERRAIN)
    ranged_source = replace(
        _source(),
        range_feet=30,
        attack_kind=AttackKind.RANGED,
    )
    sources = {
        enemy.id: _source(),
        nearby_hero.id: _source(),
        ranged_hero.id: ranged_source,
    }
    ready = ActiveCombatEffect(
        id="ready:ranged",
        actor_id="ranged",
        kind="ready_attack",
        label="Ready",
        object_id="combat_action:ready:enemy_moves",
        value=0,
    )
    intent = service.plan(
        state=state,
        board=board,
        attack_sources_by_actor=sources,
    )

    transition = service.resolve(
        state=state,
        intent=intent.intent,
        board=board,
        attack_sources_by_actor=sources,
        active_effects=(ready,),
        rng=Random(4),
    )

    assert transition.kind == EnemyTurnTransitionKind.REACTION
    assert transition.reaction_window is not None
    assert [
        option.kind.value for option in transition.reaction_window.options
    ] == ["ready_attack", "opportunity_attack"]
    assert [
        option.reactor_actor_id for option in transition.reaction_window.options
    ] == ["ranged", "nearby"]
