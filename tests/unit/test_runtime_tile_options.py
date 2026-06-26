from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.combat import (
    AttackSource,
    AttackSourceType,
    InitiativeEntry,
    InitiativeOrder,
    SceneObject,
    TileOptionKind,
    preview_turn_intent,
    start_combat,
)
from dnd_board_game.hardware import LedColor
from dnd_board_game.runtime.demo_mini_combat_loop import _attack_source_with_cover, _preview_led_feedback, _preview_led_feedback_for_turn
from dnd_board_game.rules import D20RollInput, D20RollRequest, RollModifierType, resolve_d20_roll
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


def test_tile_option_preview_led_uses_selected_option_color():
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    state = start_combat((hero, goblin), _order(hero, goblin))
    scene_object = SceneObject(
        "crate",
        "Skrzynia",
        (Coordinate(1, 0),),
        "Zbadaj skrzynię",
        allow_interaction_when_occupied_by_enemy=True,
    )

    attack_preview = preview_turn_intent(BoardState(), state, hero, _source(), Coordinate(1, 0), (scene_object,))
    interaction_preview = preview_turn_intent(
        BoardState(),
        state,
        hero,
        _source(),
        Coordinate(1, 0),
        (scene_object,),
        selected_tile_option_index=1,
    )

    assert attack_preview.tile_options[attack_preview.selected_tile_option_index].kind == TileOptionKind.ATTACK
    assert _preview_led_feedback(attack_preview).frames[0].color == LedColor.SELECTED_ATTACK_TARGET
    assert interaction_preview.tile_options[interaction_preview.selected_tile_option_index].kind == TileOptionKind.INTERACTION
    assert _preview_led_feedback(interaction_preview).frames[0].color == LedColor.INTERACTIVE_OBJECT


def test_attack_source_with_cover_adds_visible_cover_penalty():
    source = _source()
    target = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    scene_object = SceneObject(
        "crate",
        "Skrzynia",
        (Coordinate(1, 0),),
        "Zbadaj skrzynię",
        cover_bonus=2,
    )

    covered = _attack_source_with_cover(source, target, (scene_object,))

    modifier = covered.attack_roll_request.modifiers[-1]
    assert modifier.value == -2
    assert modifier.modifier_type == RollModifierType.COVER
    assert "Skrzynia" in modifier.label


def test_movement_preview_keeps_interaction_context_visible():
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(5, 5))
    state = start_combat((hero, goblin), _order(hero, goblin))
    scene_object = SceneObject("crate", "Skrzynia", (Coordinate(1, 0),), "Zbadaj skrzynię")
    preview = preview_turn_intent(BoardState(), state, hero, _source(), Coordinate(0, 1), (scene_object,))

    feedback = _preview_led_feedback_for_turn(BoardState(), state, hero, _source(), (scene_object,), preview)

    assert any(frame.color == LedColor.INTERACTIVE_OBJECT and Coordinate(1, 0) in frame.positions for frame in feedback.frames)
    assert any(frame.color == LedColor.PLAYER_MOVEMENT_PATH and Coordinate(0, 1) in frame.positions for frame in feedback.frames)
