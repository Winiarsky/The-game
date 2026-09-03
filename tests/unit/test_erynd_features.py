from dataclasses import replace
from types import SimpleNamespace

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
    PlayerCombatActionFlowService,
    PlayerCombatResourceFlowService,
)
from dnd_board_game.application.player_combat_action_flow import PendingPlayerAttack
from dnd_board_game.combat import (
    ActionEconomyCost,
    AttackKind,
    AttackSource,
    AttackSourceType,
    CombatCondition,
    DamageComponentSpec,
    DamageType,
    InitiativeEntry,
    InitiativeOrder,
    attack_source_with_combat_effects,
    combat_armor_class,
    effective_movement_speed,
    has_condition,
    reaction_available_for,
    start_combat,
)
from dnd_board_game.combat.erynd_features import (
    first_blood_damage,
    prepare_erynd_arrow,
    prepared_erynd_arrow_source,
    resolve_erynd_aim,
)
from dnd_board_game.rules import (
    ActiveEffect,
    D20RollInput,
    D20RollRequest,
    DiceExpression,
    EffectDuration,
    EffectEvent,
    EffectEventType,
    EffectSource,
    EffectSourceType,
    RollMode,
    expire_active_effects,
    resolve_d20_roll,
)
from dnd_board_game.world import Coordinate


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
        ability_scores=AbilityScores(dexterity=18),
        proficiency_bonus=2,
        features=tuple(_feature(feature_id) for feature_id in features),
    )


def _state(*actors: Actor):
    request = D20RollRequest()
    order = InitiativeOrder(
        tuple(
            InitiativeEntry(
                actor,
                resolve_d20_roll(D20RollInput(request, 20 - index)),
                4,
                index,
            )
            for index, actor in enumerate(actors)
        )
    )
    return start_combat(tuple(actors), order)


def _longbow() -> AttackSource:
    component = DamageComponentSpec(
        id="weapon",
        damage_type=DamageType.PIERCING,
        dice=DiceExpression(1, 8),
        modifier=4,
        label="Długi łuk",
    )
    return AttackSource(
        "Długi łuk",
        AttackSourceType.WEAPON,
        75,
        D20RollRequest(),
        id="longbow_shot",
        damage_hint="1k8+4",
        damage_components=(component,),
        ability="dexterity",
        source_item_id="longbow",
        attack_kind=AttackKind.RANGED,
        proficiency_id="longbow",
        ammunition_type="arrow",
    )


def test_arrow_rolls_are_validated_and_shape_the_prepared_longbow_source() -> None:
    erynd = _actor(
        "erynd",
        Faction.ALLY,
        Coordinate(0, 0),
        features=("anchoring_arrow", "exposing_arrow", "disrupting_arrow", "double_shot"),
    )
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(4, 0))
    state = _state(erynd, enemy)

    with pytest.raises(ValueError, match="k4"):
        prepare_erynd_arrow(state, (), action_id="anchoring_arrow", die_roll=5)

    anchored = prepare_erynd_arrow(
        state,
        (),
        action_id="anchoring_arrow",
        die_roll=3,
    )
    anchored_source = prepared_erynd_arrow_source(
        erynd,
        (_longbow(),),
        anchored.active_effects,
    )
    assert anchored_source is not None
    assert anchored_source.on_hit_effect_remaining_rounds == 3
    assert anchored_source.on_hit_effect_duration == EffectDuration.UNTIL_ENCOUNTER_END
    assert anchored_source.on_hit_save_dc == 14
    assert anchored_source.resource_cost == 1

    anchor_effect = ActiveEffect(
        id="erynd-anchor:test",
        actor_id=str(enemy.id),
        kind="erynd_anchored",
        label="Strzała kotwicząca",
        object_id="class_feature:anchoring_arrow",
        value=3,
        remaining_rounds=anchored_source.on_hit_effect_remaining_rounds,
        duration=anchored_source.on_hit_effect_duration,
    )
    after_one = expire_active_effects(
        (anchor_effect,), EffectEvent(EffectEventType.ROUND_ENDED)
    )
    after_two = expire_active_effects(
        after_one.active_effects, EffectEvent(EffectEventType.ROUND_ENDED)
    )
    after_three = expire_active_effects(
        after_two.active_effects, EffectEvent(EffectEventType.ROUND_ENDED)
    )
    assert after_one.active_effects[0].remaining_rounds == 2
    assert after_two.active_effects[0].remaining_rounds == 1
    assert after_three.active_effects == ()

    exposed = prepare_erynd_arrow(
        state,
        (),
        action_id="exposing_arrow",
        die_roll=7,
    )
    exposed_source = prepared_erynd_arrow_source(
        erynd,
        (_longbow(),),
        exposed.active_effects,
    )
    assert exposed_source is not None
    assert exposed_source.on_hit_effect_value == 7
    assert exposed_source.on_hit_effect_duration == EffectDuration.UNTIL_TURN_START

    doubled = prepare_erynd_arrow(state, (), action_id="double_shot")
    double_source = prepared_erynd_arrow_source(
        erynd,
        (_longbow(),),
        doubled.active_effects,
    )
    assert double_source is not None
    assert double_source.ammunition_cost == 1
    assert double_source.resource_cost == 2
    assert double_source.damage_components[0].dice == DiceExpression(2, 8)
    assert double_source.damage_components[0].modifier == 8
    assert double_source.damage_components[0].formula(critical=True) == "4d8 + 8"


def test_aim_spends_all_movement_and_grants_advantage_only_to_the_longbow() -> None:
    erynd = _actor(
        "erynd",
        Faction.ALLY,
        Coordinate(0, 0),
        features=("aim",),
    )
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(4, 0))
    resolved = resolve_erynd_aim(_state(erynd, enemy), ())
    knife = AttackSource(
        "Nóż myśliwski",
        AttackSourceType.WEAPON,
        5,
        D20RollRequest(),
        source_item_id="hunting_knife",
        attack_kind=AttackKind.MELEE,
    )

    aimed_bow = attack_source_with_combat_effects(
        erynd,
        _longbow(),
        resolved.active_effects,
    )
    aimed_knife = attack_source_with_combat_effects(
        erynd,
        knife,
        resolved.active_effects,
    )

    assert resolved.state.turn_action.movement_action_used is True
    assert aimed_bow.attack_roll_request.mode == RollMode.ADVANTAGE
    assert aimed_knife.attack_roll_request.mode == RollMode.NORMAL

    moved_state = _state(erynd, enemy)
    moved_state = replace(
        moved_state,
        turn_action=replace(moved_state.turn_action, movement_used_feet=5),
    )
    with pytest.raises(ValueError, match="przed dobrowolnym ruchem"):
        resolve_erynd_aim(moved_state, ())


def test_first_blood_applies_only_to_an_unwounded_target() -> None:
    erynd = _actor(
        "erynd",
        Faction.ALLY,
        Coordinate(0, 0),
        features=("first_blood",),
    )
    fresh = _actor("fresh", Faction.ENEMY, Coordinate(4, 0))
    wounded = _actor("wounded", Faction.ENEMY, Coordinate(5, 0), hp=19)

    bonus = first_blood_damage(erynd, fresh, DamageType.PIERCING)

    assert bonus is not None
    assert bonus.dice == DiceExpression(1, 8)
    assert first_blood_damage(erynd, wounded, DamageType.PIERCING) is None


def test_arrow_statuses_change_speed_ac_attack_mode_and_reactions() -> None:
    erynd = _actor("erynd", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(4, 0))
    exposed = ActiveEffect(
        id="exposed",
        actor_id="enemy",
        kind="erynd_exposed_ac",
        label="Strzała odsłaniająca",
        object_id="class_feature:exposing_arrow",
        value=6,
    )
    anchored = ActiveEffect(
        id="anchored",
        actor_id="enemy",
        kind="erynd_anchored",
        label="Strzała kotwicząca",
        object_id="class_feature:anchoring_arrow",
        value=2,
    )

    assert combat_armor_class(enemy, (exposed,)) == 6
    assert effective_movement_speed(enemy, (), (anchored,)) == 0

    prepared = prepare_erynd_arrow(
        _state(
            _actor(
                "erynd",
                Faction.ALLY,
                Coordinate(0, 0),
                features=("disrupting_arrow",),
            ),
            enemy,
        ),
        (),
        action_id="disrupting_arrow",
    )
    disrupting = prepared_erynd_arrow_source(
        _actor(
            "erynd",
            Faction.ALLY,
            Coordinate(0, 0),
            features=("disrupting_arrow",),
        ),
        (_longbow(),),
        prepared.active_effects,
    )
    assert disrupting is not None
    state = _state(
        _actor("erynd", Faction.ALLY, Coordinate(0, 0)),
        enemy,
    )
    transition = PlayerCombatActionFlowService().submit_damage(
        state=state,
        source=disrupting,
        pending=PendingPlayerAttack(
            attacker_id="erynd",
            target_id="enemy",
            source_id="disrupting_arrow",
            stage="damage_roll",
            hit=True,
        ),
        active_effects=(),
        component_totals={"weapon": 5},
    )

    assert has_condition(
        transition.state.condition_states,
        "enemy",
        CombatCondition.NO_REACTIONS,
    )
    enemy_after = next(actor for actor in transition.state.actors if str(actor.id) == "enemy")
    assert reaction_available_for(transition.state, enemy_after) is False
    disrupted = next(effect for effect in transition.active_effects if effect.kind == "erynd_disrupted")
    assert disrupted.duration == EffectDuration.UNTIL_NEXT_ATTACK
    assert disrupted.additional_expirations[0].duration == EffectDuration.UNTIL_TURN_END


def test_hunters_mark_moves_from_a_defeated_target_without_action_or_resource_cost() -> None:
    erynd = _actor("erynd", Faction.ALLY, Coordinate(0, 0))
    defeated = _actor("defeated", Faction.ENEMY, Coordinate(3, 0), hp=0)
    next_target = _actor("next", Faction.ENEMY, Coordinate(4, 0))
    state = _state(erynd, defeated, next_target)
    mark = ActiveEffect(
        id="hunters-mark:erynd:defeated",
        actor_id="defeated",
        kind="hunters_mark",
        label="Znak łowcy",
        object_id="combat_action:hunters_mark",
        value=6,
        source_actor_id="erynd",
        target_actor_id="defeated",
        source=EffectSource(EffectSourceType.SPELL, "hunters_mark", "Znak łowcy"),
        duration=EffectDuration.CONCENTRATION,
        spell_level=1,
    )
    action = SimpleNamespace(
        id="hunters_mark",
        action_type="targeted_status",
        label="Znak łowcy",
        spell_level=1,
        target_faction="enemy",
        target_count=1,
        upcast_targets_per_level=0,
        range_feet=90,
        area=None,
        concentration=True,
        effect_kind="hunters_mark",
        value=6,
        action_cost=ActionEconomyCost.BONUS_ACTION,
        cast_flag="cast_hunters_mark",
        duration="encounter",
    )
    service = PlayerCombatResourceFlowService()

    started = service.start_concentration(
        state=state,
        active_effects=(mark,),
        action=action,
    )
    assert started.pending_action is not None
    resolved = service.confirm_concentration(
        state=state,
        active_effects=(mark,),
        action=action,
        pending=started.pending_action,
        target_id="next",
    )

    assert resolved.state.turn_action.bonus_action_use.value == "action_available"
    assert dict(resolved.event_payload)["free_transfer"] is True
    assert [effect.actor_id for effect in resolved.active_effects if effect.kind == "hunters_mark"] == ["next"]
