from dataclasses import replace
from random import Random

import pytest

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.application import (
    PlayerCombatActionFlowService,
    PlayerReactionFlowService,
)
from dnd_board_game.combat import (
    AttackKind,
    AttackSource,
    AttackSourceType,
    SceneConclusionType,
    InitiativeEntry,
    InitiativeOrder,
    reaction_available_for,
    record_ammunition_expenditure,
    recoverable_ammunition_quantity,
    replace_actor,
    conclude_scene,
    resolve_enemy_auto_attack,
    start_combat,
)
from dnd_board_game.inventory import (
    InventoryItem,
    ammunition_quantity,
    consume_ammunition,
    has_ammunition,
)
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.scenarios import build_encounter_from_scenario, load_scenario
from dnd_board_game.world import BoardState, Coordinate


def _actor(
    actor_id: str,
    faction: Faction,
    position: Coordinate,
    *,
    inventory: tuple[InventoryItem, ...] = (),
    attacks_per_action: int = 1,
) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id,
        ac=12,
        hp=20,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=faction,
        ability_scores=AbilityScores(dexterity=14),
        inventory=inventory,
        attacks_per_action=attacks_per_action,
    )


def _state(*actors: Actor):
    entries = tuple(
        InitiativeEntry(
            actor,
            resolve_d20_roll(D20RollInput(D20RollRequest(), 20 - index)),
            2,
            index,
        )
        for index, actor in enumerate(actors)
    )
    return start_combat(tuple(actors), InitiativeOrder(entries))


def _crossbow_source() -> AttackSource:
    return AttackSource(
        id="crossbow_shot",
        name="Kusza",
        source_type=AttackSourceType.WEAPON,
        source_item_id="crossbow",
        attack_kind=AttackKind.RANGED,
        range_feet=80,
        attack_roll_request=D20RollRequest(),
        damage_fixed=1,
        damage_type="piercing",
        ammunition_type="bolt",
        loading=True,
    )


def _crossbow_inventory(bolts: int) -> tuple[InventoryItem, ...]:
    return (
        InventoryItem("crossbow", "Kusza", "weapon", equipped=True),
        InventoryItem(
            "crossbow_bolt",
            "Bełt",
            "ammunition",
            quantity=bolts,
            equipped=False,
            ammunition_type="bolt",
        ),
    )


def test_ammunition_consumes_across_compatible_stacks_without_mutating_actor():
    actor = _actor(
        "hero",
        Faction.ALLY,
        Coordinate(0, 0),
        inventory=(
            InventoryItem("bolts_a", "Bełty", "ammunition", quantity=1, equipped=False, ammunition_type="bolt"),
            InventoryItem("bolts_b", "Bełty zapasowe", "ammunition", quantity=2, equipped=False, ammunition_type="bolt"),
        ),
    )

    use = consume_ammunition(actor, "bolt", 2)

    assert ammunition_quantity(actor, "bolt") == 3
    assert ammunition_quantity(use.actor_after, "bolt") == 1
    assert use.item_ids == ("bolts_a", "bolts_b")
    assert has_ammunition(use.actor_after, "bolt") is True


def test_crossbow_content_loads_ammunition_loading_and_starting_bolts():
    encounter = build_encounter_from_scenario(
        load_scenario("content/scenarios/multi_actor_skirmish.json")
    )
    rogue = next(actor for actor in encounter.actors if str(actor.id) == "rogue")
    source = next(
        source
        for source in encounter.attack_source_options_by_actor[rogue.id]
        if source.id == "crossbow_shot"
    )

    assert source.ammunition_type == "bolt"
    assert source.loading is True
    assert ammunition_quantity(rogue, "bolt") == 20


def test_player_crossbow_attack_consumes_bolt_on_miss_and_loading_blocks_extra_attack():
    hero = _actor(
        "hero",
        Faction.ALLY,
        Coordinate(0, 0),
        inventory=_crossbow_inventory(2),
        attacks_per_action=2,
    )
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(4, 0))
    service = PlayerCombatActionFlowService()

    first = service.resolve_direct_attack(
        state=_state(hero, enemy),
        board=BoardState(),
        source=_crossbow_source(),
        target_id="enemy",
        active_effects=(),
        natural_roll=1,
    )

    hero_after = next(actor for actor in first.state.actors if actor.id == hero.id)
    assert ammunition_quantity(hero_after, "bolt") == 1
    with pytest.raises(ValueError, match="loading"):
        service.resolve_direct_attack(
            state=first.state,
            board=BoardState(),
            source=_crossbow_source(),
            target_id="enemy",
            active_effects=(),
            natural_roll=20,
        )


def test_player_crossbow_attack_is_rejected_before_action_when_bolts_are_empty():
    hero = _actor(
        "hero",
        Faction.ALLY,
        Coordinate(0, 0),
        inventory=_crossbow_inventory(0),
    )
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(4, 0))
    state = _state(hero, enemy)

    with pytest.raises(ValueError, match="Brak amunicji"):
        PlayerCombatActionFlowService().resolve_direct_attack(
            state=state,
            board=BoardState(),
            source=_crossbow_source(),
            target_id="enemy",
            active_effects=(),
            natural_roll=20,
        )

    assert state.turn_action.action_use.value == "action_available"


def test_enemy_crossbow_attack_consumes_bolt():
    enemy = _actor(
        "enemy",
        Faction.ENEMY,
        Coordinate(0, 0),
        inventory=_crossbow_inventory(1),
    )
    hero = _actor("hero", Faction.ALLY, Coordinate(4, 0))

    result = resolve_enemy_auto_attack(
        BoardState(),
        _state(enemy, hero),
        enemy,
        _crossbow_source(),
        Random(3),
    )

    enemy_after = next(actor for actor in result.state.actors if actor.id == enemy.id)
    assert result.action_used is True
    assert ammunition_quantity(enemy_after, "bolt") == 0


def test_enemy_without_bolts_does_not_spend_action():
    enemy = _actor(
        "enemy",
        Faction.ENEMY,
        Coordinate(0, 0),
        inventory=_crossbow_inventory(0),
    )
    hero = _actor("hero", Faction.ALLY, Coordinate(4, 0))

    result = resolve_enemy_auto_attack(
        BoardState(),
        _state(enemy, hero),
        enemy,
        _crossbow_source(),
        Random(3),
    )

    assert result.action_used is False
    assert "nie ma amunicji" in result.message


def test_player_reaction_attack_consumes_bolt():
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(0, 0))
    hero = _actor(
        "hero",
        Faction.ALLY,
        Coordinate(4, 0),
        inventory=_crossbow_inventory(1),
    )
    state = _state(enemy, hero)

    result = PlayerReactionFlowService().resolve_attack_roll(
        state=state,
        attacker_id="hero",
        target_id="enemy",
        attack_sources_by_actor={hero.id: _crossbow_source()},
        active_effects=(),
        natural_roll=10,
    )

    hero_after = next(actor for actor in result.state.actors if actor.id == hero.id)
    assert ammunition_quantity(hero_after, "bolt") == 0
    assert reaction_available_for(result.state, hero_after) is False


def test_party_victory_recovers_half_of_fired_bolts_as_battlefield_loot():
    hero = _actor(
        "hero",
        Faction.ALLY,
        Coordinate(0, 0),
        inventory=_crossbow_inventory(9),
    )
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(4, 0))
    state = _state(hero, enemy)

    for _ in range(9):
        current_hero = next(actor for actor in state.actors if actor.id == hero.id)
        use = consume_ammunition(current_hero, "bolt")
        state = record_ammunition_expenditure(state, current_hero, use)
        state = replace_actor(state, use.actor_after)

    state = replace_actor(state, replace(enemy, hp=0))

    assert state.status.value == "finished"
    assert state.winner == Faction.ALLY
    assert recoverable_ammunition_quantity(state, "bolt") == 4
    assert len(state.battlefield_loot) == 1
    recovered = state.battlefield_loot[0]
    assert recovered.position == enemy.position
    assert recovered.bundle.label == "Odzyskana amunicja"
    assert recovered.bundle.items[0].id == "crossbow_bolt"
    assert recovered.bundle.items[0].quantity == 4


def test_enemy_shots_are_not_added_to_party_ammunition_recovery():
    hero = _actor(
        "hero",
        Faction.ALLY,
        Coordinate(0, 0),
        inventory=_crossbow_inventory(2),
    )
    enemy = _actor(
        "enemy",
        Faction.ENEMY,
        Coordinate(4, 0),
        inventory=_crossbow_inventory(6),
    )
    state = _state(hero, enemy)
    for shooter_id, quantity in ((hero.id, 2), (enemy.id, 6)):
        for _ in range(quantity):
            shooter = next(actor for actor in state.actors if actor.id == shooter_id)
            use = consume_ammunition(shooter, "bolt")
            state = record_ammunition_expenditure(state, shooter, use)
            state = replace_actor(state, use.actor_after)

    state = replace_actor(state, replace(enemy, hp=0))

    assert recoverable_ammunition_quantity(state, "bolt") == 1
    assert state.battlefield_loot[0].bundle.items[0].quantity == 1


def test_retreat_does_not_create_recovered_ammunition_loot():
    hero = _actor(
        "hero",
        Faction.ALLY,
        Coordinate(0, 0),
        inventory=_crossbow_inventory(4),
    )
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(4, 0))
    state = _state(hero, enemy)
    for _ in range(4):
        current_hero = next(actor for actor in state.actors if actor.id == hero.id)
        use = consume_ammunition(current_hero, "bolt")
        state = record_ammunition_expenditure(state, current_hero, use)
        state = replace_actor(state, use.actor_after)

    state, result = conclude_scene(
        state,
        conclusion=SceneConclusionType.RETREAT,
    )

    assert result.conclusion == SceneConclusionType.RETREAT
    assert state.battlefield_loot == ()
