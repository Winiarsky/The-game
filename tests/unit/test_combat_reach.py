from dnd_board_game.actors import Actor, ActorId, Faction
from dnd_board_game.combat import (
    AttackKind,
    AttackSource,
    AttackSourceType,
    InitiativeEntry,
    InitiativeOrder,
    legal_attack_targets,
    opportunity_attackers_for_movement,
    plan_enemy_turn,
    start_combat,
)
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.world import BoardState, Coordinate


def _actor(actor_id: str, faction: Faction, col: int) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id,
        ac=12,
        hp=10,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(col, 0),
        faction=faction,
    )


def _source(*, reach_feet: int = 10) -> AttackSource:
    return AttackSource(
        "Halabarda",
        AttackSourceType.WEAPON,
        reach_feet,
        D20RollRequest(),
        attack_kind=AttackKind.MELEE,
        reach_feet=reach_feet,
    )


def _state(hero: Actor, enemy: Actor):
    request = D20RollRequest()
    return start_combat(
        (enemy, hero),
        InitiativeOrder(
            (
                InitiativeEntry(enemy, resolve_d20_roll(D20RollInput(request, 20)), 0, 0),
                InitiativeEntry(hero, resolve_d20_roll(D20RollInput(request, 10)), 0, 1),
            )
        ),
    )


def test_melee_reach_controls_legal_targets() -> None:
    attacker = _actor("hero", Faction.ALLY, 0)
    near = _actor("near", Faction.ENEMY, 2)
    far = _actor("far", Faction.ENEMY, 3)

    targets = legal_attack_targets(
        BoardState(),
        attacker,
        (attacker, near, far),
        _source(),
    )

    assert [target.id for target in targets] == ["near"]


def test_opportunity_attack_triggers_only_when_target_leaves_reach() -> None:
    attacker = _actor("guard", Faction.ENEMY, 0)
    mover = _actor("hero", Faction.ALLY, 2)
    state = _state(mover, attacker)
    sources = {attacker.id: _source()}

    within_reach = opportunity_attackers_for_movement(
        state,
        mover,
        Coordinate(2, 0),
        Coordinate(1, 0),
        sources,
    )
    leaves_reach = opportunity_attackers_for_movement(
        state,
        mover,
        Coordinate(2, 0),
        Coordinate(3, 0),
        sources,
    )

    assert within_reach == ()
    assert [threat.attacker.id for threat in leaves_reach] == [attacker.id]


def test_short_ranged_attack_does_not_create_melee_threat() -> None:
    attacker = _actor("thrower", Faction.ENEMY, 0)
    mover = _actor("hero", Faction.ALLY, 1)
    state = _state(mover, attacker)
    ranged = AttackSource(
        "Krótki strzał",
        AttackSourceType.WEAPON,
        10,
        D20RollRequest(),
        attack_kind=AttackKind.RANGED,
    )

    threats = opportunity_attackers_for_movement(
        state,
        mover,
        Coordinate(1, 0),
        Coordinate(2, 0),
        {attacker.id: ranged},
    )

    assert threats == ()


def test_enemy_with_reach_stops_at_first_legal_attack_position() -> None:
    enemy = _actor("guard", Faction.ENEMY, 0)
    hero = _actor("hero", Faction.ALLY, 4)
    state = _state(hero, enemy)

    plan = plan_enemy_turn(BoardState(), state, enemy, _source())

    assert plan.movement_path is not None
    assert plan.movement_path.destination == Coordinate(2, 0)
    assert plan.movement_path.cost_feet == 10
    assert plan.target is not None
    assert plan.target.id == "hero"
