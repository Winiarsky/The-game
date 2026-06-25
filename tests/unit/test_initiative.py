import random

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.combat import (
    InitiativeEntry,
    build_initiative_order,
    build_player_initiative_prompts,
    roll_enemy_initiative,
)
from dnd_board_game.rules import D20RollInput, resolve_d20_roll
from dnd_board_game.rules import D20RollRequest, RollModifier, RollModifierType
from dnd_board_game.world import Coordinate


def _actor(actor_id: str, name: str, faction: Faction, dexterity: int, hp: int = 10) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=name,
        ac=12,
        hp=hp,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(0, 0),
        faction=faction,
        ability_scores=AbilityScores(dexterity=dexterity),
    )


def _entry(actor: Actor, natural_roll: int, stable_order: int) -> InitiativeEntry:
    dex_modifier = (actor.ability_scores.dexterity - 10) // 2
    prompts = build_player_initiative_prompts((actor,))
    if prompts:
        roll = resolve_d20_roll(D20RollInput(prompts[0].request, natural_roll))
    else:
        request = D20RollRequest(
            modifiers=(
                RollModifier(
                    "Modyfikator ze Zręczności",
                    dex_modifier,
                    RollModifierType.ABILITY,
                    stacking_key="initiative_dexterity",
                ),
            )
        )
        roll = resolve_d20_roll(D20RollInput(request, natural_roll))
    return InitiativeEntry(actor, roll, dex_modifier, stable_order)


def test_player_initiative_prompts_go_in_party_order_and_skip_enemy():
    hero = _actor("hero", "Bohater", Faction.ALLY, 16)
    rogue = _actor("rogue", "Łotrzyca", Faction.ALLY, 18)
    goblin = _actor("goblin", "Goblin", Faction.ENEMY, 14)

    prompts = build_player_initiative_prompts((hero, rogue, goblin))

    assert [prompt.actor.name for prompt in prompts] == ["Bohater", "Łotrzyca"]
    assert "Test inicjatywy: Bohater" in prompts[0].message
    assert "Rzuć 1d20" in prompts[0].message


def test_enemy_initiative_uses_injected_rng():
    goblin = _actor("goblin", "Goblin", Faction.ENEMY, 14)

    entry = roll_enemy_initiative(goblin, random.Random(7))

    assert entry.roll.natural_roll == 11
    assert entry.roll.total == 13


def test_initiative_order_sorts_by_total_dexterity_and_stable_order():
    slow = _actor("slow", "Wojownik", Faction.ALLY, 10)
    quick = _actor("quick", "Łotrzyca", Faction.ALLY, 18)
    stable_a = _actor("a", "A", Faction.ALLY, 12)
    stable_b = _actor("b", "B", Faction.ALLY, 12)

    order = build_initiative_order(
        (
            _entry(slow, 15, 0),
            _entry(quick, 11, 1),
            _entry(stable_b, 10, 3),
            _entry(stable_a, 10, 2),
        )
    )

    assert [entry.actor.name for entry in order.entries] == ["Łotrzyca", "Wojownik", "A", "B"]
    assert order.current_actor.name == "Łotrzyca"


def test_advance_turn_wraps_round_and_skips_defeated_actor():
    hero = _actor("hero", "Bohater", Faction.ALLY, 12)
    defeated = _actor("down", "Pokonany", Faction.ALLY, 12, hp=0)
    goblin = _actor("goblin", "Goblin", Faction.ENEMY, 12)
    order = build_initiative_order(
        (
            _entry(hero, 15, 0),
            _entry(defeated, 10, 1),
            _entry(goblin, 5, 2),
        )
    )

    after_hero = order.advance_turn()
    next_round = after_hero.advance_turn()

    assert after_hero.current_actor.name == "Goblin"
    assert after_hero.round_number == 1
    assert next_round.current_actor.name == "Bohater"
    assert next_round.round_number == 2
