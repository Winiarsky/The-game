from dataclasses import replace

import pytest

from dnd_board_game.actors import (
    AbilityScores,
    Actor,
    ActorId,
    ActorResourcePool,
    actor_resource_pool,
    Faction,
    FeatureGrant,
    FeatureSourceKind,
    RecoveryPeriod,
)
from dnd_board_game.combat import (
    AttackKind,
    AttackSource,
    AttackSourceType,
    CombatCondition,
    DamageComponentSpec,
    DamageType,
    InitiativeEntry,
    InitiativeOrder,
    actor_as_combat_target,
    attack_source_with_hidden_advantage,
    effective_movement_speed,
    mira_ranged_armor_class_bonus,
    plan_sneak_attack,
    remove_wound_conditions_after_healing,
    start_combat,
)
from dnd_board_game.combat.archetype_flaws import attack_source_with_exposed_mira_bonus
from dnd_board_game.combat.mira_features import (
    apply_mira_wound_rider,
    attack_source_with_instinctive_dodge,
    collinear_second_target,
    legal_rear_tile,
    mira_trick_maximum,
    prepare_mira_attack,
    prepared_mira_attack_source,
    resolve_smoke_screen,
    smoke_screen_perception_penalty,
)
from dnd_board_game.combat.stealth import HiddenState
from dnd_board_game.rules import (
    ActiveEffect,
    D20RollRequest,
    DiceExpression,
    RollMode,
    D20RollInput,
    resolve_d20_roll,
)
from dnd_board_game.world import BoardState, Coordinate
from dnd_board_game.world.terrain import BLOCKING_TERRAIN


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
    position: Coordinate,
    *,
    faction: Faction = Faction.ALLY,
    dexterity: int = 18,
    features: tuple[str, ...] = (),
) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id.title(),
        ac=13,
        hp=20,
        max_hp=20,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=faction,
        ability_scores=AbilityScores(dexterity=dexterity),
        features=tuple(_feature(feature) for feature in features),
        resource_pools=(
            ActorResourcePool("trick_uses", "Fortele", 4, 4, RecoveryPeriod.LONG_REST),
        ),
    )


def _rapier() -> AttackSource:
    return AttackSource(
        "Rapier",
        AttackSourceType.WEAPON,
        5,
        D20RollRequest(),
        id="rapier",
        source_item_id="rapier",
        proficiency_id="rapier",
        attack_kind=AttackKind.MELEE,
        damage_modifier=4,
        damage_components=(
            DamageComponentSpec(
                "rapier",
                DamageType.PIERCING,
                DiceExpression(1, 8),
                modifier=4,
            ),
        ),
    )


def _state(*actors: Actor):
    order = InitiativeOrder(
        tuple(
            InitiativeEntry(
                actor,
                resolve_d20_roll(D20RollInput(D20RollRequest(), 20 - index)),
                4,
                index,
            )
            for index, actor in enumerate(actors)
        )
    )
    return start_combat(tuple(actors), order)


def test_fortels_and_smoke_penalty_follow_current_dexterity_modifier() -> None:
    weak = _actor("mira", Coordinate(0, 0), dexterity=8)
    mira = _actor("mira", Coordinate(0, 0), dexterity=19)

    assert mira_trick_maximum(weak) == 1
    assert mira_trick_maximum(mira) == 4
    assert smoke_screen_perception_penalty(mira) == -2


def test_prepared_guard_vault_is_free_and_gets_exact_attack_and_damage_bonus() -> None:
    mira = _actor("mira", Coordinate(0, 0))
    prepared = ActiveEffect(
        id="mira-prepared",
        actor_id="mira",
        kind="mira_attack_prepared",
        label="Przeskok przez gardę",
        object_id="class_feature:guard_vault",
        value=0,
    )

    source = prepared_mira_attack_source(mira, (_rapier(),), (prepared,))

    assert source is not None
    assert source.id == "guard_vault"
    assert source.resource_pool_id is None
    assert source.attack_roll_request.modifiers[-1].value == 2
    assert source.damage_components[0].modifier == 6


def test_named_mira_rapier_technique_keeps_hidden_damage_bonus() -> None:
    mira = _actor(
        "mira",
        Coordinate(0, 0),
        features=("mira_shadow_killer",),
    )
    enemy = _actor("enemy", Coordinate(1, 0), faction=Faction.ENEMY)
    prepared = ActiveEffect(
        id="mira-prepared",
        actor_id="mira",
        kind="mira_attack_prepared",
        label="Przeskok przez gardę",
        object_id="class_feature:guard_vault",
        value=0,
    )
    source = prepared_mira_attack_source(mira, (_rapier(),), (prepared,))
    assert source is not None
    hidden_source = attack_source_with_hidden_advantage(source, True)

    plan = plan_sneak_attack(
        state=_state(mira, enemy),
        active_effects=(),
        attacker=mira,
        target=enemy,
        source=hidden_source,
        roll_mode=hidden_source.attack_roll_request.mode,
    )

    assert plan.eligible is True
    bonus = next(component for component in plan.source.damage_components if component.id == "sneak_attack")
    assert bonus.dice == DiceExpression(2, 6)


def test_prepare_attack_records_exact_mode_without_spending_action_or_fortel() -> None:
    mira = _actor(
        "mira",
        Coordinate(0, 0),
        features=("hamstring_cut",),
    )
    state = _state(mira, _actor("enemy", Coordinate(1, 0), faction=Faction.ENEMY))

    prepared = prepare_mira_attack(state, (), action_id="hamstring_cut")

    assert prepared.state.turn_action.action_use.value == "action_available"
    assert actor_resource_pool(prepared.state.actors[0], "trick_uses").current == 4
    assert prepared.active_effects[0].object_id == "class_feature:hamstring_cut"


def test_paid_mira_attack_cannot_enter_targeting_with_no_fortels() -> None:
    mira = replace(
        _actor(
            "mira",
            Coordinate(0, 0),
            features=("hamstring_cut", "guard_vault"),
        ),
        resource_pools=(
            ActorResourcePool("trick_uses", "Fortele", 0, 4, RecoveryPeriod.LONG_REST),
        ),
    )
    state = _state(mira, _actor("enemy", Coordinate(1, 0), faction=Faction.ENEMY))

    with pytest.raises(ValueError, match="Brak Forteli"):
        prepare_mira_attack(state, (), action_id="hamstring_cut")
    free = prepare_mira_attack(state, (), action_id="guard_vault")
    assert free.active_effects[0].object_id == "class_feature:guard_vault"


def test_smoke_screen_spends_action_and_one_shared_fortel_and_replaces_old_stealth() -> None:
    mira = _actor(
        "mira",
        Coordinate(0, 0),
        features=("smoke_screen",),
    )
    enemy = _actor("enemy", Coordinate(1, 0), faction=Faction.ENEMY)
    state = replace(
        _state(mira, enemy),
        hidden_states=(HiddenState("mira", 18, ("enemy",)),),
    )

    resolution = resolve_smoke_screen(state, ())

    updated_mira = resolution.state.actors[0]
    assert resolution.state.turn_action.action_use.value == "action_used"
    assert actor_resource_pool(updated_mira, "trick_uses").current == 3
    assert resolution.state.hidden_states == ()
    assert {effect.kind for effect in resolution.active_effects} == {
        "smoke_screen_hide_pending",
        "movement_speed_cap",
        "disengage_until_turn_end",
    }


def test_rear_tile_must_be_in_bounds_unoccupied_and_walkable() -> None:
    board = BoardState()
    mira = _actor("mira", Coordinate(1, 1))
    enemy = _actor("enemy", Coordinate(2, 1), faction=Faction.ENEMY)
    destination = Coordinate(3, 1)

    assert legal_rear_tile(board, mira, enemy, (mira, enemy)) == destination
    blocker = _actor("blocker", destination)
    assert legal_rear_tile(board, mira, enemy, (mira, enemy, blocker)) is None
    board.set_terrain(destination, BLOCKING_TERRAIN)
    assert legal_rear_tile(board, mira, enemy, (mira, enemy)) is None

    edge_mira = replace(mira, position=Coordinate(1, 0))
    edge_enemy = replace(enemy, position=Coordinate(0, 0))
    assert legal_rear_tile(board, edge_mira, edge_enemy, (edge_mira, edge_enemy)) is None


def test_piercing_attack_finds_only_one_living_enemy_exactly_behind_first() -> None:
    mira = _actor("mira", Coordinate(1, 1))
    first = _actor("first", Coordinate(2, 1), faction=Faction.ENEMY)
    second = _actor("second", Coordinate(3, 1), faction=Faction.ENEMY)
    aside = _actor("aside", Coordinate(3, 2), faction=Faction.ENEMY)

    assert collinear_second_target(mira, first, (mira, first, second, aside)) == second
    assert collinear_second_target(
        mira,
        first,
        (mira, first, replace(second, hp=0), aside),
    ) is None


def test_wound_riders_require_applied_damage_refresh_and_clear_only_on_real_healing() -> None:
    target = _actor("target", Coordinate(2, 1), faction=Faction.ENEMY)
    none = apply_mira_wound_rider(
        (), target, action_id="hamstring_cut", source_actor_id="mira", applied_damage=0
    )
    wounded = apply_mira_wound_rider(
        (), target, action_id="hamstring_cut", source_actor_id="mira", applied_damage=1
    )
    refreshed = apply_mira_wound_rider(
        wounded.condition_states,
        target,
        action_id="hamstring_cut",
        source_actor_id="mira",
        applied_damage=3,
    )

    assert none.applied is False
    assert len(refreshed.condition_states) == 1
    assert effective_movement_speed(target, refreshed.condition_states) == 15
    assert remove_wound_conditions_after_healing(refreshed.condition_states, "target", 0) == refreshed.condition_states
    assert remove_wound_conditions_after_healing(refreshed.condition_states, "target", 1) == ()


def test_panic_flat_bonus_coexists_with_instinctive_dodge_disadvantage() -> None:
    mira = _actor(
        "mira",
        Coordinate(0, 0),
        features=("flaw_exposed_panic",),
    )
    enemy = _actor("enemy", Coordinate(1, 0), faction=Faction.ENEMY)
    source = attack_source_with_instinctive_dodge(_rapier())
    exposed = attack_source_with_exposed_mira_bonus(
        (HiddenState("mira", 18, ("other",)),),
        enemy,
        mira,
        source,
    )

    assert exposed.attack_roll_request.mode == RollMode.DISADVANTAGE
    assert [(modifier.value, modifier.stacking_key) for modifier in exposed.attack_roll_request.modifiers[-2:]] == [
        (0, "mira_instinctive_dodge"),
        (2, "flaw_exposed_panic_bonus"),
    ]


def test_ranged_evasion_affects_attack_rolls_but_not_melee_or_saves() -> None:
    mira = _actor("mira", Coordinate(0, 0), features=("mira_ranged_evasion",))
    ranged = replace(_rapier(), attack_kind=AttackKind.RANGED, range_feet=15)
    saving_throw = replace(ranged, save_ability="dexterity")

    assert mira_ranged_armor_class_bonus(mira, ranged) == 2
    assert mira_ranged_armor_class_bonus(mira, _rapier()) == 0
    assert mira_ranged_armor_class_bonus(mira, saving_throw) == 0


def test_guard_vault_escape_ac_applies_only_to_that_enemys_opportunity_attack() -> None:
    mira = _actor("mira", Coordinate(0, 0))
    marked = _actor("marked", Coordinate(1, 0), faction=Faction.ENEMY)
    other = _actor("other", Coordinate(0, 1), faction=Faction.ENEMY)
    effect = ActiveEffect(
        id="guard-vault-escape:mira:marked",
        actor_id="mira",
        kind="guard_vault_opportunity_ac",
        label="Osłona odejścia",
        object_id="class_feature:guard_vault",
        value=2,
        source_actor_id="mira",
        target_actor_id="marked",
    )

    marked_target = actor_as_combat_target(
        mira, (effect,), attacker=marked, actors=(mira, marked, other), opportunity_attack=True
    )
    other_target = actor_as_combat_target(
        mira, (effect,), attacker=other, actors=(mira, marked, other), opportunity_attack=True
    )

    assert marked_target.ac == mira.ac + 2
    assert other_target.ac == mira.ac


def test_bleeding_can_be_declared_immune_by_condition_id() -> None:
    immune = replace(
        _actor("construct", Coordinate(0, 0), faction=Faction.ENEMY),
        condition_immunities=(CombatCondition.BLEEDING.value,),
    )
    result = apply_mira_wound_rider(
        (), immune, action_id="blade_mistress", source_actor_id="mira", applied_damage=2
    )

    assert result.applied is False
    assert result.condition_states == ()


def test_instinctive_dodge_cancels_advantage_instead_of_overwriting_it() -> None:
    advantaged = replace(_rapier(), attack_roll_request=D20RollRequest(mode=RollMode.ADVANTAGE))

    assert attack_source_with_instinctive_dodge(advantaged).attack_roll_request.mode == RollMode.NORMAL
