from types import SimpleNamespace

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.application import resolve_targeted_item_action, targeted_item_action_is_legal
from dnd_board_game.combat import InitiativeEntry, InitiativeOrder, start_combat
from dnd_board_game.inventory import InventoryItem
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.world import Coordinate


def _actor(actor_id: str, faction: Faction, position: Coordinate, inventory=()) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id.title(),
        ac=12,
        hp=10,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=faction,
        ability_scores=AbilityScores(),
        inventory=tuple(inventory),
    )


def _state(hero: Actor, enemy: Actor):
    request = D20RollRequest()
    return start_combat(
        (hero, enemy),
        InitiativeOrder(
            (
                InitiativeEntry(hero, resolve_d20_roll(D20RollInput(request, 20)), 0, 0),
                InitiativeEntry(enemy, resolve_d20_roll(D20RollInput(request, 10)), 0, 1),
            )
        ),
    )


def _sticky_action():
    return SimpleNamespace(
        id="splash_sticky_flask",
        label="Oblij lepką cieczą",
        action_type="targeted_item_effect",
        value=-2,
        duration="until_next_attack",
        target_faction="enemy",
        source_item_id="sticky_flask",
        range_feet=5,
        effect_kind="grant_next_attack_penalty",
    )


def test_targeted_item_action_consumes_item_and_applies_explicit_effect() -> None:
    hero = _actor(
        "hero",
        Faction.ALLY,
        Coordinate(1, 1),
        (InventoryItem("sticky_flask", "Fiolka", "consumable"),),
    )
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(2, 1))
    state = _state(hero, enemy)

    result = resolve_targeted_item_action(
        state=state,
        active_effects=(),
        action=_sticky_action(),
        target_id="enemy",
    )

    updated_hero = next(actor for actor in result.state.actors if str(actor.id) == "hero")
    assert updated_hero.inventory[0].quantity == 0
    assert result.state.turn_action.action_use.value == "action_used"
    assert result.active_effects[0].actor_id == "enemy"
    assert result.active_effects[0].kind == "grant_next_attack_penalty"
    assert result.active_effects[0].value == -2


def test_targeted_item_action_requires_matching_target_and_range() -> None:
    hero = _actor(
        "hero",
        Faction.ALLY,
        Coordinate(1, 1),
        (InventoryItem("sticky_flask", "Fiolka", "consumable"),),
    )
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(3, 1))
    state = _state(hero, enemy)

    assert not targeted_item_action_is_legal(state, _sticky_action(), enemy)


def test_targeted_item_action_spends_charge_without_consuming_magic_item() -> None:
    wand = InventoryItem(
        "binding_wand",
        "Różdżka",
        "magic_item",
        charges_maximum=3,
        charges_current=2,
        requires_attunement=True,
        attuned=True,
    )
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 1), (wand,))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(2, 1))
    action = SimpleNamespace(
        **{
            **vars(_sticky_action()),
            "id": "binding_wand_restraint",
            "source_item_id": "binding_wand",
            "charge_cost": 1,
        }
    )

    result = resolve_targeted_item_action(
        state=_state(hero, enemy),
        active_effects=(),
        action=action,
        target_id="enemy",
    )
    updated = next(actor for actor in result.state.actors if str(actor.id) == "hero")

    assert updated.inventory[0].quantity == 1
    assert updated.inventory[0].charges_current == 1
    unattuned = _actor(
        "hero",
        Faction.ALLY,
        Coordinate(1, 1),
        (
            InventoryItem(
                "binding_wand",
                "Różdżka",
                "magic_item",
                charges_maximum=3,
                requires_attunement=True,
            ),
        ),
    )
    assert not targeted_item_action_is_legal(_state(unattuned, enemy), action, enemy)
    depleted = _actor(
        "hero",
        Faction.ALLY,
        Coordinate(1, 1),
        (InventoryItem("binding_wand", "Różdżka", "magic_item", charges_maximum=3, charges_current=0),),
    )
    assert not targeted_item_action_is_legal(_state(depleted, enemy), action, enemy)
