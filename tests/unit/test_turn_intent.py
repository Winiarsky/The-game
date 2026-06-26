from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.combat import (
    AttackSource,
    AttackSourceType,
    InitiativeEntry,
    InitiativeOrder,
    TurnPromptMode,
    confirm_turn_intent,
    preview_turn_intent,
    start_combat,
)
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.world import BoardState, Coordinate


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


def test_clicking_legal_attack_target_creates_attack_preview():
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    state = start_combat((hero, goblin), _order(hero, goblin))

    preview = preview_turn_intent(BoardState(), state, hero, _source(), Coordinate(1, 0))

    assert preview.mode == TurnPromptMode.ATTACK_PREVIEW
    assert preview.attack_target is not None
    assert preview.attack_target.id == "goblin"
    assert "Kliknij to pole ponownie" in preview.message


def test_confirming_attack_preview_returns_attack_confirmation():
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    state = start_combat((hero, goblin), _order(hero, goblin))
    preview = preview_turn_intent(BoardState(), state, hero, _source(), Coordinate(1, 0))

    confirmation = confirm_turn_intent(state, preview)

    assert confirmation.accepted is True
    assert confirmation.attack_target is not None
    assert confirmation.attack_target.id == "goblin"


def test_clicking_empty_legal_tile_creates_movement_preview_and_confirmation_moves_actor():
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(3, 0))
    state = start_combat((hero, goblin), _order(hero, goblin))

    preview = preview_turn_intent(BoardState(), state, hero, _source(), Coordinate(1, 0))
    confirmation = confirm_turn_intent(state, preview)
    moved_hero = next(actor for actor in confirmation.state.actors if actor.id == hero.id)

    assert preview.mode == TurnPromptMode.MOVEMENT_PREVIEW
    assert preview.movement_path is not None
    assert preview.movement_path.cost_feet == 5
    assert confirmation.accepted is True
    assert moved_hero.position == Coordinate(1, 0)


def test_illegal_click_is_rejected_with_reason():
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(10, 10))
    state = start_combat((hero, goblin), _order(hero, goblin))

    preview = preview_turn_intent(BoardState(), state, hero, _source(), Coordinate(10, 10))

    assert preview.mode == TurnPromptMode.INVALID
    assert "nie jest teraz legalnym celem" in preview.message


def test_clicking_active_actor_tile_previews_end_turn_option():
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(3, 0))
    state = start_combat((hero, goblin), _order(hero, goblin))

    preview = preview_turn_intent(BoardState(), state, hero, _source(), Coordinate(0, 0))
    confirmation = confirm_turn_intent(state, preview)

    assert preview.mode == TurnPromptMode.ACTOR_OPTIONS_PREVIEW
    assert "zakończ turę" in preview.message
    assert confirmation.accepted is True
    assert confirmation.end_turn_requested is True
