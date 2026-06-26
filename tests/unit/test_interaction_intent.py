from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.combat import (
    AttackSource,
    AttackSourceType,
    InitiativeEntry,
    InitiativeOrder,
    SceneObject,
    TurnPromptMode,
    confirm_turn_intent,
    movement_remaining,
    preview_turn_intent,
    start_combat,
    use_movement,
)
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.world import BoardState, Coordinate, find_path


def _actor(actor_id: str, faction: Faction, position: Coordinate) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id,
        ac=12,
        hp=10,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=faction,
        ability_scores=AbilityScores(dexterity=14),
    )


def _source() -> AttackSource:
    return AttackSource("Miecz", AttackSourceType.WEAPON, 5, D20RollRequest())


def _order(*actors: Actor) -> InitiativeOrder:
    request = D20RollRequest()
    return InitiativeOrder(
        tuple(InitiativeEntry(actor, resolve_d20_roll(D20RollInput(request, 20 - index)), 2, index) for index, actor in enumerate(actors))
    )


def test_clicking_adjacent_interactable_creates_interaction_preview():
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(5, 5))
    state = start_combat((hero, goblin), _order(hero, goblin))
    scene_object = SceneObject("crate", "Skrzynia", (Coordinate(1, 0),), "Zabezpiecz skrzynię")

    preview = preview_turn_intent(BoardState(), state, hero, _source(), Coordinate(1, 0), (scene_object,))

    assert preview.mode == TurnPromptMode.INTERACTION_PREVIEW
    assert preview.interaction_object == scene_object
    assert "potwierdzić interakcję" in preview.message


def test_confirming_interaction_uses_action_but_keeps_remaining_movement():
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(5, 5))
    state = start_combat((hero, goblin), _order(hero, goblin))
    scene_object = SceneObject("crate", "Skrzynia", (Coordinate(1, 0),), "Zabezpiecz skrzynię")
    preview = preview_turn_intent(BoardState(), state, hero, _source(), Coordinate(1, 0), (scene_object,))

    confirmed = confirm_turn_intent(state, preview)
    moved = use_movement(confirmed.state, hero, find_path(BoardState(), hero, confirmed.state.actors, Coordinate(0, 1)))

    assert confirmed.accepted is True
    assert confirmed.interaction_object == scene_object
    assert moved.accepted is True
    assert movement_remaining(moved.state, next(actor for actor in moved.state.actors if actor.id == hero.id)) == 25
