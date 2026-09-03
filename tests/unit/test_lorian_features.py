from dataclasses import replace
from random import Random

import pytest

from dnd_board_game.actors import (
    AbilityScores,
    Actor,
    ActorId,
    Faction,
    FeatureGrant,
    FeatureSourceKind,
)
from dnd_board_game.application import (
    ClassFeatureReactionFlowService,
    PlayerCombatActionFlowService,
)
from dnd_board_game.combat import (
    ActionUse,
    AttackDeclaration,
    AttackKind,
    AttackSource,
    AttackSourceType,
    CombatCondition,
    ConditionState,
    DamageComponentInput,
    DamageType,
    EnemyAutoTurnResult,
    InitiativeEntry,
    InitiativeOrder,
    ReactionKind,
    actor_as_combat_target,
    area_positions_for_center,
    apply_damage_result,
    attack_source_with_combat_effects,
    attack_source_with_target_combat_effects,
    consume_next_attack_effects,
    grant_bonus_attacks,
    resolve_actor_saving_throw,
    resolve_attack,
    resolve_damage,
    start_combat,
    effective_movement_speed,
)
from dnd_board_game.combat.lorian_features import (
    apply_lorian_entangling_effects,
    apply_lorian_shot_companion_effects,
    lorian_attacks_per_action,
    lorian_entangling_shot_source,
    lorian_hand_crossbow_source,
    lorian_has_live_audience,
    prepare_lorian_shot,
    prepared_lorian_shot_source,
    validate_lorian_optical_target,
    social_grace_bonus,
)
from dnd_board_game.rules import (
    ActiveEffect,
    D20RollInput,
    D20RollRequest,
    EffectDuration,
    RollMode,
    SavingThrowRequest,
    SavingThrowResult,
    resolve_d20_roll,
)
from dnd_board_game.exploration import (
    CheckAggregation,
    CheckParticipants,
    ConsequenceTarget,
    ExplorationCheckPlan,
)
from dnd_board_game.ui.exploration_app import (
    _actor_check_request,
    _check_inputs_from_payload,
)
from dnd_board_game.world import BoardState, Coordinate


def _feature(feature_id: str) -> FeatureGrant:
    return FeatureGrant(
        feature_id,
        feature_id,
        FeatureSourceKind.SCENARIO,
        "test",
        action_ids=(feature_id,),
    )


def _actor(
    actor_id: str,
    faction: Faction,
    position: Coordinate,
    *,
    hp: int = 20,
    features: tuple[str, ...] = (),
) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id.title(),
        ac=12,
        hp=hp,
        max_hp=20,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=faction,
        ability_scores=AbilityScores(dexterity=15, charisma=19),
        features=tuple(_feature(feature_id) for feature_id in features),
    )


def _state(*actors: Actor):
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


def _crossbow() -> AttackSource:
    return AttackSource(
        "Kusza ręczna",
        AttackSourceType.WEAPON,
        30,
        D20RollRequest(),
        id="hand_crossbow",
        damage_die_sides=6,
        damage_modifier=2,
        damage_type="piercing",
        ability="dexterity",
        source_item_id="hand_crossbow",
        proficiency_id="hand_crossbow",
        attack_kind=AttackKind.RANGED,
        ammunition_type="bolt",
        loading=True,
        long_range_feet=120,
    )


def _effect(kind: str, actor_id: str, *, source_id: str = "lorian") -> ActiveEffect:
    return ActiveEffect(
        id=f"{kind}:{actor_id}",
        actor_id=actor_id,
        kind=kind,
        label=kind,
        object_id=f"class_feature:{kind}",
        value=1,
        source_actor_id=source_id,
        duration=EffectDuration.UNTIL_TURN_START,
        expiration_actor_id=source_id,
    )


def test_crossbowman_has_two_untracked_shots_but_special_shots_replace_both() -> None:
    lorian = _actor(
        "lorian",
        Faction.ALLY,
        Coordinate(0, 0),
        features=("crossbowman", "mocking_shot", "provoking_shot"),
    )
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(5, 0))
    state = _state(lorian, enemy)
    source = lorian_hand_crossbow_source(_crossbow())

    assert source.range_feet == 45
    assert source.long_range_feet is None
    assert source.ammunition_type is None
    assert source.loading is False
    assert lorian_attacks_per_action(lorian, source) == 2

    prepared = prepare_lorian_shot(state, (), action_id="mocking_shot")
    special = prepared_lorian_shot_source(
        lorian,
        (source,),
        prepared.active_effects,
    )
    assert special is not None
    assert special.limited_attacks is True
    assert special.on_hit_effect_kind == "lorian_mocked_attack"
    assert lorian_attacks_per_action(lorian, special) == 1


def test_crossbowman_runtime_accepts_two_targets_and_rejects_a_third_attack() -> None:
    lorian = _actor(
        "lorian",
        Faction.ALLY,
        Coordinate(0, 0),
        features=("crossbowman",),
    )
    first = _actor("first", Faction.ENEMY, Coordinate(2, 0))
    second = _actor("second", Faction.ENEMY, Coordinate(3, 0))
    state = _state(lorian, first, second)
    source = replace(
        lorian_hand_crossbow_source(_crossbow()),
        source_item_id=None,
    )
    service = PlayerCombatActionFlowService()

    first_attack = service.resolve_direct_attack(
        state=state,
        board=BoardState(),
        source=source,
        target_id="first",
        active_effects=(),
        natural_roll=15,
        damage=2,
    )
    second_attack = service.resolve_direct_attack(
        state=first_attack.state,
        board=BoardState(),
        source=source,
        target_id="second",
        active_effects=first_attack.active_effects,
        natural_roll=15,
        damage=2,
    )
    assert second_attack.state.turn_action.attacks_used == 2

    with pytest.raises(ValueError, match="wszystkie ataki"):
        service.resolve_direct_attack(
            state=second_attack.state,
            board=BoardState(),
            source=source,
            target_id="first",
            active_effects=second_attack.active_effects,
            natural_roll=15,
            damage=2,
        )


def test_special_shot_cannot_be_prepared_without_the_named_feature() -> None:
    lorian = _actor("lorian", Faction.ALLY, Coordinate(0, 0))
    state = _state(lorian, _actor("enemy", Faction.ENEMY, Coordinate(1, 0)))

    with pytest.raises(ValueError, match="nie posiada"):
        prepare_lorian_shot(state, (), action_id="mocking_shot")


def test_mocking_shot_consumes_only_first_attack_penalty_not_wisdom_penalty() -> None:
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(1, 0))
    source = lorian_hand_crossbow_source(_crossbow())
    mocked_attack = replace(
        _effect("lorian_mocked_attack", "enemy"),
        duration=EffectDuration.UNTIL_NEXT_ATTACK,
        expiration_actor_id="enemy",
    )
    effects = apply_lorian_shot_companion_effects(
        (mocked_attack,),
        attacker_id="lorian",
        target_id="enemy",
        source=replace(source, on_hit_effect_kind="lorian_mocked_attack"),
    )

    modified = attack_source_with_combat_effects(enemy, source, effects)
    assert modified.attack_roll_request.mode == RollMode.DISADVANTAGE
    after_attack = consume_next_attack_effects(effects, "enemy")
    assert {effect.kind for effect in after_attack} == {"lorian_mocked_wisdom"}

    with pytest.raises(ValueError, match="two d20"):
        resolve_actor_saving_throw(
            enemy,
            SavingThrowRequest("wisdom", 14, "test"),
            natural_roll=15,
            active_effects=after_attack,
        )
    save = resolve_actor_saving_throw(
        enemy,
        SavingThrowRequest("wisdom", 14, "test"),
        natural_roll=15,
        natural_roll_2=4,
        active_effects=after_attack,
    )
    assert save.natural_roll == 4


def test_provocation_scales_with_damage_against_lorian_and_other_targets() -> None:
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(1, 0))
    lorian = _actor("lorian", Faction.ALLY, Coordinate(0, 0))
    ally = _actor("ally", Faction.ALLY, Coordinate(0, 1))
    effect = replace(_effect("lorian_provoked", "enemy"), value=7)
    source = _crossbow()

    against_lorian = attack_source_with_target_combat_effects(
        enemy, lorian, source, (effect,)
    )
    against_ally = attack_source_with_target_combat_effects(
        enemy, ally, source, (effect,)
    )
    assert sum(
        modifier.value for modifier in against_lorian.attack_roll_request.modifiers
    ) == 7
    assert sum(
        modifier.value for modifier in against_ally.attack_roll_request.modifiers
    ) == -7


def test_provoking_shot_records_actual_applied_damage_as_modifier() -> None:
    lorian = _actor(
        "lorian",
        Faction.ALLY,
        Coordinate(0, 0),
        features=("crossbowman", "provoking_shot"),
    )
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(2, 0))
    state = _state(lorian, enemy)
    prepared = prepare_lorian_shot(state, (), action_id="provoking_shot")
    source = prepared_lorian_shot_source(lorian, (_crossbow(),), prepared.active_effects)
    assert source is not None

    resolved = PlayerCombatActionFlowService().resolve_direct_attack(
        state=state,
        board=BoardState(),
        source=replace(source, source_item_id=None),
        target_id="enemy",
        active_effects=prepared.active_effects,
        natural_roll=15,
        damage=6,
    )

    effect = next(
        effect
        for effect in resolved.active_effects
        if effect.kind == "lorian_provoked"
    )
    assert effect.value == 6


def test_social_grace_applies_to_every_noncombat_charisma_test() -> None:
    lorian = _actor(
        "lorian",
        Faction.ALLY,
        Coordinate(0, 0),
        features=("social_grace_bargaining",),
    )

    assert social_grace_bonus(
        lorian,
        ability="charisma",
        skill="persuasion",
        in_combat=False,
    ) == 2
    assert social_grace_bonus(
        lorian,
        ability="charisma",
        skill="intimidation",
        in_combat=False,
        verbal=False,
    ) == 2
    assert social_grace_bonus(
        lorian,
        ability="charisma",
        skill="performance",
        in_combat=True,
    ) == 0


def test_optical_scope_has_two_locked_shots_extra_range_and_spends_movement() -> None:
    lorian = _actor(
        "lorian",
        Faction.ALLY,
        Coordinate(0, 0),
        features=("crossbowman", "optical_scope"),
    )
    first = _actor("first", Faction.ENEMY, Coordinate(9, 0))
    second = _actor("second", Faction.ENEMY, Coordinate(8, 1))
    state = _state(lorian, first, second)
    prepared = prepare_lorian_shot(state, (), action_id="optical_scope")
    source = prepared_lorian_shot_source(lorian, (_crossbow(),), prepared.active_effects)
    assert source is not None
    source = replace(source, source_item_id=None)
    assert source.range_feet == 60
    assert lorian_attacks_per_action(lorian, source) == 2
    assert sum(mod.value for mod in source.attack_roll_request.modifiers) == 2

    service = PlayerCombatActionFlowService()
    first_attack = service.resolve_direct_attack(
        state=state,
        board=BoardState(),
        source=source,
        target_id="first",
        active_effects=prepared.active_effects,
        natural_roll=15,
        damage=3,
    )
    assert first_attack.state.turn_action.movement_action_used is True
    with pytest.raises(ValueError, match="ten sam cel"):
        validate_lorian_optical_target(
            first_attack.active_effects,
            attacker_id="lorian",
            target_id="second",
            source=source,
        )
    second_attack = service.resolve_direct_attack(
        state=first_attack.state,
        board=BoardState(),
        source=source,
        target_id="first",
        active_effects=first_attack.active_effects,
        natural_roll=15,
        damage=3,
    )
    assert second_attack.state.turn_action.attacks_used == 2

    moved_state = replace(
        state,
        turn_action=replace(state.turn_action, movement_used_feet=5),
    )
    with pytest.raises(ValueError, match="przed ruchem"):
        prepare_lorian_shot(moved_state, (), action_id="optical_scope")


def test_entangling_shot_is_centered_3x3_and_controls_all_saved_targets() -> None:
    lorian = _actor(
        "lorian",
        Faction.ALLY,
        Coordinate(0, 0),
        features=("entangling_shot",),
    )
    source = lorian_entangling_shot_source(lorian, (_crossbow(),))
    assert source is not None and source.area is not None
    assert source.range_feet == 45
    assert (source.area.length_feet, source.area.width_feet) == (15, 15)
    assert len(
        area_positions_for_center(BoardState(), Coordinate(4, 4), source.area)
    ) == 9
    saves = (
        SavingThrowResult("enemy", "Enemy", "dexterity", 14, 18, 0, 18, True, 0.0),
        SavingThrowResult("ally", "Ally", "dexterity", 14, 4, 0, 4, False, 1.0),
    )
    effects = apply_lorian_entangling_effects((), attacker_id="lorian", saving_throws=saves)
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(1, 0))
    ally = _actor("ally", Faction.ALLY, Coordinate(1, 1))
    assert effective_movement_speed(enemy, (), effects) == 15
    assert effective_movement_speed(ally, (), effects) == 0
    assert all(effect.expiration_actor_id == "lorian" for effect in effects)


def test_lorian_specials_require_a_living_conscious_ally_within_ten_feet() -> None:
    lorian = _actor(
        "lorian",
        Faction.ALLY,
        Coordinate(0, 0),
        features=("flaw_needs_audience",),
    )
    near = _actor("near", Faction.ALLY, Coordinate(2, 0))
    far = replace(near, position=Coordinate(3, 0))
    down = replace(near, hp=0)

    assert lorian_has_live_audience(lorian, (lorian, near)) is True
    assert lorian_has_live_audience(lorian, (lorian, far)) is False
    assert lorian_has_live_audience(lorian, (lorian, down)) is False
    assert lorian_has_live_audience(
        lorian,
        (lorian, near),
        condition_states=(ConditionState("near", CombatCondition.UNCONSCIOUS),),
    ) is False
    isolated = replace(
        lorian,
        features=(*lorian.features, _feature("optical_scope")),
    )
    with pytest.raises(ValueError, match="żywego i przytomnego sojusznika"):
        prepare_lorian_shot(
            _state(isolated, _actor("enemy", Faction.ENEMY, Coordinate(1, 0))),
            (),
            action_id="optical_scope",
        )


def test_social_grace_is_present_in_real_exploration_check_request() -> None:
    lorian = _actor(
        "lorian",
        Faction.ALLY,
        Coordinate(0, 0),
        features=("social_grace_bargaining", "improvisation"),
    )
    plan = ExplorationCheckPlan(
        participants=CheckParticipants.SINGLE_ACTOR,
        aggregation=CheckAggregation.LEAD_RESULT,
        consequence_targets=(ConsequenceTarget.NPC,),
        ability="charisma",
        skill="persuasion",
        dc=15,
        lead_actor_id="lorian",
    )

    request = _actor_check_request(lorian, plan)

    assert any(
        modifier.label == "Obycie i targowanie" and modifier.value == 2
        for modifier in request.modifiers
    )


def test_improvisation_replaces_only_a_failed_charisma_roll_and_second_result_is_final() -> None:
    lorian = _actor(
        "lorian",
        Faction.ALLY,
        Coordinate(0, 0),
        features=("social_grace_bargaining", "improvisation"),
    )
    plan = ExplorationCheckPlan(
        participants=CheckParticipants.SINGLE_ACTOR,
        aggregation=CheckAggregation.LEAD_RESULT,
        consequence_targets=(ConsequenceTarget.NPC,),
        ability="charisma",
        skill="persuasion",
        dc=15,
        lead_actor_id="lorian",
    )

    failed = _check_inputs_from_payload(
        (lorian,),
        plan,
        {"lorian": {"natural_roll": 5, "improvisation_roll": 18}},
    )[0]
    already_successful = _check_inputs_from_payload(
        (lorian,),
        plan,
        {"lorian": {"natural_roll": 20, "improvisation_roll": 2}},
    )[0]

    assert failed.natural_roll == 18
    assert already_successful.natural_roll == 20
    assert failed.natural_rerolls == ()


def test_improvisation_rejects_wrong_actor_and_non_charisma_checks() -> None:
    other = _actor(
        "other",
        Faction.ALLY,
        Coordinate(0, 0),
        features=("improvisation",),
    )
    plan = ExplorationCheckPlan(
        participants=CheckParticipants.SINGLE_ACTOR,
        aggregation=CheckAggregation.LEAD_RESULT,
        consequence_targets=(ConsequenceTarget.SCENE,),
        ability="wisdom",
        skill="insight",
        dc=15,
        lead_actor_id="other",
    )

    with pytest.raises(ValueError, match="wyłącznie Lorianowi"):
        _check_inputs_from_payload(
            (other,),
            plan,
            {"other": {"natural_roll": 5, "improvisation_roll": 18}},
        )


def test_improvisation_rejects_a_second_use_for_the_same_npc() -> None:
    lorian = _actor(
        "lorian",
        Faction.ALLY,
        Coordinate(0, 0),
        features=("improvisation",),
    )
    plan = ExplorationCheckPlan(
        participants=CheckParticipants.SINGLE_ACTOR,
        aggregation=CheckAggregation.LEAD_RESULT,
        consequence_targets=(ConsequenceTarget.NPC,),
        ability="charisma",
        skill="persuasion",
        dc=15,
        lead_actor_id="lorian",
    )

    with pytest.raises(ValueError, match="raz na danego NPC"):
        _check_inputs_from_payload(
            (lorian,),
            plan,
            {"lorian": {"natural_roll": 5, "improvisation_roll": 18}},
            improvisation_allowed_actor_ids=frozenset(),
        )


def test_distracting_shout_requires_lorians_inspiration_and_shared_reaction() -> None:
    lorian = _actor(
        "lorian",
        Faction.ALLY,
        Coordinate(0, 0),
        features=("distracting_shout",),
    )
    ally = _actor("ally", Faction.ALLY, Coordinate(1, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(2, 0))
    state = _state(enemy, lorian, ally)
    source = _crossbow()
    attack_roll = resolve_d20_roll(D20RollInput(source.attack_roll_request, 15))
    attack = resolve_attack(
        AttackDeclaration(enemy, actor_as_combat_target(ally), source),
        attack_roll,
        ActionUse.ACTION_AVAILABLE,
    )
    damage = resolve_damage((DamageComponentInput(7, DamageType.PIERCING),))
    applied = apply_damage_result(ally, damage)
    result = EnemyAutoTurnResult(
        state=state,
        enemy=enemy,
        target=actor_as_combat_target(ally),
        message="atak",
        attack_roll=attack_roll,
        attack_resolution=attack,
        damage=damage,
        applied_damage=applied,
        updated_target=applied.actor_after,
        action_used=True,
        source=source,
    )
    service = ClassFeatureReactionFlowService()
    assert service.distracting_shout_options(
        board=BoardState(),
        state=state,
        active_effects=(),
        enemy_result=result,
    ) == ()

    inspiration = _effect("bardic_inspiration", "ally")
    options = service.distracting_shout_options(
        board=BoardState(),
        state=state,
        active_effects=(inspiration,),
        enemy_result=result,
    )
    assert len(options) == 1
    assert options[0].kind == ReactionKind.DISTRACTING_SHOUT
    resolution = service.apply_distracting_shout(
        state=state,
        enemy_result=result,
        option=options[0],
        die_roll=6,
    )
    assert resolution.damage_after == 0
    assert resolution.result.updated_target.hp == ally.hp
    assert "lorian" in resolution.state.spent_reaction_actor_ids
    assert inspiration.kind == "bardic_inspiration"


@pytest.mark.parametrize(
    ("effect_kinds", "expected_bonus_action"),
    [
        (
            ("accelerated_refrain", "accelerated_refrain_cast_attack"),
            ActionUse.ACTION_AVAILABLE,
        ),
        (("accelerated_refrain",), ActionUse.ACTION_USED),
    ],
)
def test_accelerated_refrain_cast_shot_is_free_but_later_third_shot_uses_bonus_action(
    effect_kinds: tuple[str, ...],
    expected_bonus_action: ActionUse,
) -> None:
    lorian = _actor(
        "lorian",
        Faction.ALLY,
        Coordinate(0, 0),
        features=("crossbowman",),
    )
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(2, 0))
    source = replace(lorian_hand_crossbow_source(_crossbow()), source_item_id=None)
    state = grant_bonus_attacks(_state(lorian, enemy), count=1, source_id=source.id)
    effects = tuple(_effect(kind, "lorian") for kind in effect_kinds)
    service = PlayerCombatActionFlowService()

    selected = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        position=enemy.position,
        active_effects=effects,
        class_bonus_attack=True,
    )
    assert selected.pending is not None
    confirmed = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        pending=selected.pending,
        active_effects=effects,
        rng=Random(1),
    )
    assert confirmed.pending is not None
    resolved = service.submit_attack_roll(
        state=state,
        board=BoardState(),
        source=source,
        pending=confirmed.pending,
        active_effects=effects,
        natural_roll=15,
    )

    assert resolved.state.turn_action.bonus_attacks_remaining == 0
    assert resolved.state.turn_action.bonus_action_use == expected_bonus_action


def test_accelerated_refrain_third_shot_is_rejected_after_bonus_action_was_spent() -> None:
    lorian = _actor(
        "lorian",
        Faction.ALLY,
        Coordinate(0, 0),
        features=("crossbowman",),
    )
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(2, 0))
    source = replace(lorian_hand_crossbow_source(_crossbow()), source_item_id=None)
    state = grant_bonus_attacks(_state(lorian, enemy), count=1, source_id=source.id)
    state = replace(
        state,
        turn_action=replace(
            state.turn_action,
            bonus_action_use=ActionUse.ACTION_USED,
        ),
    )
    effects = (_effect("accelerated_refrain", "lorian"),)
    service = PlayerCombatActionFlowService()
    selected = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        position=enemy.position,
        active_effects=effects,
        class_bonus_attack=True,
    )
    assert selected.pending is not None
    confirmed = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        pending=selected.pending,
        active_effects=effects,
        rng=Random(1),
    )
    assert confirmed.pending is not None

    with pytest.raises(ValueError, match="bonusowa"):
        service.submit_attack_roll(
            state=state,
            board=BoardState(),
            source=source,
            pending=confirmed.pending,
            active_effects=effects,
            natural_roll=15,
        )
