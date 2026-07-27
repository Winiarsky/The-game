from dataclasses import replace
from typing import Callable

import pytest

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.application import (
    CombatReactionFlowService,
    CounterspellReactionFlowService,
    DefensiveSpellReactionFlowService,
    PlayerReactionFlowService,
)
from dnd_board_game.combat import (
    ActionUse,
    ActiveCombatEffect,
    AttackDeclaration,
    AttackSource,
    AttackSourceType,
    CombatState,
    DamageComponentInput,
    DamageComponentSpec,
    DamageType,
    EnemyAutoTurnResult,
    InitiativeEntry,
    InitiativeOrder,
    actor_as_combat_target,
    apply_damage_result,
    combat_armor_class,
    expire_turn_start_effects,
    reaction_available_for,
    replace_actor,
    resolve_attack,
    resolve_damage,
    start_combat,
    use_actor_reaction,
)
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.rules import DiceExpression
from dnd_board_game.scenarios import build_encounter_from_scenario, load_scenario
from dnd_board_game.world import BoardState, Coordinate, PathResult, find_path


def _actor(
    actor_id: str,
    faction: Faction,
    position: Coordinate,
    *,
    hp: int = 10,
) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id.title(),
        ac=12,
        hp=hp,
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


def _source(*, damage_fixed: int = 3) -> AttackSource:
    return AttackSource(
        "Miecz",
        AttackSourceType.WEAPON,
        5,
        D20RollRequest(),
        damage_fixed=damage_fixed,
    )


def _path(state: CombatState, actor: Actor) -> PathResult:
    return find_path(BoardState(), actor, state.actors, Coordinate(0, 2))


def _roll(natural_roll: int) -> Callable[[D20RollRequest], D20RollInput]:
    return lambda request: D20RollInput(request, natural_roll)


def _enemy_spell_result(
    state: CombatState,
    enemy: Actor,
    target: Actor,
    *,
    spell_level: int,
) -> EnemyAutoTurnResult:
    source = AttackSource(
        "Wrogi płomień",
        AttackSourceType.SPELL,
        60,
        D20RollRequest(),
        damage_fixed=4,
        id="enemy_flame",
        spell_level=spell_level,
        cast_level=spell_level,
    )
    target_snapshot = actor_as_combat_target(target)
    attack_roll = resolve_d20_roll(D20RollInput(source.attack_roll_request, 15))
    attack = resolve_attack(
        AttackDeclaration(enemy, target_snapshot, source),
        attack_roll,
        ActionUse.ACTION_AVAILABLE,
    )
    damage = resolve_damage((DamageComponentInput(4, DamageType.FIRE),))
    applied = apply_damage_result(target, damage)
    return EnemyAutoTurnResult(
        state=replace_actor(state, applied.actor_after),
        enemy=enemy,
        target=target_snapshot,
        message="Wrogi czar trafia.",
        attack_roll=attack_roll,
        attack_resolution=attack,
        damage=damage,
        applied_damage=applied,
        updated_target=applied.actor_after,
        action_used=True,
        source=source,
    )


def test_counterspell_automatically_interrupts_spell_at_selected_slot_level() -> None:
    encounter = build_encounter_from_scenario(
        load_scenario("content/scenarios/gate_skirmish.json")
    )
    cleric = next(actor for actor in encounter.actors if str(actor.id) == "cleric")
    enemy = next(actor for actor in encounter.actors if actor.faction == Faction.ENEMY)
    state = _state(enemy, cleric)
    enemy_result = _enemy_spell_result(state, enemy, cleric, spell_level=3)
    service = CounterspellReactionFlowService()

    option = service.option(
        board=encounter.board,
        state=state,
        enemy_result=enemy_result,
        actions_by_actor=encounter.combat_actions_by_actor,
    )

    assert option is not None
    assert option.cast_levels == (3,)
    resolution = service.cast(
        state=state,
        enemy_result=enemy_result,
        option=option,
        cast_level=3,
        actions_by_actor=encounter.combat_actions_by_actor,
    )
    updated_cleric = next(
        actor for actor in resolution.result.state.actors if actor.id == cleric.id
    )
    assert resolution.countered
    assert resolution.check_request is None
    assert resolution.result.spell_countered
    assert resolution.result.applied_damage is None
    assert updated_cleric.hp == cleric.hp
    assert next(slot for slot in updated_cleric.spell_slots if slot.level == 3).remaining == 0
    assert not reaction_available_for(resolution.state, updated_cleric)


def test_counterspell_uses_spellcasting_ability_check_against_stronger_spell() -> None:
    encounter = build_encounter_from_scenario(
        load_scenario("content/scenarios/gate_skirmish.json")
    )
    cleric = next(actor for actor in encounter.actors if str(actor.id) == "cleric")
    enemy = next(actor for actor in encounter.actors if actor.faction == Faction.ENEMY)
    state = _state(enemy, cleric)
    enemy_result = _enemy_spell_result(state, enemy, cleric, spell_level=4)
    service = CounterspellReactionFlowService()
    option = service.option(
        board=encounter.board,
        state=state,
        enemy_result=enemy_result,
        actions_by_actor=encounter.combat_actions_by_actor,
    )
    assert option is not None

    started = service.cast(
        state=state,
        enemy_result=enemy_result,
        option=option,
        cast_level=3,
        actions_by_actor=encounter.combat_actions_by_actor,
    )
    assert not started.countered
    assert started.check_dc == 14
    assert started.check_modifier == 3
    assert started.check_request is not None

    resolved = service.resolve_check(
        state=started.state,
        enemy_result=started.result,
        caster_id=str(cleric.id),
        cast_level=3,
        interrupted_spell_level=4,
        natural_roll=11,
    )
    assert resolved.check_roll is not None
    assert resolved.check_roll.total == 14
    assert resolved.countered
    assert resolved.result.spell_countered
    assert resolved.result.applied_damage is None


def test_failed_counterspell_preserves_enemy_spell_damage_and_spent_resources() -> None:
    encounter = build_encounter_from_scenario(
        load_scenario("content/scenarios/gate_skirmish.json")
    )
    cleric = next(actor for actor in encounter.actors if str(actor.id) == "cleric")
    enemy = next(actor for actor in encounter.actors if actor.faction == Faction.ENEMY)
    state = _state(enemy, cleric)
    enemy_result = _enemy_spell_result(state, enemy, cleric, spell_level=4)
    service = CounterspellReactionFlowService()
    option = service.option(
        board=encounter.board,
        state=state,
        enemy_result=enemy_result,
        actions_by_actor=encounter.combat_actions_by_actor,
    )
    assert option is not None
    started = service.cast(
        state=state,
        enemy_result=enemy_result,
        option=option,
        cast_level=3,
        actions_by_actor=encounter.combat_actions_by_actor,
    )

    resolved = service.resolve_check(
        state=started.state,
        enemy_result=started.result,
        caster_id=str(cleric.id),
        cast_level=3,
        interrupted_spell_level=4,
        natural_roll=1,
    )

    result_cleric = next(
        actor for actor in resolved.result.state.actors if actor.id == cleric.id
    )
    assert not resolved.countered
    assert resolved.result.applied_damage is not None
    assert result_cleric.hp == cleric.hp - 4
    assert next(
        slot for slot in result_cleric.spell_slots if slot.level == 3
    ).remaining == 0
    assert str(cleric.id) in resolved.result.state.spent_reaction_actor_ids


def test_shield_reaction_consumes_slot_and_turns_hit_into_miss() -> None:
    encounter = build_encounter_from_scenario(
        load_scenario("content/scenarios/gate_skirmish.json")
    )
    cleric = next(actor for actor in encounter.actors if str(actor.id) == "cleric")
    enemy = next(actor for actor in encounter.actors if actor.faction == Faction.ENEMY)
    state = _state(enemy, cleric)
    target = actor_as_combat_target(cleric)
    source = AttackSource(
        "Testowy atak",
        AttackSourceType.WEAPON,
        5,
        D20RollRequest(),
        damage_fixed=4,
    )
    attack_roll = resolve_d20_roll(D20RollInput(source.attack_roll_request, target.ac))
    attack = resolve_attack(
        AttackDeclaration(enemy, target, source),
        attack_roll,
        ActionUse.ACTION_AVAILABLE,
    )
    damage = resolve_damage((DamageComponentInput(4, DamageType.SLASHING),))
    applied = apply_damage_result(cleric, damage)
    enemy_result = EnemyAutoTurnResult(
        state=replace_actor(state, applied.actor_after),
        enemy=enemy,
        target=target,
        message="Trafienie.",
        attack_roll=attack_roll,
        attack_resolution=attack,
        damage=damage,
        applied_damage=applied,
        updated_target=applied.actor_after,
        action_used=True,
        source=source,
    )
    service = DefensiveSpellReactionFlowService()
    option = service.option(
        state=state,
        enemy_result=enemy_result,
        actions_by_actor=encounter.combat_actions_by_actor,
    )

    assert option is not None
    resolution = service.cast(
        state=state,
        enemy_result=enemy_result,
        active_effects=(),
        option=option,
        actions_by_actor=encounter.combat_actions_by_actor,
    )

    updated_cleric = next(
        actor for actor in resolution.result.state.actors if actor.id == cleric.id
    )
    reaction_cleric = next(
        actor for actor in resolution.state.actors if actor.id == cleric.id
    )
    assert resolution.prevented_hit
    assert resolution.result.attack_resolution is not None
    assert not resolution.result.attack_resolution.hit
    assert resolution.result.applied_damage is None
    assert updated_cleric.hp == cleric.hp
    assert sum(slot.remaining for slot in reaction_cleric.spell_slots) == (
        sum(slot.remaining for slot in cleric.spell_slots) - 1
    )
    assert not reaction_available_for(resolution.state, reaction_cleric)
    assert combat_armor_class(reaction_cleric, resolution.active_effects) == target.ac + 5
    assert expire_turn_start_effects(
        resolution.active_effects,
        str(reaction_cleric.id),
    ) == ()


def test_missed_opportunity_attack_consumes_reaction_then_moves() -> None:
    service = CombatReactionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    state = _state(hero, goblin)

    resolution = service.resolve_opportunity_movement(
        state=state,
        actor_id="hero",
        path=_path(state, hero),
        threat_actor_ids=("goblin",),
        attack_sources_by_actor={goblin.id: _source()},
        active_effects=(),
        roll_d20=_roll(1),
        roll_damage=lambda _sides: 1,
    )

    moved = next(actor for actor in resolution.state.actors if actor.id == hero.id)
    updated_goblin = next(actor for actor in resolution.state.actors if actor.id == goblin.id)
    assert moved.position == Coordinate(0, 2)
    assert moved.hp == 10
    assert resolution.movement_performed
    assert not reaction_available_for(resolution.state, updated_goblin)
    assert "pudło" in resolution.message_body


def test_hit_applies_damage_and_completes_movement() -> None:
    service = CombatReactionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    state = _state(hero, goblin)

    resolution = service.resolve_opportunity_movement(
        state=state,
        actor_id="hero",
        path=_path(state, hero),
        threat_actor_ids=("goblin",),
        attack_sources_by_actor={goblin.id: _source()},
        active_effects=(),
        roll_d20=_roll(20),
        roll_damage=lambda _sides: 1,
    )

    moved = next(actor for actor in resolution.state.actors if actor.id == hero.id)
    assert moved.position == Coordinate(0, 2)
    assert moved.hp == 7
    assert len(resolution.applied_damages) == 1
    assert "trafienie" in resolution.message_body


def test_lethal_opportunity_attack_stops_movement() -> None:
    service = CombatReactionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0), hp=3)
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    state = _state(hero, goblin)

    resolution = service.resolve_opportunity_movement(
        state=state,
        actor_id="hero",
        path=_path(state, hero),
        threat_actor_ids=("goblin",),
        attack_sources_by_actor={goblin.id: _source()},
        active_effects=(),
        roll_d20=_roll(20),
        roll_damage=lambda _sides: 1,
    )

    defeated = next(actor for actor in resolution.state.actors if actor.id == hero.id)
    assert defeated.position == Coordinate(0, 0)
    assert defeated.hp == 0
    assert not resolution.movement_performed
    assert "pada przed wykonaniem ruchu" in resolution.message_body


def test_spent_or_missing_threat_is_skipped_and_movement_still_happens() -> None:
    service = CombatReactionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    state = _state(hero, goblin)
    state = use_actor_reaction(state, goblin).state

    resolution = service.resolve_opportunity_movement(
        state=state,
        actor_id="hero",
        path=_path(state, hero),
        threat_actor_ids=("missing", "goblin"),
        attack_sources_by_actor={goblin.id: _source()},
        active_effects=(),
        roll_d20=lambda _request: pytest.fail("No attack roll expected."),
        roll_damage=lambda _sides: pytest.fail("No damage roll expected."),
    )

    moved = next(actor for actor in resolution.state.actors if actor.id == hero.id)
    assert moved.position == Coordinate(0, 2)
    assert resolution.applied_damages == ()


def test_unknown_mover_is_rejected() -> None:
    service = CombatReactionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    state = _state(hero, goblin)

    with pytest.raises(ValueError, match="Aktor oczekującego ruchu nie istnieje"):
        service.resolve_opportunity_movement(
            state=state,
            actor_id="missing",
            path=_path(state, hero),
            threat_actor_ids=("goblin",),
            attack_sources_by_actor={goblin.id: _source()},
            active_effects=(),
            roll_d20=_roll(20),
            roll_damage=lambda _sides: 1,
        )


def test_player_reaction_roll_consumes_reaction_and_reports_miss() -> None:
    service = PlayerReactionFlowService()
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    state = _state(goblin, hero)

    resolution = service.resolve_attack_roll(
        state=state,
        attacker_id="hero",
        target_id="goblin",
        attack_sources_by_actor={hero.id: _source()},
        active_effects=(),
        natural_roll=1,
    )

    updated_hero = next(actor for actor in resolution.state.actors if actor.id == hero.id)
    assert not reaction_available_for(resolution.state, updated_hero)
    assert not resolution.hit
    assert resolution.attack_roll.natural_roll == 1
    assert "pudłuje" in resolution.message


def test_ready_reaction_consumes_ready_and_next_attack_effects() -> None:
    service = PlayerReactionFlowService()
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    state = _state(goblin, hero)
    ready = ActiveCombatEffect(
        id="ready:hero",
        actor_id="hero",
        kind="ready_attack",
        label="Ready",
        object_id="combat_action:ready:enemy_moves",
        value=0,
    )
    penalty = ActiveCombatEffect(
        id="penalty:hero",
        actor_id="hero",
        kind="grant_next_attack_penalty",
        label="Kara",
        object_id="rubble",
        value=-2,
    )

    resolution = service.resolve_attack_roll(
        state=state,
        attacker_id="hero",
        target_id="goblin",
        attack_sources_by_actor={hero.id: _source()},
        active_effects=(ready, penalty),
        natural_roll=20,
        consumed_effect_id=ready.id,
    )

    assert resolution.hit
    assert resolution.critical
    assert resolution.active_effects == ()


def test_player_reaction_damage_updates_target_and_clamps_negative_input() -> None:
    service = PlayerReactionFlowService()
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    state = _state(goblin, hero)

    damaged = service.apply_damage(
        state=state,
        attacker_id="hero",
        target_id="goblin",
        attack_sources_by_actor={hero.id: _source()},
        active_effects=(),
        damage=4,
    )
    unchanged = service.apply_damage(
        state=state,
        attacker_id="hero",
        target_id="goblin",
        attack_sources_by_actor={hero.id: _source()},
        active_effects=(),
        damage=-5,
    )

    assert damaged.applied_damage.hp_after == 6
    assert unchanged.applied_damage.damage.total_applied == 0


def test_player_reaction_damage_accepts_typed_component_totals() -> None:
    service = PlayerReactionFlowService()
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    state = _state(goblin, hero)
    source = replace(
        _source(),
        damage_components=(
            DamageComponentSpec(
                id="blade",
                damage_type=DamageType.SLASHING,
                fixed=3,
            ),
            DamageComponentSpec(
                id="flame",
                damage_type=DamageType.FIRE,
                fixed=2,
            ),
        ),
    )

    damaged = service.apply_damage(
        state=state,
        attacker_id="hero",
        target_id="goblin",
        attack_sources_by_actor={hero.id: source},
        active_effects=(),
        component_totals={"blade": 3, "flame": 2},
    )

    assert damaged.applied_damage.hp_after == 5
    assert [
        component.damage_type
        for component in damaged.applied_damage.damage.resolved_components
    ] == [DamageType.SLASHING, DamageType.FIRE]


def test_automatic_opportunity_attack_rolls_all_components_and_doubles_critical_dice() -> None:
    service = CombatReactionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0), hp=20)
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    state = _state(hero, goblin)
    source = replace(
        _source(),
        damage_components=(
            DamageComponentSpec(
                id="blade",
                damage_type=DamageType.SLASHING,
                dice=DiceExpression(1, 6),
            ),
            DamageComponentSpec(
                id="flame",
                damage_type=DamageType.FIRE,
                fixed=3,
            ),
        ),
    )
    rolled_sides: list[int] = []

    resolution = service.resolve_opportunity_movement(
        state=state,
        actor_id="hero",
        path=_path(state, hero),
        threat_actor_ids=("goblin",),
        attack_sources_by_actor={goblin.id: source},
        active_effects=(),
        roll_d20=_roll(20),
        roll_damage=lambda sides: rolled_sides.append(sides) or 2,
    )

    moved = next(actor for actor in resolution.state.actors if actor.id == hero.id)
    assert moved.hp == 13
    assert rolled_sides == [6, 6]
    assert [
        component.amount_before
        for component in resolution.applied_damages[0].damage.resolved_components
    ] == [4, 3]


def test_ready_trigger_detection_uses_enemy_movement_and_legal_range() -> None:
    service = PlayerReactionFlowService()
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(2, 0))
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    state = _state(goblin, hero)
    moved_goblin = replace(goblin, position=Coordinate(1, 0))
    path = find_path(BoardState(), goblin, state.actors, moved_goblin.position)
    enemy_result = EnemyAutoTurnResult(
        state=replace_actor(state, moved_goblin),
        enemy=goblin,
        target=None,
        message="Goblin rusza się.",
        movement_path=path,
        moved_enemy=moved_goblin,
    )
    ready = ActiveCombatEffect(
        id="ready:hero",
        actor_id="hero",
        kind="ready_attack",
        label="Ready",
        object_id="combat_action:ready:enemy_moves",
        value=0,
    )

    trigger = service.detect_ready_attack(
        state=state,
        enemy_result=enemy_result,
        board=BoardState(),
        attack_sources_by_actor={hero.id: _source()},
        active_effects=(ready,),
    )

    assert trigger is not None
    assert trigger.readied_actor_id == "hero"
    assert trigger.target_id == "goblin"
    assert trigger.trigger == "enemy_moves"
    actor_as_combat_target,
    apply_damage_result,
    combat_armor_class,
    resolve_attack,
    resolve_damage,
