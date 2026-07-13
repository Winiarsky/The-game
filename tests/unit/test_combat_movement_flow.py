import pytest

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.application import CombatMovementFlowService
from dnd_board_game.combat import (
    ActiveCombatEffect,
    AttackSource,
    AttackSourceType,
    CombatState,
    InitiativeEntry,
    InitiativeOrder,
    start_combat,
)
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.world import BoardState, Coordinate


def _actor(actor_id: str, faction: Faction, position: Coordinate) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id.title(),
        ac=12,
        hp=10,
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


def _melee_source() -> AttackSource:
    return AttackSource("Miecz", AttackSourceType.WEAPON, 5, D20RollRequest())


def test_preview_returns_path_and_existing_observation_payload() -> None:
    service = CombatMovementFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(5, 0))

    preview = service.preview(
        state=_state(hero, goblin),
        board=BoardState(),
        destination=Coordinate(1, 0),
    )

    assert preview.path.valid
    assert preview.path.cost_feet == 5
    assert preview.event_type == "ui_combat_movement_previewed"
    assert dict(preview.event_payload) == {
        "actor_id": "hero",
        "destination": [1, 0],
        "path": [[0, 0], [1, 0]],
        "cost_feet": 5,
    }


def test_submit_applies_safe_movement_and_tracks_remaining_speed() -> None:
    service = CombatMovementFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(5, 0))

    submission = service.submit(
        state=_state(hero, goblin),
        board=BoardState(),
        attack_sources_by_actor={goblin.id: _melee_source()},
        active_effects=(),
        destination=Coordinate(1, 0),
    )

    moved = next(actor for actor in submission.state.actors if actor.id == hero.id)
    assert moved.position == Coordinate(1, 0)
    assert submission.movement_remaining_feet == 25
    assert not submission.requires_opportunity_confirmation
    assert submission.event_type == "ui_combat_player_moved"


def test_submit_exposes_opportunity_threat_without_moving() -> None:
    service = CombatMovementFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    state = _state(hero, goblin)

    submission = service.submit(
        state=state,
        board=BoardState(),
        attack_sources_by_actor={goblin.id: _melee_source()},
        active_effects=(),
        destination=Coordinate(0, 2),
    )

    unmoved = next(actor for actor in submission.state.actors if actor.id == hero.id)
    assert unmoved.position == Coordinate(0, 0)
    assert submission.requires_opportunity_confirmation
    assert submission.threat_actor_ids == ("goblin",)
    assert submission.event_type == "ui_combat_opportunity_movement_pending"


def test_disengage_allows_same_movement_without_confirmation() -> None:
    service = CombatMovementFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    disengage = ActiveCombatEffect(
        id="disengage",
        actor_id="hero",
        kind="disengage_until_turn_end",
        label="Odwrót",
        object_id="",
        value=0,
    )

    submission = service.submit(
        state=_state(hero, goblin),
        board=BoardState(),
        attack_sources_by_actor={goblin.id: _melee_source()},
        active_effects=(disengage,),
        destination=Coordinate(0, 2),
    )

    assert not submission.requires_opportunity_confirmation
    moved = next(actor for actor in submission.state.actors if actor.id == hero.id)
    assert moved.position == Coordinate(0, 2)


def test_movement_rejects_enemy_turn_and_unreachable_destination() -> None:
    service = CombatMovementFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(5, 0))

    with pytest.raises(ValueError, match="To nie jest tura bohatera"):
        service.preview(
            state=_state(goblin, hero),
            board=BoardState(),
            destination=Coordinate(4, 0),
        )

    with pytest.raises(ValueError, match="Nie można dojść do wskazanego pola"):
        service.preview(
            state=_state(hero, goblin),
            board=BoardState(),
            destination=Coordinate(19, 29),
        )
