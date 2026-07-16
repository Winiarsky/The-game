from dataclasses import replace
from random import Random

import pytest

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.application import PlayerCombatActionFlowService
from dnd_board_game.combat import (
    ActionUse,
    AttackKind,
    AttackSource,
    AttackSourceType,
    InitiativeEntry,
    InitiativeOrder,
    eligible_two_weapon_bonus_sources,
    start_combat,
    two_weapon_bonus_attack_source,
)
from dnd_board_game.inventory import HandSlot, InventoryItem
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.world import BoardState, Coordinate


def _weapon(item_id: str, name: str, slot: HandSlot, *, light: bool = True) -> InventoryItem:
    return InventoryItem(
        item_id,
        name,
        "weapon",
        held_in=(slot,),
        hands_required=1,
        light_weapon=light,
    )


def _actor(actor_id: str, faction: Faction, position: Coordinate, inventory=()) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id.title(),
        ac=12,
        hp=20,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=faction,
        inventory=tuple(inventory),
        ability_scores=AbilityScores(dexterity=16),
    )


def _source(item_id: str, name: str, *, kind: AttackKind = AttackKind.MELEE) -> AttackSource:
    return AttackSource(
        name=name,
        source_type=AttackSourceType.WEAPON,
        range_feet=5 if kind == AttackKind.MELEE else 30,
        attack_roll_request=D20RollRequest(),
        damage_hint="1d4 + 3 piercing",
        damage_die_sides=4,
        damage_modifier=3,
        damage_type="piercing",
        id=f"{item_id}_attack",
        source_item_id=item_id,
        attack_kind=kind,
        ability="dexterity",
    )


def _state(hero: Actor, enemy: Actor):
    request = D20RollRequest()
    order = InitiativeOrder(
        (
            InitiativeEntry(hero, resolve_d20_roll(D20RollInput(request, 20)), 0, 0),
            InitiativeEntry(enemy, resolve_d20_roll(D20RollInput(request, 10)), 0, 1),
        )
    )
    return start_combat((hero, enemy), order)


def test_bonus_source_requires_different_light_melee_weapon_in_opposite_hand() -> None:
    hero = _actor(
        "hero",
        Faction.ALLY,
        Coordinate(0, 0),
        (
            _weapon("dagger", "Sztylet", HandSlot.MAIN_HAND),
            _weapon("shortsword", "Krótki miecz", HandSlot.OFF_HAND),
        ),
    )
    dagger = _source("dagger", "Sztylet")
    shortsword = _source("shortsword", "Krótki miecz")

    options = eligible_two_weapon_bonus_sources(hero, "dagger", (dagger, shortsword))

    assert options == (shortsword,)


def test_ranged_or_non_light_weapon_is_not_a_two_weapon_bonus_option() -> None:
    hero = _actor(
        "hero",
        Faction.ALLY,
        Coordinate(0, 0),
        (
            _weapon("dagger", "Sztylet", HandSlot.MAIN_HAND),
            _weapon("crossbow", "Kusza", HandSlot.OFF_HAND),
        ),
    )

    assert eligible_two_weapon_bonus_sources(
        hero,
        "dagger",
        (_source("crossbow", "Kusza", kind=AttackKind.RANGED),),
    ) == ()


def test_bonus_attack_removes_positive_damage_modifier_but_retains_penalty() -> None:
    actor = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    positive = two_weapon_bonus_attack_source(actor, _source("dagger", "Sztylet"))
    negative = two_weapon_bonus_attack_source(
        actor,
        replace(_source("dagger", "Sztylet"), damage_modifier=-1)
    )

    assert positive.damage_modifier == 0
    assert positive.damage_hint.startswith("1d4 piercing")
    assert negative.damage_modifier == -1
    assert "- 1" in negative.damage_hint


def test_bonus_attack_keeps_non_ability_damage_bonus() -> None:
    actor = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    enchanted_source = replace(_source("dagger", "Sztylet"), damage_modifier=4)

    bonus_source = two_weapon_bonus_attack_source(actor, enchanted_source)

    assert bonus_source.damage_modifier == 1
    assert bonus_source.damage_hint.startswith("1d4 + 1 piercing")


def test_main_light_attack_unlocks_bonus_attack_even_on_a_miss() -> None:
    service = PlayerCombatActionFlowService()
    dagger = _weapon("dagger", "Sztylet", HandSlot.MAIN_HAND)
    shortsword = _weapon("shortsword", "Krótki miecz", HandSlot.OFF_HAND)
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0), (dagger, shortsword))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(1, 0))
    state = _state(hero, enemy)
    source = _source("dagger", "Sztylet")
    pending = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        position=enemy.position,
        active_effects=(),
    ).pending
    assert pending is not None
    pending = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        pending=pending,
        active_effects=(),
        rng=Random(1),
    ).pending
    assert pending is not None

    missed = service.submit_attack_roll(
        state=state,
        board=BoardState(),
        source=source,
        pending=pending,
        active_effects=(),
        natural_roll=1,
    )

    assert missed.state.turn_action.action_use == ActionUse.ACTION_USED
    assert missed.state.turn_action.bonus_action_use == ActionUse.ACTION_AVAILABLE
    assert missed.state.turn_action.two_weapon_trigger_item_id == "dagger"


def test_bonus_attack_uses_bonus_action_and_has_off_hand_damage_instruction() -> None:
    service = PlayerCombatActionFlowService()
    hero = _actor(
        "hero",
        Faction.ALLY,
        Coordinate(0, 0),
        (
            _weapon("dagger", "Sztylet", HandSlot.MAIN_HAND),
            _weapon("shortsword", "Krótki miecz", HandSlot.OFF_HAND),
        ),
    )
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(1, 0))
    state = replace(
        _state(hero, enemy),
        turn_action=replace(
            _state(hero, enemy).turn_action,
            action_use=ActionUse.ACTION_USED,
            two_weapon_trigger_item_id="dagger",
        ),
    )
    source = _source("shortsword", "Krótki miecz")
    pending = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        position=enemy.position,
        active_effects=(),
        two_weapon_bonus=True,
    ).pending
    assert pending is not None and pending.two_weapon_bonus
    pending = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        pending=pending,
        active_effects=(),
        rng=Random(1),
    ).pending
    assert pending is not None

    hit = service.submit_attack_roll(
        state=state,
        board=BoardState(),
        source=source,
        pending=pending,
        active_effects=(),
        natural_roll=20,
    )

    assert hit.pending is not None
    assert hit.state.turn_action.action_use == ActionUse.ACTION_USED
    assert hit.state.turn_action.bonus_action_use == ActionUse.ACTION_USED
    assert "bez dodatniego modyfikatora cechy" in hit.message_body


def test_bonus_attack_is_rejected_before_a_qualifying_main_attack() -> None:
    service = PlayerCombatActionFlowService()
    hero = _actor(
        "hero",
        Faction.ALLY,
        Coordinate(0, 0),
        (
            _weapon("dagger", "Sztylet", HandSlot.MAIN_HAND),
            _weapon("shortsword", "Krótki miecz", HandSlot.OFF_HAND),
        ),
    )
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(1, 0))

    with pytest.raises(ValueError, match="nie jest legalnym atakiem drugą bronią"):
        service.select_attack_target(
            state=_state(hero, enemy),
            board=BoardState(),
            source=_source("shortsword", "Krótki miecz"),
            position=enemy.position,
            active_effects=(),
            two_weapon_bonus=True,
        )
