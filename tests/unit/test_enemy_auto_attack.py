import random
from dataclasses import replace

from dnd_board_game.actors import (
    AbilityScores,
    Actor,
    ActorId,
    ActorResourcePool,
    DamageAffinityProfile,
    DeathSaveState,
    Faction,
    RecoveryPeriod,
)
from dnd_board_game.combat import (
    AttackKind,
    AttackSource,
    AttackSourceType,
    CombatCondition,
    ConditionState,
    DamageComponentSpec,
    DamageType,
    HiddenState,
    InitiativeEntry,
    InitiativeOrder,
    finish_turn,
    resolve_enemy_auto_attack,
    resolve_enemy_auto_turn,
    start_combat,
)
from dnd_board_game.rules import DiceExpression, D20RollInput, D20RollRequest, RollMode, RollModifier, RollModifierType, resolve_d20_roll
from dnd_board_game.world import BoardState, Coordinate


def _actor(actor_id: str, faction: Faction, position: Coordinate, hp: int = 10) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id,
        ac=12,
        hp=hp,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=faction,
        ability_scores=AbilityScores(dexterity=14),
    )


def _source() -> AttackSource:
    return AttackSource(
        name="Szabla",
        source_type=AttackSourceType.WEAPON,
        range_feet=5,
        attack_roll_request=D20RollRequest(
            modifiers=(RollModifier("Premia ataku goblina", 4, RollModifierType.CUSTOM, stacking_key="goblin_attack"),)
        ),
        damage_die_sides=6,
        damage_modifier=2,
        damage_type="slashing",
    )


def _order(enemy: Actor, hero: Actor) -> InitiativeOrder:
    request = D20RollRequest()
    enemy_roll = resolve_d20_roll(D20RollInput(request, 20))
    hero_roll = resolve_d20_roll(D20RollInput(request, 10))
    return InitiativeOrder((InitiativeEntry(enemy, enemy_roll, 2, 0), InitiativeEntry(hero, hero_roll, 2, 1)))


def test_enemy_auto_attack_hits_with_deterministic_rng_and_applies_damage():
    enemy = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0), hp=20)
    state = start_combat((enemy, hero), _order(enemy, hero))

    result = resolve_enemy_auto_attack(BoardState(), state, enemy, _source(), random.Random(7))

    assert result.target is not None
    assert result.target.id == "hero"
    assert result.attack_roll is not None
    assert result.attack_roll.natural_roll == 11
    assert result.attack_roll.total == 15
    assert result.damage is not None
    assert result.damage.total_applied == 4
    assert result.applied_damage is not None
    assert result.applied_damage.hp_before == 20
    assert result.applied_damage.hp_after == 16
    assert result.applied_damage.defeated is False
    updated_hero = next(actor for actor in result.state.actors if actor.id == hero.id)
    assert updated_hero.hp == 16
    assert updated_hero.max_hp == 20
    assert "trafia" in result.message
    assert "HP 20 -> 16" in result.message


def test_enemy_auto_attack_reports_damage_after_target_resistance():
    enemy = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    hero = replace(
        _actor("hero", Faction.ALLY, Coordinate(0, 0), hp=20),
        damage_affinities=DamageAffinityProfile(resistances=(DamageType.SLASHING,)),
    )
    state = start_combat((enemy, hero), _order(enemy, hero))

    result = resolve_enemy_auto_attack(BoardState(), state, enemy, _source(), random.Random(7))

    assert result.damage is not None
    assert result.damage.total_before_reduction == 4
    assert result.damage.total_applied == 2
    assert result.applied_damage is not None
    assert result.applied_damage.hp_after == 18
    assert "4 -> 2 slashing" in result.message


def test_enemy_auto_attack_resolves_multicomponent_damage_per_type():
    enemy = _actor("elemental", Faction.ENEMY, Coordinate(1, 0))
    hero = replace(
        _actor("hero", Faction.ALLY, Coordinate(0, 0), hp=30),
        damage_affinities=DamageAffinityProfile(resistances=(DamageType.FIRE,)),
    )
    state = start_combat((enemy, hero), _order(enemy, hero))
    source = replace(
        _source(),
        damage_components=(
            DamageComponentSpec(
                "blade",
                DamageType.SLASHING,
                dice=DiceExpression.parse("2d6"),
                label="Ostrze",
            ),
            DamageComponentSpec(
                "flame",
                DamageType.FIRE,
                dice=DiceExpression.parse("1d4"),
                label="Płomień",
            ),
        ),
        damage_hint="",
    )

    result = resolve_enemy_auto_attack(
        BoardState(),
        state,
        enemy,
        source,
        random.Random(7),
    )

    assert result.damage is not None
    assert result.damage.total_before_reduction == 7
    assert result.damage.total_applied == 6
    assert [
        (component.damage_type, component.amount_before, component.amount_applied)
        for component in result.damage.resolved_components
    ] == [
        (DamageType.SLASHING, 6, 6),
        (DamageType.FIRE, 1, 0),
    ]


def test_enemy_save_attack_waits_for_manual_player_roll_before_damage() -> None:
    enemy = _actor("guardian", Faction.ENEMY, Coordinate(1, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0), hp=20)
    state = start_combat((enemy, hero), _order(enemy, hero))
    source = replace(
        _source(),
        name="Kamienny podmuch",
        save_ability="dexterity",
        save_dc=12,
        save_damage_on_success="half",
    )

    result = resolve_enemy_auto_attack(BoardState(), state, enemy, source, random.Random(7))

    assert result.attack_roll is None
    assert result.saving_throw_request is not None
    assert result.saving_throw_request.ability == "dexterity"
    assert result.saving_throw_request.dc == 12
    assert result.base_damage == 5
    assert result.applied_damage is None
    assert next(actor for actor in result.state.actors if actor.id == hero.id).hp == 20


def test_enemy_auto_attack_rolls_two_d20_for_disadvantage():
    enemy = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0), hp=20)
    state = start_combat((enemy, hero), _order(enemy, hero))
    source = _source()
    source = AttackSource(
        name=source.name,
        source_type=source.source_type,
        range_feet=source.range_feet,
        attack_roll_request=D20RollRequest(mode=RollMode.DISADVANTAGE, modifiers=source.attack_roll_request.modifiers),
        damage_die_sides=source.damage_die_sides,
        damage_modifier=source.damage_modifier,
        damage_type=source.damage_type,
    )

    result = resolve_enemy_auto_attack(BoardState(), state, enemy, source, random.Random(7))

    assert result.attack_roll is not None
    assert result.attack_roll.natural_rolls == (11, 5)
    assert result.attack_roll.natural_roll == 5


def test_enemy_ranged_attack_in_melee_gains_disadvantage_automatically():
    enemy = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0), hp=20)
    state = start_combat((enemy, hero), _order(enemy, hero))
    source = replace(
        _source(),
        name="Łuk",
        range_feet=80,
        attack_kind=AttackKind.RANGED,
    )

    result = resolve_enemy_auto_attack(BoardState(), state, enemy, source, random.Random(7))

    assert result.attack_roll is not None
    assert result.attack_roll.mode == RollMode.DISADVANTAGE
    assert result.attack_roll.natural_rolls == (11, 5)
    assert result.positioning.ranged_threat_actor_ids == ("hero",)


def test_enemy_melee_attack_uses_default_flanking_advantage():
    enemy = _actor("goblin", Faction.ENEMY, Coordinate(1, 2))
    hero = _actor("hero", Faction.ALLY, Coordinate(2, 2), hp=20)
    ally = _actor("goblin_ally", Faction.ENEMY, Coordinate(3, 2))
    state = start_combat((enemy, hero, ally), _order(enemy, hero))

    result = resolve_enemy_auto_attack(
        BoardState(), state, enemy, _source(), random.Random(7)
    )

    assert result.attack_roll is not None
    assert result.attack_roll.mode == RollMode.ADVANTAGE
    assert result.attack_roll.natural_rolls == (11, 5)
    assert result.attack_roll.natural_roll == 11
    assert result.positioning.flanking_ally_ids == ("goblin_ally",)


def test_enemy_close_hit_against_unconscious_target_rolls_critical_damage_dice():
    enemy = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    hero = replace(
        _actor("hero", Faction.ALLY, Coordinate(0, 0), hp=20),
        hp=0,
        uses_death_saves=True,
        death_saves=DeathSaveState(),
    )
    state = start_combat((enemy, hero), _order(enemy, hero))

    result = resolve_enemy_auto_attack(BoardState(), state, enemy, _source(), random.Random(7))

    assert result.attack_resolution is not None and result.attack_resolution.critical is True
    assert result.damage is not None and result.damage.total_applied == 8
    assert result.applied_damage is not None
    assert result.applied_damage.death_save_failures_added == 2


def test_enemy_auto_attack_skips_when_no_legal_target():
    enemy = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(5, 5), hp=20)
    state = start_combat((enemy, hero), _order(enemy, hero))

    result = resolve_enemy_auto_attack(BoardState(), state, enemy, _source(), random.Random(7))

    assert result.target is None
    assert result.attack_roll is None
    assert result.action_used is True
    assert "nie ma legalnego celu" in result.message


def test_enemy_auto_attack_ignores_defeated_targets():
    enemy = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    defeated_hero = _actor("hero", Faction.ALLY, Coordinate(0, 0), hp=0)
    state = start_combat((enemy, defeated_hero), _order(enemy, defeated_hero))

    result = resolve_enemy_auto_attack(BoardState(), state, enemy, _source(), random.Random(7))

    assert result.target is None


def test_enemy_auto_attack_tie_breaks_targets_by_position_and_id():
    enemy = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    hero_b = _actor("hero_b", Faction.ALLY, Coordinate(0, 1), hp=20)
    hero_a = _actor("hero_a", Faction.ALLY, Coordinate(0, 0), hp=20)
    state = start_combat((enemy, hero_b, hero_a), _order(enemy, hero_b))

    result = resolve_enemy_auto_attack(BoardState(), state, enemy, _source(), random.Random(7))

    assert result.target is not None
    assert result.target.id == "hero_a"


def test_enemy_auto_attack_action_is_not_available_twice_in_turn():
    enemy = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0), hp=20)
    state = start_combat((enemy, hero), _order(enemy, hero))

    first = resolve_enemy_auto_attack(BoardState(), state, enemy, _source(), random.Random(7))
    second = resolve_enemy_auto_attack(BoardState(), first.state, enemy, _source(), random.Random(7))

    assert first.action_used is True
    assert second.action_used is False
    assert "już zużyta" in second.message


def test_enemy_limited_attack_consumes_pool_and_blocks_reuse_until_recharge() -> None:
    enemy = replace(
        _actor("goblin", Faction.ENEMY, Coordinate(1, 0)),
        resource_pools=(
            ActorResourcePool("special", "Atak specjalny", 1, 1, RecoveryPeriod.NEVER),
        ),
    )
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0), hp=20)
    state = start_combat((enemy, hero), _order(enemy, hero))
    source = replace(_source(), resource_pool_id="special")

    first = resolve_enemy_auto_attack(BoardState(), state, enemy, source, random.Random(7))
    spent_enemy = next(actor for actor in first.state.actors if actor.id == enemy.id)
    next_turn_state = finish_turn(finish_turn(first.state))
    second = resolve_enemy_auto_attack(
        BoardState(),
        next_turn_state,
        spent_enemy,
        source,
        random.Random(7),
    )

    assert spent_enemy.resource_pools[0].current == 0
    assert first.action_used is True
    assert second.action_used is False
    assert "oczekuje na recharge" in second.message


def test_enemy_has_advantage_against_adjacent_prone_target() -> None:
    enemy = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0), hp=20)
    state = replace(
        start_combat((enemy, hero), _order(enemy, hero)),
        condition_states=(ConditionState("hero", CombatCondition.PRONE),),
    )

    result = resolve_enemy_auto_attack(BoardState(), state, enemy, _source(), random.Random(7))

    assert result.attack_roll is not None
    assert result.attack_roll.mode == RollMode.ADVANTAGE
    assert len(result.attack_roll.natural_rolls) == 2


def test_enemy_uses_search_instead_of_moving_toward_hidden_target() -> None:
    enemy = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(5, 5), hp=20)
    state = replace(
        start_combat((enemy, hero), _order(enemy, hero)),
        hidden_states=(HiddenState("hero", 10, ("goblin",)),),
    )

    result = resolve_enemy_auto_turn(
        BoardState(), state, enemy, _source(), random.Random(7)
    )

    assert result.movement_path is None
    assert result.attack_roll is None
    assert result.action_used is True
    assert result.state.hidden_states == ()
    assert "Search (11)" in result.message


def test_finish_turn_after_enemy_attack_advances_to_hero():
    enemy = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0), hp=20)
    state = start_combat((enemy, hero), _order(enemy, hero))

    result = resolve_enemy_auto_attack(BoardState(), state, enemy, _source(), random.Random(7))
    next_state = finish_turn(result.state)

    assert next_state.initiative_order.current_actor.id == hero.id
