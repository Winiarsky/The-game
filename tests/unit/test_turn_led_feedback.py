from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.combat import AttackSource, AttackSourceType, InitiativeEntry, InitiativeOrder, SceneObject, start_combat
from dnd_board_game.hardware import LedColor
from dnd_board_game.runtime.demo_mini_combat_loop import _turn_options_led_feedback
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


def test_turn_led_feedback_marks_visible_enemy_outside_attack_range():
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(3, 0))
    state = start_combat((hero, goblin), _order(hero, goblin))

    feedback = _turn_options_led_feedback(BoardState(), state, hero, _source())

    enemy_frames = [frame for frame in feedback.frames if Coordinate(3, 0) in frame.positions]
    assert enemy_frames
    assert enemy_frames[-1].color == LedColor.VISIBLE_ENEMY_OUT_OF_RANGE


def test_turn_led_feedback_distinguishes_legal_attack_target_from_enemy_outside_range():
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    close = _actor("close", Faction.ENEMY, Coordinate(1, 0))
    far = _actor("far", Faction.ENEMY, Coordinate(3, 0))
    state = start_combat((hero, close, far), _order(hero, close, far))

    feedback = _turn_options_led_feedback(BoardState(), state, hero, _source())

    target_frame = next(frame for frame in feedback.frames if Coordinate(1, 0) in frame.positions)
    far_frame = next(frame for frame in feedback.frames if Coordinate(3, 0) in frame.positions)
    assert target_frame.color == LedColor.LEGAL_ATTACK_TARGET
    assert far_frame.color == LedColor.VISIBLE_ENEMY_OUT_OF_RANGE


def test_turn_led_feedback_marks_interactive_object_green():
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(5, 5))
    state = start_combat((hero, goblin), _order(hero, goblin))
    scene_object = SceneObject("crate", "Skrzynia", (Coordinate(1, 0),), "Zabezpiecz")

    feedback = _turn_options_led_feedback(BoardState(), state, hero, _source(), (scene_object,))

    object_frame = next(frame for frame in feedback.frames if Coordinate(1, 0) in frame.positions and frame.color == LedColor.INTERACTIVE_OBJECT)
    assert object_frame.positions == (Coordinate(1, 0),)


def test_turn_led_feedback_marks_enemy_and_object_tile_as_multi_option_color():
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    state = start_combat((hero, goblin), _order(hero, goblin))
    scene_object = SceneObject(
        "crate",
        "Skrzynia",
        (Coordinate(1, 0),),
        "Zabezpiecz",
        allow_interaction_when_occupied_by_enemy=True,
    )

    feedback = _turn_options_led_feedback(BoardState(), state, hero, _source(), (scene_object,))

    multi_frame = next(frame for frame in feedback.frames if Coordinate(1, 0) in frame.positions)
    assert multi_frame.color == LedColor.MULTI_OPTION_TILE
